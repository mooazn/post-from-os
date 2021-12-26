from post_to_reddit_obj import ManageFlowObj

ex = ManageFlowObj('Reddit Values .txt', 'Trait DB .json OR True OR False')

# The Reddit Values file (txt) must be like shown below (More info for keys can be found on the Reddit documentation.
# you must create an app. https://www.reddit.com/prefs/apps/):

# collection name here. can be found in the URL of the homepage of a collection.
# reddit client id
# reddit client secret
# reddit password
# user agent for reddit
# redit username
# Opensea API Key

# for example:
# -----twitter_values.txt-----
# my-nft
# reddit_client_id
# reddit_client_secret
# password for your reddit account
# User Agent (can literally be any string or an actual user agent if you want)
# username for your reddit account
# Opensea API Key

# The next provided string (Trait DB Name) is the .json file name for the trait TinyDB. This DB is used to efficiently
# query traits of a collection without hitting the asset endpoint. You can also pass in True or False inplace of a DB
# where True would hit the assets endpoint endpoint and False would not do anything. Passing in nothing will do the
# same as if you passed in False

# for example:
# True OR False OR nft_trait_db.json OR nothing

# example instantiators:
mfo = ManageFlowObj('reddit_values_humanoids.txt', 'humanoids_trait_db.json')  # will print traits using DB
# or
mfo2 = ManageFlowObj('reddit_values_humanoids.txt', True)  # will print traits using asset endpoint
# or
mfo3 = ManageFlowObj('reddit_values_humanoids.txt', False)  # will NOT print traits
# mfo3 is equivalent to "mfo3 = ManageFlowObj('reddit_values_humanoids.txt')"

