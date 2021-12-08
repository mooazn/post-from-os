import pprint


from tinydb import TinyDB, Query

# x = TinyDB('yachts_db_dup.json')
# xq = Query()
# query = x.search(xq.id == 4023)
# owner = eval(query[0]['traits'])
# address = owner['owner']
# owner['address'] = '0xDEAD'
# print(owner)
# x.update({'traits': str(owner)}, xq.id == 4023)
# query2 = x.search(xq.id == 4023)
# owner2 = eval(query[0]['traits'])['owner']
# pprint.pprint(owner2)
# owner['address'] = address
# pprint.pprint(query)
# print(query_eval['asset_contract']['name'])
# 0x4028e779605bba9d59204c7eabd0b9bf039f486c

import requests

url = "https://api.opensea.io/api/v1/asset/0x24d0cbd0d5d7b50212251c5dc7cb810e7af71f6a/4955/"
request = requests.get(url)
print(request.status_code)
