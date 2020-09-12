import requests
import urllib.parse

# 提取XPATH方法:/html/body/table[2]/tbody/tr[2]/td/table[2]/tbody/tr/td/table/tbody/tr[18]/td[2]/div/table/tbody/tr/td[2]/a/@href

DOMAIN = 'hdatmos.club'
PASSKEY = 'bb5633303a9aeb2a44ecd338275683c4'

def get_id(id):
  r = requests.get('https://' + DOMAIN + '/download.php?id='+ str(id) +'&passkey=' + PASSKEY)
  if 'Content-Disposition' in r.headers and r.headers['Content-Disposition']:
      disposition = r.headers['Content-Disposition'].split(';')
      if len(disposition) > 1:
          if disposition[1].strip().lower().startswith('filename='):
              fn = urllib.parse.unquote(disposition[1].split('=')[1])

  print(fn)
  with open('./torrents/' + fn,'wb') as f:
    f.write(r.content)

torrents=[]
with open('torrents_list.txt','r') as f:
	for line in f:
		torrents.append(list(line.strip('\n').split(',')))

for torrent in torrents:
  get_id(torrent[0].replace('details.php?id=','').replace('&hit=1',''))