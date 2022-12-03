import os
import time

tmux_names = []


def begin_server():
    os.system(f'tmux kill-server')
    home = os.getcwd()
    config_file = open('config.txt', 'r')
    for path in config_file.readlines():
        cur_path = path.strip().split('/')
        cur_directory = '/'.join(cur_path[0:-1])
        cur_file_name = cur_path[-1]
        os.chdir(cur_directory)
        cur_file_name_wo_ext = cur_file_name[0:-3]
        tmux_names.append(cur_file_name_wo_ext)
        os.system(f'tmux new -d -s {cur_file_name_wo_ext}')
        os.system(f'tmux send-keys -t {cur_file_name_wo_ext} bash enter')
        time.sleep(2)
        os.system(f'tmux send-keys -t {cur_file_name_wo_ext} "python3 {cur_file_name}" enter')
        print(f'Started \"{cur_file_name_wo_ext}\".')
        time.sleep(6.66)
    os.chdir(home)
    config_file.close()


def check_server():
    pass


begin_server()
check_server()
