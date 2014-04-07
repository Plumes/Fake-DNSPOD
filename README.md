# Fake-DNSPOD
这是一个利用DNSPOD的api来完成基本操作的实验性网站
网站架构基于 Tornado
其中 `dnspod.py` 借鉴了 DNSPOD 官方 github 中的 [实现](https://github.com/DNSPod/dnspod-python/blob/master/dnspod/apicn.py)
用户输入的用户名和密码使用 `secure_cookie` 存储