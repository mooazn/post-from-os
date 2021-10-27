import asyncio
import datetime
import discord
import requests
import time
from tinydb import TinyDB, Query


class _OpenSeaTransactionObject:
    discord_message = None

    def __init__(self, name_, image_url_, seller_, buyer_, eth_nft_price_, usd_price_, total_usd_cost_, the_date_,
                 the_time_, link_, listing_id_, tx_type_):
        self.name = name_
        self.image_url = image_url_
        self.seller = seller_
        self.buyer = buyer_
        self.eth_nft_price = eth_nft_price_
        self.usd_price = usd_price_
        self.total_usd_cost = total_usd_cost_
        self.the_date = the_date_
        self.the_time = the_time_
        self.link = link_
        self.is_posted = False
        self.listing_id = listing_id_
        self.tx_type = tx_type_

    def create_discord_message(self):
        pass


class _PostFromOpenSeaDiscord:
    def __init__(self, db):
        tx_db = db
        self.contract_address = 'contract'
        self.os_events_url = 'https://api.opensea.io/api/v1/events'
        self.response = None
        self.os_obj_to_post = None
        self.driver = None
        self.tx_type = None
        self.tx_db = TinyDB(tx_db)
        self.tx_db.truncate()
        self.tx_query = Query()
        self.tx_queue = []
        self.limit = 10

    def get_recent_sales(self, tx_type):
        self.tx_type = tx_type
        if self.tx_type == 'sale':
            event_type = 'successful'
        else:
            event_type = 'created'
        try:
            querystring = {'asset_contract_address': self.contract_address,
                           'event_type': event_type,
                           "only_opensea": 'false',
                           'offset': '0',
                           'limit': self.limit}
            headers = {'Accept': 'application/json'}
            self.response = requests.request('GET', self.os_events_url, headers=headers, params=querystring)
            return self.response.status_code == 200
        except Exception as e:
            print(e, flush=True)
            return False

    def parse_response_objects(self):
        for i in range(0, self.limit):
            try:
                base = self.response.json()['asset_events'][i]
            except TypeError:
                continue
            asset = base['asset']
            try:
                name = str(asset['name'])
            except TypeError:
                continue
            try:
                image_url = asset['image_url']
                seller_address = str(base['seller']['address'])
                buyer_address = str(asset['owner']['address'])
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
            usd_price = float(base['payment_token']['usd_price'])
            link = asset['permalink']
            if self.tx_type == 'sale':
                if seller_address == buyer_address or seller == buyer:
                    continue
                tx_hash = str(base['transaction']['transaction_hash'])
                tx_exists = False if len(self.tx_db.search(self.tx_query.tx == tx_hash)) == 0 else True
                if tx_exists:
                    continue
                self.tx_db.insert({'tx': tx_hash})
                price = float('{0:.5f}'.format(int(base['total_price']) / 1e18))
                timestamp = str(base['transaction']['timestamp']).split('T')
                date = datetime.datetime.strptime(timestamp[0], '%Y-%m-%d')
                month = datetime.date(date.year, date.month, date.day).strftime('%B')
                year = str(date.year)
                day = str(date.day)
                the_date = month + ' ' + day + ', ' + year
                the_time = timestamp[1]
                total_usd_cost = '{:.2f}'.format(round(price * usd_price, 2))
                transaction = _OpenSeaTransactionObject(name, image_url, seller, buyer, price, usd_price,
                                                        total_usd_cost, the_date, the_time, link, None, self.tx_type)
            else:
                listing_id = str(base['id'])
                price = float('{0:.5f}'.format(int(base['starting_price']) / 1e18))
                total_usd_cost = '{:.2f}'.format(round(price * usd_price, 2))
                listing_exists = False if len(
                    self.tx_db.search(self.tx_query.id == listing_id)) == 0 else True
                if listing_exists:
                    continue
                self.tx_db.insert({'id': listing_id})
                transaction = _OpenSeaTransactionObject(name, image_url, seller, buyer, price, usd_price,
                                                        total_usd_cost, None, None, link, listing_id, self.tx_type)
            transaction.create_discord_message()
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
    def __init__(self, db_name):
        self.__base_obj = _PostFromOpenSeaDiscord(db_name)
        self.tx_type = None

    def check_os_api_status(self, date_time_now, tx_type):
        self.tx_type = tx_type
        os_api_working = self.__base_obj.get_recent_sales(self.tx_type)
        if not os_api_working:
            print('OS API is not working at roughly', date_time_now, flush=True)
            return False
        else:
            return True

    def check_if_new_post_exists(self, date_time_now):
        new_post_exists = self.__base_obj.parse_response_objects()
        if not new_post_exists:
            print('No new post at roughly', date_time_now, flush=True)
            return False
        else:
            return True

    def try_to_post_to_discord(self):
        self.__base_obj.os_obj_to_post.is_posted = True
        if self.tx_type == 'sale':
            embed = discord.Embed(title=self.__base_obj.os_obj_to_post.name, url=self.__base_obj.os_obj_to_post.link,
                                  description='Ξ{} (${})'.format(self.__base_obj.os_obj_to_post.eth_nft_price,
                                                                 self.__base_obj.os_obj_to_post.total_usd_cost) + '\n\n'
                                  + 'Seller: {}\nBuyer: {}'.format(self.__base_obj.os_obj_to_post.seller,
                                                                   self.__base_obj.os_obj_to_post.buyer),
                                  color=0xf50505)

            embed.set_author(name="New Purchase!",
                             icon_url="icon url")
            embed.set_image(url=self.__base_obj.os_obj_to_post.image_url)
        else:
            embed = discord.Embed(title=self.__base_obj.os_obj_to_post.name, url=self.__base_obj.os_obj_to_post.link,
                                  description='Ξ{} (${})'.format(self.__base_obj.os_obj_to_post.eth_nft_price,
                                                                 self.__base_obj.os_obj_to_post.total_usd_cost) + '\n\n'
                                              + 'Seller: {}'.format(self.__base_obj.os_obj_to_post.seller),
                                  color=0xf50505)

            embed.set_author(name="New Listing!",
                             icon_url="icon url")
            embed.set_image(url=self.__base_obj.os_obj_to_post.image_url)
        return embed


