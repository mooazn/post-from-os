import asyncio
import discord
import post_to_discord_obj
from post_to_discord_obj import ManageFlowObj, EventOrTransaction
import requests

client = discord.Client()
sales_obj = ManageFlowObj()
sales_channel = -1
listings_obj = ManageFlowObj()
listings_channel = -1


class ManageManager:
    def __init__(self, discord_sales_db_name, discord_listings_db_name, discord_keys_file, discord_values_file):
        self.sales_db = discord_sales_db_name
        self.listings_db = discord_listings_db_name
        self.discord_keys = discord_keys_file
        self.discord_values = discord_values_file
        self.validate_params_and_run()

    def validate_params_and_run(self):
        global sales_obj, listings_obj, sales_channel, listings_channel
        if not str(self.sales_db).endswith('.json'):
            raise Exception('Invalid file type for Sales DB .json')
        if not str(self.listings_db).endswith('.json'):
            raise Exception('Invalid file type for Listings DB .json')
        if str(self.discord_keys).endswith('.txt'):
            keys = open(self.discord_keys, 'r')
            token = keys.readline().strip()
            channels = keys.readline().strip().split()
            try:
                sales_channel = int(channels[0])
                listings_channel = int(channels[1])
                keys.close()
            except ValueError:
                keys.close()
                raise Exception('Channels cannot contain letters.')
        else:
            raise Exception('Invalid file type for Discord Keys .txt')
        if str(self.discord_values).endswith('.txt'):
            values = open(self.discord_values, 'r')
            contract_address = values.readline().strip()
            contract_url = 'https://api.opensea.io/api/v1/asset_contract/{}'.format(contract_address)
            response = requests.request('GET', contract_url)
            if response.status_code != 200:
                values.close()
                raise Exception('Invalid contract address.')
            values.close()
        else:
            raise Exception('Invalid file type for Discord Values .txt')
        sales_obj.create(self.sales_db, self.discord_values)
        listings_obj.create(self.listings_db, self.discord_values)
        run(token)


@client.event
async def on_ready():
    print('Logged in...', flush=True)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$test'):
        await message.channel.send('Running.')


async def process_sales():
    await client.wait_until_ready()
    channel = client.get_channel(sales_channel)
    while not client.is_closed():
        status = sales_obj.check_os_api_status(EventOrTransaction.SALE.value)
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
        status = listings_obj.check_os_api_status(EventOrTransaction.LISTING.value)
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


client.loop.create_task(process_sales())
client.loop.create_task(process_listings())


def run(discord_token):
    client.run(discord_token)
