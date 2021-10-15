import base64
import shutil
import requests
import time
import datetime
from email.mime.text import MIMEText
import smtplib
from tinydb import TinyDB, Query


class _OpenSeaTransactionObjectInstagram:
    insta_caption = None

    def __init__(self, name_, image_url_, seller_, buyer_, eth_nft_price_, usd_price_, total_usd_cost_,
                 the_date_, the_time_, insta_tags_):
        self.name = name_
        self.image_url = image_url_
        self.seller = seller_
        self.buyer = buyer_
        self.eth_nft_price = eth_nft_price_
        self.usd_price = usd_price_
        self.total_usd_cost = total_usd_cost_
        self.the_date = the_date_
        self.the_time = the_time_
        self.insta_tags = insta_tags_
        self.is_posted = False

    def create_insta_caption(self):
        self.insta_caption = '{} has been purchased on {} at {} (UTC).\n\nSeller {} has sold their Siren to {} for ' \
                             'the price of ${}!\n\nAt the time of purchase, the price of the Siren was {} ETH and ' \
                             'the price of ETH was ${}.\n\n{}'.format(self.name, self.the_date, self.the_time,
                                                                      self.seller, self.buyer, self.total_usd_cost,
                                                                      self.eth_nft_price, self.usd_price,
                                                                      self.insta_tags)


class _PostFromOpenSeaInstagram:
    def __init__(self, values_file, access_token_file, db_name):
        instagram_values_file = values_file
        self.instagram_access_token_file = access_token_file
        tx_hash_db = db_name
        self.values = open(instagram_values_file, 'r')
        self.file_name = self.values.readline().split(":")[1].strip()
        self.img_bb_key = self.values.readline().split(":")[1].strip()
        self.insta_tags = self.values.readline().split(":")[1]
        self.page_id = self.values.readline().split(":")[1].strip()
        self.contract_address = self.values.readline().split(":")[1].strip()
        self.values.close()
        self.os_url = "https://api.opensea.io/api/v1/events"
        self.insta_id_url = 'https://graph.facebook.com/v10.0/{}?fields=instagram_business_account'. \
            format(self.page_id)
        self.graph_api_url = 'https://graph.facebook.com/v10.0/'
        self.image_link = None
        self.response = None
        self.os_obj_to_post = None
        self.limit = 5
        self.tx_queue = []
        self.tx_db = TinyDB(tx_hash_db)
        self.tx_query = Query()

    def get_recent_sales(self):
        try:
            querystring = {"asset_contract_address": self.contract_address,
                           "event_type": "successful",
                           "only_opensea": "false",
                           "offset": "0",
                           "limit": self.limit}
            headers = {"Accept": "application/json"}
            self.response = requests.request("GET", self.os_url, headers=headers, params=querystring)
            return self.response.status_code == 200
        except Exception as e:
            print(e, flush=True)
            return False

    def parse_response_objects(self):
        for i in range(0, self.limit):
            base = self.response.json()['asset_events'][i]
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
            if seller_address == buyer_address or seller == buyer:
                continue
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
            tx_exists = False if len(self.tx_db.search(self.tx_query.tx == tx_hash)) == 0 else True
            if tx_exists:
                continue
            self.tx_db.insert({'tx': tx_hash})
            transaction = _OpenSeaTransactionObjectInstagram(name, image_url, seller, buyer, eth_nft_price, usd_price,
                                                             total_usd_cost, the_date, the_time, self.insta_tags)
            transaction.create_insta_caption()
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

    def post_to_image_bb(self):
        with open(self.file_name, "rb") as file:
            url = "https://api.imgbb.com/1/upload?expiration=60"
            payload = {
                "key": self.img_bb_key,
                "image": base64.b64encode(file.read()),
            }
            res = requests.post(url, payload)
            image_url = str(res.json()['data']['url'])
            image_url = image_url[:len(image_url) - 3]
            self.image_link = image_url + 'jpg'

    def post_to_instagram(self):
        user_access_token_file = open(self.instagram_access_token_file, 'r')
        user_access_token = user_access_token_file.readline()
        user_access_token_file.close()

        querystring = {"access_token": user_access_token}
        headers = {"Accept": "application/json"}
        response = requests.request("GET", self.insta_id_url, headers=headers, params=querystring)
        insta_id = response.json()['instagram_business_account']['id']

        pre_upload_url = self.graph_api_url + '{}/media'.format(insta_id)
        pre_upload = {'image_url': self.image_link,
                      'caption': self.os_obj_to_post.insta_caption,
                      'access_token': user_access_token}
        pre_upload_request = requests.post(pre_upload_url, data=pre_upload)
        pre_upload_result = pre_upload_request.json()

        if 'id' in pre_upload_result:
            creation_id = pre_upload_result['id']
            publish_url = self.graph_api_url + '{}/media_publish'.format(insta_id)
            publish = {
                'creation_id': creation_id,
                'access_token': user_access_token
            }
            requests.post(publish_url, data=publish)
            self.os_obj_to_post.is_posted = True
            return True
        else:
            print(pre_upload_result, flush=True)
            return False


