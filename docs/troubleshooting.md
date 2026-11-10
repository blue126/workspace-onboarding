# 状态与恢复

先按 [标准验证](verification.md) 的命令与预期结果执行。ping 不能作为判断依据；以脚本的 WireGuard、SSH 和 SFTP 检查为准。

| 代码 | 含义与下一步 |
| --- | --- |
| PACKAGE_MISSING / PACKAGE_HASH_MISMATCH | 项目不完整或数据包被改变；从获授权仓库取得同一发布版本，联系管理员；不要自行改 hash |
| PACKAGE_UNSAFE / MANIFEST_INVALID | 包结构、字段或版本不符合约定；由管理员重新生成，不能运行包内脚本 |
| MANIFEST_UNSUPPORTED | 设备包格式已停用。请员工联系管理员换发新包，不要修改 manifest |
| TLS_PIN_FAILED | VM 浏览器入口（`desktop_url`）的证书与设备包 pin 不符或无法握手；不要打开或信任该地址，不要点浏览器的"继续访问"。确认 VPN 已连接后仍失败则停止，联系管理员 |
| DEPENDENCY_MISSING | 缺本机客户端；获准后 setup 加 InstallClients／install-clients |
| NEEDS_ADMIN | 尚未取得系统授权，可能缺少交互输入、授权取消或 sudo 被拒绝；不是单指密码未输入。按[系统授权](system-authorization.md)处理，工具明确拒绝时由本人运行 Agent 给出的 setup→verify 命令；不依赖另一终端 sudo -v，不发送密码 |
| HOMEBREW_REQUIRED | Agent 按 [Homebrew 官方指引](https://brew.sh/) 安装 Homebrew 后重跑 setup --install-clients，系统授权交还本人 |
| ROUTE_INSPECTION_FAILED / TUNNEL_INSPECTION_FAILED | 无法检查当前路由或 CLI 接口，未修改网络；报告此代码，不盲目启停 |
| REISSUE_READY | 本机装过同一设备的旧包（管理员换发）。运行 setup：它在本人授权下停掉旧包的隧道，把旧配置移到 `.archive/<设备>-<时间>/`，再装新包；不删除任何文件 |
| STATE_ROOT_CONFLICT / CONFIG_CONFLICT | 现有目录／配置归属或内容不匹配（例如同一个包装好后又被改过）；保留原文件，联系管理员，不覆盖 |
| CONFIG_REPLACE_FAILED | 换发时旧配置没能归档；什么都没替换，报告此代码给管理员 |
| CONFIG_UPGRADE_FAILED | 无法把旧版的本设备 ssh_config 原地升级（多为状态目录不可写或磁盘已满）；原文件保留，旧命令照常可用。核对状态目录归属和权限后重跑 setup，不手工改写 ssh_config |
| SSH_CONFIG_UNSAFE | `~/.ssh` 不是可写目录，或 `~/.ssh/config` 是符号链接、硬链接、特殊文件或不可写；隧道与本设备配置已完成，`~/.ssh` 未被改动。由本人决定是否改为普通可写文件后重跑 setup，或继续用 `bootstrap.sh connect`/`mosh`；Agent 不替本人改动该文件 |
| SSH_CONFIG_WRITE_FAILED | 检查通过但写入 `~/.ssh/config` 失败（如磁盘已满）；原文件保留。排除原因后重跑 setup，期间用 `bootstrap.sh connect`/`mosh` |
| TUNNEL_DOWN | 本设备 WireGuard 隧道没有运行，常见于 Mac 或 Linux 重启后（隧道不会自动恢复）。`connect`、`sftp`、`mosh`、verify 都会报此代码。由本人在交互终端运行 `bash ./bootstrap.sh setup`（曾用 `--bundle`/`--sha256`/`--state-root` 时带同样参数），输入本人 sudo 密码；setup 只启动本设备隧道，仍先检查路由和设备地址，已有冲突时报 `ROUTE_CONFLICT`、不动其他 VPN。得到 `CONFIGURED` 后重试原命令 |
| TUNNEL_CONFLICT / ROUTE_CONFLICT | 已有隧道或路由冲突；核对是否本设备旧手工隧道，由本人处理迁移，不停止其他 VPN。`connect`/`sftp`/`mosh` 报 `ROUTE_CONFLICT` 表示到入口的路由走了其他网卡或 VPN，脚本未做任何改动 |
| NO_RECENT_HANDSHAKE | 激活隧道并触发连接，检查 Endpoint／网络；在获准网络上重试 |
| SSH_HOST_KEY_MISMATCH | 主机身份改变；暂停并联系管理员核对，不删除 known_hosts、不关闭严格校验 |
| SSH_CONNECTION_FAILED | 核对 WireGuard、设备是否启用、网络和系统时间 |
| WORKSPACE_ID_MISMATCH | 分配用户／VM 不正确，退出并联系管理员 |
| SSH_PROTOCOL_FAILED / VM_BASELINE_FAILED | 验证记录不完整或基础助手异常，停止并报管理员；不改 bashrc、不创建垫片、不自行慢喂命令 |
| VERIFY_TIMEOUT | SSH 60秒或 SFTP 30秒未结束，停止反馈，不反复验证或延长超时 |
| CLAUDE_AUTH_CHECK_FAILED | Claude 状态命令超时或返回无效结果，不等同未登录；停止交管理员处理 |
| SFTP_ROUNDTRIP_FAILED / SFTP_CONTENT_MISMATCH | 只创建本次随机 /tmp/ws-onboarding-* 目录；失败时不删除未经核实内容，管理员可按本次 nonce 核查 |
| CLAUDE_AUTH_USER_PENDING | 连接和 VM 浏览器证书已验证，个人授权待完成；按 [README 第 5 步](../README.md#第-5-步在-vm-浏览器里登录-claude)：VM 里运行 workspace-login，本机浏览器打开它显示的地址，在画面里的 VM 浏览器中完成（证书已由 verify 核对，员工不比对指纹） |
| MOSH_CLIENT_MISSING / INTERACTIVE_TERMINAL_REQUIRED / MOSH_WSL_REQUIRED / LOCALE_UNAVAILABLE | 见 [Mosh 登录](mosh.md) |
| HANDSHAKE_INSPECTION_UNAVAILABLE | SSH/SFTP 等按报告判断，先核对 CLI 客户端和本人 sudo/UAC 授权；不要把 unavailable 写成 passed |
| OPERATION_FAILED | Windows 已抑制可能含私密信息的原始异常；报告步骤、版本和此代码，别贴私钥或完整配置 |

## 没有结果码的常见现象

- **`mosh <员工ID>-vm` 报 `mosh-server needs a UTF-8 native locale to run`，或提到 `LC_CTYPE=UTF-8`：** macOS 终端默认导出 `LC_CTYPE=UTF-8`，这个名字只在 macOS 存在，经 SSH 和 Mosh 传到 VM 后 mosh-server 找不到该 locale 就退出。对同一设备包重跑 `bash ./bootstrap.sh setup` 即可：本设备 `ssh_config` 原地升级为带 `SetEnv LANG=C.UTF-8 LC_ALL=C.UTF-8` 的版本，不需要新包，也不会报 `CONFIG_CONFLICT`。`bash ./bootstrap.sh mosh` 另外只把 `LANG=C.UTF-8` 传给 Mosh。不要为此修改 `~/.zshrc`、系统 `/etc/ssh/ssh_config` 或 VM。详见 [Mosh 登录 · 字符集](mosh.md#字符集locale)。
- **重启后 `mosh <员工ID>-vm` 或 `ssh <员工ID>-vm` 长时间无响应、报超时：** 系统自带的 ssh/mosh 不经过 bootstrap，不会报 `TUNNEL_DOWN`。先运行 `bash ./bootstrap.sh connect` 看是否报 `TUNNEL_DOWN`，再按上表恢复。

个人 Claude 的邮箱、验证码、完整授权链接、令牌和浏览器会话不用于排错。客户端报告已删除这些字段；如需外发其他材料，先由本人审阅脱敏结果并明确授权。
