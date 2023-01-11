import sys
sys.path.append('../')
import datetime  # noqa: E402
from fake_useragent import UserAgent  # noqa: E402
from HelperCode import find_file  # noqa: E402
from Logs.logger import Logger, info, error, fatal  # noqa: E402
from operator import itemgetter  # noqa: E402
import requests  # noqa: E402
from requests.structures import CaseInsensitiveDict  # noqa: E402
import time  # noqa: E402
from tinydb import database, Query, TinyDB  # noqa: E402
from twython import Twython  # noqa: E402
import twython.exceptions  # noqa: E402


class _OpenSeaTransactionObject:  # an OpenSea transaction object which holds information about the object
    def __init__(self, name_, image_url_, nft_price_, total_usd_cost_, link_, rare_trait_list_, twitter_tags_,
                 num_of_assets_, key_, tx_hash_, symbol_, logger, logger_junk):
        self.LOGGER = logger
        self.LOGGER_JUNK = logger_junk
        self.twitter_caption = None
        self.name = name_
        self.image_url = image_url_
        self.nft_price = nft_price_
        self.total_usd_cost = total_usd_cost_
        self.link = link_
        self.is_posted = False
        self.rare_trait_list = rare_trait_list_
        self.twitter_tags = twitter_tags_
        self.num_of_assets = num_of_assets_
        self.key = key_
        self.tx_hash = tx_hash_
        self.symbol = symbol_
        self.LOGGER_JUNK.write_log(info(), 'Successfully created an OpenSea transaction object.')

    def __eq__(self, other):
        return self.key == other.key

    def __hash__(self):
        return hash(('key', self.key))

    def create_twitter_caption(self):
        self.twitter_caption = '{} bought for {} {} (${})\n'.format(self.name, self.nft_price, self.symbol,
                                                                    self.total_usd_cost)
        if self.num_of_assets > 1:
            self.twitter_caption = '{}\n{} assets bought for {} {} (${})\n'. \
                format(self.name, self.num_of_assets, self.nft_price, self.symbol, self.total_usd_cost)
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
        # link length and tags length are already accounted for!
        self.twitter_caption += '\n\n' + self.link + '\n\n' + (self.twitter_tags if self.twitter_tags != 'None' else '')
        self.LOGGER_JUNK.write_log(info(), f'Successfully created a Twitter caption = {self.twitter_caption.strip()}')


