import os
import smtplib
from email.mime.text import MIMEText

import pyperclip
import requests
from selenium import webdriver
import time

from webdriver_manager.chrome import ChromeDriverManager

options = webdriver.ChromeOptions()
options.add_argument('--no-sandbox')
options.add_argument("--kiosk")
options.headless = True
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
driver.get('https://www.facebook.com/login/?next=https%3A%2F%2Fdevelopers.facebook.com%2Ftools%2Fexplorer%2F')
email_field = driver.find_element_by_xpath('//*[@id="email"]')
email_field.send_keys('email')
password_field = driver.find_element_by_xpath('//*[@id="pass"]')
password_field.send_keys('pwd')
login_button = driver.find_element_by_xpath('//*[@id="loginbutton"]')
login_button.click()
time.sleep(3)
driver.get('https://developers.facebook.com/tools/explorer/')
gen_short_lived_access_token_button = driver.find_element_by_xpath(
    '//*[@id="facebook"]/body/div[1]/div[5]/div[2]/div/div[2]/span/div/div[2]/div/div[5]/div['
    '5]/div/div/div/div/div/div[2]/div/button')
gen_short_lived_access_token_button.click()
window_before = driver.window_handles[0]
window_after = driver.window_handles[1]
driver.switch_to.window(window_after)
driver.maximize_window()
continue_button = driver.find_element_by_xpath('//*[@id="platformDialogForm"]/div/div/div/div/div/div[3]/div[1]/div['
                                               '1]/div[2]')
continue_button.click()
driver.implicitly_wait(3)
close_again_flag = True
try:
    short_lived_access_token = driver.find_element_by_xpath('/html/body/div[1]/div[5]/div[2]/div/div[2]/span/div/div['
                                                            '2]/div/div[5]/div[5]/div/div/div/div/div/div['
                                                            '2]/div/div/div[1]/label/input').get_attribute('value')
except Exception:
    driver.switch_to.window(window_before)
    short_lived_access_token = driver.find_element_by_xpath('/html/body/div[1]/div[5]/div[2]/div/div[2]/span/div/div['
                                                            '2]/div/div[5]/div[5]/div/div/div/div/div/div['
                                                            '2]/div/div/div[1]/label/input').get_attribute('value')
    close_again_flag = False
driver.close()
if close_again_flag:
    driver.switch_to.window(window_before)
    driver.close()
print(short_lived_access_token)
driver.quit()
# 
# 
# class GenerateLongLivedToken:
#     def __init__(self, token_file):
#         self.graph_explorer_url_redirect = 'https://www.facebook.com/login/?next=https%3A%2F%2Fdevelopers' \
#                                            '.facebook.com%2Ftools%2Fexplorer%2F'
#         self.api_url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token'
#         self.fb_exchange_token = None
#         self.generated_time = None
#         self.email_field_xpath = '//*[@id="email"]'
#         self.pwd_field_xpath = '//*[@id="pass"]'
#         self.login_btn_xpath = '//*[@id="loginbutton"]'
#         self.gen_btn_xpath = '//*[@id="facebook"]/body/div[1]/div[5]/div[2]/div/div[2]/span/div/div[2]/div/div[' \
#                              '5]/div[5]/div/div/div/div/div/div[2]/div/button '
#         self.cnt_btn_xpath = '//*[@id="platformDialogForm"]/div/div/div/div/div/div[3]/div[1]/div[1]/div[2]'
#         self.cb_btn_xpath = '//*[@id="facebook"]/body/div[1]/div[5]/div[2]/div/div[2]/span/div/div[2]/div/div[5]/div[' \
#                             '5]/div/div/div/div/div/div[2]/div/div/div[2] '
#         tokens = open(token_file, 'r')
#         self.client_id = tokens.readline().split(":")[1].strip()
#         self.client_secret = tokens.readline().split(":")[1].strip()
#         self.file = tokens.readline().split(":")[1].strip()
#         self.email = tokens.readline().split(":")[1].strip()
#         self.password = tokens.readline().split(":")[1].strip()
#         tokens.close()
# 
#     def generate_short_lived_user_access_token(self):
#         options = webdriver.ChromeOptions()
#         options.add_argument('--no-sandbox')
#         options.headless = True
#         options.add_argument('--disable-dev-shm-usage')
#         driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
#         driver.get(self.graph_explorer_url_redirect)
#         email_field = driver.find_element_by_xpath(self.email_field_xpath)
#         email_field.send_keys(self.email)
#         password_field = driver.find_element_by_xpath(self.pwd_field_xpath)
#         password_field.send_keys(self.password)
#         login_button = driver.find_element_by_xpath(self.login_btn_xpath)
#         login_button.click()
#         gen_short_lived_access_token_button = driver.find_element_by_xpath(self.gen_btn_xpath)
#         gen_short_lived_access_token_button.click()
#         driver.implicitly_wait(3)
#         window_before = driver.window_handles[0]
#         window_after = driver.window_handles[1]
#         driver.switch_to.window(window_after)
#         driver.maximize_window()
#         continue_button = driver.find_element_by_xpath(self.cnt_btn_xpath)
#         continue_button.click()
#         driver.implicitly_wait(3)
#         close_again_flag = True
#         try:
#             copy_to_clipboard_button = driver.find_element_by_xpath(self.cb_btn_xpath)
#         except Exception:
#             driver.switch_to.window(window_before)
#             copy_to_clipboard_button = driver.find_element_by_xpath(self.cb_btn_xpath)
#             close_again_flag = False
#         copy_to_clipboard_button.click()
#         short_lived_access_token = pyperclip.paste()
#         driver.close()
#         if close_again_flag:
#             driver.switch_to.window(window_before)
#             driver.close()
#         driver.quit()
#         self.fb_exchange_token = short_lived_access_token
# 
#     def get_long_lived_user_access_token(self):
#         querystring = {"client_id": self.client_id,
#                        "client_secret": self.client_secret,
#                        "fb_exchange_token": self.fb_exchange_token}
# 
#         headers = {"Accept": "application/json"}
#         response = requests.request("GET", self.api_url, headers=headers, params=querystring)
#         long_lived_access_token = response.json()['access_token']
#         self.generated_time = int(time.time())
#         return long_lived_access_token
# 
#     def replace_old_token_with_new(self, token):
#         if os.path.exists(self.file):
#             os.remove(self.file)
#         token_file = open(self.file, 'w')
#         token_file.write(token)
#         token_file.close()
# 
# o = GenerateLongLivedToken('instagram_generate_user_token_values.txt')
# o.generate_short_lived_user_access_token()
# tkn = o.get_long_lived_user_access_token()
# o.replace_old_token_with_new(tkn)
# print(tkn)
