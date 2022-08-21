import os
import time


def begin_server():
    os.system(f'tmux kill-server')
    print('All tmux sessions killed.')
    home = os.getcwd()
    config_file = open('config.txt', 'r')
    for path in config_file.readlines():
        cur_path = path.strip().split('/')
        cur_directory = '/'.join(cur_path[0:-1])
        cur_file_name = cur_path[-1]
        os.chdir(cur_directory)
        os.system(f'tmux new -d -s {cur_file_name[0:-3]}')
        os.system(f'tmux send-keys -t {cur_file_name[0:-3]} "python3 {cur_file_name}" enter')
        print(f'Started {cur_file_name} successfully.')
        time.sleep(2.5)
    os.chdir(home)
    config_file.close()


begin_server()
