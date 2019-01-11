import configparser
import logging
import os
import re
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from zipfile import ZipFile
import smtplib, ssl

from ftplib import FTP, error_perm
import backoff

cfg = configparser.ConfigParser(inline_comment_prefixes="#")
cfg.read('config.cfg')

logging.basicConfig(level=logging.ERROR,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=cfg.get('LOG_FILES', 'default'))
logger = logging.getLogger('ftp_downloader')
logger.setLevel(logging.INFO)

PREFIXES = "shutterstock fotolia depositphoto istockphoto".strip().split(' ')
MAX_TRIES = 2


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


def exception_handler(e: Exception) -> None:
    print(e)
    logger.exception("An error has occurred. Let's try again")


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


@backoff.on_exception(backoff.expo, Exception, max_tries=MAX_TRIES, giveup=exception_handler)
def main():
    create_storage_dirs()
    downloaded_files = get_downloaded_files()

    ftp_session = FTP(cfg.get('FTP', 'host'),
                      user=cfg.get('FTP', 'user'),
                      passwd=cfg.get('FTP', 'pass'))

    ftp_session.cwd(cfg.get('FTP', 'dir'))

    file_names = []
    for file_name in ftp_session.nlst():
        try:
            ftp_session.cwd("{}/{}".format(cfg.get('FTP', 'dir'), file_name))
            ftp_session.cwd(cfg.get('FTP', 'dir'))
            continue
        except error_perm as e:
            pass

        file_name = Path(file_name)
        file_names.append(file_name)

        prefix_filter = re.search(r'([^_])*', str(file_name))
        if prefix_filter is None:
            logger.info("Unknown file: {}".format(file_name))
            continue

        prefix = prefix_filter.group().lower()
        if prefix == 'adobestock':
            prefix = 'fotolia'

        if prefix not in PREFIXES:
            logger.info("Such archive type there isn't in prefixes list: {}".format(file_name))
            continue

        if re.search(r'\(\d+\)', str(file_name)):
            logger.info("Archive {} skipped".format(file_name))
            continue

        if file_name not in downloaded_files:
            with open('{}/{}'.format(cfg.get('STORE', prefix), file_name), 'wb') as file:
                ftp_session.retrbinary("RETR {}".format(file_name), file.write)

            print('Archive downloading: ', file_name)
            logger.info('Archive loaded {} in {}'.format(file_name, cfg.get('STORE', prefix)))
            log_file(prefix, file_name)

            if prefix == 'shutterstock' and file_name.suffix == '.zip':
                file_path = cfg.get('STORE', prefix) / file_name
                unzip_archive(file_path, cfg.get('STORE', prefix))
                (cfg.get('STORE', prefix) / file_name).unlink()
        else:
            logger.info("Archive {} already downloaded".format(file_name))

    send_logs_via_email()


def log_file(prefix, filename):
    with open(cfg.get('LOG_FILES', prefix), 'a') as file:
        file.write("{}\n".format(filename))


def unzip_archive(filename, dest: str = ''):
    try:
        with ZipFile(str(filename)) as zip_ref:
            zip_ref.extractall(path=dest)
    except Exception as e:
        print('File reading error {}'.format(filename))
        raise e


if __name__ == "__main__":
    main()
