# PT练级神器

------

设计的初衷：

手里有几个PT站,也有几个VPS,盘都不大,但是流量又很足,于是打算利用起来.一个月也能贡献个七八TB吧,另外PT不属于公开P2P网路,在很多VPS上并不限制,但是BT就不行了.

记住,多机,小盘,多站,如果你是大盘用户,请绕路,这个工具效率对大盘不友好.

会真实下载,上传,当然会挑能下的种,总不能你的VPS最大的盘才10G我就允许你下载20G的资料,不现实.会自动轮询哪个机器适合下载.可以通过disable字段临时屏蔽某个VPS(比如VPS超流量暂停之后).

### 功能设计

- [x] 独立配置文件.
- [x] 自动种子添加,删除.
- [x] 自动管理多个PT站,多台服务器.(流量用完会出现API连接错误,待解决.)
- [x] (作弊)虚假做种,换取魔力,容易封号.
- [x] (工具)NexusPHP种子批量获取脚本,需要修改后使用.

### 环境需求

> * Python版本>=3.6.2 且 安装相关的Python库
> * 注册Mongodb Altas (免费数据库,当然你选择付费我也管不着对吧.)
> * 注册HoneyBadger (免费查错监控,请务必设置提醒,否则你不知道你的程序什么时候就挂了.)
> * 部署linuxserver/qbittorrent的容器 (QB软件,非容器需保证QB版本大于4.1.5.)
> * 拥有一个或多个PT网站 (数据源)
> * 拥有一台或多台VPS (服务器,不需要大盘机,我自己就在一个3.5G硬盘的机上一样挂.)

### 部署过程

**由于我懒得写文档,所以,如果有不理解不明白的也不会解释.**

**编辑config.json文件可完成配置,docker不推荐使用6881端口,Mongodb Altas和HoneyBadger请自行注册,check_in为HoneyBadger的在线检查链接,其他懒得解释了.**

### 运行方法

会自动重启的运行方法(如果发生不可修复错误,将会一直处于错误中无法解决,用户可能也无法知道已经出错):
```shell
while true;do python3 auto_seeder.py;done
```

单次执行(若用户配置了honeybadger的提醒,则出现程序死掉时候可以上来看看,可能的故障比如VPS超流量了,PT站临时维护等等.):
```shell
python3 auto_seeder.py
```

执行作弊脚本(需要先运行一段时间auto_seeder.py生成部分有效数据,作弊很容易被抓住,谨慎而为.):
```shell
python3 faker.py
```

- P.S.
### 注册Mongodb Altas 和 HoneyBadger 获得API_KEY笔记
![](https://raw.githubusercontent.com/hongwenjun/seeder/master/img/mongodb_honey.png)

### Python 3.7 运行环境
```
#  安装pip3 和更新 pip3 工具
apt install python3-pip
pip3 install --upgrade pip

#  安装所需的 py库
pip3 install dnspython bson feedparser qbittorrent-api pymongo \
     requests func_timeout honeybadger
```
