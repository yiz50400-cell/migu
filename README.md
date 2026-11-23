# migu

各种商品通用的 TikTok AI 复刻流程：按需找参考 → 使用已选图片接入生成参考图 → Hypit 生成动态视频 → 素材验收 → ChatCut 剪辑与 Remotion 包装 → 成片复核。

Windows 客户首次下载或从 DTK 初始化页面续装，见 [Windows 原地修复](docs/WINDOWS-REPAIR.md)。

## 公开下载

```sh
git clone https://github.com/yiz50400-cell/migu.git
cd migu
```

只读下载无需 GitHub 账号或 SSH 部署密钥。客户可在本机修改并测试；向主仓库推送仍需写权限。已有安装保留原目录和配置，按 [原地修复说明](docs/WINDOWS-REPAIR.md) 更新。

## 下载后怎么用

在 Codex 中打开**整个仓库**，说：

> 部署 migu，补齐需要的环境。

代理按根目录 AGENTS.md 执行统一安装，自动处理采集模块、剪辑工具箱及普通软件依赖，不需要逐项提醒。安装入口：

```sh
python3 scripts/install.py --apply
```

Windows 可用 `py -3` 替换 `python3`。不带 --apply 只查看计划。安装失败后重复同一命令继续；具体说明见 [安装指南](docs/INSTALL.md)。不要只下载单个 SKILL.md。

**仓库已经包含采集模块与剪辑工具箱源码。** Python/Node 依赖、官方 Hypit、Evil 等按平台下载安装，不把作者机器的二进制、账号或密钥拷给客户。ChatCut 实际安装所需官方许可点击、本人登录与模型密钥仍需由使用者完成，其余步骤由代理接着执行。网络或系统限制会写入安装报告，不将尚未连接的环境标为就绪。

## 包含什么

| 内容 | 交付方式 |
|---|---|
| migu 主流程、配套剪辑 skill | skills/，安装到全局 skills 目录 |
| 原有采集模块 | toolkits/collector/，包括 Evil 发现与 yt-dlp 下载入口 |
| 原有剪辑工具箱 | toolkits/editor/，包括 Python 源码、Remotion 工程、锁文件、模板预览 |
| 官方 Hypit | 安装时复用已有安装，或从官方 npm/仓库固定版本获取 CLI 和 skill |
| yt-dlp、Python、Remotion 依赖 | 安装脚本按各自依赖文件准备 |
| Docker/Evil | 发现路线复用已有服务，否则准备 Docker 和固定提交的 Evil browser 栈 |
| ChatCut | 优先复用宿主连接；缺失时按官方安装与连接流程处理 |
| 验证与恢复 | 只读预检、交接检查、回归测试、安装报告、skill 更新备份 |

[来源清单](toolkits/SOURCES.json)记录内置工具箱的来源快照。第三方许可证保留在对应目录或安装源中；主仓库尚未指定 LICENSE，不自动重新授权第三方软件。

## 默认行为

- 图片、视频模型分别核对；已确定的选择不重复询问。
- 只有客户要求找爆款才搜索，优先 15–25 秒。客户给片则完整复刻，不套时长上限。
- 保留原片完整结构、镜头职责、动作过程、顺序与节奏；操作按当前商品真实结构适配，适用于各类商品。
- 实际调用 Hypit 生成动态视频，不能用图文幻灯片交差。官方模型输出不保证逐帧相同。
- 成片请求自动接续剪辑、检查；默认无 BGM，静音或口播按当前任务。
- 超时先恢复原 Build，不重复提交；账号和费用按当前授权，不因安装完成就开始付费生成。

## 使用示例

- `用 $migu 找一个厨房收纳产品的 TK 爆款，换成我的产品并复刻成片。`
- `用 $migu 按我提供的视频复刻，换人物和商品，保留完整结构和节奏。`
- `用 $migu 只拆解这条服装视频，不生成。`

## 配置与检查

安装程序自动填写全局 migu/installation.json，本机文件不进 Git。已有有效采集/剪辑路径优先保留；新机器默认使用本仓库 toolkits。账号由对应程序的认证流程设置，不写进本机路径配置。

```sh
python3 skills/migu/scripts/preflight.py --route full --config /path/to/installed/migu/installation.json
python3 -m unittest discover -s tests -v
```

真实媒体测试需要 ffmpeg，可用 MIGU_TEST_FFMPEG 指定。安装脚本的 --skills-dir 支持独立测试目录。退出码 0 表示本地阶段完成、1 表示失败、2 表示仍有账号/服务/环境动作要继续；不能把 2 当作全链路部署完成。

本地文件、哈希与解码校验不证明画面质量或原片清单完整；实际逐镜复核仍必需。原始检查见 [验证记录](docs/VALIDATION.md)，本次完整安装升级验证见 [安装验证记录](docs/INSTALL-VALIDATION.md)。
