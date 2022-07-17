import asyncio
import post_to_discord_obj
from post_to_discord_obj import EventType, ManageFlowObj

# THIS IS AN EXAMPLE OF A GENERATED FILE


async def process_sales_0(client, sales_obj, sales_channel):
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
            

async def process_sales_1(client, sales_obj, sales_channel):
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
            

def run(client, values, traits):
    sales_obj_0 = ManageFlowObj(values[0][0], traits)
    client.loop.create_task(process_sales_0(client, sales_obj_0, values[0][1][0]))
    sales_obj_1 = ManageFlowObj(values[1][0], traits)
    client.loop.create_task(process_sales_1(client, sales_obj_1, values[1][1][0]))
    