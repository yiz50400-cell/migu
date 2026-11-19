# Migu 内置采集模块

从现有采集项目提取 workflow/collection/collector.py 和 workflow/unattended/evil_discovery.py，保留原下载、发现入口及 requirements-collect.txt。来源文件哈希见 ../SOURCES.json。

只负责按需发现 TikTok 参考链接、元数据解析与下载；不带无人值守发布或旧成片生产链。安装入口为 Migu scripts/install.py --apply --route discover。

使用本模块的 .venv Python。默认发现先探测当前 Evil；给定参考只下载该条，不启动额外搜索。Evil 服务由安装入口按需准备，客户自设账号密钥。不能从播放量推断销量，也不能把参考素材登记为本产品实拍。