client = discord.Client()
mfo = ManageFlowObj('sales_db.json')
mfo2 = ManageFlowObj('listings_db.json')


@client.event
async def on_ready():
    print('Logged in...')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

#     if message.content.startswith('$hello'):
#         await message.channel.send('Hello!')


async def process_sales():
    await client.wait_until_ready()
    channel = client.get_channel(123)
    while not client.is_closed():
        date_time_now = datetime.datetime.fromtimestamp(time.time()).strftime('%m/%d/%Y %H:%M:%S')
        status = mfo.check_os_api_status(date_time_now, 'sale')
        if status:
            exists = mfo.check_if_new_post_exists(date_time_now)
            if exists:
                result = mfo.try_to_post_to_discord()
                await channel.send(embed=result)
                print('Posted to discord at roughly', date_time_now, flush=True)
                await asyncio.sleep(5)
            else:
                await asyncio.sleep(5)
        else:
            await asyncio.sleep(30)


async def process_listings():
    await client.wait_until_ready()
    channel = client.get_channel(123)
    while not client.is_closed():
        date_time_now = datetime.datetime.fromtimestamp(time.time()).strftime('%m/%d/%Y %H:%M:%S')
        status = mfo2.check_os_api_status(date_time_now, 'listing')
        if status:
            exists = mfo2.check_if_new_post_exists(date_time_now)
            if exists:
                result = mfo2.try_to_post_to_discord()
                await channel.send(embed=result)
                print('Posted to discord at roughly', date_time_now, flush=True)
                await asyncio.sleep(5)
            else:
                await asyncio.sleep(5)
        else:
            await asyncio.sleep(30)


client.loop.create_task(process_sales())
client.loop.create_task(process_listings())
client.run('token')
