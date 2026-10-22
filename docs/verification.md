# 标准验证

由员工本机 Agent 从项目源码目录按顺序执行。以下是验收入口；不要临时编写探测脚本或改变验收条件。

| 阶段 | macOS / Linux | Windows PowerShell |
| --- | --- | --- |
| 检查 | `bash ./bootstrap.sh check` | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 check` |
| 配置 | `bash ./bootstrap.sh setup --install-clients` | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 setup -InstallClients` |
| 验证 | `bash ./bootstrap.sh verify` | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 verify` |
| 进入 VM | `bash ./bootstrap.sh connect` | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 connect` |

setup/verify 需要本人可授权的交互终端；Windows 使用已批准的管理员 PowerShell。不要把密码发给 Agent。

## 预期结果

检查脚本输出的 JSON 和退出码；只有退出 0 不足以判定通过。

| 结果码 | 退出码 | 判断及下一步 |
| --- | --- | --- |
| CHECKED | 0 | 包校验和客户端就绪；继续 setup |
| DEPENDENCY_MISSING | 3（check）或 2 | 缺本机依赖；按平台指引安装，再执行原命令 |
| CONFIGURED | 0 | 本机配置已完成；继续 verify，不代表远端已验证 |
| NEEDS_ADMIN / HOMEBREW_REQUIRED | 2 | 完成对应系统授权或依赖安装，再执行同一命令 |
| CLAUDE_AUTH_USER_PENDING | 0 | SSH 身份、VM 归属、sudo、CLI、SFTP、握手通过；个人 Claude 授权尚待本人完成 |
| CONNECTION_VERIFIED | 0 | 上述连接检查和 Claude 订阅登录状态通过；不代表真实项目任务已验收 |
| 其他错误码 | 非 0 | 停止，按故障处理说明反馈；不要改条件使其通过 |

完整连接验收要求 `package_verified=true`、`client_ready=true`，以及 `tunnel_handshake`、`ssh_identity`、`assigned_vm`、`sudo`、`cli`、`sftp_roundtrip` 全部为 `passed`。`claude_auth=user_action_required` 单独交还本人处理；`unavailable` 表示检查失败，不能当作尚未登录。

个人登录：先用 connect 进入 VM，依次执行 `workspace-browser start`、**`workspace-login`**。浏览器就绪后再打开 noVNC，在 VM Firefox 中由本人完成授权，再执行一次原 verify。按 [验证后的必含信息](after-verify.md) 交接；不得通过重新登录来掩盖 `CLAUDE_AUTH_CHECK_FAILED`。

## 连接约定与停止条件

- 网关不回应员工 VPN 的 ICMP echo，**ping 不通是预期现象**。UDP 端口探测也不能证明握手成功；以脚本的 WireGuard、SSH 和 SFTP 检查为准。
- 网关只接受固定 VM 会话和标准 `sftp` 子系统。不要附加 `ssh … id` 等远程命令，不要使用 `sftp -s employee-sftp`；PTY 与分发由脚本处理。
- SSH 验证最长 60 秒，每次 SFTP 操作最长 30 秒；超时返回 VERIFY_TIMEOUT，停止反馈，不再慢喂输入或增加等待时间。
- 验证已兼容终端 OSC/ANSI 输出，Claude 检查不读取会话输入。不要修改 VM 的 `.bashrc`、创建 ssh/sftp 垫片、关闭主机密钥校验，或把失败结果标为通过。
- 发生错误后停止，反馈命令、系统、JSON 错误码及未通过字段。依赖/授权问题解决后可重跑原命令；其他错误交管理员处理，不连续重复验证。

Claude 状态只调用 [官方 `claude auth status`](https://code.claude.com/docs/en/cli-reference)，不发模型请求、不消耗对话 token；邮箱、令牌和原始登录输出不进入验收报告。
