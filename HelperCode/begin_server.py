from find_file import find
import os
import shutil
import time


def read_buf_file(buf_file):
    with open(buf_file, 'r') as buf:
        for line in buf.readlines():
            if len(line.strip()) == 0:
                return -1
            if line.startswith('Log File Names: '):
                log_file_locations = line.split('Log File Names: ')[1].split()
                if len(log_file_locations) != 2:
                    return -2
                log_file = log_file_locations[0]
                junk_log_file = log_file_locations[1]
                return [log_file, junk_log_file]
            elif line.startswith('Heartbeat at '):
                pass
            else:
                return -2
        return -1


class BeginOSBots:
    def __init__(self):
        self.tmux_names = []
        self.cur_dir = 'HelperCode'
        if not os.getcwd().endswith(self.cur_dir):
            raise Exception('begin_server.py file incorrectly placed. Must be inside HelperCode/')
        self.buf_file_dir = 'BufferFiles'
        self.all_locations_file = 'all_locations.txt'
        self.config_file = 'sample_config.txt'
        self.all_locations_file_path = f'{os.getcwd()}/{self.buf_file_dir}/{self.all_locations_file}'
        self.delimiter = '>>>>>'
        self.retry_limit = 5
        self.begin_server()
        self.check_server()
        self.recheck_all_locations_file()

    def begin_server(self):
        os.system(f'tmux kill-server')
        home = os.getcwd()
        config_file = open(self.config_file, 'r')
        for path in config_file.readlines():
            cur_path = path.strip().split('/')
            cur_directory = '/'.join(cur_path[0:-1])
            cur_file_name = cur_path[-1]
            os.chdir(cur_directory)
            cur_file_name_wo_ext = cur_file_name[0:-3]
            self.tmux_names.append(cur_file_name_wo_ext)
            os.system(f'tmux new -d -s {cur_file_name_wo_ext}')
            os.system(f'tmux send-keys -t {cur_file_name_wo_ext} bash enter')
            time.sleep(2)
            os.system(f'tmux send-keys -t {cur_file_name_wo_ext} "python3 {cur_file_name}" enter')
            time.sleep(6.66)
        os.chdir(home)
        config_file.close()

    def check_server(self, tmux_server=None):
        if tmux_server is not None:
            buf_file_name = f'buffer_{tmux_server}.txt'
            buf_file_location = f'{self.buf_file_dir}/{buf_file_name}'
            os.system(f'tmux capture-pane -pS -200 -t {tmux_server} > {buf_file_name}')
            shutil.move(buf_file_name, buf_file_location)
            return read_buf_file(buf_file_location)
        all_location_file = open(self.all_locations_file_path, 'w')
        for tmux_session in self.tmux_names:
            buf_file_name = f'buffer_{tmux_session}.txt'
            buf_file_location = f'{self.buf_file_dir}/{buf_file_name}'
            os.system(f'tmux capture-pane -pS -200 -t {tmux_session} > {buf_file_name}')
            shutil.move(buf_file_name, buf_file_location)
            log_file_locations_call = read_buf_file(buf_file_location)
            all_location_file.write(tmux_session + self.delimiter + tmux_session + '.py' + self.delimiter)
            if log_file_locations_call == -1:
                all_location_file.write('ERR' + self.delimiter + 'NO LOGS WRITTEN\n')
            elif log_file_locations_call == -2:
                all_location_file.write('ERR' + self.delimiter + 'INVALID LOG FILES\n')
            elif log_file_locations_call is not None:
                all_location_file.write('SUCCESS' + self.delimiter + log_file_locations_call[0] + self.delimiter +
                                        log_file_locations_call[1] + '\n')
        all_location_file.close()

    def recheck_all_locations_file(self):
        data = []
        with open(self.all_locations_file_path, 'r') as f:
            for line in f:
                data.append(line.strip())
        with open(self.all_locations_file_path, 'r') as all_locations_file:
            idx = 0
            for locations in all_locations_file:
                cur_locations_split = locations.split(self.delimiter)
                if len(cur_locations_split) == 5 and cur_locations_split[4].strip() == 'PYTHON FILE CANNOT BE FOUND':
                    continue
                err_code = cur_locations_split[2]
                if err_code == 'ERR':
                    tmux_server_name = cur_locations_split[0]
                    python_file_name = cur_locations_split[1]
                    if find(python_file_name) is None:
                        data[idx] = data[idx] + self.delimiter + 'PYTHON FILE CANNOT BE FOUND\n'
                    else:
                        os.system(f'tmux send-keys -t {tmux_server_name} "python3 {python_file_name}" enter')
                        time.sleep(6.66)
                        log_file_locations_call = self.check_server(tmux_server_name)
                        iterations = 1
                        while log_file_locations_call == -1 or log_file_locations_call == -2:
                            if not data[idx].endswith(f'FAIL ITERATION {iterations}') and iterations == 1:
                                data[idx] += f'{self.delimiter}FAIL ITERATION {iterations}'
                            if iterations == self.retry_limit:
                                data[idx] += self.delimiter + 'FAILURE'
                                break
                            data[idx] = data[idx].replace(f'FAIL ITERATION {iterations}', f'FAIL ITERATION '
                                                                                          f'{iterations + 1}')
                            os.system(f'tmux send-keys -t {tmux_server_name} "python3 {python_file_name}" enter')
                            time.sleep(6.66)
                            log_file_locations_call = self.check_server(tmux_server_name)
                            iterations += 1
                        if log_file_locations_call != -1 and log_file_locations_call != -2 and log_file_locations_call \
                                is not None:
                            data[idx] = log_file_locations_call[0] + self.delimiter + log_file_locations_call[1] + \
                                        self.delimiter + data[idx] + self.delimiter + 'SUCCESS'
                idx += 1
        with open(self.all_locations_file_path, 'w') as f:
            for locations in data:
                f.write(locations + '\n')
        pass


BeginOSBots()
