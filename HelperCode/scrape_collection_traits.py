from fake_useragent import UserAgent
from fp.fp import FreeProxy
import requests
from requests.structures import CaseInsensitiveDict
import time
from tinydb import TinyDB, Query


# This whole script takes about 24 hours (or more) for a 10k collection. Although that is slow, it's a one time
# operation for ultra fast operations on getting assets within a collection. What happens when the owner changes?
# Here's a simple way to replace the previous owner:

# x = TinyDB('db.json')
# xq = Query()
# query = x.search(xq.id == ID)
# owner = eval(query[0]['traits'])['owner']
# prev_address = owner['address']
# owner['address'] = 'NEW_OWNER'

# you can change other fields accordingly

def validate_params(name, count):
    test_coll_url = 'https://api.opensea.io/api/v1/collection/{}'.format(name)
    test_coll_response = requests.request("GET", test_coll_url)
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
        self.os_asset_url = 'https://api.opensea.io/api/v1/asset/'
        self.total_supply = int(stats_json['total_supply'])
        self.collection_count = max(collection_count, self.total_supply)
        self.contract_address = primary_asset_contracts_json['address']
        self.start_time = None
        self.end_time = None
        self.iteration_num = 1
        self.ua = UserAgent()
        self.scrape()
        self.print_time_taken()

    def send_requests_for_variables(self):
        collection_url = 'https://api.opensea.io/api/v1/collection/{}'.format(self.collection_name)
        collection_response = requests.request("GET", collection_url)
        collection_json = collection_response.json()['collection']
        stats_json = collection_json['stats']
        primary_asset_contracts_json = collection_json['primary_asset_contracts'][0]
        return [stats_json, primary_asset_contracts_json]

    def scrape(self):
        self.start_time = time.time()
        missed_assets = [-1]
        while len(missed_assets) != 0:
            if -1 in missed_assets:
                missed_assets.remove(-1)
            assets = range(1, self.collection_count) if self.iteration_num == 1 else missed_assets
            for asset in assets:
                asset_trait_exists = True if len(self.db.search(self.db_query.id == asset)) == 1 else False
                if not asset_trait_exists:
                    url = "{}{}/{}".format(self.os_asset_url, self.contract_address, asset)
                    proxies = {
                        'http': FreeProxy(country_id=['US', 'CA', 'MX', 'BR']).get()
                    }
                    asset_headers = CaseInsensitiveDict()
                    asset_headers['User-Agent'] = self.ua.random
                    asset_response = requests.request('GET', url, proxies=proxies, headers=asset_headers)
                    if asset_response.status_code == 200:
                        self.db.insert({'id': asset, 'asset_json': str(asset_response.json())})
                        print('Inserted', asset, 'normally')
                        if asset in missed_assets:
                            missed_assets.remove(asset)
                    elif asset_response.status_code == 429:
                        missed_assets.append(asset)
                        print('429 encountered on', asset)
                    else:
                        print(asset_response.status_code, 'on', asset)
                else:
                    print(asset, 'already exists in DB.')
            print(missed_assets)
            self.iteration_num += 1
        self.end_time = time.time()
        print('Finished.')

    def print_time_taken(self):
        print('Approximately', int(self.end_time - self.start_time), 'seconds')
