from bs4 import BeautifulSoup
import cloudscraper
from fp.fp import FreeProxy
import json
import requests
from selenium import webdriver
import time
from tinydb import TinyDB, Query
from webdriver_manager.chrome import ChromeDriverManager

collection_trait_dict = {}


def validate_params(db_name, name, count):
    if not str(db_name).endswith('.json'):
        raise Exception('Traits DB Name MUST end with .json')
    test_coll_url = 'https://api.opensea.io/api/v1/collection/{}'.format(name)
    test_coll_response = requests.request("GET", test_coll_url)
    if test_coll_response.status_code != 200:
        raise Exception('Invalid collection name.')
    if count < 0 or count > 10000000:
        raise Exception('Invalid collection count.')


def populate_trait_dict(traits, trait_dict):
    for trait_type in traits:
        for trait_value in traits[trait_type]:
            trait_rarity = traits[trait_type][trait_value]
            if trait_type not in trait_dict:
                trait_dict[trait_type] = {}
            trait_dict[trait_type][trait_value] = trait_rarity


def generate_json(traits):
    global collection_trait_dict
    json_trait_list = []
    for trait in traits:
        json_trait_template = {
            'trait_type': trait[0],
            'trait_value': trait[1],
            'display_type': None,
            'max_value': None,
            'trait_count': collection_trait_dict[trait[0]][str(trait[1]).lower()],
            'order': None
        }
        json_trait_list.append(json_trait_template)
    json_traits = json.loads(json.dumps(json_trait_list))
    return json_traits


def get_percentage_from_rarity(rarity):
    index = 0
    for number in rarity:
        try:
            int(number)
        except ValueError:
            return rarity[0:index] + '%'
        index += 1


class ScrapeCollectionTraits:
    def __init__(self, collection_db_name, collection_name, collection_count=5000):
        global collection_trait_dict
        collection_count += 1
        validate_params(collection_db_name, collection_name, collection_count)
        print('Parameters are validated. Beginning program...')
        self.db = TinyDB(collection_db_name)
        self.db_query = Query()
        self.collection_name = collection_name
        resp_variables = self.send_requests_for_variables()
        stats_json = resp_variables[0]
        primary_asset_contracts_json = resp_variables[1]
        self.automated_browsers = ScrapeCollectionTraitsViaAutomatedBrowsers()
        self.os_asset_url = 'https://api.opensea.io/api/v1/asset/'
        self.total_supply = int(stats_json['total_supply'])
        self.collection_count = max(collection_count, self.total_supply)
        self.contract_address = primary_asset_contracts_json['address']
        self.start_time = None
        self.end_time = None
        self.iteration_num = 1
        self.scrape()
        self.print_time_taken()

    def send_requests_for_variables(self):
        collection_url = 'https://api.opensea.io/api/v1/collection/{}'.format(self.collection_name)
        collection_response = requests.request("GET", collection_url)
        collection_json = collection_response.json()['collection']
        traits_json = collection_json['traits']
        populate_trait_dict(traits_json, collection_trait_dict)
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
                    asset_response = requests.request('GET', url, proxies=proxies)
                    if asset_response.status_code == 200:
                        traits = asset_response.json()['traits']
                        self.db.insert({'id': asset, 'traits': str(traits)})
                        print('Inserted', asset, 'normally')
                        if asset in missed_assets:
                            missed_assets.remove(asset)
                    elif asset_response.status_code == 429:
                        print('429 encountered.')
                        cloudflare_scraper_tries = 0
                        cloudflare_scraper_is_valid = False
                        res_json = None
                        while True:
                            print('Trying to scrape with cloudflare scraper...')
                            if cloudflare_scraper_tries == 5:
                                print('Cloudflare scraper failed.')
                                break
                            try:
                                res_json = self.automated_browsers.get_traits_via_cloudflare_scraper(
                                    self.contract_address, asset)
                                cloudflare_scraper_is_valid = True
                                break
                            except IndexError:
                                pass
                            cloudflare_scraper_tries += 1
                            time.sleep(0.5)
                        if not cloudflare_scraper_is_valid:
                            print('Fallback to selenium.')
                            res_json = self.automated_browsers.get_traits_via_selenium(self.contract_address, asset)
                            if not res_json:
                                print('False 429! Cloudflare scraper did not fail. This is a 404 on', asset)
                                continue
                            print('Inserted', asset, 'via selenium.')
                        else:
                            print('Inserted', asset, 'via cloud scraper.')
                        if res_json is None:
                            print('Nothing works, skip asset for now :( I tried everything!')
                            missed_assets.append(asset)
                            continue
                        self.db.insert({'id': asset, 'traits': str(res_json)})
                    else:
                        print(asset_response.status_code, 'on', asset)
                else:
                    print(asset, 'already exists.')
            if len(self.db) != self.total_supply:
                print('There are currently', self.total_supply - len(self.db), 'missed assets.')
            self.iteration_num += 1
        self.end_time = time.time()
        self.automated_browsers.selenium_driver.close()
        self.automated_browsers.selenium_driver.quit()
        print('Finished.')

    def print_time_taken(self):
        print('Approximately', int(self.end_time - self.start_time), 'seconds')


