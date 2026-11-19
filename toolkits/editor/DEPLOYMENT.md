# 部署

统一入口是 Migu 仓库 scripts/install.py，安装指南见 ../../docs/INSTALL.md。

Python 3.12 和 uv.lock、Node.js 22.15+ 与 remotion/package-lock.json 分别管理依赖；不要复制别人的 .venv、node_modules 或账号。安装脚本会优先保留已配置工具箱路径；新机器默认使用本目录。

ChatCut 登录与官方安装所需点击由当前用户完成；其余已授权的依赖安装、路径配置和只读连接检查由代理继续执行。通过 list_projects 后仍要验证真实编辑/导出，不能把安装完成写成成片验收。
