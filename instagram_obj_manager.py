from post_to_instagram_obj import ManageFlowObj


mfo = ManageFlowObj('Instagram Values.txt', 'Instagram User Access Token.txt', 'Instagram Email Credentials.txt', 'DB Name.json')


# The Instagram Values file (txt) must be like shown below:

# file_name:[put the name of the .jpeg file (with the extension) you want]
# img_bb_key:[the imgbb key. more info: https://api.imgbb.com/]
# insta_tags:[put normal hashtags here separated by a space. i.e. #crypto #nfts ...]
# page_id:[the page id of the instagram page found on Facebook]
# contract_address:[contract address here. can be found on the project's Ether scan or just in the link of an asset]

# The Instagram User Access Token file (txt) must be like shown below:

# [user access token here]

# The Instagram Email Credentials file (txt) must be like shown below:
# username:[your email]
# password:[your email's password]
# toemail:[email that you want to send the email to (could send to yourself!)]

# The last provided string (DB Name) is the .json file name for the TinyDB. The DB used to make sure each post is unique
# and is also helpful in case you have to restart the program (duplicates will not be posted).

# for example:
# mfo = ManageFlowObj('instagram_values_sirens.txt', 'instagram_user_access_token.txt', 'instagram_email_credentials.txt', 'sirens_tx_hash_db_insta.json')
