import time
from tinydb import TinyDB
import requests
from fp.fp import FreeProxy


class ScrapeCollectionTraits:
    def __init__(self, collection_db_name, collection_name, contract_address, collection_count=0):
        collection_count += 1
        self.db = TinyDB(collection_db_name)
        self.db.truncate()  # this file should ideally be ran once per collection. if you end up rerunning because of
        # errors, the db is automatically reset.
        self.os_asset_url = 'https://api.opensea.io/api/v1/asset/'
        self.contract_address = contract_address
        self.collection_name = collection_name
        test_contract_url = "https://api.opensea.io/api/v1/collection/{}/stats".format(self.collection_name)
        test_headers = {"Accept": "application/json"}
        test_response = requests.request("GET", test_contract_url, headers=test_headers)
        if test_response.status_code != 200:
            raise Exception('Invalid collection name.')
        test_json = test_response.json()['stats']
        total_supply = int(test_json['total_supply'])
        count = int(test_json['count'])
        self.collection_count = max(collection_count, total_supply, count)
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
            url = "{}{}/{}".format(self.os_asset_url, self.contract_address, asset)
            proxies = {
                'http': FreeProxy(country_id=['US', 'BR', 'CA', 'MX']).get()
            }
            r = requests.request('GET', url, proxies=proxies)
            try:
                traits = r.json()['traits']
                self.db.insert({'id': asset, 'traits': str(traits)})
            except Exception as e:  # Most likely some kind of 429 error if same proxy is reused over and over
                missed_assets.append(asset)
                print(e)
        self.end_time = time.time()
        if missed_assets is not None:
            print('Missed', abs(self.collection_count - len(self.db)), 'assets.')
            print(missed_assets)
        print('Finished.')

    def print_time_taken(self):
        print('Approximately', int(self.end_time - self.start_time), 'seconds')
