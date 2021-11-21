from HelperCode import find_file
import time
from tinydb import TinyDB
import subprocess

# proc = subprocess.Popen([''' tmux ls | awk '{ print substr($1, 1, length($1) - 1) }' '''], stdout=subprocess.PIPE,
#                         shell=True)
proc2 = subprocess.Popen([''' find .. | grep post_.*_twitter.py '''], stdout=subprocess.PIPE,
                         shell=True)
print(str(proc2.communicate()[0].decode()).strip().split('\n'))
# tmux_sessions = str(proc.communicate()[0].decode()).strip().split('\n')
# notifier = open('notifier.py', 'w')
# notifier.write('from HelperCode import find_file\nimport os\nimport time\nfrom tinydb import TinyDB\n\n')
# for tmux_session in tmux_sessions:
#     notifier.write('''TMUX_{}_NAME = '{}' \n'''.format(tmux_session.upper(), tmux_session))
# notifier.write('\n')
# for python_file in range(0, len(tmux_sessions)):
#     notifier.write('''{}_FILE = find_file''')


# from HelperCode import find_file
# import os
# import time
# from tinydb import TinyDB
#
# TMUX_BANANAS_NAME = 'bananatwit'
# TMUX_SIRENS_NAME = 'sirentwit'
# TMUX_HUMANOIDS_NAME = 'humanoidtwit'
# BANANAS_FILE = 'post_bananas_twitter.py'
# SIRENS_FILE = 'post_sirens_twitter.py'
# HUMANOIDS_FILE = 'post_humanoids_twitter.py'
# # print(find_file.find('count_iterations_0x23094302439024.json'))
# count_db = TinyDB('../TwitterCode/count_iterations_0x23094302439024.json')
# occurred = False
# prev_len = 0
#
#
# def re_run_banana():
#     os.system('pkill -f {}'.format(BANANAS_FILE))
#     time.sleep(5)
#     os.system('tmux send-keys -t {} "python3 {}" enter'.format(TMUX_BANANAS_NAME, BANANAS_FILE))
#
#
# while True:
#     time.sleep(35)
#     if prev_len == len(count_db):
#         if occurred:  # check twice to make sure
#             re_run_banana()
#             occurred = False
#             continue
#         occurred = True
#     if occurred:
#         occurred = False
#     prev_len = len(count_db)
