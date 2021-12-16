from post_to_discord_manager import ManageManager

ex = ManageManager('Discord Values .txt')

# The Discord Values file (txt) must be like shown below (More info for keys can be found on the Discord Bots area.
# you must create an app and add a bot. https://discord.com/developers/applications):

# put discord bot token here
# put the channel ids here. for now, sales listings or sales
# collection name here. can be found in the URL of the homepage of a collection.
# Discord embed icon URL or None
# RGB values r g b or None
# OS API Key
# EtherScan API Key
# Bot prefix or None
# Command Description (surrounded with double quotes)

# for example:
# -----discord_values.txt-----
# bot token
# sales_channel_id listings_channel_id OR sales_channel_id
# the-nft
# image.jpg OR image.jpeg OR image.png
# 0 0 0
# OS API key
# EtherScan API Key
# ! or ? or >> or... etc.
# example "this is an example command"

# example instantiator:
mm = ManageManager('discord_values_yachts.txt')
