import datetime
import discord
from discord.embeds import EmptyEmbed
from enum import Enum
from fake_useragent import UserAgent
import requests
from requests.structures import CaseInsensitiveDict
import time
from tinydb import TinyDB, Query


class EventType(Enum):
    SALE = 'sale'
    LISTING = 'listing'
    SUCCESSFUL = 'successful'
    CREATED = 'created'


class _OpenSeaTransactionObject:
    discord_embed = None

    def __init__(self, name_, image_url_, seller_, buyer_, eth_nft_price_, total_usd_cost_, link_, tx_type_,
                 image_thumbnail_url_, embed_icon_url_, rgb_color_):
        self.name = name_
        self.image_url = image_url_
        self.seller = seller_
        self.buyer = buyer_
        self.eth_nft_price = eth_nft_price_
        self.total_usd_cost = total_usd_cost_
        self.link = link_
        self.is_posted = False
        self.tx_type = tx_type_
        self.image_thumbnail_url = image_thumbnail_url_
        self.embed_icon_url = embed_icon_url_
        self.r = rgb_color_[0]
        self.g = rgb_color_[1]
        self.b = rgb_color_[2]

    def create_discord_embed(self):
        icon_url = str(self.embed_icon_url) if self.embed_icon_url != 'None' else EmptyEmbed
        embed_color = discord.Color.from_rgb(self.r, self.g, self.b)
        embed = None
        if self.tx_type == EventType.SALE.value:
            embed = discord.Embed(title=self.name, url=self.link,
                                  description='Ξ{} (${})'.format(self.eth_nft_price, self.total_usd_cost) + '\n\n' +
                                              'Seller: {}\nBuyer: {}'.format(self.seller, self.buyer),
                                  color=embed_color)
            embed.set_author(name="New Purchase!", icon_url=icon_url)
            embed.set_image(url=self.image_url)
        elif self.tx_type == EventType.LISTING.value:
            embed = discord.Embed(title=self.name, url=self.link, description='Ξ{} (${})'.format(
                self.eth_nft_price, self.total_usd_cost) + '\n\n' + 'Seller: {}'.format(self.seller),
                                  color=embed_color)
            embed.set_author(name="New Listing!", icon_url=icon_url)
            embed.set_image(url=self.image_thumbnail_url)
        self.discord_embed = embed


