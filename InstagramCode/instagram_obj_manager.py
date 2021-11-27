from post_to_instagram_obj import ManageFlowObj


ex = ManageFlowObj('Instagram Values.txt', 'Instagram Generate User Token Values.txt')

# The Instagram Values .txt file must be like shown below:

# put normal hashtags here separated by a space. i.e. #crypto #nfts ...
# collection name here. can be found in the URL of the homepage of a collection.
# the imgbb key. more info: https://api.imgbb.com/
# the page id of the instagram page found on Facebook

# for example:
# -----instagram_values.txt-----
# #nfts #crypto #insta #newpost #follow4follow
# my-nft
# imgbb key
# page id
# OS api key

# The Instagram Generate User Token Values .txt file must be like shown below:
# facebook client id
# facebook client secret
# facebook email
# facebook password
# gmail email (this is your email. remember to allow less secure apps)
# gmail password
# gmail to_email (who are you sending it to, could be yourself...)

# for example:
# -----instagram_generate_user_token_values_sirens.txt-----
# fb client id
# fb client secret
# fb_email@domain.com
# fb_password
# gmail_email@gmail.com
# gmail_password
# gmail_to_email@gmail.com

# for example:
mfo = ManageFlowObj('instagram_values_sirens.txt', 'instagram_generate_user_token_values_sirens.txt')
