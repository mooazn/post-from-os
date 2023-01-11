from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders
from itertools import islice
import os
from pathlib import Path
import smtplib
import ssl


def send_mail(sender, password, receiver, smtp_server, port, files=None, subject=None, body=None):
    # TODO: make this use Google Drive
    err = False
    if files is None:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = receiver
        msg['Date'] = formatdate(localtime=True)
        if subject is None:
            subject = 'Log Report'
        if body is None:
            body = 'Log Report Summary'
        msg['Subject'] = subject
        msg.attach(MIMEText(body))
        try:
            with smtplib.SMTP(smtp_server, port) as server:
                server.starttls(context=ssl.create_default_context())
                server.login(sender, password)
                server.sendmail(sender, receiver, msg.as_string())
                server.quit()
        except Exception as e:
            print(e, flush=True)
            err = True
            return err
    else:
        for path in files:
            if not os.path.isabs(path):
                print('All paths passed to send_mail as a \'files\' parameter must be absolute paths.', flush=True)
                err = True
                return err
            file_size = os.path.getsize(path) / 1e6
            file_paths = []
            multiple_files = False
            if file_size >= 20:  # size in MB
                file_paths = _split_files_by_size(path, file_size)
                multiple_files = True
            else:
                file_paths.append(path)
            for file_path in file_paths:
                msg = MIMEMultipart()
                msg['From'] = sender
                msg['To'] = receiver
                msg['Date'] = formatdate(localtime=True)
                if subject is None:
                    msg['Subject'] = f"\'{path.split('/')[-1]}\' log file group for " \
                                     f"{(datetime.now() - timedelta(days=1)).strftime('%m/%d/%Y')}. " \
                                     f'Group consists of {len(file_paths)} file(s)'
                if body is None:
                    msg.attach(MIMEText(f"Log file for \'{file_path.split('/')[-1]}\'"
                                        f'\nFile Size: {os.path.getsize(file_path) / 1e6} MB'))
                part = MIMEBase('application', 'octet-stream')
                with open(file_path, 'rb') as cur_file:
                    part.set_payload(cur_file.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename={}'.format(Path(file_path).name))
                msg.attach(part)
                try:
                    with smtplib.SMTP(smtp_server, port) as server:
                        server.starttls(context=ssl.create_default_context())
                        server.login(sender, password)
                        server.sendmail(sender, receiver, msg.as_string())
                        server.quit()
                except Exception as e:
                    print(e, flush=True)
                    err = True
                    return err
            if multiple_files:
                for file_path in file_paths:
                    os.remove(file_path)
    return err


def _split_files_by_size(path, size):  # this is probably very inefficient
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
