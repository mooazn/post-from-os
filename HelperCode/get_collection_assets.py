from fake_useragent import UserAgent
import math
import requests
import time
from tinydb import TinyDB, Query


# This whole script takes roughly 1 hour to run for a collection with 10k assets. Although that is slow, it's a one time
# operation for ultra fast operations on getting assets within a collection. It makes sense, you get a 80 MB file out of
# it! It could be faster with threads. What happens when the owner changes? Here's a simple way to replace the previous
# owner:

# ID = 10
# x = TinyDB('db.json')
# xq = Query()
# query = x.search(xq.id == ID)
# base = eval(query[0]['asset_json'])
# owner = base['owner']
# prev_address = owner['address']
# owner['address'] = 'NEW_ADDRESS'
# x.update({'asset_json': str(base)}, xq.id == ID)

# you can update other fields accordingly

def validate_params(name, count):
    test_coll_url = 'https://api.opensea.io/api/v1/collection/{}'.format(name)
    test_coll_response = requests.get(test_coll_url)
    if test_coll_response.status_code != 200:
        raise Exception('Invalid collection name.')
    print('Collection name validated...')
    if count < 0 or count > 1000000:
        raise Exception('Invalid collection count.')
    print('Collection count validated...')


class ScrapeCollectionTraits:
    def __init__(self, collection_name, collection_count=5000):
        collection_count += 1
        validate_params(collection_name, collection_count)
        print('Parameters are validated. Beginning program...')
        self.db = TinyDB(collection_name + '_db.json')
        self.db_query = Query()
        self.collection_name = collection_name
        resp_variables = self.send_requests_for_variables()
        stats_json = resp_variables[0]
        primary_asset_contracts_json = resp_variables[1]
        self.total_supply = int(stats_json['total_supply'])
        self.collection_count = max(collection_count, self.total_supply)
        self.contract_address = primary_asset_contracts_json['address']
        self.os_asset_url = 'https://api.opensea.io/api/v1/assets?asset_contract_address={}&order_direction=' \
                            'asc&offset={}&limit=50'
        self.start_time = None
        self.end_time = None
        self.iteration_num = 1
        self.ua = UserAgent()
        self.scrape()
        self.print_time_taken()

    def send_requests_for_variables(self):
        collection_url = 'https://api.opensea.io/api/v1/collection/{}'.format(self.collection_name)
        collection_response = requests.get(collection_url)
        collection_json = collection_response.json()['collection']
        stats_json = collection_json['stats']
        primary_asset_contracts_json = collection_json['primary_asset_contracts'][0]
        return [stats_json, primary_asset_contracts_json]

    def scrape(self):
        self.start_time = time.time()
        for i in range(0, math.ceil(self.collection_count / 50)):
            url = self.os_asset_url.format(self.contract_address, i * 50)
            asset_response = requests.get(url)
            if asset_response.status_code == 200:
                asset_base = asset_response.json()['assets']
                for asset in asset_base:
                    token_id = asset['token_id']
                    asset_trait_exists = True if len(self.db.search(self.db_query.id == int(token_id))) == 1 else False
                    if asset_trait_exists:
                        print(token_id, 'already exists in DB.')
                        continue
                    self.db.insert({'id': int(token_id), 'asset_json': str(asset)})
                    print(token_id, 'inserted into DB.')
            else:
                print(asset_response.status_code)
        self.end_time = time.time()
        print('Finished.')

    def print_time_taken(self):
        print('Approximately', int(self.end_time - self.start_time), 'seconds')
