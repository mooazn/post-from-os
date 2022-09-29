from enum import Enum, auto
import requests

COIN_MAP = {}


class MarketPlace(Enum):
    OPENSEA = auto()
    ETHER_SCAN = auto()


def fetch_coin_by_address(token_address, cur_token_price, market_place):
    if token_address not in COIN_MAP:
        COIN_MAP[token_address] = cur_token_price
    # else:
    #     prev_token_price = COIN_MAP[token_address]
    #     if prev_token_price != cur_token_price:
    #         COIN_MAP[token_address] = cur_token_price
    #         return cur_token_price
    # token_req = requests.get('https://api.ethplorer.io/getTokenInfo/{}?apiKey=freekey'.format(token_address), timeout=3)
    # if token_req.status_code != 200:
    #     return cur_token_price
    if market_place == MarketPlace.OPENSEA:
        print(5)
    # return token_req.json()


fetch_coin_by_address('0', '0', MarketPlace.OPENSEA)
