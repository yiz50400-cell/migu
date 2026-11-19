# 安装与环境检查

Migu 是给代理执行的工作流 skill，不是自带视频模型、下载服务器和剪辑器的一键应用。先按当前任务路由检查需要的依赖，不能因为可选组件缺失就阻止其他路线。

## 本机路径

将 skill 内 installation.example.json 复制为 installation.json，仅填写当前机器上已经安装的目录：
- collection_root：采集项目根目录，需含 workflow/unattended/evil_discovery.py 和 workflow/collection/collector.py。仅“代找爆款”路线需要该适配器；缺失时说明并按用户选择配置项目或使用已授权替代方式。
- editor_toolkit_root：剪辑工具箱根目录，需含 scripts/package_remotion.py、scripts/deliver_video.py、remotion/ 及配套 docs。只在需要剪辑时检查。
- ffmpeg_path：可选的 ffmpeg 可执行文件路径；留空则查 PATH。检查脚本可通过 --ffmpeg 使用该实际路径。

以上值使用绝对路径或 ~ 开头路径；未知时用 null，不写虚假路径。不放 API key、Cookie、Runtime 认证内容。编辑器 skill 自己的 installation.json 可写 toolkit_root；由 Migu 调用时优先使用本次交接中明确的 editor_toolkit_root，冲突需先核对实际工具箱。

## 只读检查

在 skill 目录运行 `python3 scripts/preflight.py --route generate`；Windows 可用已安装的 Python 命令替换 python3。路由可选 analyze、generate、discover、edit、full；full 表示同时需要代找、生成和剪辑。可用 --config 指定本机路径配置、--skills-dir 指定包含 hypit 与编辑器 skill 的目录。

脚本只检查可执行文件、skill 文件与配置指向的文件是否存在，不联网、不安装、不读取认证内容、不提交生成任务。PASS_LOCAL_ONLY 不是账号可用、Evil 服务健康、ChatCut 已连接或生成成功的证明；这些由执行任务时按对应 skill 验证。缺依赖时返回非零退出码并列出缺项，不把不存在的目录当成成功安装。

Hypit 图片和视频配置仍须分别按 hypit-execution.md 确认。预检不能代替配置选择或费用授权。
