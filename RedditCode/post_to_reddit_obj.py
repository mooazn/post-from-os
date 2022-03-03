import datetime
from fake_useragent import UserAgent
import praw
import prawcore.exceptions
import requests
from requests.structures import CaseInsensitiveDict
import time
from tinydb import TinyDB, Query


class _OpenSeaTransactionObject:  # an OpenSea transaction object which holds information about the object
    def __init__(self, name_, image_url_, eth_nft_price_, total_usd_cost_, link_, num_of_assets_, tx_hash_):
        self.reddit_caption = None
        self.name = name_
        self.image_url = image_url_
        self.eth_nft_price = eth_nft_price_
        self.total_usd_cost = total_usd_cost_
        self.link = link_
        self.is_posted = False
        self.num_of_assets = num_of_assets_
        self.tx_hash = tx_hash_

    def __eq__(self, other):
        return self.tx_hash == other.tx_hash

    def __hash__(self):
        return hash(('tx_hash', self.tx_hash))

    def create_reddit_caption(self):
        self.reddit_caption = '{} bought for Ξ{} (${})\n\n'.format(self.name, self.eth_nft_price, self.total_usd_cost)
        if self.num_of_assets > 1:
            self.reddit_caption = '{}\n\n{} bought for Ξ{} (${})\n\n'.format(self.name, self.num_of_assets,
                                                                             self.eth_nft_price, self.total_usd_cost)
        self.reddit_caption += '\n\n Link: ' + str(self.link).replace('https://', '')


class _PostFromOpenSeaReddit:  # class which holds all operations and utilizes both OpenSea API and Reddit API
    def __init__(self, address, supply, values_file):  # initialize all the fields
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
            querystring = {
                "asset_contract_address": self.contract_address,
                "event_type": "successful",
                "only_opensea": "false"
            }
            headers = CaseInsensitiveDict()
            headers['Accept'] = 'application/json'
            headers['User-Agent'] = self.ua.random
            headers['x-api-key'] = self.os_api_key
            self.response = requests.request("GET", self.os_events_url, headers=headers, params=querystring, timeout=3)
            return self.response.status_code == 200
        except Exception as e:
            print(e, flush=True)
            return False

    def parse_response_objects(self):  # parses {limit} objects
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
                    transaction = _OpenSeaTransactionObject(name, image_url, eth_nft_price, total_usd_cost, link,
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
                eth_nft_price = float('{0:.5f}'.format(int(base['total_price']) / 1e18))
                usd_price = float(base['payment_token']['usd_price'])
                total_usd_cost = '{:.2f}'.format(round(eth_nft_price * usd_price, 2))
                link = asset['permalink']
            except (ValueError, TypeError):
                continue
            transaction = _OpenSeaTransactionObject(name, image_url, eth_nft_price, total_usd_cost, link, 1, tx_hash)
            transaction.create_reddit_caption()
            self.tx_queue.append(transaction)
        return self.process_queue()

    def process_queue(self):
        if len(self.tx_db) > 200:
            for first in self.tx_db:
                self.tx_db.remove(doc_ids=[first.doc_id])
                break
        index = 0
        self.tx_queue = list(set(self.tx_queue))
        while index < len(self.tx_queue):
            cur_os_obj = self.tx_queue[index]
            tx_exists = False if len(self.tx_db.search(self.tx_query.tx == str(cur_os_obj.tx_hash))) == 0 else True
            if cur_os_obj.is_posted or tx_exists:
                self.tx_queue.pop(index)
            else:
                index += 1
        if len(self.tx_queue) == 0:
            return False
        self.os_obj_to_post = self.tx_queue[-1]
        return True

    def download_image(self):  # downloads the image to upload
        try:
            img_response = requests.get(self.os_obj_to_post.image_url, stream=True, timeout=3)
            img = open(self.file_name, "wb")
            img.write(img_response.content)
            img.close()
            return True
        except Exception as e:
            print(e, flush=True)
            return False

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
    def __init__(self, reddit_values_file):
        self.reddit_values_file = reddit_values_file
        collection_stats = self.validate_params()
        cont_address = collection_stats[0]
        supply = collection_stats[1]
        self.__base_obj = _PostFromOpenSeaReddit(cont_address, supply, self.reddit_values_file)
        self._begin()

    def validate_params(self):
        print('Beginning validation of Reddit Values File...')
        if not str(self.reddit_values_file).lower().endswith('.txt'):
            raise Exception('Reddit Values must be a .txt file.')
        with open(self.reddit_values_file) as values_file:
            if len(values_file.readlines()) != 7:
                raise Exception('The Reddit Values file must be formatted correctly.')
        print('Number of lines validated.')
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
        values_file_test.close()
        print('Validation of Reddit Values .txt complete. No errors found...')
        print('All files are validated. Beginning program...')
        return [contract_address, total_supply]

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