class _PostFromOpenSeaDiscord:
    def __init__(self, values):
        self.collection_name = values[0][0]
        self.contract_address = values[1][0]
        self.embed_icon_url = values[2][0]
        self.embed_rgb_color = values[3]
        self.os_api_key = values[4][0]
        self.os_events_url = 'https://api.opensea.io/api/v1/events'
        self.os_asset_url = 'https://api.opensea.io/api/v1/asset/'
        self.response = None
        self.os_obj_to_post = None
        self.tx_type = None
        self.tx_db = TinyDB(self.collection_name + '_tx_hash_discord_db.json')
        self.tx_db.truncate()
        self.tx_query = Query()
        self.tx_queue = []
        self.limit = 2
        self.ua = UserAgent()

    def get_recent_sales(self, tx_type):
        self.tx_type = tx_type
        if self.tx_type == EventType.SALE.value:
            event_type = EventType.SUCCESSFUL.value
        else:
            event_type = EventType.CREATED.value
        try:
            querystring = {'asset_contract_address': self.contract_address,
                           'event_type': event_type,
                           "only_opensea": 'false',
                           'offset': '0',
                           'limit': self.limit}
            headers = CaseInsensitiveDict()
            headers['Accept'] = 'application/json'
            headers['User-Agent'] = self.ua.random
            headers['x-api-key'] = self.os_api_key
            self.response = requests.request('GET', self.os_events_url, headers=headers, params=querystring)
            return self.response.status_code == 200
        except Exception as e:
            print(e, flush=True)
            return False

    def parse_response_objects(self):
        for i in range(0, self.limit):
            try:
                base = self.response.json()['asset_events'][i]
                asset = base['asset']
                name = str(asset['name'])
                image_url = asset['image_url']
                image_thumbnail_url = asset['image_thumbnail_url']
                seller_address = str(base['seller']['address'])
                buyer_address = str(asset['owner']['address'])
                usd_price = float(base['payment_token']['usd_price'])
                link = asset['permalink']
            except TypeError:
                continue
            try:
                seller = str(base['seller']['user']['username'])
                if seller == 'None':
                    seller = seller_address[0:8]
            except TypeError:
                seller = seller_address[0:8]
            try:
                buyer = str(asset['owner']['user']['username'])
                if buyer == 'None':
                    buyer = buyer_address[0:8]
            except TypeError:
                buyer = buyer_address[0:8]
            transaction = None
            if self.tx_type == EventType.SALE.value:
                if seller_address == buyer_address or seller == buyer:
                    continue
                try:
                    tx_hash = str(base['transaction']['transaction_hash'])
                except TypeError:
                    continue
                tx_exists = False if len(self.tx_db.search(self.tx_query.tx == tx_hash)) == 0 else True
                if tx_exists:
                    continue
                try:
                    price = float('{0:.5f}'.format(int(base['total_price']) / 1e18))
                    total_usd_cost = '{:.2f}'.format(round(price * usd_price, 2))
                except (ValueError, TypeError):
                    continue
                self.tx_db.insert({'tx': tx_hash})
                transaction = _OpenSeaTransactionObject(name, image_url, seller, buyer, price,
                                                        total_usd_cost, link, self.tx_type, image_thumbnail_url,
                                                        self.embed_icon_url, self.embed_rgb_color)
            elif self.tx_type == EventType.LISTING.value:
                try:
                    listing_id = str(base['id'])
                except TypeError:
                    continue
                listing_exists = False if len(
                    self.tx_db.search(self.tx_query.id == listing_id)) == 0 else True
                if listing_exists:
                    continue
                try:
                    price = float('{0:.5f}'.format(int(base['starting_price']) / 1e18))
                    total_usd_cost = '{:.2f}'.format(round(price * usd_price, 2))
                except (ValueError, TypeError):
                    continue
                self.tx_db.insert({'id': listing_id})
                transaction = _OpenSeaTransactionObject(name, image_url, seller, buyer, price, total_usd_cost, link,
                                                        self.tx_type, image_thumbnail_url, self.embed_icon_url,
                                                        self.embed_rgb_color)
            transaction.create_discord_embed()
            self.tx_queue.append(transaction)
        return self.process_queue()

    def process_queue(self):
        index = 0
        while index < len(self.tx_queue):
            cur_os_obj = self.tx_queue[index]
            if cur_os_obj.is_posted:
                self.tx_queue.pop(index)
            else:
                index += 1
        if len(self.tx_queue) == 0:
            return False
        self.os_obj_to_post = self.tx_queue[0]
        return True


class ManageFlowObj:
    def __init__(self):
        self.base_obj = None
        self.tx_type = None
        self.date_time_now = None

    def create(self, values):
        self.base_obj = _PostFromOpenSeaDiscord(values)

    def check_os_api_status(self, tx_type):
        self.date_time_now = datetime.datetime.fromtimestamp(time.time()).strftime('%m/%d/%Y %H:%M:%S')
        self.tx_type = tx_type
        os_api_working = self.base_obj.get_recent_sales(self.tx_type)
        if not os_api_working:
            print('OS API is not working at roughly', self.date_time_now, flush=True)
            return False
        else:
            return True

    def check_if_new_post_exists(self):
        new_post_exists = self.base_obj.parse_response_objects()
        if not new_post_exists:
            print('No new post at roughly', self.date_time_now, flush=True)
            return False
        else:
            return True


async def try_to_post_embed_to_discord(mfo, channel):
    try:
        await channel.send(embed=mfo.base_obj.os_obj_to_post.discord_embed)
        mfo.base_obj.os_obj_to_post.is_posted = True
        print('Posted to Discord at roughly', mfo.date_time_now, flush=True)
        return True
    except AttributeError:
        raise Exception('Channel does not exist OR I am not authorized to send messages in this channel.')
    except Exception as e:
        print(e, flush=True)
        print('Post to Discord error at roughly', mfo.date_time_now, flush=True)
        return False
