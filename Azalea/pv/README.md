# 介绍

pv目录含义是persistent volume

保存持久化的数据，例如:

- db.sqlite3
- logs目录保存日志
- 用户上传的镜像等

docker run -d -p 9001:9001 -v <path>:/app/pv/  azalea
