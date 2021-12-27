import base64
import datetime
from email.mime.text import MIMEText
import os
import requests
import selenium.common.exceptions
from requests.structures import CaseInsensitiveDict
from selenium import webdriver
import smtplib
import time
from tinydb import TinyDB, Query
from webdriver_manager.chrome import ChromeDriverManager


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
    def __init__(self, values_file, contract_address):
        instagram_values_file = values_file
        self.instagram_access_token_file = 'instagram_user_access_token_{}.txt'.format(contract_address)
        self.values = open(instagram_values_file, 'r')
        self.insta_tags = self.values.readline()
        self.collection_name = self.values.readline().strip()
        self.img_bb_key = self.values.readline().strip()
        self.page_id = self.values.readline().strip()
        self.os_api_key = self.values.readline().strip()
        self.values.close()
        self.contract_address = contract_address
        self.file_name = self.collection_name + '_instagram.jpeg'
        self.os_url = "https://api.opensea.io/api/v1/events"
        self.insta_id_url = 'https://graph.facebook.com/v10.0/{}?fields=instagram_business_account'. \
            format(self.page_id)
        self.graph_api_url = 'https://graph.facebook.com/v10.0/'
        self.image_link = None
        self.response = None
        self.os_obj_to_post = None
        self.limit = 5
        self.daily_posts = 0
        self.tomorrow = int(time.time()) + 86400
        self.tx_queue = []
        self.tx_db = TinyDB(self.collection_name + '_tx_hash_instagram_db.json')
        self.tx_query = Query()

    def get_recent_sales(self):
        try:
            querystring = {"asset_contract_address": self.contract_address,
                           "event_type": "successful",
                           "only_opensea": "false",
                           "offset": "0",
                           "limit": self.limit}
            headers = CaseInsensitiveDict()
            headers['Accept'] = 'application/json'
            headers['x-api-key'] = self.os_api_key
            self.response = requests.get(self.os_url, headers=headers, params=querystring, timeout=1.5)
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
        if self.daily_posts == 25:
            if self.tomorrow - int(time.time()) <= 0:
                self.daily_posts = 0
                self.tomorrow = int(time.time()) + 86400
            else:
                return -1
        try:
            img_response = requests.get(self.os_obj_to_post.image_url, stream=True, timeout=2)
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
            res = requests.post(url, payload, timeout=2)
            image_url = str(res.json()['data']['url'])
            image_url = image_url[:len(image_url) - 3]
            self.image_link = image_url + 'jpg'

    def post_to_instagram(self):
        user_access_token_file = open(self.instagram_access_token_file, 'r')
        user_access_token = user_access_token_file.readline()
        user_access_token_file.close()

        querystring = {"access_token": user_access_token}
        headers = {"Accept": "application/json"}
        response = requests.get(self.insta_id_url, headers=headers, params=querystring, timeout=2)
        insta_id = response.json()['instagram_business_account']['id']

        pre_upload_url = self.graph_api_url + '{}/media'.format(insta_id)
        pre_upload = {'image_url': self.image_link,
                      'caption': self.os_obj_to_post.insta_caption,
                      'access_token': user_access_token}
        pre_upload_request = requests.post(pre_upload_url, data=pre_upload, timeout=2)
        pre_upload_result = pre_upload_request.json()

        if 'id' in pre_upload_result:
            creation_id = pre_upload_result['id']
            publish_url = self.graph_api_url + '{}/media_publish'.format(insta_id)
            publish = {
                'creation_id': creation_id,
                'access_token': user_access_token
            }
            requests.post(publish_url, data=publish, timeout=2)
            self.os_obj_to_post.is_posted = True
            self.daily_posts += 1
            return True
        else:
            print(pre_upload_result, flush=True)
            return False


