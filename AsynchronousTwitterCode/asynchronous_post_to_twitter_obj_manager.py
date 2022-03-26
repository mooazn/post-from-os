from asynchronous_post_to_twitter_manager import ManageMultipleTwitterPosts

MMTP = ManageMultipleTwitterPosts('Asynchronous Twitter Values .txt', 'Asynchronous Code File .py', False, False)

# The Asynchronous Twitter Values file (txt) must be like shown below (More info for keys can be found on the Twitter
# documentation. you must apply and create an app. https://developer.twitter.com/en):

# To separate collections, use the '|' character

# put normal hashtags here separated by a space. i.e. #crypto #nfts | #crypto #blockchain
# collection names here. can be found in the URL of the homepage of a collection.
# twitter api key
# twitter api key secret
# twitter access token
# twitter access token secret
# OS API keys
# Etherscan API keys
# Etherscan names

# for example:
# -----twitter_values.txt-----
# #nft #nfts | #crypto #eth | #eth
# my-nft | my-nft-2 | my-nft-3
# twitter_api_key
# twitter_api_key_secret
# twitter_access_token
# twitter_access_token_secret
# OS API key (additional OS API keys can be added as well, separated with '|')
# Etherscan API key (additional Etherscan API keys can be added as well, separated with '|')
# NFT | NFT-2 | NFT-3

# Following the file, there is a necessary argument which is the name of the asynchronous code file that will be
# generated when the program is ran. This is a .py file which executes all the code and keeps the program running.

# The next provided string arguments are True/False values. they should match the number of collections you provided.
# For example, if you provide one collection, you must provide a single True/False value. If you provided 3 collections,
# you must provide 3 True/False value. Etc. These True/False values determine whether or not traits will be printed for
# each collection, corresponding to the order you entered them in

# for example:
# True, False, True

# example instantiators:
mfo = ManageMultipleTwitterPosts('asynchronous_twitter_values_yachts.txt', 'asynchronous_twitter_code_yachts.py',
                                 False, False)  # will not print traits for # either collection

mfo2 = ManageMultipleTwitterPosts('asynchronous_twitter_values_yachts.txt', 'asynchronous_twitter_code_yachts.py',
                                  True, True)  # will print traits for both# collections

mfo3 = ManageMultipleTwitterPosts('asynchronous_twitter_values_yachts.txt', 'asynchronous_twitter_code_yachts.py',
                                  False, True)  # will print traits for only the 2nd collection that is provided.
# traits for first collection will not print
