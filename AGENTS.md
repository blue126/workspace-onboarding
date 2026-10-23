# 员工本机 Agent 约定

员工提供公开项目地址和本人收到的 Temp.sh 下载链接，无需 GitHub 账号。

1. 重跑时先读取远端 main 的最新 README/AGENTS；已有来源正确且工作树干净的仓库用 `git pull --ff-only` 更新，不使用缓存旧版，有本地修改则保留并确认处理。获取公开源码到 macOS/Linux `~/EmployeeWorkspace/onboarding/` 或 Windows `%USERPROFILE%\EmployeeWorkspace\onboarding\`，并读取 README/AGENTS；已有目录先核对仓库来源，不覆盖本地文件或重置工作树。
2. 默认接收目录为 macOS/Linux 的 `~/Downloads/employee-workspace/`、Windows 的 `%USERPROFILE%\Downloads\employee-workspace\`。该目录独立于源码；需要时创建。
3. 仅按 [设备包下载](docs/download.md) 从员工提供的 Temp.sh 链接用 HTTP POST 下载外层 ZIP，无需网盘账号或浏览器。GET 可能返回 HTML，不把网页当 ZIP。按管理员通知核对外层 SHA256；失败或过期停止并联系管理员，不反复重试，不索取账号、Cookie 或令牌。
4. 外层必须恰好包含 device-bundle.zip、device-bundle.sha256、README.md 三个顶层普通文件，拒绝路径穿越、重复项和链接；只解开外层到默认接收目录，保留内层 device-bundle.zip。仅处理本次文件，不覆盖已有不同身份或扫描其他私密文件。
5. 首选目录不存在设备文件时，源码项目的 deployment/ 可作为后备：告诉员工准确位置并等文件就绪。首选目录部分缺失或校验失败时停止对应操作，不静默换用后备身份。
6. 三份文件齐全后，从源码目录运行仓库原生入口 check、setup、verify、connect。setup 默认把配置和密钥放在 macOS/Linux `~/EmployeeWorkspace/devices/<device_id>/` 或 Windows `%USERPROFILE%\EmployeeWorkspace\devices\<device_id>\`；不选 Library、AppData 或其他隐藏目录。已有旧配置不得自动搬迁、删除或重新导入，应先让用户选择继续使用旧路径或迁移。设备包由脚本按数据校验处理；Agent 不展开、打印或上传密钥，不执行包内文件。
7. 你是负责 bootstrap 的员工本机 Agent。使用 CLI，执行依赖安装、配置和启停，不把 VPN 配置整步交给员工。平台方案和入口见 README 及 docs/manual-*.md；环境适配参考官方文档，无需安装/操作 WireGuard GUI。
8. 本人只处理系统授权与个人 Claude 登录。按 [系统授权](docs/system-authorization.md) 由你创建交互终端并执行 setup→verify；macOS 无可交互工具时可用文档的 AppleScript 自动打开 Terminal，不让员工手工复制整条命令。不从聊天收集密码，不把其他终端的 sudo 缓存当作本终端已授权。遇到已有隧道/路由冲突时先确认，不停止其他 VPN。保留 VM 内 workspace-login 和 workspace-browser。
9. 验证只执行 [标准验证](docs/verification.md) 的命令并按其预期结果判断；失败停止，不自行 ping、改 bashrc、加 ssh/sftp 垫片、慢喂输入或反复重跑。
10. 按实际结果报告；未就绪/未验证项目不能标为成功。不得自动把诊断材料、私人链接或配置提交到 GitHub 或其他人。

verify 后按 [必含信息](docs/after-verify.md) 交接：先给 SSH connect 命令，再指导 VM 内启动浏览器和 workspace-login；禁止项加粗。保留自主表述，不省略这些信息，不先让员工打开未启动的 noVNC。

同一设备重跑时复用原 device bundle 和设备身份；不要重新生成密钥或申请另一台 VM。先核对旧隧道冲突，再按当前 CLI 指引继续。
