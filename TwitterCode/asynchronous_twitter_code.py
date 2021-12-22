import asyncio
from asynchronous_post_to_twitter_obj import ManageFlowObj


async def collection_1(obj):        
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
        res = obj.try_to_post_to_twitter()
        if res:
            await asyncio.sleep(5)
        else:
            await asyncio.sleep(10)
    

async def collection_2(obj):        
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
        res = obj.try_to_post_to_twitter()
        if res:
            await asyncio.sleep(5)
        else:
            await asyncio.sleep(10)
    

def run(values_map):
    loop = asyncio.get_event_loop()
    collection_1_obj = ManageFlowObj(values_map[0])
    collection_2_obj = ManageFlowObj(values_map[1])
    loop.create_task(collection_1(collection_1_obj))
    loop.create_task(collection_2(collection_2_obj))
    loop.run_forever()