class ManageFlowObj:
    def __init__(self, instagram_values_file, instagram_generate_long_user_token_credentials_file):
        self.instagram_values_file = instagram_values_file
        self.instagram_gen_token_file = instagram_generate_long_user_token_credentials_file
        contract_address = self.validate_params()
        self.begin_time = int(time.time())
        self.gen_long_lived_token_class = GenerateLongLivedToken(self.instagram_gen_token_file, contract_address)
        # first_time_generated = self.gen_long_lived_token_class.generate()
        # if first_time_generated:
        #     print('Generated token for first time!', flush=True)
        self.__base_obj = _PostFromOpenSeaInstagram(self.instagram_values_file, contract_address)
        self.begin()

    def validate_params(self):
        print('Beginning validation of Instagram Values File...')
        with open(self.instagram_values_file) as values_file:
            if len(values_file.readlines()) != 5:
                raise Exception('The Instagram Values file must be formatted correctly.')
        test_instagram_values = open(self.instagram_values_file, 'r')
        hashtags_test = test_instagram_values.readline().strip()
        hashtags = 0
        words_in_hash_tag = hashtags_test.split()
        if hashtags_test != 'None':
            if len(hashtags_test) == 0 or hashtags_test.split() == 0:
                test_instagram_values.close()
                raise Exception('Hashtags field is empty.')
            if len(hashtags_test) >= 1500:
                test_instagram_values.close()
                raise Exception('Too many characters in hashtags.')
            if len(words_in_hash_tag) > 25:
                test_instagram_values.close()
                raise Exception('Too many hashtags.')
            for word in words_in_hash_tag:
                if word[0] == '#':
                    hashtags += 1
            if hashtags != len(words_in_hash_tag):
                test_instagram_values.close()
                raise Exception('All words must be preceded by a hashtag (#).')
        print('Hashtags validated...')
        collection_name_test = test_instagram_values.readline().strip()
        test_collection_name_url = 'https://api.opensea.io/api/v1/collection/{}'.format(collection_name_test)
        test_response = requests.get(test_collection_name_url, timeout=1.5)
        if test_response.status_code == 200:
            collection_json = test_response.json()['collection']
            primary_asset_contracts_json = collection_json['primary_asset_contracts'][0]  # got the contract address
            contract_address = primary_asset_contracts_json['address']
        else:
            test_instagram_values.close()
            raise Exception('The provided collection name does not exist.')
        print('Collection validated...')
        test_img_bb_key = test_instagram_values.readline().strip()
        test_img_bb_url = "https://api.imgbb.com/1/upload?expiration=60"
        payload = {
            "key": test_img_bb_key,
            "image": 'https://sienaconstruction.com/wp-content/uploads/2017/05/test-image.jpg',  # just some random pic
        }
        test_upload_req = requests.post(test_img_bb_url, payload, timeout=2)
        if test_upload_req.status_code != 200:
            test_instagram_values.close()
            raise Exception('Invalid img.bb key provided.')
        print('IMG BB key validated...')
        test_page_id = test_instagram_values.readline().strip()
        print('Page ID is:', test_page_id)
        # test_insta_id_url = 'https://graph.facebook.com/v10.0/{}?fields=instagram_business_account'. \
        #     format(test_page_id)
        # test_page_req = requests.get(test_insta_id_url, timeout=2)
        # fake_status_code = int(test_page_req.json()['error']['code'])
        # if fake_status_code != 200:
        #     test_instagram_values.close()
        #     raise Exception('Invalid page ID for Facebook supplied')
        # print('Facebook page ID validated...')
        test_os_key = test_instagram_values.readline().strip()
        if test_os_key != 'None':
            test_os_key_url = "https://api.opensea.io/api/v1/events?only_opensea=false&offset=0&limit=1"
            test_os_headers = CaseInsensitiveDict()
            test_os_headers['Accept'] = 'application/json'
            test_os_headers['x-api-key'] = test_os_key
            test_os_response = requests.get(test_os_key_url, headers=test_os_headers, timeout=2)
            if test_os_response.status_code != 200:
                test_instagram_values.close()
                raise Exception('Invalid OpenSea API key supplied.')
            print('OpenSea Key validated...')
        else:
            print('No OpenSea API Key supplied...')
        print('Validation of Instagram Values .txt complete. No errors found...')
        return contract_address

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
        if image_downloaded == -1:
            print('Daily limit reached for posts.')
            time.sleep(30)
        elif image_downloaded:
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
            if int(time.time()) - self.begin_time >= 3600 * 24 * 20:
                self.gen_long_lived_token_class.send_email_to_manually_change_user_token()
            # time_now = int(time.time())
            # time_elapsed_since_token_generated = None
            # if self.gen_long_lived_token_class.previous_time is not None:
            #     time_elapsed_since_token_generated = time_now - self.gen_long_lived_token_class.previous_time
            # elif self.gen_long_lived_token_class.generated_time is not None:
            #     time_elapsed_since_token_generated = time_now - self.gen_long_lived_token_class.generated_time
            # if time_elapsed_since_token_generated >= 3600 * 24 * 50:
            #     if self.gen_long_lived_token_class.previous_time is None:
            #         self.gen_long_lived_token_class.previous_time = None
            #     generated = self.gen_long_lived_token_class.generate()
            #     if generated:
            #         print('Generated new long lived user access token at roughly', date_time_now, flush=True)
            #     else:
            #         print('Generating token failed. Email sent.', date_time_now, flush=True)


