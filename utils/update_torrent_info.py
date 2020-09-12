import os
import bson
import pickle
import pymongo
import datetime
from lib import torrent

client = pymongo.MongoClient(
    "mongodb+srv://bentley:rMTSq7yGEKEBf72d@cluster0.pju4n.mongodb.net/default?retryWrites=true&w=majority")
db = client.torrent
collection = db['seeder']

# 枚举文件,并将其列入数据库.
f_list = os.listdir("./torrents")
seeder_list = list()
for i in f_list:
    if os.path.splitext(i)[1] == '.torrent':
      f = torrent.File("./torrents/" + i)
      # 文件的几项信息
      print(f.name)
      print(f.announce)
      print(f.file_hash)

      # 判断是否在数据库中,如果在,则更新信息(比如可能announce更新!),否则插入信息.
      record = collection.find_one({"file_hash": bson.Binary(pickle.dumps(f.file_hash))})
      if record is None:
          collection.insert_one({
              "name": f.name,
              "announce": f.announce,
              "file_hash": bson.Binary(pickle.dumps(f.file_hash)),
              "last_modified": datetime.datetime.now()
          })
      else:
          collection.update_one({"file_hash": bson.Binary(pickle.dumps(f.file_hash))}, {"$set":{
              "name": f.name,
              "announce": f.announce,
              "last_modified": datetime.datetime.now()
          }})