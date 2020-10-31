import bson
import json
import time
import datetime
import feedparser
import qbittorrentapi
import pymongo
import requests
import pickle
import func_timeout
import honeybadger

class QBAgent:
    def __init__(self, remark='未命名主机',destination='127.0.0.1', port=8080, username='admin', password='adminadmin', quota=0,
                 reserved=5.0, bandwidth=10):

        self.QBClient = qbittorrentapi.Client(host=destination + ':' + str(port), username=username, password=password)
        self.QBClient.auth_log_in()

        self.destination = destination
        self.quota = quota
        self.free_space_on_disk = 0
        self.free_space_on_task = 0
        self.alltime_ul = 0
        self.alltime_dl = 0
        self.up_info_speed = 0
        self.dl_info_speed = 0
        self.disk_latency = 0
        self.reserved = reserved
        self.bandwidth = bandwidth
        self.remark = remark

        self.auto_quota = False

        # 使用自动计算容量(会占用全盘95%空间,不能占用100%否则程序会死掉.)
        if self.quota == 0:
            torrents = self.QBClient.torrents_info(status_filter='all', SIMPLE_RESPONSES=True)
            for torrent in torrents:
                self.quota = self.quota + torrent['completed']

            sync_maindata = self.QBClient.sync_maindata(SIMPLE_RESPONSES=True)
            server_state = sync_maindata['server_state']
            self.quota = (self.quota + server_state['free_space_on_disk']) * 0.95
            self.quota = round(self.quota / 1024 / 1024 / 1024, 2)
            self.auto_quota = True
            print('[' + self.remark + ']自动计算全盘空间:' + str(self.quota) + ' GB')

    def query(self):

        torrents = self.QBClient.torrents_info(status_filter='all', SIMPLE_RESPONSES=True)

        total_size = (self.quota) * 1024 * 1024 * 1024
        for torrent in torrents:
            total_size = total_size - torrent['size']

        self.free_space_on_task = round(total_size / 1024 / 1024 / 1024, 2)

        sync_maindata = self.QBClient.sync_maindata(SIMPLE_RESPONSES=True)
        server_state = sync_maindata['server_state']

        # 实际剩余空间
        self.free_space_on_disk = round(server_state['free_space_on_disk'] / 1024 / 1024 / 1024, 2)

        # 上传总量(GB)
        self.alltime_ul = round(server_state['alltime_ul'] / 1024 / 1024 / 1024, 2)

        # 下载总量(GB)
        self.alltime_dl = round(server_state['alltime_dl'] / 1024 / 1024 / 1024, 2)

        # 上传速度(MB/s)
        self.up_info_speed = round(server_state['up_info_speed'] / 1024 / 1024, 2)

        # 下载速度(MB/s)
        self.dl_info_speed = round(server_state['dl_info_speed'] / 1024 / 1024, 2)

        # 磁盘延迟(ms)
        self.disk_latency = server_state['average_time_queue']

        print('[%s]当前磁盘空间余量 %.2f GB[%.2f GB],上传总量 %.2f GB,下传总量 %.2f GB,上传速度 %.2f MB/s,下载速度 %.2f MB/s,磁盘延迟 %d ms.' % (
            self.remark, self.free_space_on_task, self.free_space_on_disk, self.alltime_ul, self.alltime_dl,
            self.up_info_speed, self.dl_info_speed, self.disk_latency))

        #如果出现严重的意外,比如磁盘突发为0B实际空间,强制执行清理以便纠正.(如果经常发生,则可能有其他BUG)
        if self.free_space_on_disk < 0.1:
            torrents = self.QBClient.torrents_info(status_filter='all', SIMPLE_RESPONSES=True)
            for t in torrents:
                self.QBClient.torrents_delete(hashes=t['hash'], deleteFiles=True)

    def add(self, torrent_name, torrent_size, urls, category):
        if int(torrent_size) < (self.free_space_on_task * 1024 * 1024 * 1024) and self.dl_info_speed < (
                self.bandwidth / 2):
            print('[' + self.remark + ']添加种子:' + torrent_name)
            self.QBClient.torrents_add(urls=urls, category=category, save_path='/downloads/')
            return True
        else:
            return False

    def purge(self,db):

        torrents = self.QBClient.torrents_info(status_filter='all', SIMPLE_RESPONSES=True)

        total_size = (self.quota) * 1024 * 1024 * 1024
        for t in torrents:
            total_size = total_size - t['size']

        self.free_space_on_task = round(total_size / 1024 / 1024 / 1024, 2)

        if self.free_space_on_task < self.reserved:
            error_rate = 0
            for t in torrents:
                status = self.QBClient.torrents_trackers(t['hash'], SIMPLE_RESPONSES=True)[3]['status']
                if status != 2 and status != 3:
                    self.QBClient.torrents_delete(hashes=t['hash'], deleteFiles=True)
                elif t['progress'] == 1 and t['dlspeed'] == 0 and t['upspeed'] == 0:
                    # 提取hash来查询文件,并把查询结果塞到seeder的队列里面.
                    cursor = db['agent'].find_one({"id": t['hash']})
                    if cursor is not None:
                        print('[' + self.remark + ']请求下载:' + cursor['title'])
                        try:
                            r = requests.get(cursor['links'][1]['href'])
                        except requests.exceptions.ConnectionError:
                            # 偶尔错误可以忽略
                            if error_rate == 0:
                                error_rate = error_rate + 1
                            else:
                                raise RuntimeError('数据源出错:' + cursor['links'][1]['href'] + ',若不及时处理,可能引发大规模故障.')
                        if r.status_code == 200:
                            with open('/tmp/temp.torrent', 'wb') as f:
                                f.write(r.content)

                            from lib import torrent
                            f = torrent.File('/tmp/temp.torrent')

                            print('[' + self.remark + ']添加种子:' + f.name)

                            record = db['seeder'].find_one({"file_hash": bson.Binary(pickle.dumps(f.file_hash))})
                            if record is None:
                                r = db['seeder'].insert_one({
                                    "name": f.name,
                                    "announce": f.announce,
                                    "file_hash": bson.Binary(pickle.dumps(f.file_hash)),
                                    "last_modified": datetime.datetime.now()
                                })
                            else:
                                r = db['seeder'].update_one({"file_hash": bson.Binary(pickle.dumps(f.file_hash))}, {"$set": {
                                    "name": f.name,
                                    "announce": f.announce,
                                    "last_modified": datetime.datetime.now()
                                }})

                    self.QBClient.torrents_delete(hashes=t['hash'], deleteFiles=True)
                elif (time.time() - t['added_on']) > 604800:
                    # 存活大于7天的种子(就算有人下载,也不会多到那里去.)
                    self.QBClient.torrents_delete(hashes=t['hash'], deleteFiles=True)
                else:
                    msg = self.QBClient.torrents_trackers(t['hash'], SIMPLE_RESPONSES=True)[3]['msg']
                    if 'torrent not registered' in msg:
                        self.QBClient.torrents_delete(hashes=t['hash'], deleteFiles=True)

        if self.auto_quota:
            torrents = self.QBClient.torrents_info(status_filter='all', SIMPLE_RESPONSES=True)
            for torrent in torrents:
                self.quota = self.quota + torrent['completed']

            sync_maindata = self.QBClient.sync_maindata(SIMPLE_RESPONSES=True)
            server_state = sync_maindata['server_state']
            self.quota = (self.quota + server_state['free_space_on_disk']) * 0.95
            self.quota = round(self.quota / 1024 / 1024 / 1024, 2)
            print('[' + self.remark + ']自动计算全盘空间:' + str(self.quota) + ' GB')

        print('[' + self.remark + ']自动清理完成')


