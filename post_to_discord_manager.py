import asyncio
import discord
import post_to_discord_obj
from post_to_discord_obj import ManageFlowObj, EventOrTransaction


client = discord.Client()
sales_obj = None
listings_obj = None
sales_channel = None
listings_channel = None


class ManageManager:
    def __init__(self, discord_sales_db_name, discord_listings_db_name, discord_keys_file, discord_values_file):
        global sales_obj, listings_obj, sales_channel, listings_channel
        sales_obj = ManageFlowObj(discord_sales_db_name, discord_values_file)
        listings_obj = ManageFlowObj(discord_listings_db_name, discord_values_file)
        discord_keys = open(discord_keys_file, 'r')
        self.discord_token = discord_keys.readline().strip()
        discord_channels = discord_keys.readline().split(':')[1].strip()
        discord_keys.close()
        channels = discord_channels.split()
        sales_channel = int(channels[0])
        listings_channel = int(channels[1])

    def run(self):
        run(self.discord_token)


@client.event
async def on_ready():
    pass


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')


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
        res = await post_to_discord_obj.try_to_post_to_discord(sales_obj, channel)
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
        res = await post_to_discord_obj.try_to_post_to_discord(listings_obj, channel)
        if res:
            await asyncio.sleep(5)
        else:
            await asyncio.sleep(10)


client.loop.create_task(process_sales())
client.loop.create_task(process_listings())


def run(discord_token):
    client.run(discord_token)
