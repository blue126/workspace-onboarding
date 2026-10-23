# Windows

1. 把 README 中的一句话提示词和邮件里的本人 Temp.sh 链接交给本机 Agent。
2. Agent 从公开 GitHub 取得项目，按 [设备包下载](download.md) 用 HTTP POST 下载，核对外层 SHA256 后仅解开外层 ZIP，得到三份设备文件。无需网盘账号；链接过期时联系管理员。
3. 首选保存位置：`%USERPROFILE%\Downloads\employee-workspace\`。文件名必须为 device-bundle.zip、device-bundle.sha256、README.md。
4. 首选目录没有设备文件时，Agent 可提示你把文件放在已下载项目的 deployment/；首选文件校验失败时不能改用另一份身份。
5. Agent 按项目 README 执行 check、setup、verify、connect；Agent 通过官方签名 MSI 静默安装，并用 wireguard.exe 隧道服务配置和启停；本人只批准 UAC，无需 App 导入。
6. 先通过 SSH 进入 VM，依次运行 workspace-browser start、workspace-login；浏览器就绪后再打开 noVNC，在 VM Firefox 中由本人完成 Claude 授权。日常使用 workspace-browser start/status/stop，文件传输用 sftp。

项目源码：`%USERPROFILE%\EmployeeWorkspace\onboarding\`。setup 的运行配置默认在 `%USERPROFILE%\EmployeeWorkspace\devices\<device_id>\`，无需到 AppData 查找。已有旧配置保留，参见 README 的旧目录说明。