class _PostFromOpenSeaTwitter:  # class which holds all operations and utilizes both OpenSea API and Twitter API
    def __init__(self, address, supply, values_file, trait_db_name, image_db_name, logger, logger_junk):
        self.LOGGER = logger
        self.LOGGER_JUNK = logger_junk
        twitter_values_file = values_file
        values = open(twitter_values_file, 'r')
        self.twitter_tags = values.readline().strip()
        self.collection_name = values.readline().strip()
        self.LOGGER.write_log(info(), 'Inside of __init__ function in _PostFromOpenSeaTwitter in '
                                      'post_to_twitter_obj.py. Creating a base object for the '
                                      f'\'{self.collection_name}\' collection...')
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
        self.looks_rare_api_url = 'https://api.looksrare.org/api/v1/events?type=SALE'
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
        self.LOGGER.write_log(info(), f'Successfully created a base object for the \'{self.collection_name}\' '
                                      f'collection...')

    def __del__(self):
        self.twitter.client.close()
        self.LOGGER.write_log(info(), 'Twitter client has been closed. Cannot post to Twitter anymore.')

    def get_recent_sales(self):  # gets {limit} most recent sales
        try:
            query_strings = {
                'asset_contract_address': self.contract_address,
                'event_type': 'successful',
                'only_opensea': 'false'
            }
            headers = CaseInsensitiveDict()
            headers['Accept'] = 'application/json'
            headers['User-Agent'] = self.ua.random
            headers['x-api-key'] = self.os_api_key
            self.LOGGER_JUNK.write_log(info(), f'Sending a request to OpenSea at {self.os_events_url} with '
                                               f'params = {query_strings} and headers = {headers}')
            self.response = requests.get(self.os_events_url, headers=headers, params=query_strings, timeout=3)
            return self.response.status_code == 200
        except Exception as e:
            self.LOGGER.write_log(error(), f'Encountered Exception inside of get_recent sales: {e}.')
            return False

    def parse_response_objects(self):  # parses {limit} objects
        for i in range(0, self.os_limit):
            try:
                try:
                    base = self.response.json()['asset_events'][i]
                except IndexError as ie:
                    self.LOGGER.write_log(error(), f'Encountered IndexError at iteration {i}: {ie} Here is how the '
                                                   f"response looks = {self.response.json()['asset_events']}")
                    continue
                tx_hash = str(base['transaction']['transaction_hash'])
                key = tx_hash
                if base['asset_bundle'] is not None:
                    tx_exists = False if len(self.tx_db.search(self.tx_query.tx == key)) == 0 else True
                    if tx_exists:
                        continue
                    bundle = base['asset_bundle']
                    image_url = bundle['asset_contract']['image_url']
                    decimals = int(base['payment_token']['decimals'])
                    symbol = base['payment_token']['symbol']
                    nft_price = float('{0:.5f}'.format(int(base['total_price']) / (1 * 10 ** decimals)))
                    usd_price = float(base['payment_token']['usd_price'])
                    total_usd_cost = '{:.2f}'.format(round(nft_price * usd_price, 2))
                    link = bundle['permalink']
                    name = bundle['name']
                    num_of_assets = len(bundle['assets'])
                    self.LOGGER_JUNK.write_log(info(), 'A unique bundle sale has been found. Creating '
                                                       'transaction object...')
                    transaction = _OpenSeaTransactionObject(name, image_url, nft_price, total_usd_cost, link, [],
                                                            self.twitter_tags, num_of_assets, key, tx_hash, symbol,
                                                            self.LOGGER, self.LOGGER_JUNK)
                    transaction.create_twitter_caption()
                    self.tx_queue.append(transaction)
                    self.LOGGER_JUNK.write_log(info(), 'Transaction object created with a Twitter caption and appended '
                                                       'to the transaction queue.')
                    continue
                asset = base['asset']
                name = str(asset['name'])
                image_url = asset['image_url']
            except TypeError as te:
                self.LOGGER.write_log(error(), f'Encountered TypeError at iteration {i}: {te} Here is how the response '
                                               f"looks = {self.response.json()['asset_events']}")
                continue
            try:
                token_id = asset['token_id']
                key = tx_hash + ' ' + token_id
                tx_exists = False if len(self.tx_db.search(self.tx_query.tx == key)) == 0 else True
                if tx_exists:
                    continue
                decimals = int(base['payment_token']['decimals'])
                symbol = base['payment_token']['symbol']
                nft_price = float('{0:.5f}'.format(int(base['total_price']) / (1 * 10 ** decimals)))
                usd_price = float(base['payment_token']['usd_price'])
                total_usd_cost = '{:.2f}'.format(round(nft_price * usd_price, 2))
                link = asset['permalink']
            except (ValueError, TypeError) as ve_te:
                self.LOGGER.write_log(error(), f'Encountered ValueError or TypeError at iteration {i}: {ve_te} '
                                               f'Here is how "the response looks = '
                                               f"{self.response.json()['asset_events']}")
                continue
            rare_trait_list = []
            if self.trait_db is not None or self.trait_db is True:
                self.LOGGER_JUNK.write_log(info(), 'Traits requested, generating rare trait list for the sale...')
                rare_trait_list = self.create_rare_trait_list(token_id)
            self.LOGGER_JUNK.write_log(info(), 'A unique sale has been found found. Creating transaction object...')
            transaction = _OpenSeaTransactionObject(name, image_url, nft_price, total_usd_cost, link,
                                                    rare_trait_list, self.twitter_tags, 1, key, tx_hash, symbol,
                                                    self.LOGGER, self.LOGGER_JUNK)
            transaction.create_twitter_caption()
            self.tx_queue.append(transaction)
            self.LOGGER_JUNK.write_log(info(), 'Transaction object created with a Twitter caption and appended to '
                                               'the transaction queue.')
        self.LOGGER_JUNK.write_log(info(), 'Finished iterating through all of the objects in parse_response_objects.')
        return self.process_queue()

    def process_queue(self):  # processes the queue thus far
        if len(self.tx_db) > 500:
            for first in self.tx_db:
                self.tx_db.remove(doc_ids=[first.doc_id])
                break
        index = 0
        self.LOGGER_JUNK.write_log(info(), f'Size of tx_queue before removing duplicates: {len(self.tx_queue)}')
        self.tx_queue = list(set(self.tx_queue))  # remove all duplicates (based on transaction hash & token_id)
        self.LOGGER_JUNK.write_log(info(), f'Size of tx_queue after removing duplicates: {len(self.tx_queue)}')
        self.LOGGER_JUNK.write_log(info(), f'Size of tx_queue before removing posted objects: {len(self.tx_queue)}')
        while index < len(self.tx_queue):
            cur_os_obj = self.tx_queue[index]  # get current object
            tx_exists = False if len(self.tx_db.search(self.tx_query.tx == str(cur_os_obj.key))) == 0 else True
            if cur_os_obj.is_posted or tx_exists:  # if object is posted or we have already seen it, pop
                self.tx_queue.pop(index)
            else:  # else move the index to the next position, which means current index is good for processing
                index += 1
        self.LOGGER_JUNK.write_log(info(), f'Size of tx_queue after removing posted objects: {len(self.tx_queue)}')
        self.LOGGER_JUNK.write_log(info(), 'Finished processing queue in process_queue.')
        if len(self.tx_queue) == 0:
            return False
        self.os_obj_to_post = self.tx_queue[-1]
        return True

    def download_image(self):  # downloads the image to upload
        if self.os_obj_to_post.image_url is None:
            self.LOGGER_JUNK.write_log(info(), 'Image URL might not have been generated or collected if processed via'
                                               'Ether Scan. This post will upload without an image.')
            return True
        img = open(self.file_name, 'wb')
        try:
            self.LOGGER_JUNK.write_log(info(), f'Attempting to download image. Sending request with stream=True...')
            img_response = requests.get(self.os_obj_to_post.image_url, stream=True, timeout=3)
            img.write(img_response.content)
            img.close()
            return True
        except Exception as e:
            img.close()
            self.LOGGER.write_log(error(), f'Encountered Exception inside of download_image: {e} Here is the image '
                                           f'url: {self.os_obj_to_post.image_url}')
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
                self.LOGGER_JUNK.write_log(info(), f'Sending a request to OpenSea at {asset_url} with asset_headers = '
                                                   f'{asset_headers}')
                asset_response = requests.get(asset_url, headers=asset_headers, timeout=3)
                if asset_response.status_code == 200:
                    traits = asset_response.json()['traits']
            if traits is None:
                self.LOGGER_JUNK.write_log(error(), 'Traits could not be generated at this time for the object.')
                return
            for trait in traits:
                trait_type = trait['trait_type']
                trait_value = trait['value']
                trait_count = trait['trait_count']
                rarity_decimal = float(trait_count / self.total_supply)
                if rarity_decimal <= 0.05:
                    rare_trait_list.append([trait_type, trait_value, round(rarity_decimal * 100, 2)])
            rare_trait_list.sort(key=itemgetter(2))
            self.LOGGER_JUNK.write_log(info(), f'Rare trait list generated = {rare_trait_list}')
            return rare_trait_list
        except Exception as e:
            self.LOGGER.write_log(error(), f'Encountered Exception inside of create_rare_trait_list: {e}')
            return

    def process_via_ether_scan(self):
        try:
            eth_price_params = {
                'module': 'stats',
                'action': 'ethprice',
                'apikey': self.ether_scan_api_key
            }
            self.LOGGER_JUNK.write_log(info(), f'Sending a request to EtherScan at {self.ether_scan_api_url} '
                                               f'with params = {eth_price_params}')
            eth_price_req = requests.get(self.ether_scan_api_url, params=eth_price_params, timeout=3)
            eth_price_base = eth_price_req.json()['result']
            eth_usd_price = eth_price_base['ethusd']
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
            self.LOGGER_JUNK.write_log(info(), f'Sending a request to EtherScan at {self.ether_scan_api_url} '
                                               f'with params = {tx_transfer_params}')
            get_tx_transfer_request = requests.get(self.ether_scan_api_url, params=tx_transfer_params, timeout=3)
            tx_response = get_tx_transfer_request.json()
            for i in range(0, self.ether_scan_limit):
                tx_response_base = tx_response['result'][i]
                token_id = tx_response_base['tokenID']
                tx_hash = str(tx_response_base['hash'])
                tx_exists = False if len(self.tx_db.search(self.tx_query.tx == tx_hash)) == 0 else True
                if tx_exists:
                    continue
                key = tx_hash + ' ' + token_id
                tx_exists = False if len(self.tx_db.search(self.tx_query.tx == key)) == 0 else True
                if tx_exists:
                    continue
                if i + 1 != self.ether_scan_limit:  # check if next tx has is same as this one's
                    next_tx_hash = str(tx_response['result'][i + 1]['hash'])
                    next_key = next_tx_hash + ' ' + token_id
                    if key == next_key:
                        continue
                else:  # if we are at the end of the list: fetch the api again, increase offset by 1, and check if same
                    tx_transfer_params['offset'] += 1
                    self.LOGGER_JUNK.write_log(info(), 'Reached end of the list... Sending a request to EtherScan at '
                                                       f'{self.ether_scan_api_url} with params = {tx_transfer_params}')
                    get_new_tx_transfer_request = requests.get(self.ether_scan_api_url, params=tx_transfer_params,
                                                               timeout=3)
                    new_tx_response = get_new_tx_transfer_request.json()
                    next_tx_transfer_hash = str(new_tx_response['result'][i + 1]['hash'])
                    next_key = next_tx_transfer_hash + ' ' + token_id
                    if key == next_key:
                        continue
                from_address = tx_response_base['from']
                if from_address == '0x0000000000000000000000000000000000000000':
                    continue
                tx_hash_params = {
                    'module': 'proxy',
                    'action': 'eth_getTransactionByHash',
                    'txhash': tx_hash,
                    'apikey': self.ether_scan_api_key
                }
                self.LOGGER_JUNK.write_log(info(), f'Sending a request to EtherScan at {self.ether_scan_api_url} with '
                                                   f'params = {tx_hash_params}')
                get_tx_hash_request = requests.get(self.ether_scan_api_url, params=tx_hash_params, timeout=3)
                tx_details_response_base = get_tx_hash_request.json()['result']
                tx_hex_value = tx_details_response_base['value']
                tx_value = float(int(tx_hex_value, 16) / 1e18)
                usd_nft_cost = round(float(eth_usd_price) * tx_value, 2)
                input_type = tx_details_response_base['input']
                symbol = 'ETH'
                if input_type.startswith('0xab834bab'):  # atomic match
                    if tx_value == 0.0:
                        tx_hash_params = {
                            'module': 'proxy',
                            'action': 'eth_getTransactionReceipt',
                            'txhash': tx_hash,
                            'apikey': self.ether_scan_api_key
                        }
                        self.LOGGER_JUNK.write_log(info(), f'Sending a request to EtherScan at '
                                                           f'{self.ether_scan_api_url} with params = {tx_hash_params}')
                        get_tx_receipt_request = requests.get(self.ether_scan_api_url, params=tx_hash_params,
                                                              timeout=3)
                        first_log = get_tx_receipt_request.json()['result']['logs'][0]
                        data = first_log['data']
                        if data != '0x':
                            address = first_log['address']
                            if str(address).lower() == '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':  # WETH is common
                                symbol = 'WETH'
                                tx_value = float(int(data, 16) / 1e18)
                                usd_nft_cost = round(float(eth_usd_price) * tx_value, 2)
                            else:
                                token_info_req = requests.get(
                                    'https://api.ethplorer.io/getTokenInfo/{}?apiKey=freekey'.format(address),
                                    timeout=3)
                                self.LOGGER_JUNK.write_log(info(), 'Sending a request to ethplorer at '
                                                                   f'{token_info_req}')
                                token_info_json = token_info_req.json()
                                symbol = token_info_json['symbol']
                                decimals = int(token_info_json['decimals'])
                                price = round(token_info_json['price']['rate'], 3)
                                tx_value = float(int(data, 16) / (1 * 10 ** decimals))
                                usd_nft_cost = round(float(price) * tx_value, 2)
                    name = '{} #{}'.format(self.ether_scan_name, token_id)
                    asset_link = 'https://opensea.io/assets/{}/{}'.format(self.contract_address, token_id)
                    rare_trait_list = []
                    if self.trait_db is not None or self.trait_db is True:
                        rare_trait_list = self.create_rare_trait_list(token_id)
                    image_url = None
                    if self.image_db is not None:
                        asset_from_db = self.image_db.search(self.image_query.id == int(token_id))
                        image_url = asset_from_db[0]['image_url']
                    self.LOGGER_JUNK.write_log(info(), 'A unique sale has been found found. Creating transaction '
                                                       'object...')
                    transaction = _OpenSeaTransactionObject(name, image_url, tx_value, usd_nft_cost, asset_link,
                                                            rare_trait_list, self.twitter_tags, 1, key, tx_hash, symbol,
                                                            self.LOGGER, self.LOGGER_JUNK)
                    transaction.create_twitter_caption()
                    self.tx_queue.append(transaction)
                    self.LOGGER_JUNK.write_log(info(), 'Transaction object created with a Twitter caption and appended '
                                                       'to the transaction queue.')
            return self.process_queue()
        except Exception as e:
            self.LOGGER.write_log(error(), f'Encountered Exception inside of process_via_ether_scan: {e}')
            return -1

    def post_to_twitter(self):  # uploads to Twitter
        try:
            if self.os_obj_to_post.image_url is None:
                self.twitter.update_status(status=self.os_obj_to_post.twitter_caption)
                self.os_obj_to_post.is_posted = True
                self.tx_db.insert({'tx': self.os_obj_to_post.key})
                self.tx_db.insert({'tx': self.os_obj_to_post.tx_hash})
                self.LOGGER_JUNK.write_log(info(), 'Posted to Twitter without image, 2 transaction hashes inserted '
                                                   f'into the database: {self.os_obj_to_post.key} and '
                                                   f'{self.os_obj_to_post.tx_hash}')
                return True
        except Exception as e:
            self.LOGGER.write_log(error(), 'Encountered Exception inside of post_to_twitter when posting to Twitter '
                                           f'without an image: {e}')
            return False
        image = open(self.file_name, 'rb')
        try:
            response = self.twitter.upload_media(media=image)
            image.close()
            media_id = [response['media_id']]
            self.twitter.update_status(status=self.os_obj_to_post.twitter_caption, media_ids=media_id)
            self.os_obj_to_post.is_posted = True
            self.tx_db.insert({'tx': self.os_obj_to_post.key})
            self.tx_db.insert({'tx': self.os_obj_to_post.tx_hash})
            self.LOGGER_JUNK.write_log(info(), 'Posted to Twitter with image, 2 transaction hashes inserted into the '
                                               f'database: {self.os_obj_to_post.key} and {self.os_obj_to_post.tx_hash}')
            return True
        except Exception as e:
            self.LOGGER.write_log(error(), 'Encountered Exception inside of post_to_twitter when posting to Twitter '
                                           f'with an image: {e}')
            image.close()
            return False

    def delete_twitter_posts(self, count=200):  # deletes twitter posts. 200 max per call
        if count > 200:
            return False
        for i in self.twitter.get_user_timeline(count=count):
            status = int(i['id_str'])
            self.twitter.destroy_status(id=status)


