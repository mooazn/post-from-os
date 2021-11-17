import requests
import os

# the focus of this file is to run the scripts in case they die :)

os.system('python3 test.py')

# while True:
#     url = "https://api.opensea.io/api/v1/events?asset_contract_address=0x3a5051566b2241285be871f650c445a88a970edd" \
#           "&event_type=successful&only_opensea=false&offset=0&limit=300 "
#
#     headers = {"Accept": "application/json"}
#
#     response = requests.request("GET", url, headers=headers)
#
#     print(response.text)

