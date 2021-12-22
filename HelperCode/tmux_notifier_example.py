import sys
sys.path.append('../')
from HelperCode import find_file
import os
import time
from tinydb import TinyDB

# this is an example of the generated tmux notifier script

COUNT_ITERATIONS_FILE = find_file.find('count_iterations_0x42e10846bbc6d062d1a41a8883ce2b81015a9523.json')
if COUNT_ITERATIONS_FILE is not None:  # run only if iterations DB exists...
    count_SIRENTWIT_db = TinyDB(COUNT_ITERATIONS_FILE)
    occurred = False
    prev_len = 0

    def re_run_sirentwit():
        os.system('pkill -f post_sirens_twitter.py')  # kill the frozen script
        time.sleep(5)
        os.system('tmux send-keys -t sirentwit "python3 post_sirens_twitter.py" enter')  # rerun it with tmux command

    while True:
        if prev_len == len(count_SIRENTWIT_db):
            if occurred:  # we notice the length of the DB is the same as last time TWICE!
                re_run_sirentwit()
                occurred = False
                print('Restarted script.')
            else:  # first time we notice that the length of the DB is the same.
                occurred = True
                print('Noticed something off. Will check again...')
        else:
            if occurred:  # we thought the length of the DB is the same, but its not
                occurred = False
            prev_len = len(count_SIRENTWIT_db)
            print('No need to restart.')
        time.sleep(60)
