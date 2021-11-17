import os
import time
from tinydb import TinyDB, Query


TMUX_BANANAS_NAME = 'bananatwit'
TMUX_SIRENS_NAME = 'sirentwit'
TMUX_HUMANOIDS_NAME = 'humanoidtwit'
BANANAS_FILE = 'post_bananas_twitter.py'
SIRENS_FILE = 'post_sirens_twitter.py'
HUMANOIDS_FILE = 'post_humanoids_twitter.py'
count_db = TinyDB('../TwitterCode/count.json')
count_query = Query()
occurred = False
prev_len = 0


def re_run_banana():
    os.system('tmux send-keys -t {} "python3 {}" enter'.format(TMUX_BANANAS_NAME, BANANAS_FILE))
    time.sleep(15)
    os.system('pkill -f {}'.format(BANANAS_FILE))


while True:
    time.sleep(35)
    if prev_len == len(count_db):
        if occurred:  # check twice to make sure
            re_run_banana()
        occurred = True
    prev_len = len(count_db)
