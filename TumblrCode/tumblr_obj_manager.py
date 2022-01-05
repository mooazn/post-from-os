from post_to_tumblr_obj import ManageFlowObj


ex = ManageFlowObj('Tumblr Values .txt')

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

# example instantiators:
mfo = ManageFlowObj('tumblr_values_humanoids.txt')
