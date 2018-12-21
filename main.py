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
        for path, info in (await ftp_session.list(recursive=True)):
            if info['type'] == 'dir':
                continue

            print(path)
            print(info, end='\n\n')

            file_filter_regex = re.compile(r'^(?P<dir>[\-ld])(?P<permission>([\-r][\-w][\-xs]){3})\s+(?P<filecode>\d+)\s+(?P<owner>\w+)\s+(?P<group>\w+)\s+(?P<size>\d+)\s+(?P<timestamp>((?P<month>\w{3})\s+(?P<day>\d{1,2})\s+(?P<hour>\d{1,2}):(?P<minute>\d{2}))|((?P<month2>\w{3})\s+(?P<day2>\d{1,2})\s+(?P<year>\d{4})))\s+(?P<name>.+)$', re.MULTILINE)
            if re.match(file_filter_regex, path):
                pass



if __name__ == "__main__":

    asyncio.run(main())
