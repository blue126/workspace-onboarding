# 状态与恢复

先按 [标准验证](verification.md) 的命令与预期结果执行。网关不回应员工 VPN 的 ping；客户端使用标准 sftp 子系统，不指定 employee-sftp。

| 代码 | 含义与下一步 |
| --- | --- |
| PACKAGE_MISSING / PACKAGE_HASH_MISMATCH | 项目不完整或数据包被改变；从获授权仓库取得同一发布版本，联系管理员；不要自行改 hash |
| PACKAGE_UNSAFE / MANIFEST_INVALID | 包结构、字段或版本不符合约定；由管理员重新生成，不能运行包内脚本 |
| DEPENDENCY_MISSING | 缺本机客户端；获准后 setup 加 InstallClients／install-clients |
| NEEDS_ADMIN | Windows 本人确认管理员 PowerShell 的 UAC 后重跑原命令；macOS/Linux 在本人可输入密码的同一交互 TTY 重跑原命令，不依赖其他终端 sudo -v；不发送密码 |
| HOMEBREW_REQUIRED | Agent 按 macOS 指引安装 Homebrew 后重跑 setup --install-clients，系统授权交还本人 |
| ROUTE_INSPECTION_FAILED / TUNNEL_INSPECTION_FAILED | 无法检查当前路由或 CLI 接口，未修改网络；报告此代码，不盲目启停 |
| STATE_ROOT_CONFLICT / CONFIG_CONFLICT | 现有目录／配置归属或内容不匹配；保留原文件，联系管理员，不覆盖 |
| TUNNEL_CONFLICT / ROUTE_CONFLICT | 已有隧道或路由冲突；核对是否本设备旧手工隧道，由本人处理迁移，不停止其他 VPN |
| NO_RECENT_HANDSHAKE | 激活隧道并触发连接，检查 Endpoint／网络；在获准网络上重试 |
| SSH_HOST_KEY_MISMATCH | 主机身份改变；暂停并联系管理员核对，不删除 known_hosts、不关闭严格校验 |
| SSH_CONNECTION_FAILED | 核对 WireGuard、设备是否启用、网络和系统时间 |
| WORKSPACE_ID_MISMATCH | 分配用户／VM 不正确，退出并联系管理员 |
| SSH_PROTOCOL_FAILED / VM_BASELINE_FAILED | 验证记录不完整或基础助手异常，停止并报管理员；不改 bashrc、不创建垫片、不自行慢喂命令 |
| VERIFY_TIMEOUT | SSH 60秒或 SFTP 30秒未结束，停止反馈，不反复验证或延长超时 |
| CLAUDE_AUTH_CHECK_FAILED | Claude 状态命令超时或返回无效结果，不等同未登录；停止交管理员处理 |
| SFTP_ROUNDTRIP_FAILED / SFTP_CONTENT_MISMATCH | 只创建本次随机 /tmp/ws-onboarding-* 目录；失败时不删除未经核实内容，管理员可按本次 nonce 核查 |
| CLAUDE_AUTH_USER_PENDING | 连接已验证，个人授权待完成；进入 VM 运行 workspace-login，由本人操作 |
| HANDSHAKE_INSPECTION_UNAVAILABLE | SSH/SFTP 等按报告判断，先核对 CLI 客户端和本人 sudo/UAC 授权；不要把 unavailable 写成 passed |
| OPERATION_FAILED | Windows 已抑制可能含私密信息的原始异常；报告步骤、版本和此代码，别贴私钥或完整配置 |

noVNC 首次一直加载可刷新本机页面重试；确认 WireGuard 仍启用、VM 浏览器仍在运行。远端 workspace-browser status/start 可检查／启动，stop 才结束浏览器。此前出现过一次刷新后恢复的现象，尚未确证根因，不代表所有黑屏都由同一问题引起。

个人 Claude 的邮箱、验证码、完整授权链接、令牌和浏览器会话不用于排错。客户端报告已删除这些字段；如需外发其他材料，先由本人审阅脱敏结果并明确授权。

502：先通过 SSH 在 VM 内运行 `workspace-browser status`、`workspace-browser start`，等待就绪后刷新 noVNC 一次；持续失败就反馈管理员。不要把所有 502 都判定为浏览器未启动，不修改网关。
