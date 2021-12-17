import asyncio
import discord
import post_to_discord_obj
from post_to_discord_obj import ManageFlowObj, EventType
import requests
from requests.structures import CaseInsensitiveDict

CLIENT = discord.Client()
SALES_OBJ = ManageFlowObj()
SALES_CHANNEL = -1
LISTINGS_OBJ = ManageFlowObj()
LISTINGS_CHANNEL = -1
E_SCAN_KEY = ''
BOT_PREFIX = ''
COMMANDS = []
COMMANDS_DESC = []
HELP_MESSAGE = ''


class ManageManager:
    def __init__(self, discord_values_file):
        self.discord_values = discord_values_file
        self.validate_params_and_run()

    def validate_params_and_run(self):
        global SALES_OBJ, LISTINGS_OBJ, SALES_CHANNEL, LISTINGS_CHANNEL, BOT_PREFIX, COMMANDS, COMMANDS_DESC, E_SCAN_KEY
        print('Beginning validation of Discord Values File...')
        if not str(self.discord_values).endswith('.txt'):
            raise Exception('Discord values must be a .txt file.')
        with open(self.discord_values) as dv:
            if len(dv.readlines()) != 9:
                raise Exception('The Discord Values file must be formatted correctly.')
        test_discord_values = open(self.discord_values, 'r')
        discord_token = test_discord_values.readline().strip()
        channels = test_discord_values.readline().strip().split()
        try:
            SALES_CHANNEL = int(channels[0])
            if len(channels) > 1:
                LISTINGS_CHANNEL = int(channels[1])
        except Exception as e:
            test_discord_values.close()
            print(e)
            raise Exception('Channels are not valid.')
        print('Channels validated.\n  Sales channel: {}\n  Listings Channel: {}'.
              format(SALES_CHANNEL, LISTINGS_CHANNEL if LISTINGS_CHANNEL != -1 else 'No listings channel'))
        collection_name_test = test_discord_values.readline().strip()
        test_collection_name_url = 'https://api.opensea.io/api/v1/collection/{}'.format(collection_name_test)
        test_response = requests.get(test_collection_name_url, timeout=1.5)
        if test_response.status_code == 200:
            collection_json = test_response.json()['collection']
            primary_asset_contracts_json = collection_json['primary_asset_contracts'][0]  # got the contract address
            contract_address = primary_asset_contracts_json['address']
        else:
            test_discord_values.close()
            raise Exception('The provided collection name does not exist.')
        print('Collection validated...')
        test_discord_embed_icon = test_discord_values.readline().strip()
        if test_discord_embed_icon != 'None':
            valid_image_extensions = ['.jpg', '.jpeg', '.png']
            valid_image = False
            for image_extensions in valid_image_extensions:
                if test_discord_embed_icon.endswith(image_extensions):
                    valid_image = True
                    break
            if not valid_image:
                raise Exception('The Discord embed icon should be a valid image.')
            print('Discord embed icon validated...')
        else:
            print('Skipping Discord embed icon.')
        test_rgb_values = test_discord_values.readline().strip().split()
        r = 0
        g = 0
        b = 0
        if test_rgb_values != 'None':
            if len(test_rgb_values) != 3:
                raise Exception('Invalid RGB values provided.')
            r = int(test_rgb_values[0])
            g = int(test_rgb_values[1])
            b = int(test_rgb_values[2])
            if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
                print('RGB Values validated...')
            else:
                raise Exception('Invalid RGB codes. Must be between 0 and 255.')
        else:
            print('Skipping RGB Values and setting to default...')
        test_os_api_key = test_discord_values.readline().strip()
        test_os_key_url = 'https://api.opensea.io/api/v1/events?only_opensea=false&offset=0&limit=1'
        test_os_headers = CaseInsensitiveDict()
        test_os_headers['Accept'] = 'application/json'
        test_os_headers['x-api-key'] = test_os_api_key
        test_os_response = requests.get(test_os_key_url, headers=test_os_headers, timeout=1)
        if test_os_response.status_code != 200:
            test_discord_values.close()
            raise Exception('Invalid OpenSea API key supplied.')
        print('OpenSea Key validated...')
        test_ether_scan_key = test_discord_values.readline().strip()
        test_ether_scan_url = 'https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey={}'. \
            format(test_ether_scan_key)
        test_ether_scan_response = requests.get(test_ether_scan_url, timeout=1)
        if test_ether_scan_response.json()['message'] == 'NOTOK':
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
                        COMMANDS_DESC.append(desc)
                        index = end_index
                    else:
                        COMMANDS.append(word)
                    index += 1
                if len(COMMANDS) != len(COMMANDS_DESC):
                    raise Exception('Number of commands do not match number of descriptions.')
            except Exception as e:  # catch any error
                print(e)
                raise Exception('Commands are formatted incorrectly. Please list the command followed by a short '
                                'description and usage (surrounded by quotes). For example: command \"This command '
                                'is a cool command. To use, type !command\"')
            print('There {} a total of {} custom command(s): {}'.format('is' if len(COMMANDS) == 1 else 'are',
                                                                        len(COMMANDS), COMMANDS))
            print('Custom commands and custom command descriptions successfully validated...')
        else:
            print('No custom commands supplied.')
        test_discord_values.close()
        print('Validation of Discord Values .txt complete. No errors found...')
        print('All files are validated. Beginning program...')
        SALES_OBJ.create([[collection_name_test], [contract_address], [test_discord_embed_icon], [r, g, b],
                          [test_os_api_key]])
        CLIENT.loop.create_task(process_sales())
        CLIENT.loop.create_task(update_gas_presence())
        if LISTINGS_CHANNEL != -1:
            LISTINGS_OBJ.create([[collection_name_test], [contract_address], [test_discord_embed_icon], [r, g, b],
                                [test_os_api_key]])
            CLIENT.loop.create_task(process_listings())
        try:
            print('Beginning program...')
            run(discord_token)
        except discord.errors.LoginFailure:
            raise Exception('Invalid Discord token supplied.')


