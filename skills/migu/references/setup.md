# 安装与环境检查

完整 Migu 仓库已附采集模块、剪辑工具箱、锁文件与统一安装入口。部署请求按仓库 docs/INSTALL.md 执行 scripts/install.py --apply，自动补齐本次路线依赖并填本机路径；不再要求用户另找两个项目。

installation.json 的 distribution_root 定位完整仓库；缺少时从当前工作目录或用户提供的仓库目录定位。已安装 skill 但仓库不在本机时，在当前用户授权的私有仓库访问范围下载 yiz50400-cell/migu，再运行安装入口。

配置字段：collection_root 为采集模块根目录；editor_toolkit_root 为剪辑工具箱；hypit_path 为实际 Hypit 启动器（仍使用 Hypit 时填写，API 视频路线不再依赖它）；ffmpeg_path 为实际可执行文件；image_model 固定为 image2.5flare；video_channels 为可选的视频渠道列表（id、kind、端点或启动器名称、账号代号、是否启用，可注明凭据是否存在或长度）。路径使用绝对路径或 ~，未知留 null，不写密钥、Cookie 或登录态。已有自定义路径和客户已有的 DTK/管理员配置优先保留；新机器自动指向仓库 toolkits。不要无故拆掉已经可用的 Hypit 安装路径。

运行 scripts/preflight.py --route full 做只读检查；局部任务用 analyze/generate/discover/edit。已配置可用的 API 视频渠道时，generate/full 不再把缺少 Hypit CLI/skill 列为缺失项；未配置视频渠道的旧环境仍要求 Hypit。脚本只检查文件、启动器与渠道声明，不提交生成，不读取认证内容。PASS_LOCAL_ONLY 不代表账号、服务或生成可用，需继续做安装指南中的服务连通检查。

安装报告在仓库 .runtime/install-report.json。遇到 errors/pending，代理继续安装和诊断；必须由本人完成的登录、密钥、系统权限或官方安装点击才需要用户接手，处理后继续原任务。不能把 ACTION_REQUIRED 报为完成。

Windows 中断在 DTK 初始化页，使用 distribution_root 中的 docs/WINDOWS-REPAIR.md 和 scripts/repair_evil.py，优先复用当前实例。不要改客户已有的 DTK/管理员配置。

图片和视频接入分别按 video-channels.md 与 hypit-execution.md 确认，安装不触发付费生成。官方软件从原发布源安装，不复制作者账号或密钥。客户只提供参考时不启动 Evil 搜索。

## 采集登录条件

部署依据运行中 DTK 的接口策略检查 TikTok 搜索登录要求；不能把健康服务、可用游客或管理员登录成功报为搜索可用。运行仓库 `scripts/repair_evil.py --verify-search coffee` 后，按 `docs/WINDOWS-REPAIR.md` 接续；再下载并解码一条视频才完成采集链验收。已有 Chrome 登录不会自动导入 DTK。客户授权范围内复用其本机登录导入，浏览器内部页面的必要人工操作一次交代清楚，不绕过工具明确拒绝的页面权限。公开下载使用 HTTPS，无需申请 SSH 部署公钥。login required 保持 required。