class GenerateLongLivedToken:
    def __init__(self, token_file, contract_address):
        self.driver = None
        self.generated_time = None
        self.graph_explorer_url_redirect = 'https://www.facebook.com/login/?next=https%3A%2F%2Fdevelopers' \
                                           '.facebook.com%2Ftools%2Fexplorer%2F'
        self.api_fb_exchange_token_url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token'
        self.graph_explorer_url = 'https://developers.facebook.com/tools/explorer/'
        self.email_field_xpath = '//*[@id="email"]'
        self.pwd_field_xpath = '//*[@id="pass"]'
        self.login_btn_xpath = '//*[@id="loginbutton"]'
        self.gen_btn_xpath = '//*[@id="facebook"]/body/div[1]/div[5]/div[2]/div/div[2]/span/div/div[2]/div/div[' \
                             '5]/div[5]/div/div/div/div/div/div[2]/div/button '
        self.continue_btn_xpath = '//*[@id="platformDialogForm"]/div/div/div/div/div/div[3]/div[1]/div[1]/div[2]'
        self.copy_btn_xpath = '/html/body/div[1]/div[5]/div[2]/div/div[2]/span/div/div[2]/div/div[5]/div[' \
                              '5]/div/div/div/div/div/div[2]/div/div/div[1]/label/input'
        with open(token_file) as tokens:
            if 7 > len(tokens.readlines()) > 8:
                raise Exception('The Instagram Generate User Token Values file must be formatted correctly.')
        tokens = open(token_file, 'r')
        self.client_id = tokens.readline().strip()
        self.client_secret = tokens.readline().strip()
        self.facebook_email = tokens.readline().strip()
        self.facebook_password = tokens.readline().strip()
        self.gmail_email = tokens.readline().strip()
        self.gmail_password = tokens.readline().strip()
        self.gmail_to_email = tokens.readline().strip()
        self.access_token = tokens.readline().strip()
        tokens.close()
        self.first_time = True
        self.previous_time = None
        self.user_access_token_file = 'instagram_user_access_token_{}.txt'.format(contract_address)
        with open(self.user_access_token_file, 'w') as tk_file:
            if self.access_token != '':
                tk_file.write(self.access_token)
        # if os.path.exists(self.user_access_token_file):
        #     get_time_from_token_file = open(self.user_access_token_file, 'r')
        #     get_time_from_token_file.readline().strip()
        #     previous_generated_time = int(get_time_from_token_file.readline().strip())
        #     difference = int(time.time()) - previous_generated_time
        #     if difference < 3600 * 24 * 50:
        #         self.previous_time = previous_generated_time

    def generate(self):
        if self.previous_time is not None:
            print('Using already existing token', flush=True)
            return False
        try:
            short_lived_access_token = self.generate_short_lived_user_access_token()
            new_token = self.get_long_lived_user_access_token(short_lived_access_token)
            self.replace_old_token_with_new(new_token)
            self.generated_time = int(time.time())
            if self.first_time:
                self.first_time = False
            return True
        except Exception as e:  # if ANY sort of error happens, we must manually reset
            if self.first_time:  # script MUST always work for the first time. of course, it may fail 50+ days from now
                # if the website is changed, but then it is handled accordingly by sending an email and further
                # inspection can take place to fix the script.
                raise Exception('Provided Instagram Generate User Token file is formatted incorrectly.')
            print(e, flush=True)
            self.driver.quit()
            self.send_email_to_manually_change_user_token()
            self.generated_time = int(time.time()) + 3600 * 24 * 2  # allow 2 days for manual reset
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
        return short_lived_access_token

    def get_long_lived_user_access_token(self, short_lived_access_token):
        querystring = {"client_id": self.client_id,
                       "client_secret": self.client_secret,
                       "fb_exchange_token": short_lived_access_token}

        headers = {"Accept": "application/json"}
        response = requests.get(self.api_fb_exchange_token_url, headers=headers, params=querystring, timeout=2)
        long_lived_access_token = response.json()['access_token']
        return long_lived_access_token

    def replace_old_token_with_new(self, token):
        if os.path.exists(self.user_access_token_file):
            os.remove(self.user_access_token_file)
        token_file = open(self.user_access_token_file, 'w')
        token_file.write(token + '\n')
        token_file.write(str(int(time.time())))
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
        data = 'To manually refresh the exchange token, login to the Facebook Graph API Explorer (' \
               'https://developers.facebook.com/tools/explorer/) with your credentials, EMAIL: {}, PASSWORD: {}. ' \
               'Then, click the \'Generate Access Token\' button and follow the steps. Once you are redirected back ' \
               'to the page, simply click the Copy to clipboard button and open ' \
               '\'instagram_manually_reset_long_user_token.py\'. Paste the copied token into the ' \
               '\'short_lived_access_token\' field and run the program. Once the program outputs the long lived user ' \
               'token, copy and paste that token into the file where the token is kept. In your case, the file is ' \
               'called {}. Because automatic execution failed, ensure that the selenium code is properly working.'.\
            format(self.facebook_email, self.facebook_password, self.user_access_token_file)
        msg = MIMEText(data)
        msg['Subject'] = email_subject
        msg['To'] = email_space.join(email_to)
        msg['From'] = email_from
        mail = smtplib.SMTP(smtp_server, smtp_port)
        mail.starttls()
        mail.login(smtp_username, smtp_password)
        mail.sendmail(email_from, email_to, msg.as_string())
        mail.quit()
