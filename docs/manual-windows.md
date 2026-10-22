# Windows

1. 把 README 中的一句话提示词和邮件里的本人 OneDrive 链接交给本机 Agent。
2. Agent 从公开 GitHub 取得项目，并从私人共享下载三份设备文件。需要 OneDrive 登录或验证码时本人操作。
3. 首选保存位置：`%USERPROFILE%\Downloads\employee-workspace\`。文件名必须为 device-bundle.zip、device-bundle.sha256、README.md。
4. 首选目录没有设备文件时，Agent 可提示你把文件放在已下载项目的 deployment/；首选文件校验失败时不能改用另一份身份。
5. Agent 按项目 README 执行 check、setup、verify、connect；Windows 安装和启用隧道时本人批准 UAC。
6. 进入 VM 后使用 workspace-login，按下载的连接单访问 VM 浏览器，个人 Claude 登录由本人完成。日常使用 workspace-browser start/status/stop，文件传输用 sftp。
