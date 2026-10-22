# Windows 10 / 11

在项目目录用 PowerShell 5.1 或 7 执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 check
powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 setup -InstallClients
powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 verify
powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 connect
```

准备客户端及激活 WireGuard tunnel service 需要管理员 PowerShell。普通 PowerShell 可先用 setup -NoActivate 安装本人私有文件，再在本人批准的管理员窗口重跑 setup；不向 Agent 提供密码。Windows 不会全局更改 ExecutionPolicy，示例仅对当前进程生效。

缺少 OpenSSH 时使用 Windows 官方能力；WireGuard 安装器来自官方地址并核验 Authenticode 签名，安装窗口由本人操作。既有 WireGuard 不重复安装。密钥和配置在 LOCALAPPDATA 下，ACL 限制为当前用户。

脚本只使用本设备固定服务名，不卸载其他隧道。已存在服务路径不匹配或入口已有路由时停止并报告；不替换其他 VPN。verify 在未提权时可能无法读取握手，但仍分别核对实际 SSH/SFTP。

进入 VM 后使用 workspace-login。浏览器入口见本接入 ZIP 内的 deployment/README.md；本机只显示远端画面，个人授权由本人完成。文件传输使用 sftp 动作；停用接入使用管理员窗口运行 disconnect，保留设备配置。
