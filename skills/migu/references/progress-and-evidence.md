# 项目进度与证据格式

文件放在当前客户项目，不放 skill 或采集/剪辑工具箱目录。建议结构：BRIEF.md、REFERENCE-SHOTS.md、SHOT-MAP.md、FIDELITY-REVIEW.md、references/、generated/、evidence/、handoff.json、edit/、delivery/、PROGRESS.md。使用已有合适结构即可，不为目录形式重做任务。

状态：NEEDS_CONFIG → REFERENCE_READY → PLAN_READY → GENERATING → MATERIAL_QA → EDITING（如需要）→ RENDERED_PENDING_REVIEW → DELIVERED。配置准备与本地分析可并行；任一阶段受阻记录 BLOCKED 及已完成工作，提交结果不明记 SUBMISSION_UNKNOWN。

每次提交后记录 Build id、Run 路径/哈希、任务/输出映射、费用承诺及获取路径。恢复先读 Brief/Progress，再检查文件哈希和已有远端任务，不从零重生。已授权范围内的查询、下载、剪辑和验证直接继续。

## handoff.json

清单由实际计划及工具结果填写；以下是字段说明，不是可直接通过验收的假样本。

- `required_shots`: 所有必需动态镜头 id 的非空数组，来自独立 REFERENCE-SHOTS 到 SHOT-MAP 的完整映射；不能为了绕过缺片删除 id。原片中非动态的镜头也保留在完整时间线对照中，另行验收。
- `assets`: 每个素材含 `id`, `path`, `sha256`, `build_id`, `output_name`, `receipt`（含 path/sha256）、`review`（含 path/sha256）。路径相对 handoff.json 或为绝对本地路径。
- `receipt`: 保存实际 Hypit inspect/status 输出的脱敏 JSON 或文本，内容中可查到准确 Build id 和输出名；如果两者分散，在同一证据文件中原样汇集相应记录并注明命令。它不能只是手写“生成成功”。
- `review` 文件为 JSON，含 `media_sha256`, `verdict: "pass"`, `observed_motion`（实际动作描述）, `method`（如连续播放或抽帧及覆盖方法）, `reviewed_at`（实际时间）。绑定具体源视频，不复制其他视频的审核。
- `shots`: 每个条目含 `id`, `asset_id`, `in`, `out`（秒），一条必需镜头对应一个合格连续区间；需要多个素材组合时，在计划中把动作拆成明确子镜头并完整覆盖。重复使用同一素材允许，但必须符合动作和时间线。

脚本使用 Python 标准库和 ffmpeg 完整解码、计帧及读取解码时长。可用 `--ffmpeg` 指定实际安装路径；可选 `--ffprobe` 增加流元数据核验。缺少可用 ffmpeg 则停止技术放行，不通过手填 duration 绕过。检测成功仅代表结构和技术证据齐全，视觉真实性仍需实际人工/代理检查。

仅分析或提示词不需此素材清单。只生成素材也要验证对应动态镜头后交付。静态包装不作为必需动态镜头计数；完整时间线、声音和最终排版验收另由 QA 报告负责。

## 可移植性

本机 installation.json 只记录 `collection_root`、`editor_toolkit_root` 及可选的 `ffmpeg_path`。迁移到另一台机器时重配路径，不复制账号、客户项目、Runtime 密钥或浏览器状态。需要安装的依赖包括 Hypit CLI 与 skill、采集项目（仅发现路线）、yt-dlp（远程视频下载）、现有剪辑 skill/工具箱、ChatCut MCP 与 Remotion（需剪辑时）。这不是一次隐式环境安装授权。
