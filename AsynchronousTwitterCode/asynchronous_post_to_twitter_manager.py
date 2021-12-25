import asynchronous_twitter_code
import math
import requests
from requests.structures import CaseInsensitiveDict
from twython import Twython
import twython.exceptions


def generate_asynchronous_code(values_map):
    create_async_code_file = open('asynchronous_twitter_code.py', 'w')
    create_async_code_file.write('''import asyncio\nfrom asynchronous_post_to_twitter_obj import ManageFlowObj\n\n\n''')
    boiler_plate_code = '''    
    while True:
        os_status = obj.check_os_api_status()
        if not os_status:
            ether_scan_status = obj.check_ether_scan_api_status()
            if ether_scan_status == -1:
                await asyncio.sleep(30)
                continue
            elif not ether_scan_status:
                await asyncio.sleep(5)
                continue
            else:
                res = obj.try_to_post_to_twitter()
                if res:
                    await asyncio.sleep(5)
                else:
                    await asyncio.sleep(10)
                continue
        exists = obj.check_if_new_post_exists()
        if not exists:
            await asyncio.sleep(5)
            continue
        download_image = obj.try_to_download_image()
        if not download_image:
            await asyncio.sleep(5)
            continue
        res = obj.try_to_post_to_twitter()
        if res:
            await asyncio.sleep(5)
        else:
            await asyncio.sleep(10)
    '''
    space = ' ' * 4
    for index in values_map:
        create_async_code_file.write('''async def collection_{}(obj):{}'''.format(index + 1, space))
        create_async_code_file.write(boiler_plate_code)
        create_async_code_file.write('\n\n')
    create_async_code_file.write('''def run(values_map):\n{}loop = asyncio.get_event_loop()\n{}'''.
                                 format(space, space))
    for index in values_map:
        create_async_code_file.write('''collection_{}_obj = ManageFlowObj(values_map[{}])\n{}'''.
                                     format(index + 1, index, space))
    for index in values_map:
        create_async_code_file.write('''loop.create_task(collection_{}(collection_{}_obj))\n{}'''.
                                     format(index + 1, index + 1, space))
    create_async_code_file.write('''loop.run_forever()\n''')
    create_async_code_file.close()
    print('Successfully generated asynchronous code...')