@CLIENT.event
async def on_ready():
    global HELP_MESSAGE, COMMANDS, COMMANDS_DESC
    help_help = 'Default command: \'help\'. \"This command.\"\n\n'
    eth_help = 'Default command: \'eth\'. \"Fetches the current price of ETH. To use, type !eth\"\n\n'
    gas_help = 'Default command: \'gas\'. \"Fetches the current gas prices of ETH. To use, type !gas\"\n\n'
    HELP_MESSAGE = '```' + help_help + eth_help + gas_help
    for i in range(0, len(COMMANDS_DESC)):
        HELP_MESSAGE += 'Custom command: \'{}\'. {}'.format(COMMANDS[i], COMMANDS_DESC[i]) + '\n\n'
    HELP_MESSAGE += '```'
    print('Logging in and setting up help command...', flush=True)


@CLIENT.event
async def on_message(message):
    global BOT_PREFIX, COMMANDS, HELP_MESSAGE, E_SCAN_KEY
    if message.author == CLIENT.user:
        return

    if message.content.startswith('{}help'.format(BOT_PREFIX)):  # help command
        await message.channel.send(HELP_MESSAGE)

    elif message.content.startswith('{}eth'.format(BOT_PREFIX)):  # eth price
        await post_to_discord_obj.eth_price(SALES_OBJ, message)

    elif message.content.startswith('{}gas'.format(BOT_PREFIX)):  # gas tracker
        await post_to_discord_obj.gas_tracker(SALES_OBJ, message, E_SCAN_KEY)

    elif message.content.startswith('{}{}'.format(BOT_PREFIX, COMMANDS[0])):  # custom command 1
        await post_to_discord_obj.custom_command_1(SALES_OBJ, message)

    elif message.content.startswith('{}{}'.format(BOT_PREFIX, COMMANDS[1])):  # custom command 2
        await post_to_discord_obj.custom_command_2(SALES_OBJ, message)


async def process_sales():
    global CLIENT, SALES_OBJ, SALES_CHANNEL
    await CLIENT.wait_until_ready()
    channel = CLIENT.get_channel(SALES_CHANNEL)
    while not CLIENT.is_closed():
        status = SALES_OBJ.check_os_api_status(EventType.SALE.value)
        if not status:
            await asyncio.sleep(30)
            continue
        exists = SALES_OBJ.check_if_new_post_exists()
        if not exists:
            await asyncio.sleep(5)
            continue
        res = await post_to_discord_obj.try_to_post_embed_to_discord(SALES_OBJ, channel)
        if res:
            await asyncio.sleep(5)
        else:
            await asyncio.sleep(10)


async def process_listings():
    global CLIENT, LISTINGS_OBJ, LISTINGS_CHANNEL
    await CLIENT.wait_until_ready()
    channel = CLIENT.get_channel(LISTINGS_CHANNEL)
    while not CLIENT.is_closed():
        status = LISTINGS_OBJ.check_os_api_status(EventType.LISTING.value)
        if not status:
            await asyncio.sleep(30)
            continue
        exists = LISTINGS_OBJ.check_if_new_post_exists()
        if not exists:
            await asyncio.sleep(5)
            continue
        res = await post_to_discord_obj.try_to_post_embed_to_discord(LISTINGS_OBJ, channel)
        if res:
            await asyncio.sleep(5)
        else:
            await asyncio.sleep(10)


async def update_gas_presence():
    global CLIENT, BOT_PREFIX, E_SCAN_KEY
    await CLIENT.wait_until_ready()
    while not CLIENT.is_closed():
        gas_tracker_url = 'https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey={}'.format(E_SCAN_KEY)
        try:
            gas_tracker_request = requests.get(gas_tracker_url, timeout=2)
            gas = gas_tracker_request.json()['result']
            slow_gas = gas['SafeGasPrice']
            avg_gas = gas['ProposeGasPrice']
            fast_gas = gas['FastGasPrice']
            await CLIENT.change_presence(activity=discord.Game(
                name='⚡ {} | 🚶 {} | 🐢 {} | {}help'.format(fast_gas, avg_gas, slow_gas, BOT_PREFIX)))
            print('Gas updated.', flush=True)
            await asyncio.sleep(30)
        except Exception as e:
            print(e)
            await asyncio.sleep(30)


def run(discord_token):
    global CLIENT
    CLIENT.run(discord_token)