class ManageFlowObj:
    def __init__(self, instagram_values_file, instagram_user_access_token_file, instagram_email_credentials_file,
                 tx_hash_db_name):
        self.start_time = time.time()
        self.email_credentials_file = instagram_email_credentials_file
        self.__base_obj = _PostFromOpenSeaInstagram(instagram_values_file, instagram_user_access_token_file,
                                                    tx_hash_db_name)
        self._begin()

    def run_methods(self, date_time_now):
        self.check_os_api_status(date_time_now)

    def check_os_api_status(self, date_time_now):
        os_api_working = self.__base_obj.get_recent_sales()
        if os_api_working:
            self.check_if_new_post_exists(date_time_now)
        else:
            print('OS API is not working at roughly', date_time_now, flush=True)
            time.sleep(300)

    def check_if_new_post_exists(self, date_time_now):
        new_post_exists = self.__base_obj.parse_response_objects()
        if new_post_exists:
            self.try_to_download_image(date_time_now)
        else:
            print('No new post at roughly', date_time_now, flush=True)
            time.sleep(60)

    def try_to_download_image(self, date_time_now):
        image_downloaded = self.__base_obj.download_image()
        if image_downloaded:
            self.post_to_image_bb(date_time_now)
        else:
            print('Downloading image error at roughly', date_time_now, flush=True)
            time.sleep(60)

    def post_to_image_bb(self, date_time_now):
        self.__base_obj.post_to_image_bb()
        self.try_to_post_to_instagram(date_time_now)

    def try_to_post_to_instagram(self, date_time_now):
        posted_to_instagram = self.__base_obj.post_to_instagram()
        if posted_to_instagram:
            print('Posted to Instagram roughly', date_time_now, flush=True)
            time.sleep(60)
        else:
            print('Post to Instagram error at roughly', date_time_now, flush=True)
            time.sleep(120)

    def send_email_to_refresh_access_token(self, date_time_now):
        email_credentials_file = open(self.email_credentials_file, 'r')
        username = email_credentials_file.readline().split(":")[1]
        password = email_credentials_file.readline().split(":")[1]
        to_email = email_credentials_file.readline().split(":")[1]
        email_credentials_file.close()

        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_username = username
        smtp_password = password

        email_to = [to_email]
        email_from = username
        email_subject = "Refresh Exchange Token"
        email_space = ", "
        data = 'Refresh the token.'
        msg = MIMEText(data)
        msg['Subject'] = email_subject
        msg['To'] = email_space.join(email_to)
        msg['From'] = email_from
        mail = smtplib.SMTP(smtp_server, smtp_port)
        mail.starttls()
        mail.login(smtp_username, smtp_password)
        mail.sendmail(email_from, email_to, msg.as_string())
        mail.quit()
        print('Sent email to refresh token at roughly', date_time_now, flush=True)

    def _begin(self):
        while True:
            date_time_now = datetime.datetime.fromtimestamp(time.time()).strftime('%m/%d/%Y %H:%M:%S')
            self.run_methods(date_time_now)
            time_now = time.time()
            if (time_now - self.start_time) >= 1728000:
                self.send_email_to_refresh_access_token(date_time_now)
