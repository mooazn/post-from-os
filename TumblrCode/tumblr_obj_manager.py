from post_to_tumblr_obj import ManageFlowObj


ex = ManageFlowObj('Tumblr Values .txt', 'True OR False OR Trait DB.json')

# The Tumblr Values file (txt) must be like shown below (More info for keys can be found on the Tumblr documentation.
# you must register. (Follow Jimmy Ng's steps on here:
# https://stackoverflow.com/questions/16517965/python-tumblr-api-cannot-log-in-to-my-own-tumblr-to-create-posts
# /37548220#37548220)

# put normal hashtags here separated by a space. i.e. #crypto #nfts ...
# collection name here. can be found in the URL of the homepage of a collection.
# tumblr consume key
# tumblr consumer secret
# tumblr oauth token
# tumblr oauth token secret
# OS API key
# Blog Name

# for example:
# -----tumblr_values.txt-----
# #nfts
# my-nft
# tumblr_consumer_key
# tumblr_consumer_secret
# tumblr_oauth_token
# tumblr_oauth_token_secret
# OS API key OR None
# mycoolblog

# The next provided string (Trait DB Name) is the .json file name for the trait TinyDB. This DB is used to efficiently
# query traits of a collection without hitting the asset endpoint. You can also pass in True or False inplace of a DB
# where True would hit the assets endpoint endpoint and False would not do anything. Passing in nothing will do the
# same as if you passed in False

# for example:
# True OR False OR nft_trait_db.json OR nothing

# example instantiators:
mfo = ManageFlowObj('tumblr_values_humanoids.txt', 'humanoids_trait_db.json')  # will print traits using DB
# or
mfo2 = ManageFlowObj('tumblr_values_humanoids.txt', True)  # will print traits using asset endpoint
# or
mfo3 = ManageFlowObj('tumblr_values_humanoids.txt', False)  # will NOT print traits
# mfo3 is equivalent to "mfo3 = ManageFlowObj('tumblr_values_humanoids.txt')"
