# macOS

1. 取得管理员发放的完整员工接入 ZIP，打开终端进入目录，运行 `bash ./bootstrap.sh check`。
2. 运行 `bash ./bootstrap.sh setup --install-clients`。没有 WireGuard 时脚本打开官方 App Store 页面，由本人安装；已有客户端不重复安装。
3. 按脚本给出的私有配置路径，在 WireGuard 选择“从文件导入隧道”。允许系统 VPN 权限，再激活该隧道。具备 GUI 能力的本机 Agent 可以辅助，系统身份认证由本人完成。
4. 运行 `bash ./bootstrap.sh verify`，确认 SSH 身份、VM、sudo、CLI、SFTP 各项。App-only 模式的握手时间由 WireGuard UI 核对，脚本如实报告 unavailable。
5. 运行 `bash ./bootstrap.sh connect`，进入远端后运行 `workspace-login`。用配置单中的私网浏览器地址操作 VM 内 Firefox，由本人登录 Claude。
6. 日常浏览器在远端运行 `workspace-browser start`。下载保存在 VM，使用 `bash ./bootstrap.sh sftp` 取回文件。
7. 退出 SSH 使用 exit。停用接入时运行 disconnect，按提示在 WireGuard 只停用本设备隧道。无需删除项目、密钥或 VM 数据。

若已有相同身份的 employee 隧道正在工作，不要重复启用；先按 README 的手工接入迁移说明核对。
