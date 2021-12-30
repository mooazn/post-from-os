import datetime
from fake_useragent import UserAgent
from HelperCode import find_file
from operator import itemgetter
import prawcore.exceptions
import requests
from requests.structures import CaseInsensitiveDict
import time
import praw
from tinydb import TinyDB, Query


class _OpenSeaTransactionObject:  # an OpenSea transaction object which holds information about the object
    def __init__(self, name_, image_url_, eth_nft_price_, total_usd_cost_, link_, rare_trait_list_, num_of_assets_,
                 tx_hash_):
        self.reddit_caption = None
        self.name = name_
        self.image_url = image_url_
        self.eth_nft_price = eth_nft_price_
        self.total_usd_cost = total_usd_cost_
        self.link = link_
        self.is_posted = False
        self.rare_trait_list = rare_trait_list_
        self.num_of_assets = num_of_assets_
        self.tx_hash = tx_hash_

    def create_reddit_caption(self):
        self.reddit_caption = '{} bought for Ξ{} (${})\n\n'.format(self.name, self.eth_nft_price, self.total_usd_cost)
        if self.num_of_assets > 1:
            self.reddit_caption = '{}\n\n{} bought for Ξ{} (${})\n\n'.format(self.name, self.num_of_assets,
                                                                             self.eth_nft_price, self.total_usd_cost)
        if self.rare_trait_list:
            self.reddit_caption += 'Rare Traits:\n\n'
            full_rare_trait_sentence = ''
            for rare_trait in self.rare_trait_list:
                full_rare_trait_sentence += '{}: {} - {}%\n\n'.format(rare_trait[0], rare_trait[1], str(rare_trait[2]))
            self.reddit_caption += full_rare_trait_sentence
        self.reddit_caption += '\n\n Link: ' + str(self.link).replace('https://', '')


class _PostFromOpenSeaReddit:  # class which holds all operations and utilizes both OpenSea API and Reddit API
    def __init__(self, address, supply, values_file, trait_db_name):  # initialize all the fields
        reddit_values_file = values_file
        values = open(reddit_values_file, 'r')
        self.collection_name = values.readline().strip()
        client_id = values.readline().strip()
        client_secret = values.readline().strip()
        password = values.readline().strip()
        user_agent = values.readline().strip()
        self.username = values.readline().strip()
        self.os_api_key = values.readline().strip()
        values.close()
        self.file_name = self.collection_name + '.jpeg'
        self.contract_address = address
        self.total_supply = supply
        self.os_events_url = 'https://api.opensea.io/api/v1/events'
        self.os_asset_url = 'https://api.opensea.io/api/v1/asset/'
        self.response = None
        self.os_obj_to_post = None
        self.driver = None
        self.tx_db = TinyDB(self.collection_name + 'tx_hash_reddit_db.json')
        self.tx_query = Query()
        self.trait_db = trait_db_name
        if self.trait_db is not None and type(self.trait_db) != bool:
            self.trait_db = TinyDB(self.trait_db)
            self.trait_query = Query()
        self.trait_query = Query()
        self.tx_queue = []
        self.limit = 10
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            password=password,
            user_agent=user_agent,
            username=self.username,
        )
        self.reddit.validate_on_submit = True
        self.ua = UserAgent()

    def get_recent_sales(self):  # gets {limit} most recent sales
        try:
            querystring = {"asset_contract_address": self.contract_address,
                           "event_type": "successful",
                           "only_opensea": "false",
                           "offset": "0",
                           "limit": self.limit}
            headers = CaseInsensitiveDict()
            headers['Accept'] = 'application/json'
            headers['User-Agent'] = self.ua.random
            headers['x-api-key'] = self.os_api_key
            self.response = requests.request("GET", self.os_events_url, headers=headers, params=querystring)
            return self.response.status_code == 200
        except Exception as e:
            print(e, flush=True)
            return False

    def parse_response_objects(self):  # parses {limit} objects
        if len(self.tx_queue) > 0:
            queue_has_objects = self.process_queue()
            if queue_has_objects:
                return True
        for i in range(0, self.limit):
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
                                                            num_of_assets, tx_hash)
                    transaction.create_reddit_caption()
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
            if type(self.trait_db) == str or self.trait_db is True:
                rare_trait_list = self.create_rare_trait_list(token_id)
            transaction = _OpenSeaTransactionObject(name, image_url, eth_nft_price, total_usd_cost, link,
                                                    rare_trait_list, 1, tx_hash)
            transaction.create_reddit_caption()
            self.tx_queue.append(transaction)
        return self.process_queue()

    def process_queue(self):  # processes the queue thus far. this is a self-managing queue
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

    def download_image(self):  # downloads the image to upload
        try:
            img_response = requests.get(self.os_obj_to_post.image_url, stream=True)
            img = open(self.file_name, "wb")
            img.write(img_response.content)
            img.close()
            return True
        except Exception as e:
            print(e, flush=True)
            return False

    def create_rare_trait_list(self, token_id):
        try:
            rare_trait_list = []
            traits = None
            if self.trait_db is not None and type(self.trait_db) != bool:
                asset_from_db = self.trait_db.search(self.trait_query.id == int(token_id))
                if asset_from_db:
                    traits = eval(asset_from_db[0]['traits'])
            if traits is None:
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

    def post_to_reddit(self):
        try:
            sub_id = self.reddit.subreddit('r/u_{}'.format(self.username)).submit_image(self.os_obj_to_post.name,
                                                                                        image_path=self.file_name).id
            self.reddit.submission(id=sub_id).reply(self.os_obj_to_post.reddit_caption)
            self.os_obj_to_post.is_posted = True
            self.tx_db.insert({'tx': self.os_obj_to_post.tx_hash})
            return True
        except Exception as e:
            print(e, flush=True)
            return False


