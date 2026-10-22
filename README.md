# 员工工作环境 Bootstrap

公开项目：[blue126/workspace-onboarding](https://github.com/blue126/workspace-onboarding)。员工不需要 GitHub 账号。项目只包含通用客户端和指引。

员工以管理员发送的私人共享邮件为入口：邮件说明如何下载本设备接入文件，并提供给 Agent 的提示词。本项目提供补充说明和执行脚本。

## 给本机 Agent 的一句话

> 请按 https://github.com/blue126/workspace-onboarding 的指引，从“网盘链接”下载本设备接入包并完成 bootstrap；需要登录或系统授权时交给我。

注：把“网盘链接”换成你邮件中收到的 OneDrive 私人共享链接即可。请使用具备本机文件、终端及浏览器操作能力的 Agent；个人登录、验证码和系统授权由本人操作。

## Agent 执行顺序

1. 阅读本项目 README.md、AGENTS.md，获取公开源码到本机新目录；已有同名目录时先核对来源，不覆盖本地工作。
2. 使用员工给出的 OneDrive 链接获取本设备的三份文件。私人共享需要登录时交还员工；没有浏览器操作能力时给出准确的人工下载步骤。
3. 创建并使用下方的默认接收目录，下载 `device-bundle.zip`、`device-bundle.sha256` 和 `README.md`（连接单）。只保存这次共享中的文件，不扫描其他网盘内容或覆盖已有不同身份。
4. 如果 OneDrive 把整个文件夹下载成外层 ZIP，只解开外层，把这三份文件放入默认目录；保留 `device-bundle.zip` 本身，不展开其中的密钥。
5. 运行 check → setup → verify → connect。进入 VM 后用 workspace-login，由员工本人完成 Claude 登录。

## 设备文件的默认位置

| 系统 | 首选位置：独立于项目，可在下载源码前使用 |
| --- | --- |
| macOS / Linux | `~/Downloads/employee-workspace/` |
| Windows | `%USERPROFILE%\Downloads\employee-workspace\` |

目录中应有固定文件名：

```text
employee-workspace/
  device-bundle.zip
  device-bundle.sha256
  README.md
```

找不到首选目录中的设备文件时，Agent 可在取得源码后提示员工把三份文件放入项目的 `deployment/` 后继续。该目录是后备位置，私密内容被 Git 忽略。首选目录已有部分文件或校验失败时，先解决该目录的问题，不静默改用后备身份。

## 命令

脚本自动按上述顺序定位设备包和摘要。支持 Windows 10/11、macOS 12+、Ubuntu 22.04+/Debian 12+。

| 动作 | Windows PowerShell 5.1 / 7 | macOS / Linux |
| --- | --- | --- |
| 检查 | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 check` | `bash ./bootstrap.sh check` |
| 设置 | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 setup -InstallClients` | `bash ./bootstrap.sh setup --install-clients` |
| 验证 | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 verify` | `bash ./bootstrap.sh verify` |
| 终端 | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 connect` | `bash ./bootstrap.sh connect` |
| 文件传输 | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 sftp` | `bash ./bootstrap.sh sftp` |
| 断开 | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 disconnect` | `bash ./bootstrap.sh disconnect` |

Windows 安装和启用隧道可能需要管理员 PowerShell；Linux 需要本人 sudo 授权。macOS 使用官方 WireGuard App，由本人批准安装和 VPN 权限。

## VM 内的 Claude 与浏览器

连接后在 VM 内运行 `workspace-login`，用私密连接单中的浏览器地址操作 VM 的 Firefox。个人登录、验证码及授权同意由本人完成。日常浏览器使用 `workspace-browser start/status/stop`。

脚本分别报告包、设备身份、VM、SSH/SFTP 和 Claude 状态；未完成的个人授权和真实项目任务保留待处理，不把命令退出 0 当作全部验收通过。

## 详细说明

- [Agent 约定](AGENTS.md)
- [Windows](docs/manual-windows.md)
- [macOS](docs/manual-macos.md)
- [Ubuntu/Debian](docs/manual-linux.md)
- [故障处理](docs/troubleshooting.md)
- [设备文件交付约定](docs/administrator.md)

每台电脑使用独立身份，包括同一员工的多台电脑。私密共享链接、设备包和连接单不得写入公开仓库、Issue 或日志。删除文件不等于撤销服务端设备身份。
