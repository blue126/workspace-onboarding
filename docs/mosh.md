# Mosh 登录

Mosh 用于交互终端，打字响应更快，短暂断网后会话可以恢复；文件传输继续使用仓库的 SFTP 入口。本机需要保持 WireGuard 开启。macOS/Linux 的隧道由 setup 用 `wg-quick up` 启动，**重启电脑后不会自动恢复**，见下面的[重启之后](#重启之后)。

## macOS / Linux：`<员工ID>-vm`

`bash ./bootstrap.sh setup --install-clients` 会安装缺少的 Mosh 客户端（macOS 用 Homebrew，Ubuntu/Debian 用 apt）。

只支持终端模式的 OCI Hub 设备包，VM 主机名总是 `oci-hub-<员工ID>`。setup 会为本设备 SSH 配置增加 `<员工ID>-vm` 别名，并在 `~/.ssh/config` 第一行加入 `Include "<本设备 ssh_config 绝对路径>"`，使系统自带的 `ssh`/`mosh` 直接读取本设备配置（主机校验仍然严格）。`~/.ssh` 不存在时以 700 创建，`~/.ssh/config` 不存在时以 600 创建；已有相同 Include 行时只保留一行并移到第一行，其他内容不改动。Include 在 setup 最后一步写入；`~/.ssh` 不可写，或 `~/.ssh/config` 为符号链接、硬链接或不可写时返回 `SSH_CONFIG_UNSAFE`，`~/.ssh` 不被改动（隧道与本设备配置已完成），请本人决定如何处理。之后在本人交互终端直接运行：

```bash
mosh <员工ID>-vm
ssh <员工ID>-vm
```

**确认别名生效：** 员工 ID 取自 setup/verify 输出 JSON 的 `vm_hostname`（`oci-hub-<员工ID>`），例如 `employee='alice'; vm_alias="${employee}-vm"; ssh -G "$vm_alias" | grep -E '^(hostname|user) '`。`hostname` 应是 manifest 里的 `ssh_gateway`（VM 在 VPN 内的连接地址），`user` 应是 `employee`；未定义的别名会原样回显为 hostname。登录后在 VM 里运行 `hostname`，应为 `oci-hub-<员工ID>`。

已用 1.0.0 或 1.3.0 完成 setup 的设备，更新源码后对同一设备包重跑 setup 即原地升级本设备 `ssh_config`（1.0.0 同时加入 Include），无需新设备包，不会报 `CONFIG_CONFLICT`。升级前 check、verify、connect、mosh 继续使用旧文件；本人改动过的 `ssh_config` 仍按 `CONFIG_CONFLICT` 处理，不会被覆盖。

备选：从本机源码目录运行 `bash ./bootstrap.sh mosh`（SSH 用 `bash ./bootstrap.sh connect`）。它用 `ssh -F <本设备 ssh_config>` 连接 alias，保持严格主机校验；VM 运行原生 mosh-server，开放默认 UDP 60000–61000，不需要指定服务端命令或端口。`connect`、`sftp`、`mosh` 连接前先检查本设备隧道（不需要 sudo），隧道没起来时报 `TUNNEL_DOWN` 并给出恢复命令，而不是让 Mosh 报出误导性的连接错误。出现 `MOSH_CLIENT_MISSING` 时重跑 `setup --install-clients`；出现 `INTERACTIVE_TERMINAL_REQUIRED` 时，打开本人的交互终端运行同一命令，不通过管道驱动 Mosh 或记录握手输出。

### 重启之后

setup 不安装开机自启项（不写 LaunchDaemon/systemd 单元），以免开机时绕过路由与隧道归属检查、影响员工的其他 VPN。重启后：

1. 运行 `bash ./bootstrap.sh connect` 或 `bash ./bootstrap.sh mosh`；隧道未运行时得到 `TUNNEL_DOWN`，脚本没有做任何改动。
2. 本人在交互终端运行 `bash ./bootstrap.sh setup`（曾用 `--bundle`/`--sha256`/`--state-root` 时带同样参数），输入本人 sudo 密码，得到 `CONFIGURED`。
3. 再运行 `mosh <员工ID>-vm` 或 `bash ./bootstrap.sh mosh`。

系统自带的 `mosh <员工ID>-vm`/`ssh <员工ID>-vm` 不经过 bootstrap，隧道未运行时只会超时；遇到时按上面第 1 步确认。需要断开时仍用 `bash ./bootstrap.sh disconnect`，它只停止属于本设备的隧道。

### 字符集（locale）

macOS 终端默认导出 `LC_CTYPE=UTF-8`。这个名字在 Linux 上不存在：系统 SSH 通过 `SendEnv LC_*` 把它带到 VM，Mosh 也把本机的 `LANG`/`LC_*` 交给 mosh-server，结果 mosh-server 报 `needs a UTF-8 native locale` 后退出。客户端兜底如下，VM 上只有 `C.UTF-8` 也能用：

- 本设备 `ssh_config` 带 `SetEnv LANG=C.UTF-8 LC_ALL=C.UTF-8`。OpenSSH 在 `SendEnv` 之后发送 `SetEnv`，VM 的 sshd 接受这些变量时（Ubuntu 默认 `AcceptEnv LANG LC_*`）收到的是 `C.UTF-8`，mosh-server 用它启动，不再采用本机传来的值；对 `ssh`/`mosh <员工ID>-vm` 和 bootstrap 入口都生效。
- `bash ./bootstrap.sh mosh` 启动前清除所有 `LC_*`/`LANGUAGE`，只设置 `LANG=C.UTF-8`。本机没有 `C.UTF-8` 时报 `LOCALE_UNAVAILABLE`，改用 `bash ./bootstrap.sh connect` 并告诉管理员。

已经装过的设备对同一设备包重跑 `bash ./bootstrap.sh setup` 即可升级。想在 VM 里用中文等其他 locale（需 VM 已生成该 locale），由本人在 VM 的 shell 配置里设置 `LC_ALL`，不要修改本机的系统 SSH 配置。

## Windows

VPN 永远由 Windows 原生 WireGuard 承载（`bootstrap.ps1 setup`），不在 WSL 里运行 setup。setup 之后，`%USERPROFILE%\.ssh\config` 第一行已 Include 本设备配置，PowerShell 里可直接 `ssh <员工ID>-vm`。Mosh 没有 Windows 原生客户端，按下面顺序选一种：

先检查 WSL（PowerShell）：

```powershell
wsl.exe -l -q
```

有输出（至少一个发行版名）且退出码为 0 → 用 [方式 A：WSL](#方式-awsl)；否则 → [方式 B：MobaXterm](#方式-bmobaxterm)。两种都不行时用 [方式 C](#方式-c原生-ssh)。

下面的 `<device_id>` 与 `<员工ID>` 取自 setup/verify 输出 JSON 的 `device_id` 和 `vm_hostname`（`oci-hub-<员工ID>`），由 Agent 替换后再运行。

### 方式 A：WSL

先向员工说明：WSL 是 Windows 里的 Linux 环境，Mosh 在其中运行；安装 Mosh 需要员工输入**WSL 里 Linux 用户的密码**（不是 Windows 密码），只在他自己的 WSL 终端输入。

在 WSL 终端运行（只复制这一台设备的文件，私钥权限 600）：

```bash
DEVICE='<device_id>'
WINHOME="$(wslpath "$(cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')")"
SRC="$WINHOME/EmployeeWorkspace/devices/oci-hub/$DEVICE"
DST="$HOME/.ssh/remotecc/$DEVICE"
if [ -e "$DST" ]; then
  echo "STOP: $DST already exists; ask the employee before replacing it"
else
  mkdir -p "$DST" && chmod 700 "$HOME/.ssh" "$HOME/.ssh/remotecc" "$DST"
  cp "$SRC/client-key" "$SRC/known_hosts" "$DST/" && chmod 600 "$DST/client-key" "$DST/known_hosts"
  sed -e "s#^\( *IdentityFile \).*#\1\"$DST/client-key\"#" \
      -e "s#^\( *UserKnownHostsFile \).*#\1\"$DST/known_hosts\"#" \
      -e 's#^\( *GlobalKnownHostsFile \).*#\1/dev/null#' \
      "$SRC/ssh_config" > "$DST/ssh_config" && chmod 600 "$DST/ssh_config"
fi
```

成功：`ssh -G -F "$DST/ssh_config" <员工ID>-vm | grep -E '^(hostname|user|identityfile) '` 显示 manifest 里的 `ssh_gateway`（VM 在 VPN 内的连接地址）、`employee` 和 `$DST/client-key`。登录后在 VM 里运行 `hostname`，应为 `oci-hub-<员工ID>`。

再把 Include 放到 WSL `~/.ssh/config` 第一行（已有相同行时不重复；该文件是符号链接时停止并询问员工）：

```bash
INC="Include \"$DST/ssh_config\""
if [ -L "$HOME/.ssh/config" ]; then
  echo 'STOP: ~/.ssh/config is a symlink; ask the employee'
else
  touch "$HOME/.ssh/config" && chmod 600 "$HOME/.ssh/config"
  if [ "$(head -n 1 "$HOME/.ssh/config")" != "$INC" ]; then
    { printf '%s\n' "$INC"; grep -vxF "$INC" "$HOME/.ssh/config"; } > "$HOME/.ssh/config.new" &&
      chmod 600 "$HOME/.ssh/config.new" && mv "$HOME/.ssh/config.new" "$HOME/.ssh/config"
  fi
fi
```

安装 Mosh（员工输入 WSL Linux 密码）：`sudo apt-get update && sudo apt-get install -y mosh`；成功：`mosh --version` 退出 0。之后员工在 WSL 终端运行 `mosh <员工ID>-vm`。

没有任何发行版、员工又愿意安装时：管理员 PowerShell 运行 `wsl --install -d Ubuntu`，按提示重启并创建 Linux 用户（只能由员工操作），然后回到本节。

### 方式 B：MobaXterm

先向员工说明：Windows 没有原生 Mosh，MobaXterm Home Edition 是免费的 Windows 终端，自带 Mosh。请员工从官方页面 https://mobaxterm.mobatek.net/download-home-edition.html 下载安装（Installer 或 Portable 均可）。

Agent 在 PowerShell 打印新建会话要填的值（只打印路径和公开信息，不打印密钥内容）：

```powershell
$state="$env:USERPROFILE\EmployeeWorkspace\devices\oci-hub\<device_id>"
Select-String -Path "$state\ssh_config" -Pattern '^\s*(Host|HostName|User|Port) '
"Private key: $state\client-key"
ssh-keygen.exe -lf "$state\known_hosts"
```

请员工在 MobaXterm 点 **Session → Mosh**，填写：

| 字段 | 值 |
| --- | --- |
| Remote host | 上面 `HostName` 的值（manifest 的 `ssh_gateway`，VM 在 VPN 内的连接地址） |
| Specify username | `employee` |
| Port | `22` |
| 私钥（Use private key） | 上面打印的 `client-key` 完整路径 |

首次连接 MobaXterm 会显示主机指纹：必须与上面 `ssh-keygen -lf` 打印的 `SHA256:…` 一致才接受，不一致就停止并联系管理员。

MobaXterm 连接不上时，不要改服务器或防火墙，改用方式 C，并把现象告诉管理员。

### 方式 C：原生 SSH

PowerShell 里直接运行 `ssh <员工ID>-vm`（setup 已加 Include）；没有 Mosh 的断线恢复，但可立即使用。setup 报 `SSH_CONFIG_UNSAFE` 时，改用源码目录的 `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 connect`。

## 确认登录正确

| 检查 | 动作 | 预期结果 |
| --- | --- | --- |
| 客户端 | `mosh --version`、`command -v mosh-client` | 退出 0，客户端可用。 |
| 目标 VM | 进入后运行 `whoami`、`hostname` | 用户为 `employee`，主机名与设备包的 VM 一致。 |

不要添加远端 `sh -c` 探测、ProxyJump、端口转发或自制 ssh 垫片；连接被拒绝时停止，把脱敏后的错误文字交给管理员。握手中的会话密钥不得写入报告或聊天。

退出远端 shell 用 `exit`；紧急退出 Mosh 可按 `Ctrl-^`（通常为 Ctrl+Shift+6），松开后按 `.`。

参考：[Mosh](https://mosh.org/)、[Homebrew mosh](https://formulae.brew.sh/formula/mosh)、[微软 WSL 安装](https://learn.microsoft.com/en-us/windows/wsl/install)。