class ManageFlowObj:  # Main class which does all of the operations
    def __init__(self, twitter_values_file, logging_enabled=False, trait_db_name=None, image_db_name=None):
        self.LOGGER = Logger(logging_enabled)
        self.LOGGER_JUNK = Logger(logging_enabled)
        self.LOGGER.write_log(info(), 'Inside of __init__ function in ManageFlowObj in post_to_twitter_obj.py.')
        self.twitter_values_file = twitter_values_file
        self.trait_db_name = trait_db_name
        self.image_db_name = image_db_name
        self.platform = 'twitter'
        self.log_file_name = ''
        self.junk_log_file_name = ''
        collection_stats = self.validate_params()
        cont_address = collection_stats[0]
        supply = collection_stats[1]
        self.trait_db_name = collection_stats[2]
        self.image_db_name = collection_stats[3]
        self.__base_obj = _PostFromOpenSeaTwitter(cont_address, supply, self.twitter_values_file, self.trait_db_name,
                                                  self.image_db_name, self.LOGGER, self.LOGGER_JUNK)
        self._begin()

    def validate_params(self):
        self.LOGGER.write_log(info(), 'Beginning validation of Twitter Values file...')
        self.LOGGER.write_log(info(), 'Checking if the Twitter Values file ends with a .txt file extension...')
        if not str(self.twitter_values_file).lower().endswith('.txt'):
            invalid_twitter_values_file_extension = 'The Twitter Values file must end with a .txt file extension.'
            self.LOGGER.write_log(fatal(), invalid_twitter_values_file_extension)
            raise Exception(invalid_twitter_values_file_extension)
        with open(self.twitter_values_file) as values_file:
            self.LOGGER.write_log(info(), 'Checking the Twitter Values file for format validation...')
            if len(values_file.readlines()) != 8:
                invalid_twitter_values_format = 'The Twitter Values file must be formatted correctly with the right ' \
                                                'of lines.'
                self.LOGGER.write_log(fatal(), invalid_twitter_values_format)
                raise Exception(invalid_twitter_values_format)
        self.LOGGER.write_log(info(), 'Number of lines validated.')
        values_file_test = open(self.twitter_values_file, 'r')
        hashtags_test = values_file_test.readline().strip()
        hashtags = 0
        words_in_hash_tag = hashtags_test.split()
        self.LOGGER.write_log(info(), 'Checking the hashtags in the Twitter Values file...')
        if hashtags_test != 'None':
            if len(hashtags_test) == 0 or hashtags_test.split() == 0:
                values_file_test.close()
                empty_hashtag_field = 'Hashtags field is empty. \'None\' should be written if no hashtags are needed.'
                self.LOGGER.write_log(fatal(), empty_hashtag_field)
                raise Exception(empty_hashtag_field)
            if len(hashtags_test) >= 120:
                values_file_test.close()
                hashtag_too_many_chars = 'There are too many characters in the hashtags, maximum of 120 ' \
                                         '(including spaces and hash sign).'
                self.LOGGER.write_log(fatal(), hashtag_too_many_chars)
                raise Exception(hashtag_too_many_chars)
            if len(words_in_hash_tag) > 10:
                values_file_test.close()
                too_many_hashtags = 'There are too many hashtags, there can only be a maximum of 10.'
                self.LOGGER.write_log(fatal(), too_many_hashtags)
                raise Exception(too_many_hashtags)
            for word in words_in_hash_tag:
                if word[0] == '#':
                    hashtags += 1
            if hashtags != len(words_in_hash_tag):
                values_file_test.close()
                hashtags_not_preceded_by_hash = 'There were one or more words not preceded by a hashtag (#).'
                self.LOGGER.write_log(fatal(), hashtags_not_preceded_by_hash)
                raise Exception(hashtags_not_preceded_by_hash)
        self.LOGGER.write_log(info(), 'The hashtags field has been validated.')
        collection_name_test = values_file_test.readline().strip()
        test_collection_name_url = 'https://api.opensea.io/api/v1/collection/{}'.format(collection_name_test)
        test_response = requests.get(test_collection_name_url)
        self.LOGGER.write_log(info(), 'Checking if the collection name is a valid collection on OpenSea...')
        if test_response.status_code == 200:
            collection_json = test_response.json()['collection']
            stats_json = collection_json['stats']
            total_supply = int(stats_json['total_supply'])
            primary_asset_contracts_json = collection_json['primary_asset_contracts'][0]  # got the contract address
            contract_address = primary_asset_contracts_json['address']
            self.LOGGER.write_log(info(), 'Collection name has been validated.')
        else:
            values_file_test.close()
            invalid_collection_name_msg = 'The provided collection name does not exist.'
            self.LOGGER.write_log(fatal(), invalid_collection_name_msg)
            raise Exception(invalid_collection_name_msg)
        self.log_file_name = collection_name_test + self.platform
        self.junk_log_file_name = collection_name_test + self.platform + '_junk'
        self.LOGGER.rename_log_file(self.log_file_name)
        self.LOGGER_JUNK.rename_log_file(self.junk_log_file_name)
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
        self.LOGGER.write_log(info(), 'Checking if the Twitter credentials are valid...')
        try:
            twitter_test.verify_credentials()
            twitter_test.client.close()
            self.LOGGER.write_log(info(), 'Twitter credentials have been validated.')
        except twython.exceptions.TwythonAuthError:
            values_file_test.close()
            twitter_test.client.close()
            invalid_twitter_credentials = 'Authentication error. Please recheck the credentials, they are invalid.'
            self.LOGGER.write_log(fatal(), invalid_twitter_credentials)
            raise Exception(invalid_twitter_credentials)
        test_os_key = values_file_test.readline().strip()
        test_os_key_url = 'https://api.opensea.io/api/v1/events?only_opensea=false'
        test_os_headers = CaseInsensitiveDict()
        test_os_headers['Accept'] = 'application/json'
        test_os_headers['x-api-key'] = test_os_key
        test_os_response = requests.get(test_os_key_url, headers=test_os_headers)
        self.LOGGER.write_log(info(), 'Checking if the OpenSea API key is valid...')
        if test_os_response.status_code != 200:
            values_file_test.close()
            invalid_opensea_key = 'Provided OpenSea API key is invalid.'
            self.LOGGER.write_log(fatal(), invalid_opensea_key)
            raise Exception(invalid_opensea_key)
        self.LOGGER.write_log(info(), 'OpenSea API key has been validated.')
        test_ether_scan_values = values_file_test.readline().strip().split()
        test_ether_scan_key = test_ether_scan_values[0]
        test_ether_scan_url = 'https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey={}'. \
            format(test_ether_scan_key)
        test_ether_scan_response = requests.get(test_ether_scan_url)
        self.LOGGER.write_log(info(), 'Checking if the Ether Scan API key is valid...')
        if test_ether_scan_response.json()['message'] == 'NOTOK':
            values_file_test.close()
            invalid_ether_scan_key = 'Provided Ether Scan API key is invalid.'
            self.LOGGER.write_log(fatal(), invalid_ether_scan_key)
            raise Exception(invalid_ether_scan_key)
        self.LOGGER.write_log(info(), 'Ether Scan API key has been validated.')
        values_file_test.close()
        self.LOGGER.write_log(info(), 'Validation of Twitter Values complete. No errors found.')
        trait_db = self.trait_db_name
        self.LOGGER.write_log(info(), 'Beginning validation of any additional parameters...')
        if self.trait_db_name is not None and type(self.trait_db_name) != bool:
            self.LOGGER.write_log(info(), 'Validating the existence of the trait database file...')
            if not str(self.trait_db_name).lower().endswith('.json'):
                invalid_trait_db_extension = 'Trait DB must end with a .json file extension.'
                self.LOGGER.write_log(fatal(), invalid_trait_db_extension)
                raise Exception(invalid_trait_db_extension)
            trait_db = find_file.find(self.trait_db_name)
            if trait_db is None:
                trait_db_not_found = 'Trait DB .json not found. Please type the name correctly or remove the parameter.'
                self.LOGGER.write_log(fatal(), trait_db_not_found)
                raise Exception(trait_db_not_found)
            self.LOGGER.write_log(info(), 'Validation of Trait DB Name .json complete. No errors found.')
        else:
            self.LOGGER.write_log(info(), 'Skipping Trait DB Name .json. No file was provided.')
        image_db = self.image_db_name
        if self.image_db_name is not None:
            self.LOGGER.write_log(info(), 'Validating the existence of the image database file...')
            if not str(self.image_db_name).lower().endswith('.json'):
                invalid_image_db_extension = 'Image DB must end with a .json file extension.'
                self.LOGGER.write_log(fatal(), invalid_image_db_extension)
                raise Exception(invalid_image_db_extension)
            image_db = find_file.find(self.image_db_name)
            if image_db is None:
                image_db_not_found = 'Image DB .json not found. Either type the name correctly or remove the parameter.'
                self.LOGGER.write_log(fatal(), image_db_not_found)
                raise Exception(image_db_not_found)
            self.LOGGER.write_log(info(), 'Validation of Image DB Name .json complete. No errors found.')
        else:
            self.LOGGER.write_log(info(), 'Skipping Image DB Name .json. No file was provided.')
        self.LOGGER.write_log(info(), 'Validation of Twitter Values file and any extra parameter(s) is complete.')
        return [contract_address, total_supply, trait_db, image_db]

    def run_methods(self):
        self.check_os_api_status()

    def check_os_api_status(self):
        os_api_working = self.__base_obj.get_recent_sales()
        if os_api_working:
            self.check_if_new_post_exists()
        else:
            time.sleep(10)  # 10
            new_post_exists = self.__base_obj.process_via_ether_scan()
            if new_post_exists == -1:
                self.LOGGER.write_log(error(), 'Ether Scan API is not working currently either. Sleeping for 30 '
                                               'seconds...')
                time.sleep(30)  # 30
            elif new_post_exists:
                image_downloaded = self.__base_obj.download_image()
                if image_downloaded:
                    self.try_to_post_to_twitter()
                else:
                    self.LOGGER.write_log(error(), 'There was an error while downloading the image. Sleeping for '
                                                   '10 seconds...')
                    time.sleep(10)  # 10
            else:
                self.LOGGER_JUNK.write_log(info(), 'There is no new post. Sleeping for 5 seconds...')
                time.sleep(5)  # 5

    def check_if_new_post_exists(self):
        new_post_exists = self.__base_obj.parse_response_objects()
        if new_post_exists:
            self.try_to_download_image()
        else:
            self.LOGGER_JUNK.write_log(info(), 'There is no new post. Sleeping for 5 seconds...')
            time.sleep(5)  # 5

    def try_to_download_image(self):
        image_downloaded = self.__base_obj.download_image()
        if image_downloaded:
            self.try_to_post_to_twitter()
        else:
            self.LOGGER.write_log(error(), 'There was an error while downloading the image. Sleeping for 10 seconds...')
            time.sleep(10)  # 10

    def try_to_post_to_twitter(self):
        posted_to_twitter = self.__base_obj.post_to_twitter()
        if posted_to_twitter:
            self.LOGGER_JUNK.write_log(info(), 'Posted to Twitter successfully. Sleeping for 5 seconds...')
            time.sleep(5)  # 5
        else:
            self.LOGGER.write_log(error(), 'There was an error while posting to Twitter. Sleeping for 15 seconds...')
            time.sleep(15)  # 15

    def _begin(self):  # begin program!
        self.LOGGER.write_log(info(), 'Beginning the program in ManageFlowObj in post_to_twitter_obj.py...')
        min_before = time.time()
        first = True
        while True:
            if first:
                print(f'Log File Names: {self.log_file_name} {self.junk_log_file_name}')
            if first or time.time() - min_before >= 60:
                print('Heartbeat at ' + datetime.datetime.fromtimestamp(time.time()).strftime('%m/%d/%Y %H:%M:%S'),
                      flush=True)
                min_before = time.time()
                first = False
            self.run_methods()

# TODO: Time between pinging API:
#   Find a way to increase the time to sleep based on how many transactions have been occurring
#   More posts happening? keep checking every few seconds or decrease if time awaited is higher
#   Less posts happening? space out the time we send each request.
#   Implement exponential backoff mechanism...
