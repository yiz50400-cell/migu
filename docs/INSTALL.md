# 一次部署与失败续装

在 Codex 中打开整个仓库，说“部署 migu”即可。根目录 AGENTS.md 要求代理自行运行下面流程，继续处理失败项，不再等待用户提醒安装采集或剪辑项目。

## 统一入口

```sh
python3 scripts/install.py --apply
```

Windows 可用 `py -3 scripts/install.py --apply`。不带 --apply 只显示计划；--route 可选 analyze、generate、discover、edit、full，默认 full。部署包含所有组件；日常只用给定参考时不启动搜索。登录和模型花费不属于安装授权。

脚本会备份被更新的 skill，保留本地配置；已有 collection_root/editor_toolkit_root 优先复用，新机器指向本仓库 toolkits/。安装报告在 .runtime/install-report.json；重跑从已安装环境恢复，锁定依赖由包管理器复用。

## 已随仓库提供

- migu 与配套剪辑 skill。
- 原采集项目的发现/下载模块、yt-dlp 依赖文件。
- 剪辑工具箱 Python 源码、配置示例、文档、Remotion 工程、锁文件及模板预览。
- 安装脚本、版本清单、预检、回归测试。

## 脚本自动准备的部分

- 优先复用 uv；缺少时通过当前 Python 的 pip 安装到仓库 .runtime/bootstrap。uv 管理 Python 3.12。
- Node/npm 缺少或太旧时，使用已有 Homebrew/winget 安装兼容版本。
- FFmpeg/FFprobe 缺少时使用已有 Homebrew/winget 安装。
- 若将使用 Hypit，或尚未配置 API 视频渠道：Hypit CLI 缺少时把官方 @hypit/hypit 固定版本安装到 .runtime/hypit；缺官方 skill 时从官方仓库固定提交获取。保留现有可用安装，不要无故拆掉。路径写入 hypit_path，执行时使用该路径。已配置 API 视频渠道时，不再把缺少 Hypit Runtime 当作安装失败。
- 采集独立虚拟环境、yt-dlp/curl_cffi/imageio-ffmpeg。
- 剪辑工具箱 uv sync --frozen 和 Remotion npm ci。
- 发现路线准备 Evil：复用现有可达服务；否则通过已有包管理器安装 Docker、从官方固定提交取得 Evil，生成本机随机服务密钥并启动 browser profile。Docker 首次系统许可由本人处理。采集服务启动后自动运行本机修复入口，验证或初始化内部凭据。

所有运行环境、上游下载、服务数据、密钥只留 .runtime/ 或工具箱本机环境目录，不提交 Git。Hypit 二进制和源码不打包转售；在客户机器从官方源安装并保留上游条款。Evil 和 Remotion 保留各自许可，内置 third-party 目录保留原许可证。

## 没有包管理器时，代理继续准备

不把“缺依赖”当最终答复。代理先检查当前平台和官方安装说明，再在已授权范围安装缺失工具：

- Python 启动器完全缺失：Windows 用已有 winget 安装 Python.Python.3.12；macOS 使用已安装 Python，或官方 Python 安装器。不要为本任务升级系统 Python。
- Node：从 nodejs.org 获取与平台/架构匹配的版本（dependencies.json 给出基准），校验该版本 SHASUMS256.txt 后安装到当前用户目录，再加入本次进程 PATH。
- FFmpeg/FFprobe：按 ffmpeg.org 的平台下载入口获取配对二进制，核对分发校验信息，安装到当前用户工具目录。已有包管理器优先；不要把 Windows exe 放到 macOS。自动安装失败时保留具体错误，不关闭 TLS 校验。
- Docker：根据实际操作系统使用 Docker 官方安装步骤；系统虚拟化、管理员弹窗或重启要求由本人完成。不能把未运行引擎误报成已可采集。

这是代理执行的续装步骤，不是要求客户自行找软件。只有出现实际系统权限、登录或缺少网络访问等阻塞才停在对应动作，完成后继续原部署任务。

## ChatCut：连接与真实安装点击

先调用宿主已有的 list_projects。能响应就复用，不重新安装。如果缺连接，读取可用的 chatcut-product-help skill，并按当前官方 CLI 帮助核实：

```sh
npx --yes --prefer-online @chatcut/cli@latest connect --no-install --json
```

实际 Desktop 缺失时，官方流程要求真实宿主许可点击，具体命令为：

```sh
npx --yes --prefer-online @chatcut/cli@latest connect --allow-install --json
```

该命令可能下载、安装并打开签名 Desktop，必须通过宿主支持的许可界面提交；不能把 --apply、自动批准或 --allow-install 标志本身当作已点击。宿主不支持该许可界面时让用户从官方 ChatCut Desktop 页面安装，或本人运行官方命令。尊重拒绝，不换安装器绕过。

用户用自己的 ChatCut 登录。核实 CLI 连接和当前宿主 MCP 是两项检查；以 list_projects 真实响应为准。配置片段只合并必要项，不覆盖用户全局配置或账号。

## 配置与完成条件

安装写入 installation.json：distribution_root、collection_root、editor_toolkit_root、hypit_path、ffmpeg_path（存在时）。这些都是本机路径。旧路径仍可用就保留；失效时先定位现有环境再改，不删除原项目。

客户截图若停在 DTK 创建管理员页面，按 [Windows 原地修复](WINDOWS-REPAIR.md) 继续。脚本优先验证已有采集凭据，仅在空实例上创建本机管理账号和单独的 tiktok:read 采集凭据。图片和视频分别复用客户已选接入；图片沿用其已配置的 Key、URL，模型固定为 image2.5flare。视频可填写多个渠道或多个账号。不要改客户已有的 DTK/管理员配置。

完成安装后执行 preflight.py。已配置 API 视频渠道时，不把缺少 Hypit 列为缺失项，但仍可核实已有 Hypit 安装；未配置视频渠道的旧环境仍核实 Hypit version/配置状态。同时核实采集模块可导入、Evil readyz+browser-rpc+凭据、ChatCut list_projects、Remotion 模板加载。尚未填账号或缺点击就标记 ACTION_REQUIRED，不能宣称完整生产可用。真实生成/成片验收按用户任务和费用范围另行执行，安装与预检不得提交付费生成。

## 搜索登录条件与验收

安装器依据运行中 DTK 的接口策略检查 TikTok 登录候选，并用 `coffee` 运行一次真实搜索。服务健康但缺少所需登录身份时仍是 ACTION_REQUIRED；不会反复创建游客来替代登录。客户既有 Chrome 登录不会自动成为 DTK 身份。按 [原地修复](WINDOWS-REPAIR.md) 处理唯一阻塞，随后验证视频下载/解码。该规则适用于所有系统，不以发布者的旧实例代替新客户验收。
