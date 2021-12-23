from post_to_twitter_obj import ManageFlowObj


ex = ManageFlowObj('Twitter Values .txt', 'True OR False OR Trait DB.json')

# The Twitter Values file (txt) must be like shown below (More info for keys can be found on the Twitter documentation.
# you must apply and create an app. https://developer.twitter.com/en):

# put normal hashtags here separated by a space. i.e. #crypto #nfts ...
# collection name here. can be found in the URL of the homepage of a collection.
# twitter api key
# twitter api key secret
# twitter access token
# twitter access token secret
# OS API key
# Etherscan API key Default Name

# for example:
# -----twitter_values.txt-----
# #nfts
# my-nft
# twitter_api_key
# twitter_api_key_secret
# twitter_access_token
# twitter_access_token_secret
# OS API key OR None
# Etherscan API key Name OR Etherscan API key

# The next provided string (Trait DB Name) is the .json file name for the trait TinyDB. This DB is used to efficiently
# query traits of a collection without hitting the asset endpoint. You can also pass in True or False inplace of a DB
# where True would hit the assets endpoint endpoint and False would not do anything. Passing in nothing will do the
# same as if you passed in False

# for example:
# True OR False OR nft_trait_db.json OR nothing

# example instantiators:
mfo = ManageFlowObj('twitter_values_humanoids.txt', 'humanoids_trait_db.json')  # will print traits using DB
# or
mfo2 = ManageFlowObj('twitter_values_humanoids.txt', True)  # will print traits using asset endpoint
# or
mfo3 = ManageFlowObj('twitter_values_humanoids.txt', False)  # will NOT print traits
# mfo3 is equivalent to "mfo3 = ManageFlowObj('twitter_values_humanoids.txt')"
