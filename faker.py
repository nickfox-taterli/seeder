import time
import json
import pickle
import pymongo
import honeybadger
import multiprocessing
from lib import torrent

f = open('config.json')
config = f.read()
f.close()
config = json.loads(config)

honeybadger.honeybadger.configure(api_key=config['debug']['check'])

client = pymongo.MongoClient(
    config['dbserver'])
db = client.torrent
collection = db['seeder']

seeders = list()
cursor = collection.find({})
for document in cursor:
    f = torrent.FileCache(document['announce'], pickle.loads(document["file_hash"]))
    s = torrent.Seeder(f, 49152, 'qB4250', 'qBittorrent/4.2.5')
    seeders.append(s)

p = multiprocessing.Pool(processes=10)
for seeder in seeders:
    p.apply_async(seeder.start)
p.close()
p.join()

while True:
    time.sleep(900)
    # 根据种子总数,决定每个种子的延迟数量.
    p = multiprocessing.Pool(processes=10)
    for seeder in seeders:
        p.apply_async(seeder.heartbeat)
    p.close()
    p.join()

