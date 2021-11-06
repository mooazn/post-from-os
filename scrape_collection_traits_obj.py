from scrape_collection_traits import ScrapeCollectionTraits

sct = ScrapeCollectionTraits('DB Name .json', 'Collection Name', 'Contract Address', 123)

# This file scrapes traits for the provided collection. The parameters are explained below:

# First parameters is the .json DB name for the traits DB. The DB will store all traits of each asset and the
# corresponding ID.

# The second parameter is the collection slug, or collection name, of the NFT collection. this MUST match what you see
# on the main page of the collection on OpenSea. The easiest way is to extract the name from the URL. for example:
# https://opensea.io/collection/boredapeyachtclub. You would extract 'boredapeyachtclub' and put that as the 2nd param.

# The third parameter is simply the contract address of the collection. I will remove this parameter later since I can
# extract that myself with the correct name.

# The last parameter is not necessary. However, it is preferred to provide it if you know the MAX COLLECTION SIZE (not
# the number there are right now). A collection could be still be minting and have 2000/5000 total so far. You MUST
# provide 5000 in this case, not 2000. another case is mints in the same project. for instance, if a project has
# "SOME NFT #2059" and they release a new project which maps the previous ID to the new one, it would look like
# "ANOTHER NFT #2059". If you provided 2000 in this case, it would obviously not put #2059 into the DB. This script
# really only makes sense to use for projects that have finished minting completely so you get accurate results.

# Ex.
# sct = ScrapeCollectionTraits('humanoids_trait_db.json', 'thehumanoids', '0x3a5051566b2241285be871f650c445a88a970edd',
#                              10000)
