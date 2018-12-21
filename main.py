import asyncio
import configparser
import re

from aioftp import ClientSession

cfg = configparser.ConfigParser(inline_comment_prefixes="#")
cfg.read('config.cfg')

HOST = cfg.get('FTP', 'HOST')
PORT = cfg.get('FTP', 'PORT')
USER = cfg.get('FTP', 'USER')
PASS = cfg.get('FTP', 'PASS')
DIR = cfg.get('FTP', 'DIR')


async def main():
    prefixes = "shutterstock fotolia depositphoto istockphoto".split(' ')
    async with ClientSession(HOST, PORT, USER, PASS) as ftp_session:
        await ftp_session.change_directory(DIR)
        for filename, info in (await ftp_session.list(recursive=True)):
            if info['type'] == 'dir':
                continue

            # print(filename)
            # print(info, end='\n\n')

            pattern = re.compile(r'^(?P<dir>[\-ld])'
                                 r'(?P<permission>([\-r][\-w][\-xs]){3})\s+'
                                 r'(?P<filecode>\d+)\s+'
                                 r'(?P<owner>\w+)\s+'
                                 r'(?P<group>\w+)\s+'
                                 r'(?P<size>\d+)\s+'
                                 r'(?P<timestamp>((?P<month>\w{3})\s+(?P<day>\d{1,2})\s+(?P<hour>\d{1,2}):(?P<minute>\d{2}))|((?P<month2>\w{3})\s+(?P<day2>\d{1,2})\s+(?P<year>\d{4})))\s+'
                                 r'(?P<name>.+)$', re.MULTILINE)

            prefix = pattern.search(filename)

            print(prefix)


if __name__ == "__main__":

    asyncio.run(main())
