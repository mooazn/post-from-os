import datetime
from fake_useragent import UserAgent
from operator import itemgetter
import requests
from requests.structures import CaseInsensitiveDict
import time
from tinydb import TinyDB, Query
from twython import Twython


class _OpenSeaTransactionObject:
    def __init__(self, name_, image_url_, eth_nft_price_, total_usd_cost_, link_, rare_trait_list_,
                 twitter_tags_, num_of_assets_, tx_hash_):
        self.twitter_caption = None
        self.name = name_
        self.image_url = image_url_
        self.eth_nft_price = eth_nft_price_
        self.total_usd_cost = total_usd_cost_
        self.link = link_
        self.is_posted = False
        self.rare_trait_list = rare_trait_list_
        self.twitter_tags = twitter_tags_
        self.num_of_assets = num_of_assets_
        self.tx_hash = tx_hash_

    def create_twitter_caption(self):
        self.twitter_caption = '{} bought for Ξ{} (${})\n'.format(self.name, self.eth_nft_price, self.total_usd_cost)
        if self.num_of_assets > 1:
            self.twitter_caption = '{}\n{} assets bought for Ξ{} (${})\n'.\
                format(self.name, self.num_of_assets, self.eth_nft_price, self.total_usd_cost)
        stringed_twitter_tags = " ".join(self.twitter_tags)
        remaining_characters = 280 - len(self.twitter_caption) - len(self.link) - len(stringed_twitter_tags)
        if self.rare_trait_list:
            if remaining_characters >= 13 and len(self.rare_trait_list) != 0:
                self.twitter_caption += 'Rare Traits:\n'
                full_rare_trait_sentence = ''
                for rare_trait in self.rare_trait_list:
                    next_rare_trait_sentence = '{}: {} - {}%\n'.format(rare_trait[0], rare_trait[1], str(rare_trait[2]))
                    if len(next_rare_trait_sentence) + len(full_rare_trait_sentence) > remaining_characters:
                        break
                    full_rare_trait_sentence += next_rare_trait_sentence
                self.twitter_caption += full_rare_trait_sentence
        self.twitter_caption += '\n\n' + self.link + '\n\n' + \
                                (stringed_twitter_tags if stringed_twitter_tags != 'None' else '')


