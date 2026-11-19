# Migu 内置剪辑工具箱

这是现有商品剪辑项目的生产源码快照，包含 Python 工具、工作流、Remotion 工程及模板预览。来源及文件哈希见 ../SOURCES.json。没有复制虚拟环境、客户素材或运行数据库。

从 Migu 仓库根目录执行 `python3 scripts/install.py --apply --route edit`，自动安装本工具箱依赖并填写 skill 路径。首次安装与恢复说明见 ../../docs/INSTALL.md。

使用本工具箱时读取 docs/local-editing-workflow.md、docs/chatcut-remotion-workflow.md 和 docs/template-guided-editing.md；当它们的通用模板示例与本次 Migu 复刻要求冲突时，以当前用户要求和 Migu 镜头映射为准。静音片不需要口播字幕；缺素材返回上游 Hypit。不要把模板中的 CTA 强加到参考复刻。

运行 `uv sync --frozen`、`npm --prefix remotion ci` 可分别恢复 Python 和 Node 依赖。兼容调试脚本不是 ChatCut 原生编辑器。
