from post_to_instagram_obj import ManageFlowObj


ex = ManageFlowObj('Instagram Values.txt', 'Instagram User Access Token.txt',
                   'Instagram User Token Values.txt', 'TX Hash DB Name.json')


# The Instagram Values .txt file must be like shown below:

# put the name of the .jpeg file (with the extension) you want
# the imgbb key. more info: https://api.imgbb.com/
# put normal hashtags here separated by a space. i.e. #crypto #nfts ...
# the page id of the instagram page found on Facebook
# contract address here. can be found on the project's Ether scan or just in the link of an asset

# The Instagram User Access Token .txt file must be like shown below:

# user access token here

# The Instagram User Token Values .txt file must be like shown below:
# facebook client id
# facebook client secret
# token file (where the User Access Token exists, should be same as Instagram User Access Token .txt)
# facebook email
# facebook password
# gmail email (remember to allow less secure apps)
# gmail password
# gmail to_email (who are you sending it to)

# The last provided string (DB Name) is the .json file name for the TinyDB. The DB used to make sure each post is unique
# and is also helpful in case you have to restart the program (duplicates will not be posted).

# for example:
mfo = ManageFlowObj('instagram_values_sirens.txt', 'instagram_user_access_token.txt',
                    'instagram_generate_user_token_values.txt', 'sirens_tx_hash_db_insta.json')
