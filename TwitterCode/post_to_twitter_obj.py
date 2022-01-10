import sys
sys.path.append('../')
import datetime  # noqa: E402
from fake_useragent import UserAgent  # noqa: E402
from HelperCode import find_file  # noqa: E402
from operator import itemgetter  # noqa: E402
import requests  # noqa: E402
from requests.structures import CaseInsensitiveDict  # noqa: E402
import time  # noqa: E402
from tinydb import database, Query, TinyDB  # noqa: E402
from twython import Twython  # noqa: E402
import twython.exceptions  # noqa: E402


class _OpenSeaTransactionObject:  # an OpenSea transaction object which holds information about the object
    def __init__(self, name_, image_url_, eth_nft_price_, total_usd_cost_, link_, rare_trait_list_, twitter_tags_,
                 num_of_assets_, tx_hash_):
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

    def __eq__(self, other):
        return self.tx_hash == other.tx_hash

    def __hash__(self):
        return hash(('tx_hash', self.tx_hash))

    def create_twitter_caption(self):
        self.twitter_caption = '{} bought for Ξ{} (${})\n'.format(self.name, self.eth_nft_price, self.total_usd_cost)
        if self.num_of_assets > 1:
            self.twitter_caption = '{}\n{} assets bought for Ξ{} (${})\n'. \
                format(self.name, self.num_of_assets, self.eth_nft_price, self.total_usd_cost)
        remaining_characters = 280 - len(self.twitter_caption) - len(self.link) - len(self.twitter_tags)  # 280 is max
        # the remaining characters at this stage should roughly be 130-180 characters.
        if self.rare_trait_list:
            if remaining_characters >= 13 and len(self.rare_trait_list) != 0:  # 13... why not
                self.twitter_caption += 'Rare Traits:\n'
                full_rare_trait_sentence = ''
                for rare_trait in self.rare_trait_list:
                    next_rare_trait_sentence = '{}: {} - {}%\n'.format(rare_trait[0], rare_trait[1], str(rare_trait[2]))
                    if len(next_rare_trait_sentence) + len(full_rare_trait_sentence) > remaining_characters:
                        break
                    full_rare_trait_sentence += next_rare_trait_sentence
                self.twitter_caption += full_rare_trait_sentence
        self.twitter_caption += '\n\n' + self.link + '\n\n' + \
                                (self.twitter_tags if self.twitter_tags != 'None' else '')
        # link length and tags length are already accounted for!


