from datetime import datetime, timedelta, time as t
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders
import os
from itertools import islice
from os import listdir
from os.path import isfile, join
from pathlib import Path
import smtplib
import ssl
import time


class _LogEmailer:
    def __init__(self):
        self.__log_file_directory = 'LogFiles'
        self.__log_email_creds_file = 'log_email_creds.txt'
        self.__from = ''
        self.__password = ''
        self.__to = ''
        self.__smtp_server = 'smtp.gmail.com'
        self.__port = 587
        self._parse_log_email_creds_file()
        self._cleanup_logs_and_send_email()

    def _parse_log_email_creds_file(self):
        if not os.path.exists(os.getcwd() + '/' + self.__log_email_creds_file):
            raise Exception('The email credentials file must exist inside Logs/ and be named \'log_email_creds.txt\'.')
        with open(self.__log_email_creds_file) as creds_file:
            if len(creds_file.readlines()) != 3:
                raise Exception('The email credentials file must be formatted properly.')
        with open(self.__log_email_creds_file) as creds_file:
            self.__from = creds_file.readline().strip()
            self.__password = creds_file.readline().strip()
            self.__to = creds_file.readline().strip()
            with smtplib.SMTP(self.__smtp_server, self.__port) as test_server:
                try:
                    test_server.starttls(context=ssl.create_default_context())
                    test_server.login(self.__from, self.__password)
                except Exception as e:
                    raise Exception(f'The supplied credentials are invalid. {e}')

    def _cleanup_logs_and_send_email(self):
        path = os.getcwd() + '/' + self.__log_file_directory
        while True:
            now = datetime.now()
            tomorrow = now + timedelta(days=1)
            seconds_left = (datetime.combine(tomorrow, t.min) - now).total_seconds()
            print(f"Time right now: {datetime.now().strftime('%m-%d-%Y %H:%M:%S')}.\nTime until 12 AM: {seconds_left}")
            time.sleep(seconds_left)
            files = [join(path, f) for f in listdir(path) if isfile(join(path, f)) and 'temp' in join(path, f)]
            send_mail(self.__from, self.__password, self.__to, self.__smtp_server, self.__port, files)
            for file in files:
                with open(join(path, file), 'r+') as log_file:
                    log_file.truncate(0)


def send_mail(sender, password, receiver, smtp_server, port, files):  # TODO: make this use Google Drive
    for path in files:
        file_size = os.path.getsize(path) / 1e6
        file_paths = []
        multiple_files = False
        if file_size > 20:
            file_paths = split_files_by_size(path, file_size)
            multiple_files = True
        else:
            file_paths.append(path)
        for file_path in file_paths:
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = receiver
            msg['Date'] = formatdate(localtime=True)
            msg['Subject'] = f"\'{path.split('/')[-1]}\' log file group for " \
                             f"{(datetime.now() - timedelta(days=1)).strftime('%m/%d/%Y')}. " \
                             f'Group consists of {len(file_paths)} file(s).'
            msg.attach(MIMEText(f"Log file for \'{file_path.split('/')[-1]}\'"
                                f'\nFile Size: {os.path.getsize(file_path) / 1e6} MB'))
            part = MIMEBase('application', 'octet-stream')
            with open(file_path, 'rb') as cur_file:
                part.set_payload(cur_file.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename={}'.format(Path(file_path).name))
            msg.attach(part)

            with smtplib.SMTP(smtp_server, port) as server:
                server.starttls(context=ssl.create_default_context())
                server.login(sender, password)
                server.sendmail(sender, receiver, msg.as_string())
                server.quit()

        if multiple_files:
            for file_path in file_paths:
                os.remove(file_path)


def split_files_by_size(path, size):  # this is probably very inefficient
    num_files_needed = int(round(size / 20, 2)) + 1
    new_file_paths = []
    with open(path, 'r') as ofp:
        for file in range(0, num_files_needed):
            cur_new_file_path = path[0:len(path) - 4] + f'_split_file_{file + 1}.txt'
            with open(cur_new_file_path, 'w') as cnf:
                new_file_paths.append(cur_new_file_path)
                cur_new_file_size = os.path.getsize(cur_new_file_path) / 1e6
                while cur_new_file_size < 20:
                    next_lines = list(islice(ofp, 999))
                    if not next_lines:
                        break
                    for line in next_lines:
                        cnf.write(line)
                    cur_new_file_size = os.path.getsize(cur_new_file_path) / 1e6
        if ofp.readline() != '':
            last_file = path[0:len(path) - 4] + f'_split_file_last.txt'
            with open(last_file, 'w') as cnf:
                new_file_paths.append(last_file)
                for line in ofp:
                    cnf.write(line)
    return new_file_paths


le = _LogEmailer()
