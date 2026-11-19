# 完整部署升级验证

日期：2026-11-19。此记录对应新增统一安装入口和内置工具箱的版本；旧 VALIDATION.md 是上一版纯 skill 发布的历史检查。

## 实际执行

- 37 项本地回归测试通过，包含原媒体/交接检查、独立安装目录、重复安装、旧 skill 备份、本机配置保留、非法配置不覆盖、失败/pending 状态和本机 Hypit 启动器路径。
- macOS arm64 新建工具箱虚拟环境，执行 uv sync --frozen，46 个剪辑 Python 依赖安装成功。
- 内置 Remotion 工程执行 npm ci，336 个包安装成功；npm run lint（ESLint + TypeScript）通过。
- 新建采集虚拟环境，安装 yt-dlp/curl_cffi/imageio-ffmpeg 等依赖，collector、evil_discovery、yt_dlp 实际导入成功。
- package_remotion.py templates 成功加载六套模板。
- 复用本机 Hypit 0.3.2 并执行 version；从官方仓库固定提交取得官方 skill，安装到独立测试 skills 目录成功，保留上游 LICENSE。
- 全局 migu 和配套剪辑 skill 已更新，原本机采集/剪辑路径保留，补入 distribution_root。
- skill 格式、Python 语法、JSON、本地文档链接、源码敏感模式检查与发布清单检查。

所有安装测试都在本仓库隔离环境中进行；没有把原工具箱的 .venv/node_modules 拷入发行版，没有提交付费图像/视频生成。

## 尚未实测

- 本机已有 uv/Node/Hypit，因此“全新机器从零安装 uv、Node、Hypit CLI”的所有分支尚未实际走完。安装失败会记录并交给代理按 INSTALL.md 接续，不宣称一键必成功。
- 没有为测试重新安装或重启 Docker/Evil、ChatCut Desktop，也没有改变现有活跃制作任务。Docker 自动安装、Evil 初始化和 Windows/macOS 首次系统弹窗需要目标环境验收。
- ChatCut 官方安装需要实际宿主许可点击与本人登录；脚本不会绕过这一步，也不能自动提供客户账号密钥。
- Windows/Linux 未做真机完整部署测试。缺 Homebrew/winget 的系统由代理执行文档中的官方安装续装步骤；未将系统权限和网络阻塞隐藏为成功。
- 真实 Hypit 图片/视频生成、Evil 搜索质量、ChatCut 剪辑导出与最终成片验收，仍按实际生产任务验证。

## 范围变化

采集和剪辑项目的生产源码现在已随仓库提供，不再让客户另找这两个项目。第三方程序和依赖由安装入口从原发布源获取，保留各自许可。安装报告退出 1 表示失败，2 表示还需处理账号/连接/系统动作；两者都不能报成完整环境可用。