class ManageMultipleTwitterPosts:
    def __init__(self, twitter_values_file_multiple, *args):
        self.args = *args,
        self.twitter_values_file = twitter_values_file_multiple
        self.hashtags = []
        self.collection_names = []
        self.collection_stats = []
        self.twitter_keys = []
        self.os_keys = []
        self.ether_scan_keys = []
        self.collection_names_for_ether_scan = []
        self.validate_params()
        self.values_map = {}
        self.create_map()
        generate_asynchronous_code(self.values_map)
        print('Beginning program...')
        asynchronous_twitter_code.run(self.values_map)

    def validate_params(self):
        print('Beginning validation of Twitter Values File...')
        if not str(self.twitter_values_file).lower().endswith('.txt'):
            raise Exception('Twitter Values must be a .txt file.')
        with open(self.twitter_values_file) as values_file:
            if len(values_file.readlines()) != 9:
                raise Exception('The Twitter Values file must be formatted correctly.')
        print('Number of lines validated.')
        values_file_test = open(self.twitter_values_file, 'r')
        hashtags_test = values_file_test.readline().strip()
        if '|' not in hashtags_test:
            values_file_test.close()
            raise Exception('Hashtags for other collections should be separated by \"|\"')
        hashtag_collections = hashtags_test.split('|')
        collection_count = len(hashtag_collections)
        if len(self.args) != collection_count:
            raise Exception('The number of args is not the same as the number of hashtags.')
        print('Args validated...')
        count = 1
        for hashtag_collection in hashtag_collections:
            cur_hashtags = []
            hashtags = 0
            words_in_hash_tag = hashtag_collection.split()
            if hashtag_collection.strip() != 'None':
                if len(words_in_hash_tag) == 0 or hashtag_collection.split() == 0:
                    values_file_test.close()
                    raise Exception('Hashtags field in collection {} is empty.'.format(count))
                if len(words_in_hash_tag) >= 120:
                    values_file_test.close()
                    raise Exception('Too many characters in hashtags in collection {}.'.format(count))
                if len(words_in_hash_tag) > 10:
                    values_file_test.close()
                    raise Exception('Too many hashtags in collection {}.'.format(count))
                for word in words_in_hash_tag:
                    if word[0] == '#':
                        hashtags += 1
                        cur_hashtags.append(word.strip())
                if hashtags != len(words_in_hash_tag):
                    values_file_test.close()
                    raise Exception('All words must be preceded by a hashtag (#) in collection {}.'.
                                    format(count))
            self.hashtags.append(cur_hashtags)
            print('Hashtag for collection {} validated...'.format(count))
            count += 1
        print('Hashtag for all collections validated...')
        collection_name_test = values_file_test.readline().strip()
        if '|' not in collection_name_test:
            values_file_test.close()
            raise Exception('Collection names should be separated by \"|\"')
        collection_names = collection_name_test.split('|')
        if len(collection_names) != collection_count:
            values_file_test.close()
            raise Exception('The length of provided collection names does not match the length of the hashtags.')
        count = 1
        for collection_name in collection_names:
            test_collection_name_url = 'https://api.opensea.io/api/v1/collection/{}'.format(collection_name.strip())
            test_response = requests.get(test_collection_name_url, timeout=1)
            if test_response.status_code == 200:
                collection_json = test_response.json()['collection']
                stats_json = collection_json['stats']
                total_supply = int(stats_json['total_supply'])
                primary_asset_contracts_json = collection_json['primary_asset_contracts'][0]  # got the contract address
                contract_address = primary_asset_contracts_json['address']
                self.collection_stats.append([total_supply, contract_address])
            else:
                values_file_test.close()
                raise Exception('The provided collection {} does not exist.'.format(count))
            print('Collection {} validated...'.format(count))
            self.collection_names.append(collection_name.strip())
            count += 1
        print('All collection names validated...')
        api_key = values_file_test.readline().strip()
        api_key_secret = values_file_test.readline().strip()
        access_token = values_file_test.readline().strip()
        access_token_secret = values_file_test.readline().strip()
        twitter_test = Twython(
            api_key,
            api_key_secret,
            access_token,
            access_token_secret
        )
        try:
            twitter_test.verify_credentials()
            twitter_test.client.close()
        except twython.exceptions.TwythonAuthError:
            values_file_test.close()
            twitter_test.client.close()
            raise Exception('Invalid Twitter Keys supplied.')
        self.twitter_keys = [api_key, api_key_secret, access_token, access_token_secret]
        print('Twitter credentials validated...')
        test_os_keys = values_file_test.readline().strip()
        if test_os_keys is None or len(test_os_keys) == 0:
            values_file_test.close()
            raise Exception('No key provided for Opensea.')
        if collection_count >= 6:
            if '|' not in test_os_keys:
                values_file_test.close()
                raise Exception('More Opensea keys needed for provided collections.')
            keys_needed = math.ceil(collection_count / 5)
            cur_keys = test_os_keys.count('|') + 1
            if keys_needed != cur_keys:
                values_file_test.close()
                raise Exception('Please provided a new Opensea key for every 5 collections.')
        os_keys = test_os_keys.split('|')
        count = 1
        for os_key in os_keys:
            test_os_key_url = 'https://api.opensea.io/api/v1/events?only_opensea=false&offset=0&limit=1'
            test_os_headers = CaseInsensitiveDict()
            test_os_headers['Accept'] = 'application/json'
            test_os_headers['x-api-key'] = os_key.strip()
            test_os_response = requests.get(test_os_key_url, headers=test_os_headers, timeout=1)
            if test_os_response.status_code != 200:
                values_file_test.close()
                raise Exception('Invalid OpenSea API key {} supplied.'.format(count))
            print('Opensea key {} validated...'.format(count))
            self.os_keys.append(os_key.strip())
            count += 1
        print('All Opensea keys validated...')
        test_ether_scan_values = values_file_test.readline().strip()
        if test_ether_scan_values is None or len(test_ether_scan_values) == 0:
            values_file_test.close()
            raise Exception('No keys provided for EtherScan.')
        if collection_count >= 6:
            if '|' not in test_ether_scan_values:
                values_file_test.close()
                raise Exception('More EtherScan keys needed for provided collections.')
            keys_needed = math.ceil(collection_count / 5)
            cur_keys = test_ether_scan_values.count('|') + 1
            if keys_needed != cur_keys:
                values_file_test.close()
                raise Exception('Please provided a new EtherScan key for every 5 collections.')
        ether_scan_keys = test_ether_scan_values.split('|')
        count = 1
        for ether_scan_key in ether_scan_keys:
            test_ether_scan_url = 'https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey={}'. \
                format(ether_scan_key.strip())
            test_ether_scan_response = requests.get(test_ether_scan_url, timeout=1)
            if test_ether_scan_response.json()['message'] == 'NOTOK':
                values_file_test.close()
                raise Exception('Invalid Ether Scan key {}.'.format(count))
            print('EtherScan key {} validated...'.format(count))
            self.ether_scan_keys.append(ether_scan_key.strip())
            count += 1
        print('All EtherScan keys validated...')
        collection_names_for_ether_scan_test = values_file_test.readline().strip()
        if '|' not in collection_names_for_ether_scan_test:
            values_file_test.close()
            raise Exception('Collection names for EtherScan should be separated by \"|\"')
        collection_names_for_ether_scan = collection_names_for_ether_scan_test.split('|')
        if len(collection_names_for_ether_scan) != collection_count:
            values_file_test.close()
            raise Exception('The number of collection names for EtherScan does not match the number of hashtags.')
        for collection_name_for_ether_scan in collection_names_for_ether_scan:
            self.collection_names_for_ether_scan.append(collection_name_for_ether_scan.strip())
        print('Collection names for EtherScan validated...')
        values_file_test.close()
        print('Validation of Twitter Values .txt complete. No errors found...')
        print('Validation successfully completed.')

    def create_map(self):
        os_ether_key_index = 0
        for index in range(0, len(self.collection_names)):
            if len(self.values_map) >= 6 and len(self.values_map) % 6 == 0:
                os_ether_key_index += 1
            cur_hashtags = self.hashtags[index]
            cur_collection_name = self.collection_names[index]
            cur_collection_stats = self.collection_stats[index]
            cur_os_key = self.os_keys[os_ether_key_index]
            cur_ether_scan_key = self.ether_scan_keys[os_ether_key_index]
            cur_collection_name_for_ether_scan = self.collection_names_for_ether_scan[index]
            cur_values = [cur_hashtags, cur_collection_name, cur_collection_stats, self.twitter_keys,
                          cur_os_key, cur_ether_scan_key, cur_collection_name_for_ether_scan, self.args[index]]
            self.values_map[index] = cur_values
            index += 1
        print('Successfully created values map...')
