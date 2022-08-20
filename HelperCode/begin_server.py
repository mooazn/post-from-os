import os
import time


def begin_server():
    home = os.getcwd()
    config_file = open('sample_config.txt', 'r')
    for path in config_file.readlines():
        cur_path = path.strip().split('/')
        cur_directory = '/'.join(cur_path[0:4])
        cur_file_name = cur_path[-1]
        os.chdir(cur_directory)
        os.system(f'tmux new -d -s {cur_file_name[0:-3]}')
        os.system(f'tmux send-keys -t {cur_file_name[0:-3]} "python3 {cur_file_name}" enter')
        time.sleep(5)
    os.chdir(home)
    config_file.close()


begin_server()
