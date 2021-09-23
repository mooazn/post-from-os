import requests
import os

url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token'
tokens = open('generate_user_token_values.txt')
client_id = tokens.readline().split(":")[1]
client_secret = tokens.readline().split(":")[1]
fb_exchange_token = tokens.readline().split(":")[1]
file = tokens.readline().split(":")[1]
path = tokens.readline().split(":")[1]
tokens.close()

querystring = {"client_id": client_id,
               "client_secret": client_secret,
               "fb_exchange_token": fb_exchange_token}

headers = {"Accept": "application/json"}
response = requests.request("GET", url, headers=headers, params=querystring)
long_life_access_token = response.json()['access_token']
os.remove(path)
token_file = open(file, 'w')
token_file.write(long_life_access_token)
token_file.close()