class _PostFromOpenSeaTwitter:  # class which holds all operations and utilizes both OpenSea API and Twitter API
    def __init__(self, address, supply, values_file, trait_db_name, image_db_name):  # initialize all the fields
        twitter_values_file = values_file
        values = open(twitter_values_file, 'r')
        self.twitter_tags = values.readline().strip()
        self.collection_name = values.readline().strip()
        twitter_api_key = values.readline().strip()
        twitter_api_key_secret = values.readline().strip()
        twitter_access_token = values.readline().strip()
        twitter_access_token_secret = values.readline().strip()
        self.os_api_key = values.readline().strip()
        self.ether_scan_values = values.readline().strip().split()
        values.close()
        self.ether_scan_api_key = self.ether_scan_values[0]
        self.ether_scan_name = self.collection_name
        if len(self.ether_scan_values) > 1:
            self.ether_scan_name = self.ether_scan_values[1]
        self.file_name = self.collection_name + '_twitter.jpeg'
        self.contract_address = address
        self.total_supply = supply
        self.os_events_url = 'https://api.opensea.io/api/v1/events/'
        self.os_asset_url = 'https://api.opensea.io/api/v1/asset/'
        self.ether_scan_api_url = 'https://api.etherscan.io/api'
        self.response = None
        self.os_obj_to_post = None
        self.tx_db = TinyDB(self.collection_name + '_tx_hash_twitter_db.json')
        self.tx_query = Query()
        self.trait_db = None
        if trait_db_name is not None and type(trait_db_name) != bool:
            self.trait_db = TinyDB(trait_db_name)
            self.trait_query = Query()
        elif type(trait_db_name) == bool:
            self.trait_db = trait_db_name
        self.image_db = None
        if image_db_name is not None:
            self.image_db = TinyDB(image_db_name)
            self.image_query = Query()
        self.tx_queue = []
        self.os_limit = 10
        self.ether_scan_limit = int(self.os_limit * 1.5)
        self.twitter = Twython(
            twitter_api_key,
            twitter_api_key_secret,
            twitter_access_token,
            twitter_access_token_secret
        )
        self.ua = UserAgent()

    def __del__(self):
        self.twitter.client.close()

    def get_recent_sales(self):  # gets {limit} most recent sales
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
            self.response = requests.get(self.os_events_url, headers=headers, params=query_strings, timeout=3)
            return self.response.status_code == 200
        except Exception as e:
            print(e, flush=True)
            return False

    def parse_response_objects(self):  # parses {limit} objects
        if len(self.tx_queue) > 0:
            queue_has_objects = self.process_queue()  # check if there are more objects to be processed
            if queue_has_objects:  # if there are, return true and then proceed to post the object
                return True
        # otherwise, call the API again to see if there are any new objects to add to the queue
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
            if self.trait_db is not None or self.trait_db is True:
                rare_trait_list = self.create_rare_trait_list(token_id)
            transaction = _OpenSeaTransactionObject(name, image_url, eth_nft_price, total_usd_cost, link,
                                                    rare_trait_list, self.twitter_tags, 1, tx_hash)
            transaction.create_twitter_caption()
            self.tx_queue.append(transaction)
        return self.process_queue()

    def process_queue(self):  # processes the queue thus far
        if len(self.tx_db) > 200:
            for first in self.tx_db:
                self.tx_db.remove(doc_ids=[first.doc_id])
                break
        index = 0
        self.tx_queue = list(set(self.tx_queue))  # remove all duplicates (based on transaction hash)
        while index < len(self.tx_queue):
            cur_os_obj = self.tx_queue[index]  # get current object
            tx_exists = False if len(self.tx_db.search(self.tx_query.tx == str(cur_os_obj.tx_hash))) == 0 else True
            if cur_os_obj.is_posted or tx_exists:  # if object is posted or we have already seen it, pop
                self.tx_queue.pop(index)
            else:  # else move the index to the next position, which means current index is good for processing
                index += 1
        if len(self.tx_queue) == 0:
            return False
        self.os_obj_to_post = self.tx_queue[-1]
        return True

    def download_image(self):  # downloads the image to upload
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
            if type(self.trait_db) == database.TinyDB:
                asset_from_db = self.trait_db.search(self.trait_query.id == int(token_id))
                if asset_from_db:
                    traits = eval(asset_from_db[0]['traits'])
            if traits is None:
                asset_url = self.os_asset_url + self.contract_address + '/' + token_id
                asset_headers = CaseInsensitiveDict()
                asset_headers['User-Agent'] = self.ua.random
                asset_headers['x-api-key'] = self.os_api_key
                asset_response = requests.get(asset_url, headers=asset_headers, timeout=3)
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
        if len(self.tx_queue) > 0:
            queue_has_objects = self.process_queue()
            if queue_has_objects:
                return True
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
            get_tx_transfer_request = requests.get(self.ether_scan_api_url, params=tx_transfer_params, timeout=3)
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
                                                               timeout=3)
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
                get_tx_hash_request = requests.get(self.ether_scan_api_url, params=tx_hash_params, timeout=3)
                tx_details_response_base = get_tx_hash_request.json()['result']
                tx_eth_hex_value = tx_details_response_base['value']
                tx_eth_value = float(int(tx_eth_hex_value, 16) / 1e18)
                eth_price_params = {
                    'module': 'stats',
                    'action': 'ethprice',
                    'apikey': self.ether_scan_api_key
                }
                eth_price_req = requests.get(self.ether_scan_api_url, params=eth_price_params, timeout=3)
                eth_price_base = eth_price_req.json()['result']
                eth_usd_price = eth_price_base['ethusd']
                usd_nft_cost = round(float(eth_usd_price) * tx_eth_value, 2)
                input_type = tx_details_response_base['input']
                if input_type.startswith('0xab834bab'):  # this is an atomic match (check ether scan logs)
                    if tx_eth_value == 0.0:  # check if ETH value of atomic match is 0.0 -> this means it's a bid
                        tx_hash_params = {
                            'module': 'proxy',
                            'action': 'eth_getTransactionReceipt',
                            'txhash': tx_hash,
                            'apikey': self.ether_scan_api_key
                        }
                        get_tx_receipt_request = requests.get(self.ether_scan_api_url, params=tx_hash_params,
                                                              timeout=3)
                        first_log = get_tx_receipt_request.json()['result']['logs'][0]
                        data = first_log['data']  # this is the price in WETH (because its a bid)
                        if data != '0x':
                            tx_eth_value = float(int(data, 16) / 1e18)
                            usd_nft_cost = round(float(eth_usd_price) * tx_eth_value, 2)
                    name = '{} #{}'.format(self.ether_scan_name, token_id)
                    asset_link = 'https://opensea.io/assets/{}/{}'.format(self.contract_address, token_id)
                    rare_trait_list = []
                    if self.trait_db is not None or self.trait_db is True:
                        rare_trait_list = self.create_rare_trait_list(token_id)
                    image_url = None
                    if self.image_db is not None:
                        asset_from_db = self.image_db.search(self.image_query.id == int(token_id))
                        image_url = asset_from_db[0]['image_url']
                    transaction = _OpenSeaTransactionObject(name, image_url, tx_eth_value, usd_nft_cost, asset_link,
                                                            rare_trait_list, self.twitter_tags, 1, tx_hash)
                    transaction.create_twitter_caption()
                    self.tx_queue.append(transaction)
            return self.process_queue()
        except Exception as e:
            print(e, flush=True)
            return -1

    def post_to_twitter(self):  # uploads to Twitter
        try:
            if self.os_obj_to_post.image_url is None:
                self.twitter.update_status(status=self.os_obj_to_post.twitter_caption)
                self.os_obj_to_post.is_posted = True
                self.tx_db.insert({'tx': self.os_obj_to_post.tx_hash})
                return True
        except Exception as e:
            print(e, flush=True)
            return False
        image = open(self.file_name, 'rb')
        try:
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

    def delete_twitter_posts(self, count=200):  # deletes twitter posts. 200 max per call
        if count > 200:
            return False
        for i in self.twitter.get_user_timeline(count=count):
            status = int(i['id_str'])
            self.twitter.destroy_status(id=status)