class _PostFromOpenSeaTwitter:
    def __init__(self, values):
        self.twitter_tags = values[0]
        self.collection_name = values[1]
        self.collection_stats = values[2]
        self.twitter_keys = values[3]
        self.os_api_key = values[4]
        self.ether_scan_api_key = values[5]
        self.collection_name_for_ether_scan = values[6]
        self.collection_needs_traits = values[7]
        self.file_name = self.collection_name + '_twitter_asynchronous.jpeg'
        self.total_supply = self.collection_stats[0]
        self.contract_address = self.collection_stats[1]
        self.os_events_url = 'https://api.opensea.io/api/v1/events/'
        self.os_asset_url = 'https://api.opensea.io/api/v1/asset/'
        self.ether_scan_api_url = 'https://api.etherscan.io/api'
        self.response = None
        self.os_obj_to_post = None
        self.tx_db = TinyDB(self.collection_name + '_tx_hash_twitter_db_asynchronous.json')
        self.tx_query = Query()
        self.tx_queue = []
        self.os_limit = 5
        self.ether_scan_limit = int(self.os_limit * 1.5)
        self.twitter = Twython(
            self.twitter_keys[0],
            self.twitter_keys[1],
            self.twitter_keys[2],
            self.twitter_keys[3]
        )
        self.ua = UserAgent()

    def __del__(self):
        self.twitter.client.close()

    def get_recent_sales(self):  # gets {limit} most recent sales
        if self.os_api_key == 'None':
            return False
        try:
            query_strings = {
                'asset_contract_address': self.contract_address,
                'event_type': 'successful',
                'only_opensea': 'false',
                'offset': 0,
                'limit': self.os_limit
            }
            headers = CaseInsensitiveDict()
            headers['Accept'] = 'application/json'
            headers['User-Agent'] = self.ua.random
            headers['x-api-key'] = self.os_api_key
            self.response = requests.get(self.os_events_url, headers=headers, params=query_strings, timeout=1)
            return self.response.status_code == 200
        except Exception as e:
            print(e, flush=True)
            return False

    def parse_response_objects(self):
        if len(self.tx_queue) > 0:
            queue_has_objects = self.process_queue()
            if queue_has_objects:
                return True
        for i in range(0, self.os_limit):
            try:
                try:
                    base = self.response.json()['asset_events'][i]
                except IndexError:
                    continue
                tx_hash = str(base['transaction']['transaction_hash'])
                tx_exists = False if len(self.tx_db.search(self.tx_query.tx == tx_hash)) == 0 else True
                if tx_exists:
                    continue
                if base['asset_bundle'] is not None:
                    bundle = base['asset_bundle']
                    image_url = bundle['asset_contract']['collection']['large_image_url']
                    eth_nft_price = float('{0:.5f}'.format(int(base['total_price']) / 1e18))
                    usd_price = float(base['payment_token']['usd_price'])
                    total_usd_cost = '{:.2f}'.format(round(eth_nft_price * usd_price, 2))
                    link = bundle['permalink']
                    name = bundle['name']
                    num_of_assets = len(bundle['assets'])
                    transaction = _OpenSeaTransactionObject(name, image_url, eth_nft_price, total_usd_cost, link, [],
                                                            self.twitter_tags, num_of_assets, tx_hash)
                    transaction.create_twitter_caption()
                    self.tx_queue.append(transaction)
                    continue
                asset = base['asset']
                name = str(asset['name'])
                image_url = asset['image_url']
            except TypeError:
                continue
            try:
                token_id = asset['token_id']
                eth_nft_price = float('{0:.5f}'.format(int(base['total_price']) / 1e18))
                usd_price = float(base['payment_token']['usd_price'])
                total_usd_cost = '{:.2f}'.format(round(eth_nft_price * usd_price, 2))
                link = asset['permalink']
            except (ValueError, TypeError):
                continue
            rare_trait_list = []
            if self.collection_needs_traits:
                rare_trait_list = self.create_rare_trait_list(token_id)
            transaction = _OpenSeaTransactionObject(name, image_url, eth_nft_price, total_usd_cost, link,
                                                    rare_trait_list, self.twitter_tags, 1, tx_hash)
            transaction.create_twitter_caption()
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
        self.os_obj_to_post = self.tx_queue[-1]
        return True

    def download_image(self):
        if self.os_obj_to_post.image_url is None:
            return True
        img = open(self.file_name, 'wb')
        try:
            img_response = requests.get(self.os_obj_to_post.image_url, stream=True, timeout=3)
            img.write(img_response.content)
            img.close()
            return True
        except Exception as e:
            img.close()
            print(e, flush=True)
            return False

    def create_rare_trait_list(self, token_id):
        try:
            rare_trait_list = []
            traits = None
            asset_url = self.os_asset_url + self.contract_address + '/' + token_id
            asset_headers = CaseInsensitiveDict()
            asset_headers['User-Agent'] = self.ua.random
            asset_headers['x-api-key'] = self.os_api_key
            asset_response = requests.get(asset_url, headers=asset_headers, timeout=1.5)
            if asset_response.status_code == 200:
                traits = asset_response.json()['traits']
            if traits is None:
                return
            for trait in traits:
                trait_type = trait['trait_type']
                trait_value = trait['value']
                trait_count = trait['trait_count']
                rarity_decimal = float(trait_count / self.total_supply)
                if rarity_decimal <= 0.05:
                    rare_trait_list.append([trait_type, trait_value, round(rarity_decimal * 100, 2)])
            rare_trait_list.sort(key=itemgetter(2))
            return rare_trait_list
        except Exception as e:
            print(e, flush=True)
            return

    def process_via_ether_scan(self):
        try:
            tx_transfer_params = {
                'module': 'account',
                'action': 'tokennfttx',
                'contractaddress': self.contract_address,
                'startblock': 0,
                'endblock': 999999999,
                'sort': 'desc',
                'apikey': self.ether_scan_api_key,
                'page': 1,
                'offset': self.ether_scan_limit
            }
            get_tx_transfer_request = requests.get(self.ether_scan_api_url, params=tx_transfer_params, timeout=1.5)
            tx_response = get_tx_transfer_request.json()
            for i in range(0, self.ether_scan_limit):
                tx_response_base = tx_response['result'][i]
                token_id = tx_response_base['tokenID']
                tx_hash = str(tx_response_base['hash'])
                tx_exists = False if len(self.tx_db.search(self.tx_query.tx == tx_hash)) == 0 else True
                if tx_exists:
                    continue
                if i + 1 != self.ether_scan_limit:  # check if next tx has is same as this one's
                    next_tx_hash = str(tx_response['result'][i + 1]['hash'])
                    if tx_hash == next_tx_hash:
                        continue
                else:  # if we are at the end of the list: fetch the api again, increase offset by 1, and check if same
                    tx_transfer_params['offset'] += 1
                    get_new_tx_transfer_request = requests.get(self.ether_scan_api_url, params=tx_transfer_params,
                                                               timeout=1.5)
                    new_tx_response = get_new_tx_transfer_request.json()
                    next_tx_transfer_hash = str(new_tx_response['result'][i + 1]['hash'])
                    if tx_hash == next_tx_transfer_hash:
                        continue
                from_address = tx_response_base['from']
                if from_address == '0x0000000000000000000000000000000000000000':  # this is a mint, NOT a buy!!!
                    continue
                tx_hash_params = {
                    'module': 'proxy',
                    'action': 'eth_getTransactionByHash',
                    'txhash': tx_hash,
                    'apikey': self.ether_scan_api_key
                }
                get_tx_hash_request = requests.get(self.ether_scan_api_url, params=tx_hash_params, timeout=1.5)
                tx_details_response_base = get_tx_hash_request.json()['result']
                tx_eth_hex_value = tx_details_response_base['value']
                tx_eth_value = float(int(tx_eth_hex_value, 16) / 1e18)
                eth_price_params = {
                    'module': 'stats',
                    'action': 'ethprice',
                    'apikey': self.ether_scan_api_key
                }
                eth_price_req = requests.get(self.ether_scan_api_url, params=eth_price_params, timeout=1.5)
                eth_price_base = eth_price_req.json()['result']
                eth_usd_price = eth_price_base['ethusd']
                usd_nft_cost = round(float(eth_usd_price) * tx_eth_value, 2)
                input_type = tx_details_response_base['input']
                if input_type.startswith('0xab834bab'):  # this is an atomic match! (check ether scan logs)
                    if tx_eth_value == 0.0:  # check if ETH value of atomic match is 0.0 -> this means it's a bid!
                        tx_hash_params = {
                            'module': 'proxy',
                            'action': 'eth_getTransactionReceipt',
                            'txhash': tx_hash,
                            'apikey': self.ether_scan_api_key
                        }
                        get_tx_receipt_request = requests.get(self.ether_scan_api_url, params=tx_hash_params,
                                                              timeout=1.5)
                        first_log = get_tx_receipt_request.json()['result']['logs'][0]
                        data = first_log['data']
                        if data != '0x':
                            tx_eth_value = float(int(data, 16) / 1e18)
                            usd_nft_cost = round(float(eth_usd_price) * tx_eth_value, 2)
                    name = '{} #{}'.format(self.collection_name_for_ether_scan, token_id)
                    asset_link = 'https://opensea.io/assets/{}/{}'.format(self.contract_address, token_id)
                    rare_trait_list = []
                    if self.collection_needs_traits:
                        rare_trait_list = self.create_rare_trait_list(token_id)
                    transaction = _OpenSeaTransactionObject(name, None, tx_eth_value, usd_nft_cost, asset_link,
                                                            rare_trait_list, self.twitter_tags, 1, tx_hash)
                    transaction.create_twitter_caption()
                    self.tx_queue.append(transaction)
            return self.process_queue()
        except Exception as e:
            print(e, flush=True)
            return -1

    def post_to_twitter(self):
        image = open(self.file_name, 'rb')
        try:
            if self.os_obj_to_post.image_url is None:
                self.twitter.update_status(status=self.os_obj_to_post.twitter_caption)
                self.os_obj_to_post.is_posted = True
                return True
            response = self.twitter.upload_media(media=image)
            image.close()
            media_id = [response['media_id']]
            self.twitter.update_status(status=self.os_obj_to_post.twitter_caption, media_ids=media_id)
            self.os_obj_to_post.is_posted = True
            self.tx_db.insert({'tx': self.os_obj_to_post.tx_hash})
            return True
        except Exception as e:
            image.close()
            print(e, flush=True)
            return False

    def delete_twitter_posts(self, count=200):
        if count > 200:
            return False
        for i in self.twitter.get_user_timeline(count=count):
            status = int(i['id_str'])
            self.twitter.destroy_status(id=status)


