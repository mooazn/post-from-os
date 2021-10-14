from post_to_twitter_obj import ManageFlowObj


mfo = ManageFlowObj('Twitter Values.txt', 'Twitter Keys.txt', 'DB Name.json')

# The Twitter Values file (txt) must be like shown below:

# file_name:[put the name of the .jpeg file (with the extension) you want]
# twitter_tags:[put normal hashtags here separated by a space. i.e. #crypto #nfts ...]
# contract_address:[contract address here. can be found on the project's Ether scan or just in the link of an asset]

# The Twitter Keys file (txt) must be like shown below:

# api_key:[twitter api key]I
# api_key_secret:[twitter api key secret]
# access_token:[twitter access token]
# access_token_secret:[twitter access token secret]

# More info can be found on the Twitter documentation. you must apply and create an app.
# https://developer.twitter.com/en

# The last provided string (DB Name) is the .json file name for the TinyDB. The DB used to make sure each post is unique
# and is also helpful in case you have to restart the program (duplicates will not be posted).

# for example:
# mfo = ManageFlowObj('twitter_values_humanoids.txt', 'twitter_keys_humanoids.txt', 'humanoids_tx_hash_db.json')
