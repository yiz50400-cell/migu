# Windows 客户原地修复 Migu

在上次部署的 Codex 对话、原仓库目录继续。如果界面停在 DTK 初始化问题，选择“稍后设置账号”，然后提交修复任务。让 Codex 执行以下步骤。

1. 检查仓库为 yiz50400-cell/migu，记录当前提交与 git status。使用本机已有只读部署身份 fetch origin main，然后做快进更新。若有会被覆盖的修改，把修复版本检出到旁边的独立目录运行，同时保留原目录、Docker 项目和数据卷。客户已有五个健康服务时直接修复当前实例。
2. 首次下载时，先用 git --version 和 ssh -V 检查 Git 与 OpenSSH。使用客户生成公钥时对应的私钥。若用了自定义文件名，在用户 SSH 配置中为 github.com 增加独立别名 migu-github，设置 HostName github.com、User git、IdentityFile 指向该私钥、IdentitiesOnly yes。保留已有配置。先用 git ls-remote git@migu-github:yiz50400-cell/migu.git HEAD 验证只读访问，再 clone 同一地址。首次连接按 GitHub 公布的主机指纹核对。
3. 已有 Windows 服务时，在获取的修复版仓库执行以下命令。使用本机已安装的 Python 3。第二条命令用于第一条报告尚需初始化的情况。

   ```powershell
   py -3 -X utf8 scripts/repair_evil.py
   py -3 -X utf8 scripts/repair_evil.py --apply
   ```

   修复器复用本机采集 key，核验其读取权限。空实例使用上游官方 CLI 建立本机独立管理员，签发仅有 tiktok:read 的 key。生成的文件位于客户用户目录 .config/video-workflow 下，Windows 使用当前用户 ACL。将其中管理凭据文件的位置交给客户保管，聊天和报告只显示状态。模型 Key 和 SSH 私钥各按原用途保管。
4. 已经有管理员而旧 key 未找回时，先检查当前服务原有 VW_EVIL_API_KEY_FILE 和采集模块支持的本地配置。确需已有管理员授权时，让客户在自己的本机安全登录或提供既有 key 文件路径，再验证。若出现 pending 签发记录，通过现有管理员会话按记录的名称核对 API key 列表。查明上次未签发或已由所有者处理遗失的 key 后才移走该记录并继续。
5. 保留已有项目、素材、模型配置、数据卷和本地代码修改。按 docs/INSTALL.md 先运行脚本计划，结合原安装报告补齐其余未完成项。Docker 使用 Linux 容器，ChatCut Desktop 打开后检查 list_projects。Windows 编辑器执行 toolkits/editor/scripts/check_windows.bat。报告分别列出采集 API 鉴权、浏览器、身份池、实际搜索、ChatCut 连接与 Remotion 验证结果。部署过程使用本地诊断，真实付费生成另按客户任务执行。

修复器只自动管理已识别的本机实例。LOCAL_SERVICE_READY 表示服务、凭据、浏览器和身份池通过检查，实际搜索结果另行验证。已有实例的 Docker 绑定或自定义安装不匹配时，记录具体阻塞并使用原项目设置继续。
