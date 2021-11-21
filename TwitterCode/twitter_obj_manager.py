from post_to_twitter_obj import ManageFlowObj


ex = ManageFlowObj('Twitter Values .txt', 'Trait DB.json')

# The Twitter Values file (txt) must be like shown below (More info for keys can be found on the Twitter documentation.
# you must apply and create an app. https://developer.twitter.com/en):

# put normal hashtags here separated by a space. i.e. #crypto #nfts ...
# collection name here. can be found in the URL of the homepage of a collection.
# twitter api key
# twitter api key secret
# twitter access token
# twitter access token secret

# for example:
# -----twitter_values.txt-----
# #nfts
# my-nft
# api_key
# api_key_secret
# access_token
# access_token_secret

# The next provided string (Trait DB Name) is the .json file name for the trait TinyDB. This DB is used to efficiently
# query traits of a collection without hitting the asset endpoint (defaulted to None. if you do not pass a string in
# (which is valid and has all traits in it), no traits will not be printed in the output)

# for example:
# nft_trait_db.json

# example instantiator:
mfo = ManageFlowObj('twitter_values_humanoids.txt', 'humanoids_trait_db.json')
