import asyncio
import configparser

from aioftp import ClientSession


cfg = configparser.ConfigParser(inline_comment_prefixes="#")
cfg.read('config.cfg')

HOST = cfg.get('FTP', 'HOST')
PORT = cfg.get('FTP', 'PORT')
USER = cfg.get('FTP', 'USER')
PASS = cfg.get('FTP', 'PASS')
DIR = cfg.get('FTP', 'DIR')


async def main():
    async with ClientSession(HOST, PORT, USER, PASS) as ftp_session:
        for path, info in (await ftp_session.list(recursive=False)):
            pass


if __name__ == "__main__":

    asyncio.run(main())
