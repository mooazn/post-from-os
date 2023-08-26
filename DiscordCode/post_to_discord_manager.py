import asyncio
import difflib
import discord
import importlib
import post_to_discord_obj
import requests
from requests.structures import CaseInsensitiveDict
import time

CLIENT = discord.Client()
VALUES = {}
CONTRACT_ADDRESSES = []
E_SCAN_KEY = ''
BOT_PREFIX = ''
COMMANDS = []
COMMANDS_DESC = []
HELP_MESSAGE = ''
USER_TIME_ELAPSED_MAP = {}
GAS_CACHE = []


class ManageManager:
    def __init__(self, discord_values_file, file_name: str, traits: bool):
        global VALUES, CONTRACT_ADDRESSES
        self.discord_values = discord_values_file
        self.contract_addresses = CONTRACT_ADDRESSES
        self.has_listings = []
        self.values = VALUES
        self.file_name = file_name
        self.traits = traits
        self.validate_params_and_run()

    def validate_params_and_run(self):
        global BOT_PREFIX, COMMANDS, COMMANDS_DESC, E_SCAN_KEY
        print('Beginning validation of Discord Values File...')
        if not str(self.discord_values).endswith('.txt'):
            raise Exception('Discord values must be a .txt file.')
        with open(self.discord_values) as dv:
            if len(dv.readlines()) != 9:
                raise Exception('The Discord Values file must be formatted correctly.')
        if not self.file_name.endswith('.py'):
            raise Exception('Invalid asynchronous code file name. Must be a .py file.')
        if self.file_name == 'asynchronous_discord_code.py':
            raise Exception('Asynchronous code file name must be something other than the default.')
        print('Asynchronous Code File .py validated...')
        test_discord_values = open(self.discord_values, 'r')
        test_os_api_key = test_discord_values.readline().strip()
        test_os_key_url = 'https://api.opensea.io/api/v1/events?only_opensea=false'
        test_os_headers = CaseInsensitiveDict()
        test_os_headers['Accept'] = 'application/json'
        test_os_headers['x-api-key'] = test_os_api_key
        test_os_response = requests.get(test_os_key_url, headers=test_os_headers, timeout=1)
        if test_os_response.status_code != 200:
            test_discord_values.close()
            raise Exception('Invalid OpenSea API key supplied.')
        print('OpenSea Key validated...')
        discord_token = test_discord_values.readline().strip()
        collection_names_test = test_discord_values.readline().split('|')
        if len(collection_names_test) > 5:
            test_discord_values.close()
            raise Exception('Too many collections. Please create a new bot for every 5 collections.')
        test_coll_headers = CaseInsensitiveDict()
        test_coll_headers['Accept'] = 'application/json'
        test_coll_headers['x-api-key'] = test_os_api_key
        for collection_name_test in collection_names_test:
            test_collection_name_url = 'https://api.opensea.io/api/v1/collection/{}'. \
                format(collection_name_test.strip())
            test_response = requests.get(test_collection_name_url, headers=test_coll_headers, timeout=1.5)
            if test_response.status_code == 200:
                collection_json = test_response.json()['collection']
                primary_asset_contracts_json = collection_json['primary_asset_contracts'][0]  # got the contract address
                contract_address = primary_asset_contracts_json['address']
                self.contract_addresses.append(contract_address)
                self.values[contract_address] = []
                self.values[contract_address].append(collection_name_test.strip())
            else:
                test_discord_values.close()
                raise Exception('The provided collection name does not exist.')
        print('Collections validated...')
        channels = test_discord_values.readline().strip()
        sales_listings_channels = []
        if '|' in channels:
            channels = channels.split('|')
            for channel in channels:
                sales_listings_channels.append(channel.split())
            total_channels = 0
            for sales_listings_channel in sales_listings_channels:
                for _ in sales_listings_channel:
                    total_channels += 1
                    if total_channels > 5:
                        test_discord_values.close()
                        raise Exception('Too many channels utilized. PLease create a new bot for every 5 channels.')
        try:
            if len(sales_listings_channels) > 0:
                index = 0
                for sales_listings_channel in sales_listings_channels:
                    needed_channels = []
                    try:
                        cur_contract_address = self.contract_addresses[index]
                    except IndexError:
                        test_discord_values.close()
                        raise Exception('The collection names should match the channels. There should ONLY be 1 name '
                                        'for every 1-2 channels')
                    sales_channel = int(sales_listings_channel[0])
                    needed_channels.append(sales_channel)
                    if len(sales_listings_channel) > 1:
                        listings_channel = int(sales_listings_channel[1])
                        needed_channels.append(listings_channel)
                        self.has_listings.append(True)
                    else:
                        self.has_listings.append(False)
                    self.values[cur_contract_address].append(needed_channels)
                    index += 1
            else:
                needed_channels = []
                channels = channels.split()
                sales_channel = int(channels[0])
                needed_channels.append(sales_channel)
                if len(channels) > 1:
                    listings_channel = int(channels[1])
                    needed_channels.append(listings_channel)
                    self.has_listings.append(True)
                else:
                    self.has_listings.append(False)
                self.values[self.contract_addresses[0]].append(needed_channels)
        except Exception as e:
            test_discord_values.close()
            print(e)
            raise Exception('Channels are not valid.')
        print('Channels validated.')
        test_discord_embed_icons = test_discord_values.readline().strip().split('|')
        if len(test_discord_embed_icons) != len(collection_names_test):
            test_discord_values.close()
            raise Exception('Number of icons must match the number of collections.')
        index = 0
        for test_discord_embed_icon in test_discord_embed_icons:
            valid_image_extensions = ['.jpg', '.jpeg', '.png']
            valid_image = False
            for image_extensions in valid_image_extensions:
                if test_discord_embed_icon.strip().endswith(image_extensions):
                    valid_image = True
                    break
            if not valid_image:
                test_discord_values.close()
                raise Exception('The Discord embed icon should be a valid image.')
            self.values[self.contract_addresses[index]].append(test_discord_embed_icon.strip())
            index += 1
        print('Discord embed icon validated...')
        test_rgb_values = test_discord_values.readline().strip().split('|')
        if len(test_rgb_values) != len(collection_names_test):
            test_discord_values.close()
            raise Exception('Number of RGB values must match the number of collections.')
        index = 0
        for test_rgb_value in test_rgb_values:
            test_rgb_value = test_rgb_value.split()
            if len(test_rgb_value) != 3:
                test_discord_values.close()
                raise Exception('Invalid RGB values provided.')
            r = int(test_rgb_value[0])
            g = int(test_rgb_value[1])
            b = int(test_rgb_value[2])
            if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
                test_discord_values.close()
                raise Exception('Invalid RGB codes. Must be between 0 and 255.')
            self.values[self.contract_addresses[index]].append([r, g, b])
            index += 1
        print('RGB Values validated...')
        for i in range(0, index):
            self.values[self.contract_addresses[i]].append(test_os_api_key)
        test_ether_scan_key = test_discord_values.readline().strip()
        test_ether_scan_url = 'https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey={}'. \
            format(test_ether_scan_key)
        test_ether_scan_response = requests.get(test_ether_scan_url, timeout=1)
        if test_ether_scan_response.json()['message'] == 'NOTOK':
            test_discord_values.close()
            raise Exception('Invalid Ether Scan key.')
        E_SCAN_KEY = test_ether_scan_key
        print('Ether Scan key validated...')
        test_prefix = test_discord_values.readline().strip()
        if test_prefix == 'None':
            BOT_PREFIX = '!'
            print('Set default value of \'!\' as prefix.')
        else:
            BOT_PREFIX = test_prefix
            print('Set value of \'{}\' as prefix.'.format(BOT_PREFIX))
        test_commands = test_discord_values.readline().strip()
        if test_commands != 'None':
            test_commands = test_commands.split()
            index = 0
            try:
                while index < len(test_commands):
                    word = test_commands[index]
                    if word[0] == '\"':
                        end_index = index
                        while test_commands[end_index][-1] != '\"':
                            end_index += 1
                        desc = ' '.join(test_commands[index:end_index + 1])
                        if 'To use, type: ' in desc:
                            usage = desc.split('To use, type: ')[1]
                            if not usage.startswith(BOT_PREFIX):
                                test_discord_values.close()
                                raise Exception('Custom command prefix does not begin with the provided prefix.')
                        else:
                            test_discord_values.close()
                            raise Exception('Command descriptions must always end in this format: \'To use, type: '
                                            '[BOT_PREFIX][usage]\'')
                        COMMANDS_DESC.append(desc)
                        index = end_index
                    else:
                        COMMANDS.append(word)
                    index += 1
                if len(COMMANDS) != len(COMMANDS_DESC):
                    test_discord_values.close()
                    raise Exception('Number of commands do not match number of descriptions.')
            except Exception as e:  # catch any error
                test_discord_values.close()
                print(e)
                raise Exception('Commands are formatted incorrectly. Please list the command followed by a short '
                                'description and usage (surrounded by quotes). For example: command \"This command '
                                'is a cool command. To use, type: !command\"')
            print('Custom commands and custom command descriptions successfully validated...')
            print('{} custom command(s): {}'.format(len(COMMANDS), COMMANDS))
        else:
            print('No custom commands supplied...')
        test_discord_values.close()
        print('Validation of Discord Values .txt complete. No errors found...')
        print('Validation complete...')
        self.generate_asynchronous_code(self.file_name)
        print('Successfully generated asynchronous code...')
        values_listing = []
        for ca, v in self.values.items():
            values_listing.append([[v[0], ca, v[2], v[3], v[4]], v[1]])
        async_code = importlib.import_module(self.file_name[:-3])
        async_code.run(CLIENT, values_listing, self.traits)
        CLIENT.loop.create_task(update_gas_presence())
        try:
            print('Beginning program...')
            run(discord_token)
        except discord.errors.LoginFailure:
            raise Exception('Invalid Discord token supplied.')

    def generate_asynchronous_code(self, file_name):
        index = 0
        space = ' ' * 4
        sales_boiler_plate_code = '''
    await client.wait_until_ready()
    channel = client.get_channel(sales_channel)
    while not client.is_closed():
        status = sales_obj.check_os_api_status(EventType.SALE.value)
        if not status:
            await asyncio.sleep(SLEEP_TIME)
            continue
        exists = sales_obj.check_if_new_post_exists()
        if not exists:
            await asyncio.sleep(SLEEP_TIME)
            continue
        res = await post_to_discord_obj.try_to_post_embed_to_discord(sales_obj, channel)
        if res:
            await asyncio.sleep(SLEEP_TIME)
        else:
            await asyncio.sleep(SLEEP_TIME)
            '''
        listings_boiler_plate_code = '''
    await client.wait_until_ready()
    channel = client.get_channel(listings_channel)
    while not client.is_closed():
        status = listings_obj.check_os_api_status(EventType.LISTING.value)
        if not status:
            await asyncio.sleep(SLEEP_TIME)
            continue
        exists = listings_obj.check_if_new_post_exists()
        if not exists:
            await asyncio.sleep(SLEEP_TIME)
            continue
        res = await post_to_discord_obj.try_to_post_embed_to_discord(listings_obj, channel)
        if res:
            await asyncio.sleep(SLEEP_TIME)
        else:
            await asyncio.sleep(SLEEP_TIME)
            '''
        code_file = open(file_name, 'w')
        code_file.write(
            '''import asyncio\nimport post_to_discord_obj\nfrom post_to_discord_obj import EventType, ManageFlowObj
            \n\nSLEEP_TIME = 300\n''')
        for _ in self.values.items():
            code_file.write('''async def process_sales_{}(client, sales_obj, sales_channel):'''.format(index))
            code_file.write(sales_boiler_plate_code + '\n\n')
            if self.has_listings[index]:
                code_file.write('''async def process_listings_{}(client, listings_obj, listings_channel):'''.
                                format(index))
                code_file.write(listings_boiler_plate_code + '\n\n')
            index += 1
        code_file.write('''def run(client, values, traits):\n{}'''.format(space))
        index = 0
        for _ in self.values.items():
            code_file.write('''sales_obj_{} = ManageFlowObj(values[{}][0], traits)\n{}'''.format(index, index, space))
            code_file.write('''client.loop.create_task(process_sales_{}(client, sales_obj_{}, values[{}][1][0]))\n{}'''.
                            format(index, index, index, space))
            if self.has_listings[index]:
                code_file.write('''listings_obj_{} = ManageFlowObj(values[{}][0], traits)\n{}'''.
                                format(index, index, space))
                code_file.write(
                    '''client.loop.create_task(process_listings_{}(client, listings_obj_{}, values[{}][1][1]))\n{}'''.
                    format(index, index, index, space))
            index += 1
        code_file.close()


