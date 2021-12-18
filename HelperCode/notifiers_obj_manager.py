from generate_notifiers_for_tmux_obj import Generator

g = Generator('generator_values_for_tmux_file.txt')

# The Generator Values file (txt) must be like shown below:

# collection names separated by space. they can be found in the URL of the homepage
# tmux session names separated by space. make sure they match your collection names a little bit

# for example:
# -----twitter_values.txt-----
# nft-1 nft-2
# nft-1session nft-2session