class ManageFlowObj:  # Main class which does all of the operations
    def __init__(self, twitter_values_file, trait_db_name=None, image_db_name=None):
        self.twitter_values_file = twitter_values_file
        self.trait_db_name = trait_db_name
        self.image_db_name = image_db_name
        collection_stats = self.validate_params()
        cont_address = collection_stats[0]
        supply = collection_stats[1]
        self.trait_db_name = collection_stats[2]
        self.image_db_name = collection_stats[3]
        self.__base_obj = _PostFromOpenSeaTwitter(cont_address, supply, self.twitter_values_file, self.trait_db_name,
                                                  self.image_db_name)
        self._begin()

    def validate_params(self):
        print('Beginning validation of Twitter Values File...')
        if not str(self.twitter_values_file).lower().endswith('.txt'):
            raise Exception('Twitter Values must be a .txt file.')
        with open(self.twitter_values_file) as values_file:
            if len(values_file.readlines()) != 8:
                raise Exception('The Twitter Values file must be formatted correctly.')
        print('Number of lines validated.')
        values_file_test = open(self.twitter_values_file, 'r')
        hashtags_test = values_file_test.readline().strip()
        hashtags = 0
        words_in_hash_tag = hashtags_test.split()
        if hashtags_test != 'None':
            if len(hashtags_test) == 0 or hashtags_test.split() == 0:
                values_file_test.close()
                raise Exception('Hashtags field is empty.')
            if len(hashtags_test) >= 120:
                values_file_test.close()
                raise Exception('Too many characters in hashtags.')
            if len(words_in_hash_tag) > 10:
                values_file_test.close()
                raise Exception('Too many hashtags.')
            for word in words_in_hash_tag:
                if word[0] == '#':
                    hashtags += 1
            if hashtags != len(words_in_hash_tag):
                values_file_test.close()
                raise Exception('All words must be preceded by a hashtag (#).')
        print('Hashtags validated...')
        collection_name_test = values_file_test.readline().strip()
        test_collection_name_url = 'https://api.opensea.io/api/v1/collection/{}'.format(collection_name_test)
        test_response = requests.get(test_collection_name_url)
        if test_response.status_code == 200:
            collection_json = test_response.json()['collection']
            stats_json = collection_json['stats']
            total_supply = int(stats_json['total_supply'])
            primary_asset_contracts_json = collection_json['primary_asset_contracts'][0]  # got the contract address
            contract_address = primary_asset_contracts_json['address']
        else:
            values_file_test.close()
            raise Exception('The provided collection name does not exist.')
        print('Collection validated...')
        api_key = values_file_test.readline().strip()
        api_key_secret = values_file_test.readline().strip()
        access_token = values_file_test.readline().strip()
        access_token_secret = values_file_test.readline().strip()
        twitter_test = Twython(
            api_key,
            api_key_secret,
            access_token,
            access_token_secret
        )
        try:
            twitter_test.verify_credentials()
            twitter_test.client.close()
        except twython.exceptions.TwythonAuthError:
            values_file_test.close()
            twitter_test.client.close()
            raise Exception('Invalid Twitter Keys supplied.')
        print('Twitter credentials validated...')
        test_os_key = values_file_test.readline().strip()
        test_os_key_url = 'https://api.opensea.io/api/v1/events?only_opensea=false&offset=0&limit=1'
        test_os_headers = CaseInsensitiveDict()
        test_os_headers['Accept'] = 'application/json'
        test_os_headers['x-api-key'] = test_os_key
        test_os_response = requests.get(test_os_key_url, headers=test_os_headers)
        if test_os_response.status_code != 200:
            values_file_test.close()
            raise Exception('Invalid OpenSea API key supplied.')
        print('OpenSea Key validated...')
        test_ether_scan_values = values_file_test.readline().strip().split()
        test_ether_scan_key = test_ether_scan_values[0]
        test_ether_scan_url = 'https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey={}'. \
            format(test_ether_scan_key)
        test_ether_scan_response = requests.get(test_ether_scan_url)
        if test_ether_scan_response.json()['message'] == 'NOTOK':
            raise Exception('Invalid Ether Scan key.')
        print('Ether Scan key validated...')
        values_file_test.close()
        print('Validation of Twitter Values .txt complete. No errors found...')
        trait_db = self.trait_db_name
        if self.trait_db_name is not None and type(self.trait_db_name) != bool:
            if not str(self.trait_db_name).lower().endswith('.json'):
                raise Exception('Trait DB must end with a .json file extension.')
            trait_db = find_file.find(self.trait_db_name)
            if trait_db is None:
                raise Exception('Trait DB .json not found. Either type the name correctly or remove the parameter.')
            print('Validation of Trait DB Name .json complete. No errors found...')
        else:
            print('Skipping Trait DB Name .json. No file was provided.')
        image_db = self.image_db_name
        if self.image_db_name is not None:
            if not str(self.image_db_name).lower().endswith('.json'):
                raise Exception('Image DB must end with a .json file extension.')
            image_db = find_file.find(self.image_db_name)
            if image_db is None:
                raise Exception('Image DB .json not found. Either type the name correctly or remove the parameter.')
            print('Validation of Image DB Name .json complete. No errors found...')
        else:
            print('Skipping Image DB Name .json. No file was provided.')
        print('All files are validated. Beginning program...')
        return [contract_address, total_supply, trait_db, image_db]

    def run_methods(self, date_time_now):  # runs all the methods
        self.check_os_api_status(date_time_now)

    def check_os_api_status(self, date_time_now):
        os_api_working = self.__base_obj.get_recent_sales()
        if os_api_working:
            self.check_if_new_post_exists(date_time_now)
        else:
            print('OS API is not working at roughly', date_time_now, flush=True)
            print('Attempting to use Ether Scan API at roughly', date_time_now, flush=True)
            new_post_exists = self.__base_obj.process_via_ether_scan()
            if new_post_exists == -1:
                print('Error processing via Ether Scan API at roughly', date_time_now, flush=True)
                time.sleep(30)
            elif new_post_exists:
                image_downloaded = self.__base_obj.download_image()
                if image_downloaded:
                    self.try_to_post_to_twitter(date_time_now)
                else:
                    print('Downloading image error at roughly', date_time_now, flush=True)
                    time.sleep(10)
            else:
                print('No new post at roughly', date_time_now, flush=True)
                time.sleep(5)

    def check_if_new_post_exists(self, date_time_now):
        new_post_exists = self.__base_obj.parse_response_objects()
        if new_post_exists:
            self.try_to_download_image(date_time_now)
        else:
            print('No new post at roughly', date_time_now, flush=True)
            time.sleep(5)

    def try_to_download_image(self, date_time_now):
        image_downloaded = self.__base_obj.download_image()
        if image_downloaded:
            self.try_to_post_to_twitter(date_time_now)
        else:
            print('Downloading image error at roughly', date_time_now, flush=True)
            time.sleep(10)

    def try_to_post_to_twitter(self, date_time_now):
        posted_to_twitter = self.__base_obj.post_to_twitter()
        if posted_to_twitter:
            print('Posted to Twitter at roughly', date_time_now, flush=True)
            time.sleep(5)
        else:
            print('Post to Twitter error at roughly', date_time_now, flush=True)
            time.sleep(15)

    def _begin(self):  # begin program!
        while True:
            date_time_now = datetime.datetime.fromtimestamp(time.time()).strftime('%m/%d/%Y %H:%M:%S')
            self.run_methods(date_time_now)
