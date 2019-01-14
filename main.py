import os
import re
import ssl
import smtplib
import configparser
from pathlib import Path
from email import encoders
from zipfile import ZipFile
from ftplib import FTP, error_perm
from threading import Thread, Event
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor
from logging import basicConfig, getLogger, ERROR, INFO
from tkinter import Tk, Button, Text, END, Scrollbar, RIGHT, Y, LEFT

cfg = configparser.ConfigParser(inline_comment_prefixes="#")
cfg.read('config.cfg')

basicConfig(level=ERROR,
            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
            datefmt='%m-%d %H:%M',
            filename=cfg.get('LOG_FILES', 'default'))

PREFIXES = "shutterstock fotolia depositphoto istockphoto".strip().split(' ')


def log_it(message: str, text_field: Text = None, level: str = INFO) -> None:
    logger = getLogger('ftp_downloader')
    logger.setLevel(level)

    print(message)
    logger.info(message)
    if text_field:
        try:
            text_field.insert(END, str(message) + '\n')
        except RuntimeError:
            # Для ситуации, когда окно программы уже закрыто (следовательно этот элемент уже уничтожен),
            # а некоторые таски ещё выполняются и вызывают функцию логирования
            pass


def create_storage_dirs():
    for prefix, dir_name in cfg.items('STORE'):
        os.makedirs(dir_name, exist_ok=True)


def get_downloaded_files():
    file_names = []
    for prefix, dir_name in cfg.items('STORE'):
        file_names.extend([Path(file_name)
                           for file_name in Path(dir_name).iterdir()
                           if file_name.is_file()])
    for prefix, log_file_name in cfg.items('LOG_FILES'):
        if prefix == 'default':
            continue
        try:
            with open(log_file_name) as file:
                file_names.extend([Path(line.strip('\n')) for line in file.readlines()])
        except FileNotFoundError:
            pass

    return file_names


def send_logs_via_email():
    # Create a secure SSL context
    context = ssl.create_default_context()

    message = MIMEMultipart()
    message["From"] = cfg.get('LOADER_EMAIL', 'email')
    message["To"] = cfg.get('EMAIL', 'email')
    message["Subject"] = 'FTP Downloader log'

    # Add body to email
    message.attach(MIMEText('FTP Downloader log', "plain"))

    # Open PDF file in binary mode
    with open(cfg.get('LOG_FILES', 'default'), "rb") as attachment:
        # Add file as application/octet-stream
        # Email client can usually download this automatically as attachment
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    encoders.encode_base64(part)

    # Add header as key/value pair to attachment part
    part.add_header(
        "Content-Disposition",
        "attachment; filename=ftp_downloader.log",
    )

    # Add attachment to message and convert message to string
    message.attach(part)
    text = message.as_string()

    with smtplib.SMTP_SSL("smtp.mail.ru", cfg.get('LOADER_EMAIL', 'port'),
                          context=context) as server:
        server.login(cfg.get('LOADER_EMAIL', 'email'), cfg.get('LOADER_EMAIL', 'password'))

        server.sendmail(cfg.get('LOADER_EMAIL', 'email'), cfg.get('EMAIL', 'email'), text)

        log_it('Logs sent')


def get_ftp_connection():
    ftp_session = FTP(cfg.get('FTP', 'host'))
    ftp_session.login(user=cfg.get('FTP', 'user'), passwd=cfg.get('FTP', 'pass'))
    ftp_session.cwd(cfg.get('FTP', 'dir'))

    return ftp_session


def download_archive(file_name, text_field):
    if not flag.is_set():
        return

    with get_ftp_connection() as ftp_session:
        try:
            ftp_session.cwd("{}/{}".format(cfg.get('FTP', 'dir'), file_name))
            ftp_session.cwd(cfg.get('FTP', 'dir'))
            return
        except error_perm:
            pass

        prefix_filter = re.search(r'([^_])*', str(file_name))
        if prefix_filter is None:
            log_it("Unknown file: {}".format(file_name), text_field=text_field)
            return

        prefix = prefix_filter.group().lower()
        if prefix == 'adobestock':
            prefix = 'fotolia'

        if prefix not in PREFIXES:
            log_it("Such file type there isn't in prefixes list: {}".format(file_name),
                   text_field=text_field)
            return

        if re.search(r'\(\d+\)', str(file_name)):
            log_it("File {} skipped".format(file_name),
                   text_field=text_field)
            return

        if file_name not in downloaded_files:
            log_it("File {} will be load".format(file_name), text_field=text_field)
            with open('{}/{}'.format(cfg.get('STORE', prefix), file_name), 'wb') as file:
                ftp_session.retrbinary("RETR {}".format(file_name), file.write)

            log_it('File loaded {} in {}'.format(file_name, cfg.get('STORE', prefix)),
                   text_field=text_field)
            log_file(prefix, file_name)  # запоминаем имя скачанного файла

            if prefix == 'shutterstock' and file_name.suffix == '.zip':
                file_path = cfg.get('STORE', prefix) / file_name
                unzip_archive(file_path, text_field=text_field, dest=cfg.get('STORE', prefix))
                (cfg.get('STORE', prefix) / file_name).unlink()

    return True


def main(text_field):
    create_storage_dirs()
    global downloaded_files
    downloaded_files = get_downloaded_files()

    with get_ftp_connection() as ftp_session:
        entry_names = ftp_session.nlst()

    futures = []
    with ThreadPoolExecutor(max_workers=4, ) as executor:
        for entry_name in entry_names:
            futures.append(executor.submit(download_archive, Path(entry_name), text_field))

    results = [future.result() for future in futures]

    if any(results):
        send_logs_via_email()


def log_file(prefix, filename):
    with open(cfg.get('LOG_FILES', prefix), 'a') as file:
        file.write("{}\n".format(filename))


def unzip_archive(filename, text_field, dest=''):
    try:
        with ZipFile(str(filename)) as zip_ref:
            zip_ref.extractall(path=dest)
            log_it('File {} unpacked to {}'.format(filename, dest), text_field=text_field)
    except Exception as e:
        log_it('File reading error {}'.format(filename), text_field=text_field)
        raise e


def on_closing():
    flag.clear()
    APP_WINDOW.destroy()


if __name__ == "__main__":
    flag = Event()
    flag.set()

    APP_WINDOW = Tk()
    APP_WINDOW.title = "Stock photo archives downloader"

    SCROLLBAR = Scrollbar(APP_WINDOW)
    SCROLLBAR.pack(side=RIGHT, fill=Y)

    TEXT_FIELD = Text(APP_WINDOW, height=15, width=70)
    TEXT_FIELD.pack(side=LEFT, fill=Y)
    TEXT_FIELD.insert(END, '')

    SCROLLBAR.config(command=TEXT_FIELD.yview)
    TEXT_FIELD.config(yscrollcommand=SCROLLBAR.set)

    ftp_downloader = Thread(target=main, args=(TEXT_FIELD,))
    START_BUTTON = Button(master=APP_WINDOW, text='Start', command=ftp_downloader.start, width=20)
    START_BUTTON.pack(side=LEFT, fill=Y)

    APP_WINDOW.protocol("WM_DELETE_WINDOW", on_closing)
    APP_WINDOW.mainloop()
