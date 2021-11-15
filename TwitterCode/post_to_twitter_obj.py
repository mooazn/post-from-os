import datetime
from operator import itemgetter
import requests
import time
import twython.exceptions
from tinydb import TinyDB, Query
from twython import Twython


class _OpenSeaTransactionObject:  # an OpenSea transaction object which holds information about the object
    twitter_caption = None

    def __init__(self, name_, image_url_, seller_, buyer_, eth_nft_price_, usd_price_, total_usd_cost_, the_date_,
                 the_time_, link_, rare_trait_list_, twitter_tags_):
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
        self.rare_trait_list = rare_trait_list_
        self.twitter_tags = twitter_tags_

    def create_twitter_caption(self):
        self.twitter_caption = '{} bought for Ξ{} (${})\n'.format(self.name, self.eth_nft_price, self.total_usd_cost)
        remaining_characters = 280 - len(self.twitter_caption) - len(self.link) - len(self.twitter_tags)  # 280 is max
        # the remaining characters at this stage should roughly be 130-180 characters.
        if self.rare_trait_list is not None:
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
    def __init__(self, address, supply, values_file, db_name, trait_db_name):  # initialize all the fields
        twitter_values_file = values_file
        values = open(twitter_values_file, 'r')
        self.twitter_tags = values.readline().strip()
        self.collection_name = values.readline().strip()
        api_key = values.readline().strip()
        api_key_secret = values.readline().strip()
        access_token = values.readline().strip()
        access_token_secret = values.readline().strip()
        values.close()
        self.file_name = self.collection_name + '.jpeg'
        self.contract_address = address
        self.total_supply = supply
        self.os_events_url = 'https://api.opensea.io/api/v1/events'
        self.os_asset_url = 'https://api.opensea.io/api/v1/asset/'
        self.response = None
        self.os_obj_to_post = None
        self.driver = None
        self.tx_db = TinyDB(db_name)
        self.tx_query = Query()
        self.trait_db = TinyDB(trait_db_name)
        self.trait_query = Query()
        self.tx_queue = []
        self.limit = 10
        self.twitter = Twython(
            api_key,
            api_key_secret,
            access_token,
            access_token_secret
        )

    def __del__(self):
        self.twitter.client.close()

    def create_rare_trait_list(self, traits, rare_trait_list):
        for trait in traits:
            trait_type = trait['trait_type']
            trait_value = trait['value']
            trait_count = trait['trait_count']
            rarity_decimal = float(trait_count / self.total_supply)
            if rarity_decimal <= 0.05:
                rare_trait_list.append([trait_type, trait_value, round(rarity_decimal * 100, 2)])
        rare_trait_list.sort(key=itemgetter(2))

    def get_recent_sales(self):  # gets {limit} most recent sales
        try:
            querystring = {"asset_contract_address": self.contract_address,
                           "event_type": "successful",
                           "only_opensea": "false",
                           "offset": "0",
                           "limit": self.limit}
            headers = {"Accept": "application/json"}
            self.response = requests.request("GET", self.os_events_url, headers=headers, params=querystring)
            return self.response.status_code == 200
        except Exception as e:
            print(e, flush=True)
            return False

    def parse_response_objects(self):  # parses {limit} objects
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
            if seller_address == buyer_address or seller == buyer:
                continue
            tx_hash = str(base['transaction']['transaction_hash'])
            tx_exists = False if len(self.tx_db.search(self.tx_query.tx == tx_hash)) == 0 else True
            if tx_exists:
                continue
            try:
                token_id = asset['token_id']
                eth_nft_price = float('{0:.5f}'.format(int(base['total_price']) / 1e18))
                usd_price = float(base['payment_token']['usd_price'])
                total_usd_cost = '{:.2f}'.format(round(eth_nft_price * usd_price, 2))
                timestamp = str(base['transaction']['timestamp']).split('T')
                date = datetime.datetime.strptime(timestamp[0], '%Y-%m-%d')
                month = datetime.date(date.year, date.month, date.day).strftime('%B')
            except (ValueError, TypeError):
                continue
            year = str(date.year)
            day = str(date.day)
            the_date = month + ' ' + day + ', ' + year
            the_time = timestamp[1]
            link = asset['permalink']
            asset_url = self.os_asset_url + self.contract_address + '/' + token_id
            rare_trait_list = []
            asset_from_db = self.trait_db.search(self.trait_query.id == int(token_id))
            if asset_from_db:
                traits = eval(asset_from_db[0]['traits'])
                self.create_rare_trait_list(traits, rare_trait_list)
            if not rare_trait_list:
                asset_response = requests.request("GET", asset_url)
                if asset_response.status_code == 200:
                    traits = asset_response.json()['traits']
                    self.create_rare_trait_list(traits, rare_trait_list)
            self.tx_db.insert({'tx': tx_hash})
            transaction = _OpenSeaTransactionObject(name, image_url, seller, buyer, eth_nft_price, usd_price,
                                                    total_usd_cost, the_date, the_time, link, rare_trait_list,
                                                    self.twitter_tags)
            print(transaction.twitter_caption)
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
        self.os_obj_to_post = self.tx_queue[0]
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

    def post_to_twitter(self):  # uploads to Twitter
        try:
            image = open(self.file_name, 'rb')
            response = self.twitter.upload_media(media=image)
            image.close()
            media_id = [response['media_id']]
            self.twitter.update_status(status=self.os_obj_to_post.twitter_caption, media_ids=media_id)
            self.os_obj_to_post.is_posted = True
            return True
        except Exception as e:
            print(e, flush=True)
            return False

    def delete_twitter_posts(self, count=200):  # deletes twitter posts. 200 max per call
        if count > 200:
            return False
        for i in self.twitter.get_user_timeline(count=count):
            status = int(i['id_str'])
            self.twitter.destroy_status(id=status)


