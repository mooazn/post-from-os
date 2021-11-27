import requests


tokens = open('instagram_generate_user_token_values_sirens.txt', 'r')
client_id = tokens.readline().strip()
client_secret = tokens.readline().strip()
tokens.close()
short_lived_access_token = 'PASTE HERE'
api_fb_exchange_token_url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token'

querystring = {"client_id": client_id,
               "client_secret": client_secret,
               "fb_exchange_token": short_lived_access_token}

headers = {"Accept": "application/json"}
response = requests.request("GET", api_fb_exchange_token_url, headers=headers, params=querystring)
long_lived_access_token = response.json()['access_token']
print(long_lived_access_token)
