from fp.fp import FreeProxy
import requests
import time
from tinydb import TinyDB, Query


def validate_params(db_name, name, count):
    if not str(db_name).endswith('.json'):
        raise Exception('Traits DB Name MUST end with .json')
    test_coll_url = 'https://api.opensea.io/api/v1/collection/{}'.format(name)
    test_coll_response = requests.request("GET", test_coll_url)
    if test_coll_response.status_code != 200:
        raise Exception('Invalid collection name.')
    if count < 0 or count > 10000000:
        raise Exception('Invalid collection count.')


class ScrapeCollectionTraits:
    def __init__(self, collection_db_name, collection_name, collection_count=5000):
        validate_params(collection_db_name, collection_name, collection_count)
        print('Parameters are validated. Beginning program...')
        collection_count += 1
        self.db = TinyDB(collection_db_name)
        self.db_query = Query()
        self.os_asset_url = 'https://api.opensea.io/api/v1/asset/'
        self.collection_name = collection_name
        collection_url = 'https://api.opensea.io/api/v1/collection/{}'.format(self.collection_name)
        collection_response = requests.request("GET", collection_url)
        collection_json = collection_response.json()['collection']
        stats_json = collection_json['stats']
        primary_asset_contracts_json = collection_json['primary_asset_contracts'][0]
        total_supply = int(stats_json['total_supply'])
        self.collection_count = max(collection_count, total_supply)
        self.contract_address = primary_asset_contracts_json['address']
        self.start_time = None
        self.end_time = None
        self.scrape()
        self.print_time_taken()

    def scrape(self):  # yes, I tried using threads but I was being rate-limited. I also tried using threads with the
        # proxies, but that was way slower (8 hours vs 3 hours for a 10,0000 collection)!!
        # this is the simplest approach...
        self.start_time = time.time()
        missed_assets = []
        for asset in range(1, self.collection_count):
            asset_trait_exists = True if len(self.db.search(self.db_query.id == asset)) == 1 else False
            if not asset_trait_exists:
                url = "{}{}/{}".format(self.os_asset_url, self.contract_address, asset)
                proxies = {
                    'http': FreeProxy(country_id=['US', 'BR', 'CA', 'MX']).get()
                }
                r = requests.request('GET', url, proxies=proxies)
                try:
                    traits = r.json()['traits']
                    self.db.insert({'id': asset, 'traits': str(traits)})
                    print('Inserted', asset)
                except Exception as e:  # Most likely some kind of 429 error if same proxy is reused over and over
                    missed_assets.append(asset)
                    print(e)
            else:
                print(asset, 'already exists.')
        self.end_time = time.time()
        if missed_assets is not None:
            print('Missed', abs(self.collection_count - len(self.db)), 'assets.')
            print(missed_assets)
        print('Finished.')

    def print_time_taken(self):
        print('Approximately', int(self.end_time - self.start_time), 'seconds')
