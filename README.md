# 员工工作环境 Bootstrap

公开项目：[blue126/workspace-onboarding](https://github.com/blue126/workspace-onboarding)。员工不需要 GitHub 账号。项目只包含通用客户端和指引。

员工以管理员发送的私人共享邮件为入口：邮件说明如何下载本设备接入文件，并提供给 Agent 的提示词。本项目提供补充说明和执行脚本。

## 给本机 Agent 的一句话

> 请按 https://github.com/blue126/workspace-onboarding 的指引，从“网盘链接”下载本设备接入包并完成 bootstrap；需要登录或系统授权时交给我。

注：把“网盘链接”换成你邮件中收到的 Temp.sh 下载链接即可。请使用具备本机文件和终端操作能力的 Agent；个人登录、验证码和系统授权由本人操作。

重跑时获取远端 main 的最新代码；已有干净仓库用 `git pull --ff-only` 更新，保留任何本地修改。同一设备继续使用原接入包，不重新生成身份；设备换机时再申请独立接入包。

## Agent 执行顺序

1. 阅读本项目 README.md、AGENTS.md，获取公开源码到下表指定的源码目录；已有同名目录时先核对来源，不覆盖本地工作。
2. 按 [设备包下载](docs/download.md)，对员工提供的 Temp.sh 链接发送 HTTP POST 下载外层 ZIP；无需网盘账号或浏览器，不能用普通 GET 页面代替下载。失败停止，请管理员核对链接，不反复重试。
3. 校验管理员通知中的外层 SHA256，确认外层恰好是三个顶层普通文件；创建下方默认接收目录。只保存本次交付，不覆盖已有不同身份。
4. 仅解开外层 ZIP，把 `device-bundle.zip`、`device-bundle.sha256`、`README.md` 放入默认接收目录；保留内层 `device-bundle.zip`，不要自行展开密钥。
5. 按 [标准验证](docs/verification.md) 运行 check → setup → verify；连接通过且个人授权待处理时，再 connect 进入 VM，用 workspace-login 交本人完成登录。

## 默认目录

所有日常文件都放在当前用户可见、可写的目录，源码与设备凭据分开：

| 系统 | 项目源码 | 下载的三个设备文件 | 运行配置与密钥 |
| --- | --- | --- | --- |
| macOS | `~/EmployeeWorkspace/onboarding/` | `~/Downloads/employee-workspace/` | `~/EmployeeWorkspace/devices/<device_id>/` |
| Linux | `~/EmployeeWorkspace/onboarding/` | `~/Downloads/employee-workspace/` | `~/EmployeeWorkspace/devices/<device_id>/` |
| Windows | `%USERPROFILE%\EmployeeWorkspace\onboarding\` | `%USERPROFILE%\Downloads\employee-workspace\` | `%USERPROFILE%\EmployeeWorkspace\devices\<device_id>\` |

Agent 先创建源码目录的父目录，再将仓库 clone 到 `onboarding/`，后续命令从该源码目录执行。下载接入包不依赖源码是否已下载。运行目录由 setup 创建；目录可见，凭据仍限制为本人读取。

目录中应有固定文件名：

```text
employee-workspace/
  device-bundle.zip
  device-bundle.sha256
  README.md
```

找不到首选目录中的设备文件时，Agent 可在取得源码后提示员工把三份文件放入项目的 `deployment/` 后继续。该目录是后备位置，私密内容被 Git 忽略。首选目录已有部分文件或校验失败时，先解决该目录的问题，不静默改用后备身份。

旧版已配置的设备不会自动移动或删除原文件。继续使用旧目录时，在每次命令后显式传 `--state-root "原运行目录"`（Windows 使用 `-StateRoot "原运行目录"`）。迁移时先由本人选择；不要直接移动目录，因为 SSH 配置和 Windows 隧道服务可能引用原绝对路径。

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

VPN 使用 CLI：macOS 为 Homebrew wireguard-tools，Linux 为 wg-quick，Windows 为官方 wireguard.exe 隧道服务。员工 Agent 负责环境检测、依赖安装、配置和启停，参考对应平台指引；无需员工手工导入 App。

本人只处理 sudo/UAC 和个人 Claude 授权。已有旧隧道发生冲突时，先确认再处理，不自动关闭其他 VPN。CONFIGURED 不等于连接验收通过，仍需 verify。

## Mosh 终端试用

收到管理员的 Mosh 试用参数后，让本机 Agent 按 [Mosh 安装、连接与验证](docs/mosh.md) 完成设置。先识别当前设备账号，复用现有接入配置；按实际系统安装客户端，再使用该设备分配的端口连接。终端试用以打字响应和断线恢复为主，Claude 登录可跳过。复制给 Agent 的提示词必须包含实际下载链接（需要补包时）、Mosh 服务端命令和该设备端口，不能只写“参考邮件”。

## VM 内的 Claude 与浏览器

先通过 SSH 进入 VM，依次运行 `workspace-browser start`、`workspace-login`；浏览器就绪后再打开 noVNC，在 VM 的 Firefox 内完成个人授权。交接时按 [验证后的必含信息](docs/after-verify.md) 提醒员工；日常浏览器使用 `workspace-browser start/status/stop`。

脚本分别报告包、设备身份、VM、SSH/SFTP 和 Claude 状态；未完成的个人授权和真实项目任务保留待处理，不把命令退出 0 当作全部验收通过。

## 详细说明

- [Agent 约定](AGENTS.md)
- [Windows](docs/manual-windows.md)
- [macOS](docs/manual-macos.md)
- [Ubuntu/Debian](docs/manual-linux.md)
- [Mosh：客户端安装、连接与终端试用](docs/mosh.md)
- [标准验证：固定命令与预期结果](docs/verification.md)
- [验证后的必含信息](docs/after-verify.md)
- [系统授权](docs/system-authorization.md)
- [故障处理](docs/troubleshooting.md)
- [设备包下载](docs/download.md)
- [设备文件交付约定](docs/administrator.md)

每台电脑使用独立身份，包括同一员工的多台电脑。私密共享链接、设备包和连接单不得写入公开仓库、Issue 或日志。删除文件不等于撤销服务端设备身份。

OCI Hub v2 设备包显式声明 `profile=oci-hub`，使用独立 `devices/oci-hub/<device_id>` 状态、`wh-` 隧道和 `oci-hub-<device_id>` SSH alias。目标为本人 VM 的 `employee` native SSH；员工 WireGuard 使用 51824/15 秒。严格核对目标 SSH host pin 与 HTTPS 证书 SHA256；v1 原入口继续可用。未知版本、profile 或字段均拒绝。细节见 [OCI Hub 接入](docs/oci-hub.md)。
