from thefuzz import fuzz
import subprocess


# proc = subprocess.Popen([''' tmux ls | awk '{ print substr($1, 1, length($1) - 1) }' '''], stdout=subprocess.PIPE,
#                         shell=True)
proc2 = subprocess.Popen([''' find .. | grep post_.*_twitter.py '''], stdout=subprocess.PIPE, shell=True)
paths = str(proc2.communicate()[0].decode()).strip().split('\n')
files = []
for path in paths:
    slash_split_path = path.split('/')
    file_name = slash_split_path[len(slash_split_path) - 1]
    files.append(file_name)
# tmux_sessions = str(proc.communicate()[0].decode()).strip().split('\n')
tmux_sessions = ['bananatwit', 'sirentwit', 'humanoidtwit']
if len(files) != len(tmux_sessions):
    print('Error')  # return the call
file_to_session = {}
for i in files:
    for j in tmux_sessions:
        if i != j:
            fuzz_partial_ratio = fuzz.partial_ratio(i.lower(), j.lower())
            if fuzz_partial_ratio >= 75:
                file_to_session[j] = i

session_num = 0
for i in range(0, len(tmux_sessions)):
    with open('notifier_{}.py'.format(tmux_sessions[session_num]), 'w') as n:
        n.write('from HelperCode import find_file\nimport os\nimport time\nfrom tinydb import TinyDB\n\n')
        n.write('''TMUX_{}_NAME = '{}' \n'''.format(tmux_sessions[session_num].upper(), tmux_sessions[session_num]))
        n.write('\n')
        n.write('''{}_FILE = find_file.find(\'{}\')\n'''.format(tmux_sessions[session_num].upper(),
                                                                file_to_session[tmux_sessions[session_num]]))
        n.write('''count_{}_db = TinyDB(\'count_iterations_{}.json\')\n\n'''.
                format(tmux_sessions[session_num].upper(), file_to_session[tmux_sessions[session_num]]. split('.')[0]))
        n.write('''occurred = False\n''')
        n.write('''prev_len = 0\n\n\n''')
        n.write('''def re_run_{}():\n\t'''.format(tmux_sessions[session_num]))
        n.write('''os.system(\'pfkill -f {}\')\n\t'''.format(file_to_session[tmux_sessions[session_num]]))
        n.write('''time.sleep(5)\n\t''')
        n.write('''os.system(\'tmux send-keys -t {} \"python3 {}\" enter\')\n\n\n'''.
                format(tmux_sessions[session_num], file_to_session[tmux_sessions[session_num]]))
        n.write('''while True:\n\t''')
        n.write('''if prev_len == len(count_{}_db):\n\t\t'''.format(tmux_sessions[session_num].upper()))
        n.write('''if occurred:\n\t\t\t''')
        n.write('''re_run_{}()\n\t\t\t'''.format(tmux_sessions[session_num]))
        n.write('''occurred = False\n\t\t\t''')
        n.write('''continue\n\t\t''')
        n.write('''occurred = True\n\t''')
        n.write('''if occurred:\n\t\t''')
        n.write('''occurred = False\n\t''')
        n.write('''prev_len = len(count_{}_db)\n'''.format(tmux_sessions[session_num].upper()))
        session_num += 1
