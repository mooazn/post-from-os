from twython import Twython
import requests
import datetime
import shutil
import time


class OpenSeaTransactionObject:
    twitter_caption = None

    def __init__(self, name_, image_url_, seller_, buyer_, eth_nft_price_, usd_price_, total_usd_cost_, the_date_,
                 the_time_):
        self.name = name_
        self.image_url = image_url_
        self.seller = seller_
        self.buyer = buyer_
        self.eth_nft_price = eth_nft_price_
        self.usd_price = usd_price_
        self.total_usd_cost = total_usd_cost_
        self.the_date = the_date_
        self.the_time = the_time_

    def create_twitter_caption(self):
        first_s = self.name
        second_s = 'Time of purchase: ' + self.the_date + ' at ' + self.the_time + ' (UTC).'
        third_s = 'Buyer: ' + self.buyer
        fourth_s = 'Seller: ' + self.seller
        fifth_s = 'Total USD Cost: $' + str(self.total_usd_cost)
        sixth_s = 'ETH Price: ' + str(self.eth_nft_price) + ' ETH'
        seventh_s = 'ETH Value: $' + str(self.usd_price)
        self.twitter_caption = first_s + '\n\n' + second_s + '\n\n' + third_s + '\n\n' + fourth_s + '\n\n' + fifth_s \
                                       + '\n\n' + sixth_s + '\n\n' + seventh_s


class PostFromOpenSeaTwitter:
    def __init__(self):
        self.values = open('twitter_values.txt', 'r')
        self.file_name = self.values.readline().split(":")[1].strip()
        self.twitter_tags = self.values.readline().split(":")[1]
        self.values.close()
        self.os_url = "https://api.opensea.io/api/v1/events"
        self.response = None
        self.os_obj_to_post = None
        self.driver = None
        self.tx_hash_set = {''}

    def get_most_recent_sale(self):
        try:
            querystring = {"asset_contract_address": "0x42e10846bbc6d062d1a41a8883ce2b81015a9523",
                           "event_type": "successful",
                           "only_opensea": "false",
                           "offset": "0",
                           "limit": "1"}
            headers = {"Accept": "application/json"}
            self.response = requests.request("GET", self.os_url, headers=headers, params=querystring)
            return self.response.status_code == 200
        except Exception as e:
            print(e)
            return False

    def parse_response_object(self):
        base = self.response.json()['asset_events'][0]
        asset = base['asset']
        try:
            name = str(asset['name'])
        except TypeError:
            return False
        image_url = asset['image_original_url']
        seller_address = str(base['seller']['address'])
        buyer_address = str(asset['owner']['address'])
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
        if seller_address != buyer_address or seller != buyer:
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
            tx_hash = str(base['transaction']['transaction_hash'])
            transaction = OpenSeaTransactionObject(name, image_url, seller, buyer, eth_nft_price, usd_price,
                                                   total_usd_cost, the_date, the_time)
            transaction.create_twitter_caption()
            if tx_hash in self.tx_hash_set:
                return False
            self.tx_hash_set.add(tx_hash)
            self.os_obj_to_post = transaction
            return True

    def download_image(self):
        r = requests.get(self.os_obj_to_post.image_url, stream=True)
        if r.status_code == 200:
            r.raw.decode_content = True
            with open(self.file_name, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
            time.sleep(5)

    def post_to_twitter(self):
        twitter_keys = open('twitter_keys.txt', 'r')
        api_key = twitter_keys.readline().split(":")[1].strip()
        api_key_secret = twitter_keys.readline().split(":")[1].strip()
        access_token = twitter_keys.readline().split(":")[1].strip()
        access_token_secret = twitter_keys.readline().split(":")[1].strip()
        twitter_keys.close()

        twitter = Twython(
            api_key,
            api_key_secret,
            access_token,
            access_token_secret
        )

        try:
            image = open(self.file_name, 'rb')
            response = twitter.upload_media(media=image)
            image.close()
            media_id = [response['media_id']]
            twitter.update_status(status=self.os_obj_to_post.twitter_caption + '\n\n' +
                                  self.twitter_tags, media_ids=media_id)
            return True
        except Exception as e:
            print(e)
            return False


post = PostFromOpenSeaTwitter()
while True:
    os_api_working = post.get_most_recent_sale()
    date_time_now = datetime.datetime.fromtimestamp(time.time()).strftime('%m/%d/%Y %H:%M:%S')
    if os_api_working:
        new_post_exists = post.parse_response_object()
        if new_post_exists:
            post.download_image()
            posted_to_twitter = post.post_to_twitter()
            if posted_to_twitter:
                print('Posted to Twitter roughly', date_time_now)
                time.sleep(5)
            else:
                print('Post to Twitter error at roughly', date_time_now)
                time.sleep(10)
        else:
            print('No new post at roughly', date_time_now)
            time.sleep(5)
    else:
        print('OS API is not working at roughly', date_time_now)
        time.sleep(15)
