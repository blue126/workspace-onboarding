# RemoteCC 工作区接入

本页写给员工电脑上的 AI 助手（Claude Code、Codex、Cursor 等能操作本机文件和终端的 Agent）。员工从交付邮件复制给你的话是：

> 请阅读 https://github.com/blue126/workspace-onboarding 的 README.md，帮我完成 RemoteCC 工作区接入。

本页给出每一步的需求、验收标准和常见问题，具体怎么执行由你根据员工的系统决定；细节见文末 [资料目录](#资料目录)。只有标出的命令需要原样使用。

**支持范围：** 只支持统一格式的 OCI Hub 设备包（v2、`profile=oci-hub`、`access_mode=mosh`，并带 VM 浏览器入口 `desktop_url` 与证书 pin），VM 主机名总是 `oci-hub-<员工ID>`。系统：macOS 12+、Ubuntu 22.04+/Debian 12+、Windows 10/11（在 WSL 里运行的 Agent 也按 Windows 处理）。其他情况停止并告诉员工。

## 规则

1. **失败即停。** bootstrap 的 check/setup/verify 每次输出一行 JSON，以其中的 `code` 判断，不以退出码判断；外层 ZIP 检查只看最后一行 `READY`/`STOP`；`connect`、`mosh` 等交互入口不输出 JSON。出错就停下，把命令、系统和 `code` 告诉员工，按 [故障处理](docs/troubleshooting.md) 处理；不改条件、不反复重试、不绕过。
2. **员工只做下表的事，每次先说明原因。** 其余都由你完成。
3. **不收集秘密。** 设备包由员工本人在 https://cc.willfan.me/me 下载；你不代为登录，不索取验证码、密码、Cookie 或令牌。sudo 密码和 UAC 由员工在自己的终端或弹窗里输入，见 [系统授权](docs/system-authorization.md)。
4. **私钥不出现在任何输出里。** 不打开内层设备包，不打印、上传或转发密钥，不执行包内文件；提醒员工妥善保管设备包。
5. **不动别人的东西。** 不覆盖或复用接收目录里已有的设备文件，不停止其他 VPN；冲突先问员工。
6. **Claude 只在 VM 里登录。** 员工在 VM 内运行 `workspace-login`，在 VM 的浏览器（本机浏览器经 VPN 打开 `workspace-login` 显示的地址看到的 VM 桌面）里完成；不在本机登录，不用本机浏览器打开授权链接或登录邮件里的链接。

## 需要员工亲自做的

| 员工要做的事 | 你向员工说明的原因 |
| --- | --- |
| 登录 https://cc.willfan.me/me ，点击「下载设备接入包」 | 登录验证码只发到你的邮箱，设备包里有你专属的私钥。登录后可随时重新下载；页面显示没有设备包时，请发邮件到 hello@willfan.me 重新发送。 |
| macOS / Linux：在终端输入 sudo 密码 | 安装 VPN、Mosh 等软件并启用隧道要改系统网络设置；密码只在你自己的终端里输入，通常一次即可。 |
| Windows：在 UAC 弹窗点「是」 | 安装 WireGuard 隧道服务需要管理员权限；setup 和 verify 在同一个管理员窗口里运行，只需确认一次。 |
| 条件：安装缺少的 Git / python3 / unzip / Homebrew | 用来下载本项目、检查和解开设备包、安装客户端；安装需要你确认或输入密码。见 [系统授权](docs/system-authorization.md#会装什么为什么)。 |
| 条件，Windows：WSL 里输入 Linux 密码装 Mosh，或安装 MobaXterm | Windows 没有原生 Mosh 客户端。见 [Mosh 登录](docs/mosh.md#windows)。 |
| 最后：在自己的终端运行 `mosh <员工ID>-vm` | 这是你和工作区的交互会话，只能在你自己的终端里打开。 |
| 登录 Claude：VM 里运行 `workspace-login`，在本机浏览器打开它显示的地址（VM 桌面），在画面里的 VM 浏览器完成登录 | Claude 账号是你自己的，登录状态只留在你的 VM 里。浏览器的证书提示是正常的，证书已由我在 verify 中核对过。 |

## 第 1 步：取得源码

- **需求：** 把 `https://github.com/blue126/workspace-onboarding.git` clone 到 `~/EmployeeWorkspace/onboarding`（Windows：`%USERPROFILE%\EmployeeWorkspace\onboarding`），之后的命令都在这个目录运行。
- **验收：** `git remote get-url origin` 是上面的地址，工作树是远端 `main` 的最新版本。
- **可能遇到的问题：** 目录已存在 → 来源正确且没有本地修改就 `git pull --ff-only`，否则停下问员工。没有 Git → 见上表。

## 第 2 步：设备包

- **需求：** 员工下载后，你在下载目录找到最近一天内的 `device-bundle*.zip`（外层 ZIP），检查通过后只把它的三个文件解开到接收目录：macOS/Linux `~/Downloads/employee-workspace/`，Windows `%USERPROFILE%\Downloads\employee-workspace\`。
- **检查（原样运行）：** macOS / Linux 在源码目录运行 `python3 -I scripts/check-outer-zip.py "<外层ZIP>" "$HOME/Downloads/employee-workspace"`；Windows 用 [设备包下载](docs/download.md#校验与解开) 里的 PowerShell 检查。
- **验收：** 检查结果为 `READY`；解开后接收目录里有 `device-bundle.zip`、`device-bundle.sha256`、`README.md`（目录里原有的其他文件保留）。内层包的完整性由第 3 步的 bootstrap 用 `device-bundle.sha256` 核对。
- **可能遇到的问题：**
  - 外层 ZIP 和内层包同名 `device-bundle.zip`：外层留在下载目录，别放进接收目录。
  - 找不到或找到多个 → 问员工是哪个文件；macOS 无权读“下载”文件夹 → 请员工在隐私弹窗中允许。
  - `STOP: already in …` → 上一次的设备文件还在接收目录。告诉员工后按 [移走上一次的设备文件](docs/download.md#校验与解开) 移到 `_archive-<时间>/`，再重新检查；不覆盖、不删除。其他 `STOP` → 停止，请员工联系管理员。

## 第 3 步：check → setup → verify

原样使用这些入口，在源码目录运行：

| 动作 | macOS / Linux | Windows（setup、verify 在管理员 PowerShell 中） |
| --- | --- | --- |
| 检查 | `bash ./bootstrap.sh check` | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 check` |
| 安装配置 | `bash ./bootstrap.sh setup --install-clients` | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 setup -InstallClients` |
| 验证 | `bash ./bootstrap.sh verify` | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 verify` |

- **验收：** check → `CHECKED`（新电脑上 `DEPENDENCY_MISSING` 属正常，继续 setup；`REISSUE_READY` 表示本机装过这台设备的旧包，setup 会自动停掉旧隧道、把旧配置归档到 `devices/oci-hub/.archive/`，继续即可）；setup → `CONFIGURED`；verify → `CLAUDE_AUTH_USER_PENDING`（连接已通过，Claude 待登录）或 `CONNECTION_VERIFIED`。结果码含义见 [标准验证](docs/verification.md)。
- **Windows 管理员窗口（原样）：** `Start-Process powershell -Verb RunAs -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-Command',"Set-Location '$env:USERPROFILE\EmployeeWorkspace\onboarding'"`
- **可能遇到的问题：**
  - `NEEDS_ADMIN` → 需要员工在可输入的终端或管理员窗口里授权，按 [系统授权](docs/system-authorization.md)；你的工具拒绝提权时，把整条命令交给员工自己运行。
  - `HOMEBREW_REQUIRED` → 请员工安装 Homebrew 后重跑 setup。
  - `MANIFEST_UNSUPPORTED` → 旧版、只有终端或只有桌面的设备包，请员工联系管理员换发。
  - `TLS_PIN_FAILED`（verify）→ VM 浏览器入口的证书与设备包不符；停止，不要打开或信任该地址，请员工联系管理员。
  - `SSH_CONFIG_UNSAFE` → 隧道已配好，但 `~/.ssh/config` 不能安全写入，登录别名不可用；请员工决定，登录改用下面的备选。
  - 其他 `code` → [故障处理](docs/troubleshooting.md)。

## 第 4 步：交接登录方式

- **需求：** 从 setup 或 verify 输出的 JSON 读取 `device_id` 和 `vm_hostname`（不含密钥），不要去目录里猜。`vm_hostname` 是 `oci-hub-alice` 时员工 ID 是 `alice`，登录命令是 `mosh alice-vm`。
- **macOS / Linux：** setup 已创建 `<员工ID>-vm` 别名（[如何确认](docs/mosh.md#macos--linux员工id-vm)）。请员工在自己的终端运行 `mosh <员工ID>-vm`；别名不可用时用源码目录的 `bash ./bootstrap.sh mosh`。
- **Windows：** 隧道由原生 WireGuard 承载，PowerShell 里 `ssh <员工ID>-vm` 可用。Mosh 先检查 `wsl.exe -l -q`：有发行版用 WSL，没有就用 MobaXterm，都不行用原生 SSH，步骤见 [Mosh 登录 · Windows](docs/mosh.md#windows)。
- **验收：** 员工登录后在 VM 里运行 `hostname`，输出 `oci-hub-<员工ID>`。
- **最后提醒员工：** 不要向任何人发送密码、验证码、私钥或接入配置，不要共用设备包。

## 第 5 步：在 VM 浏览器里登录 Claude

- **需求：** 员工在 `mosh <员工ID>-vm` 会话里运行 `workspace-login`，它在 VM 里启动图形 Firefox，并显示 VM 桌面的地址；员工在**本机**浏览器打开**这个地址**（只能经 VPN 访问），在画面里的 VM Firefox 完成 Claude 登录；页面给出授权码时回 mosh 终端粘贴。你不要自己把地址交给员工：它与 verify 输出的 `desktop_url` 相同，`desktop_url` 只供你检查。
- **登录方式：** 用 Google 或 Apple 账号的，直接在 VM Firefox 里完成。用邮箱的，Anthropic 会发一封登录邮件：请员工**不要点击**邮件里的「Sign In」按钮（会在本机浏览器登录），而是右键复制链接地址，粘贴到 VM Firefox 的地址栏打开；无法直接粘贴时，先在 VM Firefox 地址栏点一下，再用同一网页里的「需要粘贴文本到远程浏览器？」粘贴。
- **画面后端：** `desktop_url` 背后是 noVNC + Firefox（尚未升级的 VM），或 KasmVNC 桌面（已升级和新开户的 VM）。两者流程相同，也都不要求输入 VNC 或网页密码（只靠 VPN 和证书 pin 保护）；出现密码框就停止并联系管理员。
- **为什么：** Claude 登录必须在 VM 里完成，账号凭据不落到本机；该地址只在 VPN 内可达，证书是这台 VM 自签的，浏览器会提示"不安全"。
- **证书（由你核对，不交给员工）：** 只有 verify 输出 `desktop_tls=passed` 才让员工继续：这表示 verify 已用设备包里的 pin 核对过该地址的证书。此时告诉员工浏览器的证书提示是正常的，可以继续访问；不要请员工查看或比对指纹。`desktop_tls` 不是 `passed` 或出现 `TLS_PIN_FAILED` 时停止，请员工联系管理员，不要让员工打开该地址。
- **验收：** 员工再运行一次 verify，结果 `CONNECTION_VERIFIED`（`claude_auth=passed`）。
- **可能遇到的问题：** 页面打不开 → VPN 未连接，重跑 setup；画面空白或提示桌面未启动 → 先在 mosh 里运行 `workspace-login`，再刷新；不要在本机浏览器直接打开 Claude 授权链接。
- **完成后告诉员工：** 除了 mosh，还可以用浏览器打开 https://hapi.willfan.me （用申请邮箱的验证码登录，电脑和手机都可以）查看和继续 VM 上的 Claude Code 会话。这是同一台 VM 的网页入口，已经配置好，你不用做任何设置，也不要改动 VM 上和 HAPI 有关的配置。

## 资料目录

| 文档 | 什么时候读 |
| --- | --- |
| [docs/download.md](docs/download.md) | 下载入口、两层 ZIP 的结构、检查规则、Windows 检查与解开 |
| [docs/system-authorization.md](docs/system-authorization.md) | sudo、UAC、macOS 授权；会装哪些软件、为什么 |
| [docs/verification.md](docs/verification.md) | check/setup/verify 的结果码与验收字段（含 `desktop_tls`） |
| [docs/troubleshooting.md](docs/troubleshooting.md) | 任何非成功的 `code` |
| [docs/mosh.md](docs/mosh.md) | 别名细节；Windows 的 WSL、MobaXterm、原生 SSH |
| [docs/administrator.md](docs/administrator.md) | 管理员侧的设备包格式与交付约定 |

迁移或更新通知要求换新包时，按本页重新下载并运行 check → setup → verify，不复用旧包。旧运行目录用 `--state-root "原目录"`（Windows `-StateRoot`）继续使用。其他入口：`bootstrap.sh connect`（SSH 进入 VM）、`sftp`、`disconnect`（断开 VPN），Windows 用 `bootstrap.ps1` 的同名动作。
