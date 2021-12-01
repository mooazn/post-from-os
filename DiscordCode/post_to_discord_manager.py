import asyncio
import discord
import post_to_discord_obj
from post_to_discord_obj import ManageFlowObj, EventType
import requests
from requests.structures import CaseInsensitiveDict

client = discord.Client()
sales_obj = ManageFlowObj()
sales_channel = -1
listings_obj = ManageFlowObj()
listings_channel = -1


class ManageManager:
    def __init__(self, discord_values_file):
        self.discord_values = discord_values_file
        self.validate_params_and_run()

    def validate_params_and_run(self):
        global sales_obj, listings_obj, sales_channel, listings_channel
        print('Beginning validation of Discord Values File...')
        if not str(self.discord_values).endswith('.txt'):
            raise Exception('Discord values must be a .txt file.')
        with open(self.discord_values) as dv:
            if len(dv.readlines()) != 6:
                raise Exception('The Discord Values file must be formatted correctly.')
        test_discord_values = open(self.discord_values, 'r')
        discord_token = test_discord_values.readline().strip()
        channels = test_discord_values.readline().strip().split()
        try:
            sales_channel = int(channels[0])
            if len(channels) > 1:
                listings_channel = int(channels[1])
        except Exception as e:
            test_discord_values.close()
            print(e)
            raise Exception('Channels are not valid.')
        print('Channels validated.\n  Sales channel: {}\n  Listings Channel: {}'.
              format(sales_channel, listings_channel if listings_channel != -1 else 'No listings channel'))
        collection_name_test = test_discord_values.readline().strip()
        test_collection_name_url = 'https://api.opensea.io/api/v1/collection/{}'.format(collection_name_test)
        test_response = requests.request('GET', test_collection_name_url)
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
        if test_os_api_key != 'None':
            test_os_key_url = "https://api.opensea.io/api/v1/events?only_opensea=false&offset=0&limit=1"
            test_os_headers = CaseInsensitiveDict()
            test_os_headers['Accept'] = 'application/json'
            test_os_headers['x-api-key'] = test_os_api_key
            test_os_response = requests.request('GET', test_os_key_url, headers=test_os_headers)
            if test_os_response.status_code != 200:
                test_discord_values.close()
                raise Exception('Invalid OpenSea API key supplied.')
            print('OpenSea Key validated...')
        else:
            print('No OpenSea API Key supplied...')
        test_discord_values.close()
        print('Validation of Discord Values .txt complete. No errors found...')
        sales_obj.create([[collection_name_test], [contract_address], [test_discord_embed_icon], [r, g, b],
                          [test_os_api_key]])
        if listings_channel != -1:
            listings_obj.create([[collection_name_test], [contract_address], [test_discord_embed_icon], [r, g, b],
                                [test_os_api_key]])
        client.loop.create_task(process_sales())
        if listings_channel != -1:
            client.loop.create_task(process_listings())
        try:
            run(discord_token)
        except discord.errors.LoginFailure:
            raise Exception('Invalid Discord token supplied.')


@client.event
async def on_ready():
    print('Logged in...', flush=True)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content == '$yacht':
        await message.channel.send('https://www.fraseryachts.com/uploads/image/yachts/ace/Lurssen_yacht_for_sale_Ace_'
                                   '18362.jpg')


async def process_sales():
    await client.wait_until_ready()
    channel = client.get_channel(sales_channel)
    while not client.is_closed():
        status = sales_obj.check_os_api_status(EventType.SALE.value)
        if not status:
            await asyncio.sleep(30)
            continue
        exists = sales_obj.check_if_new_post_exists()
        if not exists:
            await asyncio.sleep(5)
            continue
        res = await post_to_discord_obj.try_to_post_embed_to_discord(sales_obj, channel)
        if res:
            await asyncio.sleep(5)
        else:
            await asyncio.sleep(10)


async def process_listings():
    await client.wait_until_ready()
    channel = client.get_channel(listings_channel)
    while not client.is_closed():
        status = listings_obj.check_os_api_status(EventType.LISTING.value)
        if not status:
            await asyncio.sleep(30)
            continue
        exists = listings_obj.check_if_new_post_exists()
        if not exists:
            await asyncio.sleep(5)
            continue
        res = await post_to_discord_obj.try_to_post_embed_to_discord(listings_obj, channel)
        if res:
            await asyncio.sleep(5)
        else:
            await asyncio.sleep(10)


def run(discord_token):
    client.run(discord_token)
