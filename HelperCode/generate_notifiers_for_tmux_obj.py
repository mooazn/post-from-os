import requests
import subprocess
from thefuzz import fuzz

# this script creates notifier python files for running tmux sessions in case they die unexpectedly.


class Generator:
    def __init__(self, generator_values_file):
        self.generator_values = open(generator_values_file, 'r')
        self.collection_names = self.generator_values.readline().strip().split()
        self.tmux_sessions = self.generator_values.readline().strip().split()
        self.contract_addresses = self.validate_collection()
        self.session_to_file = {}
        self.generator_values.close()
        self.find_python_files()
        self.generate_python_files()

    def validate_collection(self):
        if len(self.collection_names) != len(self.tmux_sessions):
            raise Exception('The number of collections must be the same number as the tmux sessions.')
        contract_addresses = []
        for collection_name in self.collection_names:
            test_collection_name_url = 'https://api.opensea.io/api/v1/collection/{}'.format(collection_name)
            test_response = requests.request('GET', test_collection_name_url)
            if test_response.status_code == 200:
                collection_json = test_response.json()['collection']
                primary_asset_contracts_json = collection_json['primary_asset_contracts'][0]
                contract_address = primary_asset_contracts_json['address']
                contract_addresses.append(contract_address)
            else:
                self.generator_values.close()
                raise Exception('The provided collection name does not exist.')
            print('Collection name validated...')
        return contract_addresses

    def find_python_files(self):  # looks for all .py files in the parent directory
        if len(self.collection_names) != len(self.tmux_sessions):
            return
        find_proc = subprocess.Popen([''' find .. | grep post_.*.*.py '''], stdout=subprocess.PIPE, shell=True)
        paths = str(find_proc.communicate()[0].decode()).strip().split('\n')
        files = []
        for path in paths:
            slash_split_path = path.split('/')
            file_name = slash_split_path[len(slash_split_path) - 1]
            files.append(file_name)
        for i in files:
            for j in self.tmux_sessions:
                if i != j:
                    fuzz_partial_ratio = fuzz.partial_ratio(i.lower(), j.lower())
                    if fuzz_partial_ratio >= 75:
                        self.session_to_file[j] = i

    def generate_python_files(self):
        if len(self.collection_names) != len(self.tmux_sessions):
            return
        for session_num in range(0, len(self.tmux_sessions)):
            cur_tmux_session_lower = self.tmux_sessions[session_num]
            with open('tmux_notifier_{}.py'.format(cur_tmux_session_lower), 'w') as n:
                cur_tmux_session_upper = cur_tmux_session_lower.upper()
                session_python_file = self.session_to_file[cur_tmux_session_lower]
                n.write(
                    '''import sys\nsys.path.append('../')\nfrom HelperCode import find_file\nimport os\nimport time\nfrom tinydb import TinyDB\n\n''')
                n.write('''COUNT_ITERATIONS_FILE = find_file.find(\'count_iterations_{}.json\')\n'''.
                        format(self.contract_addresses[session_num]))
                n.write('''if COUNT_ITERATIONS_FILE is not None:\n\t''')
                n.write('''count_{}_db = TinyDB(COUNT_ITERATIONS_FILE)\n\t'''.format(cur_tmux_session_upper))
                n.write('''occurred = False\n\tprev_len = 0\n\n\t''')
                n.write('''def re_run_{}():\n\t\t'''.format(cur_tmux_session_lower))
                n.write('''os.system(\'pkill -f {}\')\n\t\t'''.format(session_python_file))
                n.write('''time.sleep(5)\n\t\t''')
                n.write('''os.system(\'tmux send-keys -t {} \"python3 {}\" enter\')\n\n\t'''.
                        format(cur_tmux_session_lower, session_python_file))
                n.write('''while True:\n\t\tif prev_len == len(count_{}_db):\n\t\t\t'''.format(cur_tmux_session_upper))
                n.write('''if occurred:\n\t\t\t\tre_run_{}()\n\t\t\t\t'''.format(cur_tmux_session_lower))
                n.write('''occurred = False\n\t\t\t\tprint('Restarted script.')\n\t\t\telse:\n\t\t\t\t''')
                n.write('''occurred = True\n\t\t\t\tprint('Noticed something off. Will check again...')\n\t\t''')
                n.write('''else:\n\t\t\tif occurred:\n\t\t\t\toccurred = False\n\t\t\t''')
                n.write('''prev_len = len(count_{}_db)\n\t\t\t'''.format(cur_tmux_session_upper))
                n.write('''print('No need to restart.')\n\t\ttime.sleep(60)\n''')
        print('Generated notifier python files!')
