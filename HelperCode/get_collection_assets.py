from fake_useragent import UserAgent
import math
import requests
from requests.structures import CaseInsensitiveDict
import time
from tinydb import TinyDB, Query


# This whole script takes roughly a few minutes for a collection with 10k assets. It's a one time
# operation for ultra fast operations on getting assets and their respective image URLs within a collection and ease
# of downloading with the EtherScan workaround!


def validate_params(name, count):
    test_coll_url = 'https://api.opensea.io/api/v1/collection/{}'.format(name)
    test_coll_response = requests.get(test_coll_url, timeout=2)
    if test_coll_response.status_code != 200:
        raise Exception('Invalid collection name.')
    print('Collection name validated...')
    if count < 0 or count > 10001:
        raise Exception('Invalid collection count.')
    print('Collection count validated...')


class RetrieveCollectionTraits:
    def __init__(self, collection_name, api_key, collection_count=5000):
        self.api_key = api_key
        test_os_key_url = 'https://api.opensea.io/api/v1/events?only_opensea=false&offset=0&limit=1'
        test_os_headers = CaseInsensitiveDict()
        test_os_headers['Accept'] = 'application/json'
        test_os_headers['x-api-key'] = self.api_key
        test_os_response = requests.get(test_os_key_url, headers=test_os_headers)
        if test_os_response.status_code != 200:
            raise Exception('Invalid API Key.')
        print('API Key Validated.')
        collection_count += 1
        validate_params(collection_name, collection_count)
        print('Parameters are validated. Beginning program...')
        self.db = TinyDB(collection_name + '_db.json')
        self.db_query = Query()
        self.collection_name = collection_name
        stats_json = self.send_requests_for_variables()
        self.total_supply = int(stats_json['total_supply'])
        self.collection_count = max(collection_count, self.total_supply)
        self.os_asset_url = 'https://api.opensea.io/api/v1/assets?order_direction=asc&' \
                            'collection_slug={}&limit=50&offset={}'
        self.start_time = 0
        self.end_time = 0
        self.ua = UserAgent()
        self.get_assets()
        self.print_time_taken()

    def send_requests_for_variables(self):
        collection_url = 'https://api.opensea.io/api/v1/collection/{}'.format(self.collection_name)
        collection_response = requests.get(collection_url)
        collection_json = collection_response.json()['collection']
        stats_json = collection_json['stats']
        return stats_json

    def get_assets(self):
        self.start_time = time.time()
        headers = CaseInsensitiveDict()
        headers['Accept'] = 'application/json'
        headers['User-Agent'] = UserAgent().random
        headers['x-api-key'] = self.api_key
        for i in range(0, math.ceil(self.collection_count / 50)):
            url = self.os_asset_url.format(self.collection_name, i * 50)
            asset_response = requests.get(url, headers=headers)
            print(asset_response.json())
            if asset_response.status_code == 200:
                asset_base = asset_response.json()['assets']
                for asset in asset_base:
                    token_id = asset['token_id']
                    image_url = asset['image_url']
                    asset_trait_exists = True if len(self.db.search(self.db_query.id == int(token_id))) == 1 else False
                    if asset_trait_exists:
                        print(token_id, 'already exists in DB.')
                        continue
                    self.db.insert({'id': int(token_id), 'asset_json': str(image_url)})  # you can literally store the
                    # whole JSON here if you want by replacing image_url with asset. This will take longer to run.
                    # if you do get the whole JSON, you will likely need to change owners manually during an event.
                    # here is how:

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

                    print(token_id, 'inserted into DB.')
            else:
                print(asset_response.status_code)
        self.end_time = time.time()
        print('Finished.')

    def print_time_taken(self):
        print('Approximately', int(self.end_time - self.start_time), 'seconds')