class ManageFlowObj:  # Main class which does all of the operations
    def __init__(self, reddit_values_file, trait_db_name=None):
        self.reddit_values_file = reddit_values_file
        self.trait_db_name = trait_db_name
        collection_stats = self.validate_params()
        cont_address = collection_stats[0]
        supply = collection_stats[1]
        self.trait_db_name = trait_db_name if collection_stats[2] is None else collection_stats[2]
        print('All files are validated. Beginning program...')
        self.__base_obj = _PostFromOpenSeaReddit(cont_address, supply, self.reddit_values_file, self.trait_db_name)
        self._begin()

    def validate_params(self):
        values_file_test = open(self.reddit_values_file, 'r')
        collection_name_test = values_file_test.readline().strip()
        client_id_test = values_file_test.readline().strip()
        client_secret_test = values_file_test.readline().strip()
        password_test = values_file_test.readline().strip()
        user_agent_test = values_file_test.readline().strip()
        username_test = values_file_test.readline().strip()
        test_collection_name_url = "https://api.opensea.io/api/v1/collection/{}".format(collection_name_test)
        test_response = requests.request("GET", test_collection_name_url)
        if test_response.status_code == 200:
            collection_json = test_response.json()['collection']
            stats_json = collection_json['stats']
            total_supply = int(stats_json['total_supply'])
            primary_asset_contracts_json = collection_json['primary_asset_contracts'][0]
            contract_address = primary_asset_contracts_json['address']
        else:
            values_file_test.close()
            raise Exception('The provided collection name does not exist.')
        reddit_test = praw.Reddit(
            client_id=client_id_test,
            client_secret=client_secret_test,
            password=password_test,
            user_agent=user_agent_test,
            username=username_test,
        )
        try:
            for _ in reddit_test.front.hot(limit=1):
                pass
        except prawcore.exceptions.ResponseException:
            values_file_test.close()
            raise Exception('Invalid keys supplied for Reddit API.')
        values_file_test.close()
        print('Validation of Reddit Values .txt complete. No errors found...')
        trait_db_full_name = None
        if self.trait_db_name is not None and type(self.trait_db_name) != bool:
            if not str(self.trait_db_name).lower().endswith('.json'):
                raise Exception('Trait DB must end with a .json file extension.')
            trait_db_full_name = find_file.find(self.trait_db_name)
            print('Validation of Trait DB Name .json complete. No errors found...')
        else:
            print('Skipping Trait DB Name .json. No file was provided.')
        return [contract_address, total_supply, trait_db_full_name]

    def run_methods(self, date_time_now):  # runs all the methods
        self.check_os_api_status(date_time_now)

    def check_os_api_status(self, date_time_now):
        os_api_working = self.__base_obj.get_recent_sales()
        if os_api_working:
            self.check_if_new_post_exists(date_time_now)
        else:
            print('OS API is not working at roughly', date_time_now, flush=True)
            time.sleep(30)

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
            self.try_to_post_to_reddit(date_time_now)
        else:
            print('Downloading image error at roughly', date_time_now, flush=True)
            time.sleep(10)

    def try_to_post_to_reddit(self, date_time_now):
        posted_to_reddit = self.__base_obj.post_to_reddit()
        if posted_to_reddit:
            print('Posted to Reddit at roughly', date_time_now, flush=True)
            time.sleep(5)
        else:
            print('Post to Reddit error at roughly', date_time_now, flush=True)
            time.sleep(15)

    def _begin(self):  # begin program!
        while True:
            date_time_now = datetime.datetime.fromtimestamp(time.time()).strftime('%m/%d/%Y %H:%M:%S')
            self.run_methods(date_time_now)
