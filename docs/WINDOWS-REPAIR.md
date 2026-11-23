# Windows 客户原地修复 Migu

在上次部署的 Codex 对话、原仓库目录继续。如果界面停在 DTK 初始化问题，选择“稍后设置账号”，然后提交修复任务。让 Codex 执行以下步骤。

1. 检查仓库为 yiz50400-cell/migu，记录当前提交与 git status。使用公开 HTTPS 地址 fetch origin main，然后做快进更新。原有 SSH remote 可继续使用；不要覆盖它，只读下载不再需要申请部署公钥。若有会被覆盖的修改，把修复版本检出到旁边的独立目录运行，同时保留原目录、Docker 项目和数据卷。客户已有五个健康服务时直接修复当前实例。
2. 首次下载检查 `git --version`，然后执行 `git clone https://github.com/yiz50400-cell/migu.git`。公开下载不需要 GitHub 登录或 SSH key。已有私有部署身份可保留，客户本地修复也不需要仓库写权限；向上游推送则另需权限。
3. 已有 Windows 服务时，在获取的修复版仓库执行以下命令。使用本机已安装的 Python 3。第二条命令用于第一条报告尚需初始化的情况。

   ```powershell
   py -3 -X utf8 scripts/repair_evil.py
   py -3 -X utf8 scripts/repair_evil.py --apply --verify-search "coffee"
   ```

   修复器复用本机采集 key，核验其读取权限。空实例使用上游官方 CLI 建立本机独立管理员，签发仅有 tiktok:read 的 key。生成的文件位于客户用户目录 .config/video-workflow 下，Windows 使用当前用户 ACL。将其中管理凭据文件的位置交给客户保管，聊天和报告只显示状态。模型 Key 和 SSH 私钥各按原用途保管。
4. 已经有管理员而旧 key 未找回时，先检查当前服务原有 VW_EVIL_API_KEY_FILE 和采集模块支持的本地配置。确需已有管理员授权时，让客户在自己的本机安全登录或提供既有 key 文件路径，再验证。若出现 pending 签发记录，通过现有管理员会话按记录的名称核对 API key 列表。查明上次未签发或已由所有者处理遗失的 key 后才移走该记录并继续。
5. 保留已有项目、素材、模型配置、数据卷和本地代码修改。按 docs/INSTALL.md 先运行脚本计划，结合原安装报告补齐其余未完成项。Docker 使用 Linux 容器，ChatCut Desktop 打开后检查 list_projects。Windows 编辑器执行 toolkits/editor/scripts/check_windows.bat。报告分别列出采集 API 鉴权、浏览器、身份池、实际搜索、ChatCut 连接与 Remotion 验证结果。部署过程使用本地诊断，真实付费生成另按客户任务执行。

修复器只自动管理已识别的本机实例。它读取**运行中容器**的搜索登录策略，并分别报告游客/登录身份和可参与搜索的登录候选；候选数量不证明会话有效。`--verify-search` 返回真实视频 URL 后才标为 `SEARCH_VERIFIED`，仍不代表视频下载或素材质量已经验收。其余状态退出 2，保留 pending 原因。已有实例的 Docker 绑定或自定义安装不匹配时，记录具体阻塞并使用原项目设置继续。

## TikTok 登录身份缺失与 Chrome 扩展等待

这部分同时适用于 Windows 和 macOS，不能仅凭客户操作系统归因。

- 已核对的发行版 Evil 提交 `3c045e11aecd58ab076562f1246931b9dd5d909b`，`tiktok.search_posts` 的第一页要求登录；旧实例可能是 `preferred`。部署时检查实际运行版本，不把发布者已有服务的结果推广到新实例，也不将上游 `required` 改成 `preferred` 来隐藏错误。
- DTK 管理员、采集 API key、TikTok 登录会话是三个不同对象。Chrome 中已登录不会自动同步到 Docker 的身份池。`TIKTOK_LOGIN_REQUIRED` 时不要重装 Docker、重建管理员或反复铸造游客；`TIKTOK_LOGIN_UNAVAILABLE` 时先检查已有登录身份的冷却和搜索轮换设置，保留现有数据。
- 只在客户已经授权的范围内导入其本人的 TikTok 登录会话。支持的上游入口是 `POST /api/v1/admin/identities/import`，要求匹配的浏览器 User-Agent；同时核对浏览器与 Docker 使用的网络出口。导入后按上游登录态检查和真实搜索确认，不凭 `authenticated` 标记宣称成功。不要让客户把 Cookie 或密码粘贴进聊天。
- 截图所示的本地 Chrome 导入助手是客户会话临时创建的，**不是本仓库已验证组件**。先检查代码、TikTok 域名权限、本机接收地址和日志，再复用已有授权。不要反复新建扩展或更换导入方案。若收件器限时运行，先检查是否仍有效。
- 浏览器工具若明确禁止打开 `chrome://extensions/`，保留该边界，由客户完成一次正常的“加载已解压扩展”操作；不能用其他自动化入口绕开该限制。已有 Cookie 授权不代表扩展已经加载。操作后由 Codex 自动续接导入、登录态检查、搜索和下载验收，避免反复询问已同意的授权范围。完成后停止临时接收器并移除临时导入扩展。

## 客户本机修复验收

在原 Codex 对话中粘贴以下任务即可，不要求客户自己写代码：

> 在这台机器原地修复 Migu 采集链。先记录仓库提交、实际 DTK 版本、系统、当前服务与未提交修改。通过公开仓库获取修复版，保留已有模型配置、账号、Docker 项目、数据卷和素材；有冲突就在旁边检出修复版，连接原服务。读取 docs/WINDOWS-REPAIR.md，执行 repair_evil.py --verify-search coffee。根据实际状态继续修复，不因服务健康或游客数大于零宣称采集可用。复用已授权且检查过的 TikTok 本机导入助手；如必须由本人加载扩展，只交代一次具体操作，完成后自动继续。不要绕开浏览器权限限制，不重建已有管理员，不更改上游登录要求。验证至少一次真实搜索取得视频链接、下载一条可访问视频并确认能解码，再报告通过。若平台拒绝、账号验证或网络阻塞仍存在，保留原始错误代码并明确尚未通过，不反复重装。将本机修复写成 Git diff/补丁，删除其中密钥、Cookie和机器私密配置，方便回传合并；本地修改不需要仓库写权限。

下载失败要与搜索失败分开记录；搜索通过不保证所有视频均可下载。Windows 真机验收必须在客户机器完成，macOS 单机或模拟测试不能替代。
