# 项目进度与证据格式

文件放在当前客户项目，不放 skill 或采集/剪辑工具箱目录。建议结构：BRIEF.md、REFERENCE-SHOTS.md、SHOT-MAP.md、FIDELITY-REVIEW.md、references/、generated/、evidence/（含 `ledger.sqlite`）、handoff.json、edit/、delivery/、PROGRESS.md。使用已有合适结构即可，不为目录形式重做任务。台账只存账户代号、渠道代号、幂等键、请求哈希、金额和状态，不写密钥、Cookie 或登录态。

状态：NEEDS_CONFIG → REFERENCE_READY → PLAN_READY → GENERATING → MATERIAL_QA → EDITING（如需要）→ RENDERED_PENDING_REVIEW → DELIVERED。配置准备与本地分析可并行；任一阶段受阻记录 BLOCKED 及已完成工作，提交结果不明记 SUBMISSION_UNKNOWN。生成成功不能把状态直接标成 DELIVERED。

每次提交后记录渠道/账号、幂等键、任务 id、请求路径/哈希、任务/输出映射、费用承诺及获取路径。恢复先读 Brief/Progress 和台账，再检查文件哈希和已有远端任务，不从零重生，也不在 `submission_unknown` 时重投同一请求。已授权范围内的查询、下载、剪辑和验证直接继续。

## handoff.json

清单由实际计划及工具结果填写；以下是字段说明，不是可直接通过验收的假样本。

- `required_shots`: 计划中真实分镜 id 的非空数组，通常最多 6 个，由原片的结构、节奏和重点映射而来；不能为了绕过缺片删除 id，也不能为了“完整切点一一对应”扩到 20 个及以上。7–19 个时必须同时给出 `allow_more_than_usual_shots: true` 和书面 `allow_more_than_usual_shots_reason`。
- `assets`: 每个素材含 `id`, `path`, `sha256`, `build_id`, `output_name`, `receipt`（含 path/sha256）、`review`（含 path/sha256）。路径相对 handoff.json 或为绝对本地路径。
- `receipt`: 保存实际渠道查询/回执的脱敏 JSON 或文本，内容中可查到准确任务 id 和输出名；如果两者分散，在同一证据文件中原样汇集相应记录并注明命令。它不能只是手写“生成成功”。密钥只记长度或是否存在。
- `review` 文件为 JSON，含 `media_sha256`, `verdict: "pass"`, `observed_motion`（实际动作描述）, `method`（如连续播放或抽帧及覆盖方法）, `reviewed_at`（实际时间）。绑定具体源视频，不复制其他视频的审核。
- `shots`: 每个条目含 `id`, `asset_id`, `requested_duration`, `in`, `out`, `output_duration`（秒），以及该镜 `scene_reference`（`path`、`sha256`、`source` 为 `image2.5flare` 或同等构图的 `accepted_still`）。可选 `identity_references` 或顶层 `shared_identity_references` 记录全片共用的演员身份图和商品图，只用于锁身份，不能替代 `scene_reference`。若记录 `primary_reference`、`video_primary_reference` 或 `video_references`，主视觉/首帧必须是该镜场景图，不能是构图不符的人物主图或产品图。一条必需镜头对应一个合格连续区间；`output_duration` 必须为正且落在可用区间内。需要多个素材组合时，在计划中把动作拆成明确子镜头，但仍遵守通常最多 6 个真实分镜的上限。重复使用同一素材允许，但必须符合动作和时间线。
- 提交任一真实分镜的视频前，先运行 `scripts/check_handoff.py --ready-for-video <项目清单>`。该检查不提交付费生成；没有分镜场景图、或主参考仍是共用人物/产品图时会被拦住。`SHOT-MAP.md` 也要写下每镜场景参考图路径。
- `delivery`（成片交付时需要）：最终文件的 `path`、`sha256`、`duration`（成片时长）和 `acceptance`。acceptance.verdict 必须为 pass，并分别勾选切镜、穿帮、对应国家语言、视频包装（含需复刻的画面文字）、字幕和最终导出。生成成功不能当作验收通过。

脚本使用 Python 标准库和 ffmpeg 完整解码、计帧及读取解码时长。可用 `--ffmpeg` 指定实际安装路径；可选 `--ffprobe` 增加流元数据核验。缺少可用 ffmpeg 则停止技术放行，不通过手填 duration 绕过。检测成功仅代表结构和技术证据齐全，视觉真实性仍需实际人工/代理检查；生成成功不能算完成。

仅分析或提示词不需此素材清单。只生成素材也要验证对应动态镜头后交付。静态包装不作为必需动态镜头计数；切镜、穿帮、语言、包装文字、字幕和最终导出另由 delivery.acceptance 与 QA 报告负责。

## 可移植性

本机 installation.json 记录 `distribution_root`、`collection_root`、`editor_toolkit_root`、可选的 `hypit_path`、`ffmpeg_path`、`image_model`（固定为 image2.5flare）和 `video_channels`。迁移到另一台机器时重配路径和渠道名称，不复制账号、客户项目、密钥、Cookie 或浏览器状态。API 视频路线不再依赖 Hypit Runtime；如仍使用 Hypit，保留或重配其启动器路径，不要无故拆掉已有可用安装。采集模块与剪辑工具箱已随完整仓库提供，scripts/install.py 负责依赖安装与路径配置。用户已请求部署时自动完成普通安装，不反复询问；本人登录、密钥与官方许可点击单独处理。
