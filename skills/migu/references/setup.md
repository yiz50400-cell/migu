# 安装与环境检查

完整 Migu 仓库已附采集模块、剪辑工具箱、锁文件与统一安装入口。部署请求按仓库 docs/INSTALL.md 执行 scripts/install.py --apply，自动补齐本次路线依赖并填本机路径；不再要求用户另找两个项目。

installation.json 的 distribution_root 定位完整仓库；缺少时从当前工作目录或用户提供的仓库目录定位。已安装 skill 但仓库不在本机时，在当前用户授权的私有仓库访问范围下载 yiz50400-cell/migu，再运行安装入口。

配置字段：collection_root 为采集模块根目录；editor_toolkit_root 为剪辑工具箱；hypit_path 为实际 Hypit 启动器；ffmpeg_path 为实际可执行文件。路径使用绝对路径或 ~，未知留 null，不写密钥。已有自定义路径优先保留；新机器自动指向仓库 toolkits。

运行 scripts/preflight.py --route full 做只读检查；局部任务用 analyze/generate/discover/edit。脚本只检查文件与启动器存在，不提交生成，不读取认证内容。PASS_LOCAL_ONLY 不代表账号、服务或生成可用，需继续做安装指南中的服务连通检查。

安装报告在仓库 .runtime/install-report.json。遇到 errors/pending，代理继续安装和诊断；必须由本人完成的登录、密钥、系统权限或官方安装点击才需要用户接手，处理后继续原任务。不能把 ACTION_REQUIRED 报为完成。

Windows 中断在 DTK 初始化页，使用 distribution_root 中的 docs/WINDOWS-REPAIR.md 和 scripts/repair_evil.py，优先复用当前实例。

图片和视频接入分别按 hypit-execution.md 分别确认，安装不触发付费生成。官方软件从原发布源安装，不复制作者账号或 Runtime。客户只提供参考时不启动 Evil 搜索。
