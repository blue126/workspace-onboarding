# 状态与恢复

| 代码 | 含义与下一步 |
| --- | --- |
| PACKAGE_MISSING / PACKAGE_HASH_MISMATCH | 项目不完整或数据包被改变；从获授权仓库取得同一发布版本，联系管理员；不要自行改 hash |
| PACKAGE_UNSAFE / MANIFEST_INVALID | 包结构、字段或版本不符合约定；由管理员重新生成，不能运行包内脚本 |
| DEPENDENCY_MISSING | 缺本机客户端；获准后 setup 加 InstallClients／install-clients |
| NEEDS_ADMIN | 本人打开管理员 PowerShell，重跑 setup 或 disconnect；不发送密码 |
| NEEDS_VPN_PERMISSION | Mac 在官方 WireGuard 导入脚本给出的文件、允许 VPN 并激活，再 verify |
| STATE_ROOT_CONFLICT / CONFIG_CONFLICT | 现有目录／配置归属或内容不匹配；保留原文件，联系管理员，不覆盖 |
| TUNNEL_CONFLICT / ROUTE_CONFLICT | 已有隧道或路由冲突；核对是否本设备旧手工隧道，由本人处理迁移，不停止其他 VPN |
| NO_RECENT_HANDSHAKE | 激活隧道并触发连接，检查 Endpoint／网络；在获准网络上重试 |
| SSH_HOST_KEY_MISMATCH | 主机身份改变；暂停并联系管理员核对，不删除 known_hosts、不关闭严格校验 |
| SSH_CONNECTION_FAILED | 核对 WireGuard、设备是否启用、网络和系统时间 |
| WORKSPACE_ID_MISMATCH | 分配用户／VM 不正确，退出并联系管理员 |
| SSH_PROTOCOL_FAILED / VM_BASELINE_FAILED | 远端交互验证或基础助手异常，由管理员检查服务端，不改为任意远程命令 |
| SFTP_ROUNDTRIP_FAILED / SFTP_CONTENT_MISMATCH | 只创建本次随机 /tmp/ws-onboarding-* 目录；失败时不删除未经核实内容，管理员可按本次 nonce 核查 |
| CLAUDE_AUTH_USER_PENDING | 连接已验证，个人授权待完成；进入 VM 运行 workspace-login，由本人操作 |
| HANDSHAKE_INSPECTION_UNAVAILABLE | SSH/SFTP 等按报告判断，握手时间需在 WireGuard UI 查看；不要把 unavailable 写成 passed |
| OPERATION_FAILED | Windows 已抑制可能含私密信息的原始异常；报告步骤、版本和此代码，别贴私钥或完整配置 |

noVNC 首次一直加载可刷新本机页面重试；确认 WireGuard 仍启用、VM 浏览器仍在运行。远端 workspace-browser status/start 可检查／启动，stop 才结束浏览器。此前出现过一次刷新后恢复的现象，尚未确证根因，不代表所有黑屏都由同一问题引起。

个人 Claude 的邮箱、验证码、完整授权链接、令牌和浏览器会话不用于排错。客户端报告已删除这些字段；如需外发其他材料，先由本人审阅脱敏结果并明确授权。
