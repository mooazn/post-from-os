import base64
import shutil
import requests
import time
import datetime
from email.mime.text import MIMEText
import smtplib


class OpenSeaTransactionObjectInstagram:
    insta_caption = None

    def __init__(self, name_, image_url_, seller_, buyer_, eth_nft_price_, usd_price_, total_usd_cost_,
                 the_date_, the_time_):
        self.name = name_
        self.image_url = image_url_
        self.seller = seller_
        self.buyer = buyer_
        self.eth_nft_price = eth_nft_price_
        self.usd_price = usd_price_
        self.total_usd_cost = total_usd_cost_
        self.the_date = the_date_
        self.the_time = the_time_
        self.is_posted = False

    def create_insta_caption(self):
        first_s = self.name + ' has been purchased on ' + self.the_date + ' at ' + self.the_time + ' (UTC).'
        second_s = 'Seller \'' + self.seller + '\' has sold their siren to \'' + self.buyer + '\' for the price of ' + \
                   '$' + str(self.total_usd_cost) + '! '
        third_s = 'At the time of purchase, the price of the Siren was ' + str(self.eth_nft_price) + \
                  ' ETH and the price of ETH was $' + str(self.usd_price) + '. '
        self.insta_caption = first_s + '\n\n' + second_s + '\n\n' + third_s


class PostFromOpenSeaInstagram:
    def __init__(self):
        self.values = open('values.txt', 'r')
        self.file_name = self.values.readline().split(":")[1].strip()
        self.img_bb_key = self.values.readline().split(":")[1].strip()
        self.insta_tags = self.values.readline().split(":")[1]
        self.page_id = self.values.readline().split(":")[1].strip()
        self.values.close()
        self.os_url = "https://api.opensea.io/api/v1/events"
        self.insta_id_url = 'https://graph.facebook.com/v10.0/{}?fields=instagram_business_account'. \
            format(self.page_id)
        self.graph_api_url = 'https://graph.facebook.com/v10.0/'
        self.image_link = None
        self.response = None
        self.os_obj_to_post = None
        self.driver = None
        self.tx_queue = []
        self.tx_hash_set = {''}

    def get_four_recent_sales(self):
        try:
            querystring = {"asset_contract_address": "0x42e10846bbc6d062d1a41a8883ce2b81015a9523",
                           "event_type": "successful",
                           "only_opensea": "false",
                           "offset": "0",
                           "limit": "4"}
            headers = {"Accept": "application/json"}
            self.response = requests.request("GET", self.os_url, headers=headers, params=querystring)
            return self.response.status_code == 200
        except Exception as e:
            print(e)
            return False

    def parse_response_objects(self):
        for i in range(0, 4):
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
            transaction = OpenSeaTransactionObjectInstagram(name, image_url, seller, buyer, eth_nft_price, usd_price,
                                                            total_usd_cost, the_date, the_time)
            transaction.create_insta_caption()
            if tx_hash in self.tx_hash_set:
                continue
            self.tx_queue.append(transaction)
            self.tx_hash_set.add(tx_hash)

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
        r = requests.get(self.os_obj_to_post.image_url, stream=True)
        if r.status_code == 200:
            r.raw.decode_content = True
            with open(self.file_name, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
            time.sleep(5)

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
        user_access_token_file = open('user_access_token.txt', 'r')
        user_access_token = user_access_token_file.readline()
        user_access_token_file.close()

        querystring = {"access_token": user_access_token}
        headers = {"Accept": "application/json"}
        response = requests.request("GET", self.insta_id_url, headers=headers, params=querystring)
        insta_id = response.json()['instagram_business_account']['id']

        pre_upload_url = self.graph_api_url + '{}/media'.format(insta_id)
        pre_upload = {'image_url': self.image_link,
                      'caption': self.os_obj_to_post.insta_caption + '\n\n' + self.insta_tags,
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
            print(pre_upload_result)
            return False


start_time = time.time()
post = PostFromOpenSeaInstagram()
while True:
    os_api_working = post.get_four_recent_sales()
    date_time_now = datetime.datetime.fromtimestamp(time.time()).strftime('%m/%d/%Y %H:%M:%S')
    if os_api_working:
        new_post_exists = post.parse_response_objects()
        if new_post_exists:
            post.download_image()
            post.post_to_image_bb()
            posted_to_instagram = post.post_to_instagram()
            if posted_to_instagram:
                print('Posted to Instagram roughly', date_time_now)
                time.sleep(70)
            else:
                print('Post to Instagram error at roughly', date_time_now)
                time.sleep(120)
        else:
            print('No new post at roughly', date_time_now)
            time.sleep(60)
    else:
        print('OS API is not working at roughly', date_time_now)
        time.sleep(300)
    time_now = time.time()
    if (time_now - start_time) >= 3456000:
        email_credentials_file = open('email_creds.txt', 'r')
        username = email_credentials_file.readline().split(":")[1]
        password = email_credentials_file.readline().split(":")[1]
        to_email = email_credentials_file.readline().split(":")[1]
        email_credentials_file.close()

        SMTP_SERVER = "smtp.gmail.com"
        SMTP_PORT = 587
        SMTP_USERNAME = username
        SMTP_PASSWORD = password

        EMAIL_TO = [to_email]
        EMAIL_FROM = username
        EMAIL_SUBJECT = "Refresh Exchange Token"
        EMAIL_SPACE = ", "
        DATA = 'Refresh the token.'
        msg = MIMEText(DATA)
        msg['Subject'] = EMAIL_SUBJECT
        msg['To'] = EMAIL_SPACE.join(EMAIL_TO)
        msg['From'] = EMAIL_FROM
        mail = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        mail.starttls()
        mail.login(SMTP_USERNAME, SMTP_PASSWORD)
        mail.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        mail.quit()
        print('Sent email to refresh token at roughly', date_time_now)
