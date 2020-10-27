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
    s = torrent.Seeder(f, config['faker']['port'], config['faker']['peer_id'], config['faker']['user_agent'])
    seeders.append(s)

p = multiprocessing.Pool(processes=16)
for seeder in seeders:
    p.apply_async(seeder.start)
p.close()
p.join()

# for seeder in seeders:
#     seeder.start()

while True:
    time.sleep(900)
    # 能适配大多数PT站的配置!
    p = multiprocessing.Pool(processes=16)
    for seeder in seeders:
        p.apply_async(seeder.heartbeat)
    p.close()
    p.join()

    # for seeder in seeders:
    #     seeder.heartbeat()
