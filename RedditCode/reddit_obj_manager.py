from post_to_reddit_obj import ManageFlowObj

ex = ManageFlowObj('Reddit Values .txt')

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

# example instantiators:
mfo = ManageFlowObj('reddit_values_humanoids.txt')
