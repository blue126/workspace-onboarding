# 员工本机 Agent 约定

员工提供公开项目地址和本人收到的 Temp.sh 下载链接，无需 GitHub 账号。

1. 重跑时先读取远端 main 的最新 README/AGENTS；已有来源正确且工作树干净的仓库用 `git pull --ff-only` 更新，不使用缓存旧版，有本地修改则保留并确认处理。获取公开源码到 macOS/Linux `~/EmployeeWorkspace/onboarding/` 或 Windows `%USERPROFILE%\EmployeeWorkspace\onboarding\`，并读取 README/AGENTS；已有目录先核对仓库来源，不覆盖本地文件或重置工作树。
2. 默认接收目录为 macOS/Linux 的 `~/Downloads/employee-workspace/`、Windows 的 `%USERPROFILE%\Downloads\employee-workspace\`。该目录独立于源码；需要时创建。
3. 仅按 [设备包下载](docs/download.md) 从员工提供的 Temp.sh 链接用 HTTP POST 下载外层 ZIP，无需网盘账号或浏览器。GET 可能返回 HTML，不把网页当 ZIP。按管理员通知核对外层 SHA256；失败或过期停止并联系管理员，不反复重试，不索取账号、Cookie 或令牌。
4. 外层必须恰好包含 device-bundle.zip、device-bundle.sha256、README.md 三个顶层普通文件，拒绝路径穿越、重复项和链接；只解开外层到默认接收目录，保留内层 device-bundle.zip。仅处理本次文件，不覆盖已有不同身份或扫描其他私密文件。
5. 首选目录不存在设备文件时，源码项目的 deployment/ 可作为后备：告诉员工准确位置并等文件就绪。首选目录部分缺失或校验失败时停止对应操作，不静默换用后备身份。
6. 三份文件齐全后，从源码目录运行仓库原生入口 check、setup、verify、connect。setup 默认把配置和密钥放在 macOS/Linux `~/EmployeeWorkspace/devices/<device_id>/` 或 Windows `%USERPROFILE%\EmployeeWorkspace\devices\<device_id>\`；不选 Library、AppData 或其他隐藏目录。已有旧配置不得自动搬迁、删除或重新导入，应先让用户选择继续使用旧路径或迁移。设备包由脚本按数据校验处理；Agent 不展开、打印或上传密钥，不执行包内文件。
7. 你是负责 bootstrap 的员工本机 Agent。使用 CLI，执行依赖安装、配置和启停，不把 VPN 配置整步交给员工。平台方案和入口见 README 及 docs/manual-*.md；环境适配参考官方文档，无需安装/操作 WireGuard GUI。
8. 本人只处理系统授权与个人 Claude 登录。按 [系统授权](docs/system-authorization.md) 由你创建交互终端并执行 setup→verify；macOS 无可交互工具时可用文档的 AppleScript 自动打开 Terminal，工具明确拒绝 sudo 或终端控制时，按文档给出单条人工执行命令并停止自动化提权尝试；其他情况下不要把整步配置交给员工。不从聊天收集密码，不把其他终端的 sudo 缓存当作本终端已授权。遇到已有隧道/路由冲突时先确认，不停止其他 VPN。保留 VM 内 workspace-login 和 workspace-browser。
9. 验证只执行 [标准验证](docs/verification.md) 的命令并按其预期结果判断；失败停止，不自行 ping、改 bashrc、加 ssh/sftp 垫片、慢喂输入或反复重跑。
10. 按实际结果报告；未就绪/未验证项目不能标为成功。不得自动把诊断材料、私人链接或配置提交到 GitHub 或其他人。

Mosh 试用按 [客户端安装、连接与验证](docs/mosh.md) 执行。先识别本机系统和当前 SSH 设备账号，安装客户端并验证，再用管理员提供的对应端口连接；不要从姓名推断端口。员工复制的提示词必须自包含，Agent 无法读取员工邮件。以终端体验为主的任务允许跳过 Claude 登录，不主动打开浏览器或授权流程。

verify 后按 [必含信息](docs/after-verify.md) 交接：先给 SSH connect 命令，再指导 VM 内启动浏览器和 workspace-login；禁止项加粗。保留自主表述，不省略这些信息，不先让员工打开未启动的 noVNC。

普通同设备重跑复用原 device bundle 和设备身份。收到管理员明确的迁移／更新链接时，必须使用此次链接和 SHA256 对应的新包；不要复用缓存旧包、旧地址、旧密钥或仅修改旧隧道 Endpoint。默认接收目录中的旧三件套先保留到独立目录，避免新旧文件混用。按新包 profile 创建独立状态与 SSH 配置；确认归属并获员工授权后，仅停用本工作区旧隧道，不删除旧文件或操作其他 VPN。先按新包 verify，通过后才执行管理员另行明确的加速测试。交接时展示实际 profile、Endpoint、SSH 目标及桌面地址，不展示密钥。不要自行生成密钥或申请另一台 VM。

OCI Hub v2 设备包显式声明 `profile=oci-hub`，使用独立 `devices/oci-hub/<device_id>` 状态、`wh-` 隧道和 `oci-hub-<device_id>` SSH alias。目标为本人 VM 的 `employee` native SSH；员工 WireGuard 使用 51824/15 秒。严格核对目标 SSH host pin；桌面模式另核对 HTTPS 证书 SHA256；v1 原入口继续可用。未知版本、profile 或字段均拒绝。细节见 [OCI Hub 接入](docs/oci-hub.md)。

OCI Hub 终端试点包另有 `access_mode=mosh`、`mosh_ports`，保留原 VM 主机名，不包含桌面字段。按 docs/mosh.md 的 OCI Hub 小节执行，macOS/Linux 用 `bootstrap.sh mosh`，Windows 用 WSL Mosh；不对终端包要求 TLS/noVNC 验证。verify 仍先给 SSH 入口；Mosh/个人体验另行验收。旧网关 `employee-mosh` 与新 VM `workspace-mosh` 不混用。