@CLIENT.event
async def on_ready():
    global HELP_MESSAGE, COMMANDS, COMMANDS_DESC, BOT_PREFIX
    print('Logging in and setting up help command...')
    COMMANDS.append('help')
    COMMANDS.append('eth')
    COMMANDS.append('gas')
    bot_prefix = 'The prefix for this bot is \"{}\"\n\n'.format(BOT_PREFIX)
    help_help = 'Default command: \'help\'. \"This command.\"\n\n'
    eth_help = 'Default command: \'eth\'. \"Fetches the current price of ETH. To use, type: {}eth\"\n\n'.\
        format(BOT_PREFIX)
    gas_help = 'Default command: \'gas\'. \"Fetches the current gas prices of ETH. To use, type: {}gas\"\n\n'.\
        format(BOT_PREFIX)
    HELP_MESSAGE = '```' + bot_prefix + help_help + eth_help + gas_help
    for i in range(0, len(COMMANDS_DESC)):
        HELP_MESSAGE += 'Custom command: \'{}\'. {}'.format(COMMANDS[i], COMMANDS_DESC[i]) + '\n\n'
    HELP_MESSAGE += '```'


@CLIENT.event
async def on_message(message):
    global BOT_PREFIX, COMMANDS, VALUES, CONTRACT_ADDRESSES, USER_TIME_ELAPSED_MAP, GAS_CACHE
    if message.author == CLIENT.user:
        return

    if message.content.startswith(BOT_PREFIX):
        message.content = message.content[len(BOT_PREFIX):]
        command_param = message.content.split()

        if message.content in COMMANDS or command_param[0] in COMMANDS:
            sender = message.author.id
            cur_epoch = int(time.time())
            if sender not in USER_TIME_ELAPSED_MAP:
                USER_TIME_ELAPSED_MAP[sender] = cur_epoch
            elif cur_epoch - USER_TIME_ELAPSED_MAP[sender] <= 5:
                await message.channel.send('Please wait 5 seconds before using a command again.')
                return
            USER_TIME_ELAPSED_MAP[sender] = cur_epoch

            if message.content == COMMANDS[len(COMMANDS) - 3]:  # help command
                await message.channel.send(HELP_MESSAGE)

            elif message.content == COMMANDS[len(COMMANDS) - 2]:  # eth price
                await post_to_discord_obj.eth_price(message)

            elif message.content == COMMANDS[len(COMMANDS) - 1]:  # gas tracker
                await post_to_discord_obj.gas_tracker(message, GAS_CACHE)

            elif message.content == ('{}'.format(COMMANDS[0])):  # custom command 1 - floor price
                await post_to_discord_obj.custom_command_1(message, VALUES, CONTRACT_ADDRESSES[0])

            elif command_param[0] == ('{}'.format(COMMANDS[1])):  # custom command 2 - post asset
                await post_to_discord_obj.custom_command_2(message, VALUES, CONTRACT_ADDRESSES[0])

            elif message.content == ('{}'.format(COMMANDS[2])):  # custom command 3 - floor price
                await post_to_discord_obj.custom_command_1(message, VALUES, CONTRACT_ADDRESSES[1])

            elif command_param[0] == ('{}'.format(COMMANDS[3])):  # custom command 4 - post asset
                await post_to_discord_obj.custom_command_2(message, VALUES, CONTRACT_ADDRESSES[1])

        else:
            closest_words = difflib.get_close_matches(message.content, COMMANDS)
            if len(closest_words) > 0:
                closest_word = closest_words[0]
                if message.content != closest_word:
                    await message.channel.send('Did you mean `{}`?'.format(closest_word))


async def update_gas_presence():
    global CLIENT, BOT_PREFIX, E_SCAN_KEY, GAS_CACHE
    await CLIENT.wait_until_ready()
    while not CLIENT.is_closed():
        gas_tracker_url = 'https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey={}'.format(E_SCAN_KEY)
        try:
            gas_tracker_request = requests.get(gas_tracker_url, timeout=2)
            gas = gas_tracker_request.json()['result']
            fast_gas = gas['FastGasPrice']
            avg_gas = gas['ProposeGasPrice']
            slow_gas = gas['SafeGasPrice']
            await CLIENT.change_presence(activity=discord.Game(
                name='⚡ {} | 🚶 {} | 🐢 {} | {}help'.format(fast_gas, avg_gas, slow_gas, BOT_PREFIX)))
            GAS_CACHE.clear()
            GAS_CACHE.append(fast_gas)
            GAS_CACHE.append(avg_gas)
            GAS_CACHE.append(slow_gas)
            print('Gas updated.', flush=True)
        except Exception as e:
            print(e, flush=True)
        await asyncio.sleep(30)


def run(discord_token):
    global CLIENT
    CLIENT.run(discord_token)
