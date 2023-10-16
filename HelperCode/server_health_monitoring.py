import os
import threading
import time

one_week_sleep = 604800
two_days_sec = 172800


def cleanup_unnecessary_logs():
    os.chdir('..')
    full_path = os.getcwd() + '/Logs/LogFiles'
    while True:
        count = 0
        os.chdir(full_path)
        for f in os.listdir():
            cur_file = full_path + '/' + f
            time_modified = int(os.path.getmtime(cur_file))
            seconds_since_modified = int(time.time()) - time_modified
            if seconds_since_modified >= two_days_sec:
                os.remove(cur_file)
                count += 1
        print(f'Removed {count} log files.')
        time.sleep(one_week_sleep)


cleanup_thread = threading.Thread(target=cleanup_unnecessary_logs)
cleanup_thread.start()