class ManageFlowObj:
    def __init__(self, values):
        self.__base_obj = _PostFromOpenSeaTwitter(values)
        self.date_time_now = None

    def check_os_api_status(self):
        self.date_time_now = datetime.datetime.fromtimestamp(time.time()).strftime('%m/%d/%Y %H:%M:%S')
        os_api_working = self.__base_obj.get_recent_sales()
        if not os_api_working:
            print('OS API is not working at roughly', self.date_time_now, flush=True)
            return False
        else:
            return True

    def check_ether_scan_api_status(self):
        print('Attempting to use Ether Scan API at roughly', self.date_time_now, flush=True)
        new_post_exists = self.__base_obj.process_via_ether_scan()
        if new_post_exists == -1:
            print('Error processing via Ether Scan API at roughly', self.date_time_now, flush=True)
            return -1
        elif new_post_exists:
            return True
        else:
            print('No new post at roughly', self.date_time_now, flush=True)
            return False

    def check_if_new_post_exists(self):
        new_post_exists = self.__base_obj.parse_response_objects()
        if not new_post_exists:
            print('No new post at roughly', self.date_time_now, flush=True)
            return False
        else:
            return True

    def try_to_download_image(self):
        image_downloaded = self.__base_obj.download_image()
        if not image_downloaded:
            print('Downloading image error at roughly', self.date_time_now, flush=True)
            return False
        else:
            return True

    def try_to_post_to_twitter(self):
        posted_to_twitter = self.__base_obj.post_to_twitter()
        if posted_to_twitter:
            print('Posted to Twitter at roughly', self.date_time_now, flush=True)
            return True
        else:
            print('Post to Twitter error at roughly', self.date_time_now, flush=True)
            return False
