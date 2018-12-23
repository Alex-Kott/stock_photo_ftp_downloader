import asyncio
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

import backoff
from aioftp import ClientSession
from aiogram import Bot
from aiogram.utils.exceptions import NetworkError

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
    # for prefix, dir_name in cfg.items('STORE'):
    #     file_names.extend([Path(file_name) for file_name in Path(dir_name).iterdir() if file_name.is_file()])
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
    logger.exception(f"An error has occurred. Let's try again")


def send_logs_via_email():
    import smtplib, ssl

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
        f"attachment; filename= ftp_downloader.log",
    )

    # Add attachment to message and convert message to string
    message.attach(part)
    text = message.as_string()

    with smtplib.SMTP_SSL("smtp.mail.ru", cfg.get('LOADER_EMAIL', 'port'), context=context) as server:
        server.login(cfg.get('LOADER_EMAIL', 'email'), cfg.get('LOADER_EMAIL', 'password'))

        server.sendmail(cfg.get('LOADER_EMAIL', 'email'), cfg.get('EMAIL', 'email'), text)


async def send_logs_via_tg():
    bot = Bot(token=cfg.get('TG', 'bot_token'))
    with open(cfg.get('LOG_FILES', 'default'), 'rb') as file:
        await bot.send_document(cfg.get('TG', 'chat_id'), document=file)


async def send_logs():
    try:
        await send_logs_via_tg()
    except NetworkError:
        logger.exception("Can't connect to Telegram server")
        send_logs_via_email()


@backoff.on_exception(backoff.expo, Exception, max_tries=MAX_TRIES, giveup=exception_handler)
async def main():
    create_storage_dirs()
    downloaded_files = get_downloaded_files()

    async with ClientSession(cfg.get('FTP', 'host'), cfg.get('FTP', 'port'),
                             cfg.get('FTP', 'user'), cfg.get('FTP', 'pass')) as ftp_session:
        await ftp_session.change_directory(cfg.get('FTP', 'dir'))
        for filename, info in (await ftp_session.list(recursive=True)):
            filename = Path(filename)
            if info['type'] == 'dir':
                continue

            prefix_filter = re.search(r'([^_])*', str(filename))
            if prefix_filter is None:
                logger.info(f"Unknown file: {filename}")
                continue

            prefix = prefix_filter.group().lower()
            if prefix == 'adobestock':
                prefix = 'fotolia'

            if prefix not in PREFIXES:
                logger.info(f"Such archive type there isn't in prefixes list: {filename}")
                continue

            if re.search(r'\(\d+\)', str(filename)):
                logger.info(f"Archive {filename} skipped")
                continue

            if filename not in downloaded_files:
                await ftp_session.download(filename, destination=cfg.get('STORE', prefix))
                print('Archive downloading: ', filename)
                logger.info(f'Archive loaded {filename} in {cfg.get("STORE", prefix)}')
                log_file(prefix, filename)

                if prefix == 'shutterstock' and filename.suffix == '.zip':
                    file_path = cfg.get('FTP', 'dir') / filename
                    unzip_archive(file_path, cfg.get('STORE', prefix))
                    (cfg.get('STORE', prefix) / filename).unlink()
            else:
                logger.info(f"Archive {filename} already downloaded")

    await send_logs()


def log_file(prefix, filename):
    with open(cfg.get('LOG_FILES', prefix), 'a') as file:
        file.write(f"{filename}\n")


def unzip_archive(filename, dest: str = ''):
    try:
        with ZipFile(filename) as zip_ref:
            zip_ref.extractall(path=dest)
    except Exception as e:
        print(f'Ошибка при чтении архива {filename}')
        raise e


if __name__ == "__main__":
    asyncio.run(main())
