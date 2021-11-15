import base64
import datetime
from email.mime.text import MIMEText
import os
import requests
import selenium.common.exceptions
from selenium import webdriver
import smtplib
import time
from tinydb import TinyDB, Query
from webdriver_manager.chrome import ChromeDriverManager

# TODO:
#  I need to find a way to limit posts per day to 25 only.
#  25 is the maximum number of posts you can do per day with the API.


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
        self.insta_caption = '{} has been purchased on {} at {} (UTC).\n\nSeller {} has sold their NFT to {} for ' \
                             'the price of ${}!\n\nAt the time of purchase, the price of the NFT was {} ETH and ' \
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
        self.file_name = self.values.readline().strip()
        self.img_bb_key = self.values.readline().strip()
        self.insta_tags = self.values.readline()
        self.page_id = self.values.readline().strip()
        self.contract_address = self.values.readline().strip()
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
            tx_hash = str(base['transaction']['transaction_hash'])
            tx_exists = False if len(self.tx_db.search(self.tx_query.tx == tx_hash)) == 0 else True
            if tx_exists:
                continue
            try:
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
    def __init__(self, instagram_values_file, instagram_user_access_token_file, facebook_credentials_file,
                 tx_hash_db_name):
        self.__base_obj = _PostFromOpenSeaInstagram(instagram_values_file, instagram_user_access_token_file,
                                                    tx_hash_db_name)
        self.gen_long_lived_token_class = GenerateLongLivedToken(facebook_credentials_file)
        self.gen_long_lived_token_class.generate()
        print('Generated token for first time!', flush=True)
        self.begin()

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
            print('Posted to Instagram at roughly', date_time_now, flush=True)
            time.sleep(60)
        else:
            print('Post to Instagram error at roughly', date_time_now, flush=True)
            time.sleep(120)

    def begin(self):
        while True:
            date_time_now = datetime.datetime.fromtimestamp(time.time()).strftime('%m/%d/%Y %H:%M:%S')
            self.run_methods(date_time_now)
            time_now = int(time.time())
            if self.gen_long_lived_token_class.generated_time is not None:
                time_elapsed_since_token_generated = time_now - self.gen_long_lived_token_class.generated_time
                if time_elapsed_since_token_generated > 3600 * 24 * 50:  # 50 days
                    generated = self.gen_long_lived_token_class.generate()
                    if generated:
                        print('Generated new long lived user access token at roughly', date_time_now, flush=True)
                    else:
                        print('Generating token failed. Email sent.', date_time_now, flush=True)


class GenerateLongLivedToken:
    def __init__(self, token_file):
        self.driver = None
        self.graph_explorer_url_redirect = 'https://www.facebook.com/login/?next=https%3A%2F%2Fdevelopers' \
                                           '.facebook.com%2Ftools%2Fexplorer%2F'
        self.api_fb_exchange_token = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token'
        self.graph_explorer_url = 'https://developers.facebook.com/tools/explorer/'
        self.fb_exchange_token = None
        self.generated_time = None
        self.email_field_xpath = '//*[@id="email"]'
        self.pwd_field_xpath = '//*[@id="pass"]'
        self.login_btn_xpath = '//*[@id="loginbutton"]'
        self.gen_btn_xpath = '//*[@id="facebook"]/body/div[1]/div[5]/div[2]/div/div[2]/span/div/div[2]/div/div[' \
                             '5]/div[5]/div/div/div/div/div/div[2]/div/button '
        self.continue_btn_xpath = '//*[@id="platformDialogForm"]/div/div/div/div/div/div[3]/div[1]/div[1]/div[2]'
        self.copy_btn_xpath = '/html/body/div[1]/div[5]/div[2]/div/div[2]/span/div/div[2]/div/div[5]/div[' \
                              '5]/div/div/div/div/div/div[2]/div/div/div[1]/label/input'
        tokens = open(token_file, 'r')
        self.client_id = tokens.readline().strip()
        self.client_secret = tokens.readline().strip()
        self.token_file = tokens.readline().strip()
        self.facebook_email = tokens.readline().strip()
        self.facebook_password = tokens.readline().strip()
        self.gmail_email = tokens.readline().strip()
        self.gmail_password = tokens.readline().strip()
        self.gmail_to_email = tokens.readline().strip()
        tokens.close()

    def generate(self):
        try:
            self.generate_short_lived_user_access_token()
            token = self.get_long_lived_user_access_token()
            self.replace_old_token_with_new(token)
            self.generated_time = int(time.time())
            return True
        except Exception as e:
            print(e, flush=True)
            self.driver.quit()
            self.send_email_to_manually_change_user_token()
            return False

    def generate_short_lived_user_access_token(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument("--kiosk")
        options.headless = True
        options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
        self.driver.get(self.graph_explorer_url_redirect)
        email_field = self.driver.find_element_by_xpath(self.email_field_xpath)
        email_field.send_keys(self.facebook_email)
        password_field = self.driver.find_element_by_xpath(self.pwd_field_xpath)
        password_field.send_keys(self.facebook_password)
        login_button = self.driver.find_element_by_xpath(self.login_btn_xpath)
        login_button.click()
        time.sleep(3)
        self.driver.get(self.graph_explorer_url)
        gen_short_lived_access_token_button = self.driver.find_element_by_xpath(self.gen_btn_xpath)
        gen_short_lived_access_token_button.click()
        window_before = self.driver.window_handles[0]
        window_after = self.driver.window_handles[1]
        self.driver.switch_to.window(window_after)
        self.driver.maximize_window()
        continue_button = self.driver.find_element_by_xpath(self.continue_btn_xpath)
        continue_button.click()
        self.driver.implicitly_wait(3)
        close_again_flag = True
        try:
            short_lived_access_token = self.driver.find_element_by_xpath(self.copy_btn_xpath).get_attribute('value')
        except selenium.common.exceptions.NoSuchWindowException:
            self.driver.switch_to.window(window_before)
            short_lived_access_token = self.driver.find_element_by_xpath(self.copy_btn_xpath).get_attribute('value')
            close_again_flag = False
        self.driver.close()
        if close_again_flag:
            self.driver.switch_to.window(window_before)
            self.driver.close()
        self.driver.quit()
        self.fb_exchange_token = short_lived_access_token

    def get_long_lived_user_access_token(self):
        querystring = {"client_id": self.client_id,
                       "client_secret": self.client_secret,
                       "fb_exchange_token": self.fb_exchange_token}

        headers = {"Accept": "application/json"}
        response = requests.request("GET", self.api_fb_exchange_token, headers=headers, params=querystring)
        long_lived_access_token = response.json()['access_token']
        return long_lived_access_token

    def replace_old_token_with_new(self, token):
        if os.path.exists(self.token_file):
            os.remove(self.token_file)
        token_file = open(self.token_file, 'w')
        token_file.write(token)
        token_file.close()

    def send_email_to_manually_change_user_token(self):
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_username = self.gmail_email
        smtp_password = self.gmail_password

        email_to = [self.gmail_to_email]
        email_from = self.gmail_email
        email_subject = "Refresh Exchange Token"
        email_space = ", "
        data = 'Refresh the long user token.'
        msg = MIMEText(data)
        msg['Subject'] = email_subject
        msg['To'] = email_space.join(email_to)
        msg['From'] = email_from
        mail = smtplib.SMTP(smtp_server, smtp_port)
        mail.starttls()
        mail.login(smtp_username, smtp_password)
        mail.sendmail(email_from, email_to, msg.as_string())
        mail.quit()
