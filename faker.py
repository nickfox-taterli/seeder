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
collection = db['agent']

seeders = list()
cursor = collection.find({"finished": True})

for document in cursor:
    try:
        f = torrent.FileCache(document['torrent_announce'],bytes.fromhex(document['torrent_hash']))
        s = torrent.Seeder(f, config['faker']['port'], config['faker']['peer_id'], config['faker']['user_agent'])
        seeders.append(s)
    except:
        pass

p = multiprocessing.Pool(processes=16)
for seeder in seeders:
    p.apply_async(seeder.start)
p.close()
p.join()
 
# for seeder in seeders:
#     seeder.start()
try:
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
except KeyboardInterrupt:
    exit(0)