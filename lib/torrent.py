import hashlib
import requests
from lib import utils
from lib import bencoding


class File:
    def __init__(self, filepath):
        # 读入文件
        self.f = open(filepath, "rb")
        self.content = self.f.read()
        self.f.close()

        # 解释文件
        self.header = bencoding.decode(self.content)
        self.announce = self.header[b"announce"].decode("utf-8")
        self.info = self.header[b"info"]

        # 获取文件Hash
        m = hashlib.sha1()
        m.update(bencoding.encode(self.info))
        self.file_hash = m.digest()

        # 获取文件对应名
        self.name = self.info[b"name"].decode("utf-8")


class FileCache:
    def __init__(self, announce, file_hash):
        # 解释文件
        self.announce = announce
        self.file_hash = file_hash


class Seeder:
    def __init__(self, torrent, port, peer_id, ua):
        self.torrent = torrent
        self.peer_id = '-' + peer_id + '-' + utils.random_id(12)
        self.download_key = utils.random_id(12)
        self.port = port
        # 为了防止被扫描作弊,进行一定程度的屏蔽.
        # 1)有人下载时不做种.(因为做不了)
        # 2)做种人太少时候不保种. (因为别人一旦撤销,都是你在提供)
        self.complete = 0
        self.incomplete = 0
        self.stop_timer = 0
        self.header = {
            "Accept-Encoding": "gzip",
            "User-Agent": ua
        }

    def start(self):
        http_params = {
            "info_hash": self.torrent.file_hash,
            "peer_id": self.peer_id.encode("ascii"),
            "port": self.port,
            "uploaded": 0,
            "downloaded": 0,
            "left": 0,  # 假下载模式:self.torrent.total_size 假上传模式:0
            "event": "started",
            "key": self.download_key,
            "compact": 1,
            "numwant": 200,
            "supportcrypto": 1,
            "no_peer_id": 1
        }
        req = requests.get(self.torrent.announce, params=http_params,
                           headers=self.header)
        self.info = bencoding.decode(req.content)
        self.complete = self.info[b'complete']
        self.incomplete = self.info[b'incomplete']

        print('[' + self.download_key + ']开始任务,下载完成:' + str(self.complete) + ',等待下载:' + str(self.incomplete))

    def stop(self):
        http_params = {
            "info_hash": self.torrent.file_hash,
            "peer_id": self.peer_id.encode("ascii"),
            "port": self.port,
            "uploaded": 0,
            "downloaded": 0,
            "left": 0,  # 假下载模式:self.torrent.total_size 假上传模式:0
            "event": "stopped",
            "key": self.download_key,
            "compact": 1,
            "numwant": 0,
            "supportcrypto": 1,
            "no_peer_id": 1
        }
        r = requests.get(self.torrent.announce, params=http_params,
                         headers=self.header)
        # 等待100回合之后再试
        self.stop_timer = 100
        print('[' + self.download_key + ']暂停任务,下载完成:' + str(self.complete) + ',等待下载:' + str(self.incomplete))

    def heartbeat(self):
        if self.stop_timer > 1:
            print('[' + self.download_key + ']暂停等待:' + str(self.stop_timer))
            self.stop_timer = self.stop_timer - 1
            return
        elif self.stop_timer == 1:
            print('[' + self.download_key + ']暂停等待:' + str(self.stop_timer))
            self.start()
            self.stop_timer = 0
            self.complete = 0
            self.incomplete = 0
            return

        http_params = {
            "info_hash": self.torrent.file_hash,
            "peer_id": self.peer_id.encode("ascii"),
            "port": self.port,
            "uploaded": 0,  # 如果要作弊上传速度
            "downloaded": 0,
            "left": 0,  # 假下载模式:self.torrent.total_size 假上传模式:0
            "key": self.download_key,
            "compact": 1,
            "numwant": 0,
            "supportcrypto": 1,
            "no_peer_id": 1
        }
        req = requests.get(self.torrent.announce, params=http_params,
                           headers=self.header)
        self.info = bencoding.decode(req.content)
        self.complete = self.info[b'complete']
        self.incomplete = self.info[b'incomplete']

        print('[' + self.download_key + ']进行任务,下载完成:' + str(self.complete) + ',等待下载:' + str(self.incomplete))

        if self.complete < 5 or self.incomplete > 0:
            self.stop()