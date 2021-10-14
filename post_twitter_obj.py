import datetime
import requests
import time
from tinydb import TinyDB, Query
from twython import Twython


class _OpenSeaTransactionObject:
    twitter_caption = None

    def __init__(self, name_, image_url_, seller_, buyer_, eth_nft_price_, usd_price_, total_usd_cost_, the_date_,
                 the_time_, link_, rare_trait_list_):
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

    def create_twitter_caption(self):
        self.twitter_caption = '{} bought for Ξ{} (${})\n'.format(self.name, self.eth_nft_price, self.total_usd_cost)
        if len(self.rare_trait_list) != 0:
            self.twitter_caption += 'Rare Traits:\n'
            rare_trait_sentence = ''
            for rare_trait in self.rare_trait_list:
                rare_trait_sentence += '{}: {} - {}%\n'.format(rare_trait[0], rare_trait[1], str(rare_trait[2]))
            self.twitter_caption += rare_trait_sentence
        self.twitter_caption += '\n\n{}'.format(self.link)


class _PostFromOpenSeaTwitter:
    def __init__(self, values_file, keys_file, db_name):
        twitter_values_file = values_file
        twitter_keys_file = keys_file
        tx_hash_db = db_name
        values = open(twitter_values_file, 'r')
        self.file_name = values.readline().split(":")[1].strip()
        self.twitter_tags = values.readline().split(":")[1]
        self.contract_address = values.readline().split(":")[1].strip()
        values.close()
        self.os_events_url = 'https://api.opensea.io/api/v1/events'
        self.os_asset_url = 'https://api.opensea.io/api/v1/asset/'
        self.response = None
        self.os_obj_to_post = None
        self.driver = None
        self.tx_db = TinyDB(tx_hash_db)
        self.tx_query = Query()
        self.tx_queue = []
        self.limit = 10
        twitter_keys = open(twitter_keys_file, 'r')
        api_key = twitter_keys.readline().split(":")[1].strip()
        api_key_secret = twitter_keys.readline().split(":")[1].strip()
        access_token = twitter_keys.readline().split(":")[1].strip()
        access_token_secret = twitter_keys.readline().split(":")[1].strip()
        twitter_keys.close()
        self.twitter = Twython(
            api_key,
            api_key_secret,
            access_token,
            access_token_secret
        )

    def get_recent_sales(self):
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
            if seller_address == buyer_address or seller == buyer:
                continue
            tx_hash = str(base['transaction']['transaction_hash'])
            tx_exists = False if len(self.tx_db.search(self.tx_query.tx == tx_hash)) == 0 else True
            if tx_exists:
                continue
            self.tx_db.insert({'tx': tx_hash})
            token_id = asset['token_id']
            eth_nft_price = float('{0:.5f}'.format(int(base['total_price']) / 1e18))
            usd_price = float(base['payment_token']['usd_price'])
            total_usd_cost = '{:.2f}'.format(round(eth_nft_price * usd_price, 2))
            timestamp = str(base['transaction']['timestamp']).split('T')
            date = datetime.datetime.strptime(timestamp[0], '%Y-%m-%d')
            month = datetime.date(date.year, date.month, date.day).strftime('%B')
            year = str(date.year)
            day = str(date.day)
            the_date = month + ' ' + day + ', ' + year
            the_time = timestamp[1]
            link = asset['permalink']
            asset_url = self.os_asset_url + self.contract_address + '/' + token_id
            asset_response = requests.request("GET", asset_url)
            traits = asset_response.json()['traits']
            rare_trait_list = []
            for trait in traits:
                trait_type = trait['trait_type']
                trait_value = trait['value']
                trait_count = trait['trait_count']
                if float(trait_count / 10000) <= 0.05:
                    rare_trait_list.append([trait_type, trait_value, float(trait_count / 100)])
            transaction = _OpenSeaTransactionObject(name, image_url, seller, buyer, eth_nft_price, usd_price,
                                                    total_usd_cost, the_date, the_time, link, rare_trait_list)
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
        self.os_obj_to_post = self.tx_queue[0]
        return True

    def download_image(self):
        try:
            img_response = requests.get(self.os_obj_to_post.image_url, stream=True)
            img = open(self.file_name, "wb")
            img.write(img_response.content)
            img.close()
            return True
        except Exception as e:
            print(e, flush=True)
            return False

    def post_to_twitter(self):
        try:
            image = open(self.file_name, 'rb')
            response = self.twitter.upload_media(media=image)
            image.close()
            media_id = [response['media_id']]
            self.twitter.update_status(status=self.os_obj_to_post.twitter_caption + '\n\n' +
                                       self.twitter_tags, media_ids=media_id)
            self.os_obj_to_post.is_posted = True
            return True
        except Exception as e:
            print(e, flush=True)
            return False

    def delete_twitter_posts(self, count=200):
        if count > 200:
            return False
        for i in self.twitter.get_user_timeline(count=count):
            status = int(i['id_str'])
            self.twitter.destroy_status(id=status)


class ManageFlowObj:
    def __init__(self, twitter_values_file, twitter_keys_file, tx_hash_db_name):
        self.__base_obj = _PostFromOpenSeaTwitter(twitter_values_file, twitter_keys_file, tx_hash_db_name)
        self._begin()

    def run_methods(self, date_time_now):
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
            print('Posted to Twitter roughly', date_time_now, flush=True)
            time.sleep(5)
        else:
            print('Post to Twitter error at roughly', date_time_now, flush=True)
            time.sleep(15)

    def _begin(self):
        while True:
            date_time_now = datetime.datetime.fromtimestamp(time.time()).strftime('%m/%d/%Y %H:%M:%S')
            self.run_methods(date_time_now)
