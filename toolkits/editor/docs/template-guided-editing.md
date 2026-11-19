# 先选模板，再按文案剪镜头

`tiktok-product-video-editor` 是本项目的 Codex 剪辑入口，`TikTok-Product-Video` 是包含它的仓库。现在这一个入口同时使用 ChatCut 剪镜头、Remotion 做包装。

## 已吸收的方法

先看目标画面 → 准备真实商品文案与校正 SRT → 为每句话找有依据的镜头 → 将动画做成可复用参数 → 渲染后逐条复核。对应表把镜头、字幕和卖点时间绑在一起，减少后期反复拼凑。

新增 `kinetic-product` 适配 MotionGit 385712 的 B2 编号玻璃卡、B4 渐变强调线，保留 MIT 许可和原始源码摘要。原版是横屏 DOM 动画，本项目移植为竖屏 React/Remotion；没有安装完整上游引擎，也不是任意 `.motion` 包导入器。没有引入上游演示人物、配乐、音效或字体。

## 选择模板

| 模板 ID | 名称 | 适合内容 | 预览 |
|---|---|---|---|
| `classic` | 简洁商品 | 实拍与直接卖点，延续原包装 | [简洁预览](../remotion/previews/classic.png) |
| `kinetic-product` | 科技卖点 | 数码、工具、家居；逐项说明细节 | [科技预览](../remotion/previews/kinetic-product.png) |
| `comparison-review` | 对比测评 | 顺序 A/B 演示；当前侧高亮 | [对比预览](../remotion/previews/comparison-review.png) |
| `step-guide` | 步骤演示 | 安装、教程、操作；编号与分段进度 | [步骤预览](../remotion/previews/step-guide.png) |
| `unboxing-reveal` | 开箱展示 | 真实拆封与细节；展开边角和吊牌卡 | [开箱预览](../remotion/previews/unboxing-reveal.png) |
| `minimal-luxe` | 极简高级感 | 美妆、香氛、设计家居；浅色留白与细线 | [极简预览](../remotion/previews/minimal-luxe.png) |

新增四款为本项目原创，未宣称下载或导入完整上游模板包。[查看六款总览](../remotion/previews/comparison.jpg)。

对比款用第 1、3、5…张卡表示 A，第 2、4、6…张卡表示 B。两侧只高亮当前卡，不延长前一条卖点的显示时间，不凭空生成对比数据；同时并排的 A/B 视频需要先在 ChatCut 合成。步骤款一张卡对应一个真实步骤，间隔期间进度停留在已完成位置。开箱款边角仅作装饰，动作必须来自原素材。极简款上下浅色留白较多，先检查商品主体是否在中央可见区。

所有模板都可省略标题/卖点卡/CTA；内容为空时不补造事实。建议对比卡成对、步骤卡按实际操作顺序填写。字幕继续由同一组件和 SRT 驱动。

预览是同一个生产组件实际渲染的合成演示，不是客户商品。查看完整目录：

```sh
uv run python scripts/package_remotion.py templates
```

在 Codex 里直接说：

> 用科技卖点模板，剪我提供的本地素材，做一条墨西哥西语视频。先按真实卖点安排镜头和字幕，无 BGM，成片逐条复核。

Codex 按现有授权制作；无需客户自己写 JSON。以下命令用于维护和排查。

## 生成镜头对应表

先创建任务并导入真实本地素材，获得 job_id、asset_id 和 SHA256。复制 [对应表请求示例](../config/packaging-storyboard.example.json)，填入实际素材观察、原片时间、成片时间、文案和可选卖点卡。SRT 使用最终成片时间轴。

```sh
uv run python scripts/package_remotion.py plan --request /absolute/job/storyboard-request.json --output /absolute/job/plan-v1
```

输出三份文件：

- `storyboard.md`：成片时间、素材源时间、画面观察、文案、字幕 cue、动画对应表。
- `storyboard.json`：模板版本、素材/SRT 哈希、时长、对应内容与指纹。
- `package-request.draft.json`：包装草稿，故意没有底片路径和 ChatCut 项目 ID，尚不可渲染。

第一版支持等速、顺序、连续镜头；不支持重叠转场、变速或冻结补时。源时间不能超出真实原片，时间轴从 0 开始且连续，最长 180 秒，最多 100 镜头/20 张卖点卡。`sources` 只列实际选用素材，列出的素材必须全部用到。跨镜头的字幕 cue 会出现在每个有重叠的镜头行中，仍保留原 cue 时间，不拆改口播。

画面观察与商品事实由执行者核实。程序验证归属、哈希、时间和文本一致性，不能证明商品功效，也不能单凭底片时长证明 ChatCut 使用了正确镜头。

## ChatCut 实际制作和绑定

按对应表用 ChatCut MCP 剪辑，保留真实项目 ID。原素材音轨静音；需要口播时只保留口播。导出无烧字幕底片。

将草稿复制为新的 `package-request.json`，补入真实 `chatcut_project_id`、`video_path`，保留 `storyboard_path`。然后运行：

```sh
uv run python scripts/package_remotion.py prepare --request /absolute/job/package-request.json --output /absolute/job/remotion-v1
uv run python scripts/package_remotion.py render --output /absolute/job/remotion-v1
```

prepare 拒绝与对应表不一致的任务、素材、模板、音频模式、标题、CTA、卖点时间、SRT 或底片时长。复制对应表到包装目录并记哈希；渲染记录关联模板、对应表、底片和 ChatCut 项目。修改方案应从新 plan 目录生成，再用新包装目录，旧目录不可覆盖。不要直接在草稿中改文案后继续使用旧表。

已有请求不填 `template_id` 仍使用 `classic`；不带 `storyboard_path` 的旧请求继续可用。模板目录与渲染源码改变后，已有渲染不能冒充新版本结果复用。

## 复核和复用

结果始终先是 `RENDERED_PENDING_REVIEW`。完整观看商品动作、卖点证据、卡片遮挡、字幕和开头/片尾；口播版必须试听。按 [协同指南](chatcut-remotion-workflow.md) 填真实复核并执行 `deliver_video.py` 才登记交付。

第一条实际通过后，可沿用模板 ID、配色和布局，为新素材重新建立对应表。不会复制旧客户的素材、项目 ID 或复核证据。模板布局可调整，镜头问题回 ChatCut；合成 MP4 不会自动还原为多轨工程。

维护者重新生成静帧：`node remotion/preview.mjs /absolute/new-preview-directory`；增加 `--videos` 可生成每款 5 秒静音合成动画演示。视频要求新目录，不覆盖已有视频。默认输出仓库 `remotion/previews`，会更新预览图；已有文件应先备份。预览开关只在预览脚本使用，正式 render 拒绝该开关。