class ScrapeCollectionTraitsViaAutomatedBrowsers:
    def __init__(self):
        self.os_asset_url = 'https://opensea.io/assets/'
        self.selenium_driver = webdriver.Chrome(ChromeDriverManager().install())
        self.cloudflare_scraper = None
        self.current_result = None

    def get_traits_via_cloudflare_scraper(self, c_address, t_id):
        self.cloudflare_scraper = cloudscraper.create_scraper()
        asset_page = self.cloudflare_scraper.get('{}{}/{}'.format(self.os_asset_url, c_address, str(t_id)))
        asset_soup = BeautifulSoup(asset_page.content, 'html.parser')
        prop_types = asset_soup.find_all('div', {'class': 'Property--type'})
        prop_values = asset_soup.find_all('div', {'class': 'Property--value'})
        prop_rarities = asset_soup.find_all('div', {'class': 'Property--rarity'})
        length = 0
        first = prop_types[0]
        for div in prop_types:
            if length != 0 and first == div:
                break
            length += 1
        cloudflare_asset_traits = []
        for div_index in range(0, length):
            cloudflare_asset_type = prop_types[div_index].text
            cloudflare_asset_value = prop_values[div_index].text
            cloudflare_asset_rarity = prop_rarities[div_index].text
            cloudflare_asset_rarity = get_percentage_from_rarity(cloudflare_asset_rarity)
            cloudflare_asset_traits.append([cloudflare_asset_type, cloudflare_asset_value, cloudflare_asset_rarity])
        result = generate_json(cloudflare_asset_traits)
        self.current_result = result
        return result

    def get_traits_via_selenium(self, c_address, t_id):
        self.selenium_driver.get('{}{}/{}'.format(self.os_asset_url, c_address, str(t_id)))
        self.selenium_driver.implicitly_wait(3)
        prop_types = self.selenium_driver.find_elements_by_class_name('Property--type')
        prop_values = self.selenium_driver.find_elements_by_class_name('Property--value')
        prop_rarities = self.selenium_driver.find_elements_by_class_name('Property--rarity')
        num_traits = len(prop_types)
        selenium_asset_traits = []
        for num in range(0, num_traits):
            selenium_asset_type = prop_types[num].get_attribute('innerHTML')
            selenium_asset_value = prop_values[num].get_attribute('innerHTML')
            selenium_asset_rarity = prop_rarities[num].get_attribute('innerHTML')
            selenium_asset_rarity = get_percentage_from_rarity(selenium_asset_rarity)
            selenium_asset_traits.append([selenium_asset_type, selenium_asset_value, selenium_asset_rarity])
        result = generate_json(selenium_asset_traits)
        self.current_result = result
        return result
