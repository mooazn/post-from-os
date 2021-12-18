import sys
sys.path.append('../')
from HelperCode import find_file
import os
import time
from tinydb import TinyDB

COUNT_ITERATIONS_FILE = find_file.find('count_iterations_CONTRACTADDRESS.json')
if COUNT_ITERATIONS_FILE is not None:  # run only if iterations DB exists...
	count_FILE_db = TinyDB(COUNT_ITERATIONS_FILE)
	occurred = False
	prev_len = 0

	def re_run_FILEtwit():
		os.system('pkill -f post_FILE_twitter.py')  # kill the dead script
		time.sleep(5)
		os.system('tmux send-keys -t SESSION "python3 post_FILE_twitter.py" enter')  # rerun it with tmux command

	while True:
		if prev_len == len(count_FILE_db):
			if occurred:  # we notice the length of the DB is the same as last time TWICE!
				re_run_FILEtwit()
				occurred = False
				print('Restarted script.')
			else:  # first time we notice that the length of the DB is the same.
				occurred = True
				print('Noticed something off. Will check again...')
		else:
			if occurred:  # we thought the length of the DB is the same, but its not!
				occurred = False
			prev_len = len(count_FILE_db)
			print('No need to restart.')
		time.sleep(60)
