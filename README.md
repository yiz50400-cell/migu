# migu

面向各种商品的 TikTok AI 视频复刻工作流 skill。统一协调按需采集参考、Hypit 图片与视频生成、素材检查，以及 ChatCut / Remotion 剪辑。

**这是流程 skill 和检查脚本，不是包含模型、账号、采集服务器及剪辑运行环境的一键应用。** 发布目录不含 API key、Cookie、客户素材、历史任务或本机配置。

## 工作方式

1. 分别检查图片与视频模型，确认是否沿用现有配置；同一任务已确定的不重复询问。
2. 客户给参考视频或具体链接，直接使用，不另找替代；只有要求“找爆款”时才采集，默认优先 15–25 秒。
3. 拆解完整参考，保留镜头职责、动作过程、顺序和节奏。换人物、换产品，操作按新产品真实结构调整；正常适配直接执行。
4. 通过 Hypit 实际生成所需动态镜头，记录任务和输出，按动作与模型能力分段。
5. 检查产品、人物、动作、画面和可用区间。不能用图文幻灯片替代 AI 视频，也不能把缺镜头当成正常改编。
6. 需要成片时接入配套编辑器 skill，检查成片后交付。只要分析、提示词或素材时，不擅自扩大范围。

完整结构复刻不承诺逐帧/逐像素一致。模型生成失败、超预算、参考不可读等问题会如实记录；轮询不会重新提交生成。

## 目录

```text
skills/migu/                         主流程、参考说明、环境和素材检查脚本
skills/tiktok-product-video-editor/  配套本地剪辑 skill（不含剪辑工具箱）
tests/                              本地测试，使用合成数据，不调用生成服务
docs/VALIDATION.md                   检查结果与尚未验证项
```

## 安装

将 `skills/` 内的两个目录复制到你的全局 skills 目录（默认 `~/.codex/skills/`；若设置了 `CODEX_HOME`，使用其下的 `skills/`）。已有同名 skill 时先备份并对照差异，避免覆盖自定义内容。复制完成后，在能够发现新 skill 的会话中调用 `$migu`；正在执行的任务需要重新读取更新后的文件。

将 `skills/migu/installation.example.json` 复制为安装位置中的 `migu/installation.json`，填写自己的实际目录；不使用的字段保持 null。该本机文件已被 `.gitignore` 排除。编辑器单独使用时，可将其示例复制为 `installation.json` 并填写 `toolkit_root`。

```json
{
  "schema_version": 1,
  "collection_root": null,
  "editor_toolkit_root": null,
  "ffmpeg_path": null
}
```

具体字段和只读检查说明见 [setup.md](skills/migu/references/setup.md)。不要将模型密钥写入上述文件；账号由 Hypit 的实际 Runtime/认证流程配置。

## 运行依赖

| 路线 | 额外依赖 | 本仓库是否包含 |
|---|---|---|
| 分析/拆解 | 能读取参考的代理环境；实际视频分析能力按环境提供 | 不提供代理宿主或视频理解模型 |
| AI 图片/视频生成 | 官方 Hypit CLI、hypit skill、所选模型端点和客户自己的账号 | 不包含 |
| 代找爆款 | 适配的 tiktok-video-workflow 采集项目、yt-dlp；该项目的 Evil 搜索服务或允许的搜索降级路线 | 不包含 |
| 给定链接下载 | 可用的 yt-dlp 或已配置下载路线 | 不包含 |
| 剪辑成片 | ChatCut Desktop/MCP、Remotion、配套剪辑工具箱及其 Python/Node 依赖 | 仅包含编辑器 skill |
| 素材技术检查 | Python 3.11+、ffmpeg；ffprobe 为可选增强检查 | 包含 Python 检查脚本，不包含二进制 |

采集项目应含 `workflow/unattended/evil_discovery.py` 和 `workflow/collection/collector.py`。剪辑工具箱应含 `scripts/package_remotion.py`、`scripts/deliver_video.py`、`docs/`、`remotion/` 等文件；缺工具箱时仅复制编辑器 skill 无法完成整条剪辑路线。本仓库不修改这些工具的授权或付费范围。

## 使用示例

- `用 $migu 找一个厨房收纳产品的 TikTok 爆款，换成我的产品并复刻成片。`
- `用 $migu 按我提供的视频复刻，换人物和商品，保留完整结构与节奏；操作按我的产品来。`
- `用 $migu 只拆解这条服装视频，不生成。`
- `用 $migu 生成这组商品演示素材，先不剪辑。`

默认剪辑配置为无背景音乐；静音或口播按本次要求。图片和视频费用分别核对，已有授权范围内继续执行，增加付费范围时才请求新的决定。

## 本地验证

从仓库根目录运行：

```sh
python3 -m unittest discover -s tests -v
python3 skills/migu/scripts/preflight.py --route analyze
python3 skills/migu/scripts/preflight.py --route full --config skills/migu/installation.json
```

Windows 使用已安装的 Python 命令。没有 ffmpeg 时真实媒体测试会跳过；要完成这些测试，安装 ffmpeg 或将 `MIGU_TEST_FFMPEG` 设为已有二进制的绝对路径。测试不连接 Hypit、TikTok 或 ChatCut，不花生成积分。`full` 预检在未配置环境上返回缺项是预期行为，不代表安装完成。

素材交接检查：

```sh
python3 skills/migu/scripts/check_handoff.py /path/to/project/handoff.json --ffmpeg /path/to/ffmpeg
```

清单字段见 [progress-and-evidence.md](skills/migu/references/progress-and-evidence.md)。脚本验证本地文件、哈希、解码、证据关联和已登记镜头覆盖；不能独立证明 AI 来源、视觉质量或原片镜头清单是否完整。实际逐镜复核仍必需。

## 发布范围与验证状态

见 [验证报告](docs/VALIDATION.md)。真实账号生成、TikTok 采集和 ChatCut 成片需要在目标环境验收，不能用本地单元测试代替。此版本未附带开源许可证；发布者可按自己的分发计划另行选定 LICENSE。第三方程序和依赖不随本仓库重新授权。