class ManageFlowObj:  # Main class which does all of the operations
    def __init__(self, twitter_values_file, tx_hash_db_name, trait_db_name=None):
        self.twitter_values_file = twitter_values_file
        self.tx_hash_db_name = tx_hash_db_name
        self.trait_db_name = trait_db_name
        collection_stats = self.validate_params()
        cont_address = collection_stats[0]
        supply = collection_stats[1]
        print('All files are validated. Beginning program...')
        self.__base_obj = _PostFromOpenSeaTwitter(cont_address, supply, self.twitter_values_file, self.tx_hash_db_name,
                                                  self.trait_db_name)
        self._begin()

    def validate_params(self):
        values_file_test = open(self.twitter_values_file, 'r')
        hashtags_test = values_file_test.readline().strip()
        hashtags = 0
        words_in_hash_tag = hashtags_test.split()
        if len(hashtags_test) >= 120:
            values_file_test.close()
            raise Exception('Too many characters in hashtags.')
        if len(words_in_hash_tag) > 10:
            values_file_test.close()
            raise Exception('Too many hashtags.')
        if hashtags_test != 'None':
            for word in words_in_hash_tag:
                if word[0] == '#':
                    hashtags += 1
            if hashtags != len(words_in_hash_tag):
                values_file_test.close()
                raise Exception('All words must be preceded by a hashtag (#).')
        collection_name_test = values_file_test.readline().strip()
        test_collection_name_url = "https://api.opensea.io/api/v1/collection/{}".format(collection_name_test)
        test_response = requests.request("GET", test_collection_name_url)
        if test_response.status_code == 200:
            collection_json = test_response.json()['collection']
            stats_json = collection_json['stats']
            total_supply = int(stats_json['total_supply'])
            primary_asset_contracts_json = collection_json['primary_asset_contracts'][0]  # got the contract address
            contract_address = primary_asset_contracts_json['address']
        else:
            values_file_test.close()
            raise Exception('The provided collection name does not exist.')
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
            values_file_test.close()
        except twython.exceptions.TwythonAuthError:
            values_file_test.close()
            twitter_test.client.close()
            raise Exception('Invalid Twitter Keys supplied.')
        print('Validation of Twitter Values .txt complete. No errors found...')
        if not str(self.tx_hash_db_name).lower().endswith('.json'):
            raise Exception('Transaction Hash DB must end with a .json file extension.')
        print('Validation of TX Hash DB Name .json complete. No errors found...')
        if self.trait_db_name is not None:
            if not str(self.trait_db_name).lower().endswith('.json'):
                raise Exception('Trait DB must end with a .json file extension.')
            print('Validation of Trait DB Name .json complete. No errors found...')
        else:
            print('Skipping Trait DB Name .json. No file was provided.')
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