class PTSource:
    def __init__(self, source, passkey, limit=1 ):
        self.source = source
        self.passkey = passkey
        self.limit = str(limit)

    def check(self):
        while True:
            try:
                torrents = feedparser.parse(
                    'https://' + self.source + '/torrentrss.php?rows=' + self.limit + '&linktype=dl&passkey=' + self.passkey)
                break
            except KeyboardInterrupt:
                exit(0)
            except :
                print('PT站数据源出现了临时错误,若此提示长时间不消失,则可能是PT站数据源配置问题.')
                time.sleep(1)
            
        return torrents['entries']

    def name(self):
        return self.source

@func_timeout.func_set_timeout(120)
def run(Agent,PT,db):
    print('==================================================')
    for a in Agent:
        a.query()
    print('==================================================')

    for p in PT:
        for torrent in p.check():
            # 如果出现RSS错误,则暂时忽略
            try:
                torrent_title = torrent['title']
                torrent_id = torrent['id']
                torrent_size = torrent['links'][1]['length']
            except:
                break

            cursor = db['agent'].find_one({'id': torrent_id})
            if cursor is None:
                db['agent'].insert_one(torrent)

                # 设置当种子大于某个大小,则自动忽略,这里定义为40GB.
                # 这一类种子通常占用大量的硬盘,而且没什么上传量,如果硬盘大,可以适当放宽.
                if int(torrent_size) > 40 * 1024 * 1024 * 1024:
                    break

                added = False
                for a in Agent:
                    if a.add(torrent_title, torrent_size, torrent['links'][1]['href'], p.name()):
                        added = True
                        break
                if added is False:
                    for a in Agent:
                        a.purge(db)
f = open('config.json')
config = f.read()
f.close()
config = json.loads(config)

honeybadger.honeybadger.configure(api_key=config['debug']['check'])

client = pymongo.MongoClient(
    config['dbserver'])
db = client.torrent

# 源站域名 source 默认值 无
# 密钥 passkey 默认值 无
PT = list()
for c in config['node']:
    PT.append(PTSource(source=c['source'], passkey=c['passkey']))

# 服务器地址 destination 默认值 '127.0.0.1'
# 端口 port 默认值 8080
# 用户名 username 默认值 'admin'
# 密码 password 默认值 'adminadmin'
# 容量 quota 默认值 0 <= 当为0则自动使用全盘刷PT,否则请设置合理阈值.单位GB.
# 低容量阈值 reserved 默认值 1.0 <= 当容量低于这个数值时候,会进行磁盘清理.
# 带宽容量 bandwidth 默认值 10 <= 假定跑满带宽为10MB/s,这个选项用于判断队列满的程度.
Agent = list()
for c in config['server']:
    try:
        if c['disable'] is False:
            a = QBAgent(remark=c['remark'],destination=c['destination'],port=c['port'],username=c['username'],password=c['password'],quota=c['quota'],reserved=c['reserved'],bandwidth=c['bandwidth'])
            Agent.append(a)
    except qbittorrentapi.exceptions.APIConnectionError:
        pass
while True:
    try:
        # 主程序
        run(Agent, PT, db)
        # 告知监控我还活着!
        try:
            requests.get(config['debug']['check_in'])
        except requests.exceptions.ConnectionError:
            # 临时的访问失败,不会造成什么严重后果.
            break
    except func_timeout.exceptions.FunctionTimedOut:
        pass
    except qbittorrentapi.exceptions.APIError:
        print('PT站数据出现问题!')
    except KeyboardInterrupt:
        exit(0)
