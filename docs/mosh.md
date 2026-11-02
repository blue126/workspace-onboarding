# Mosh 登录

Mosh 用于交互终端，打字响应更快，短暂断网后会话可以恢复；文件传输继续使用仓库的 SFTP 入口。本机需要保持 WireGuard 开启。

## macOS / Linux：`<员工ID>-vm`

`bash ./bootstrap.sh setup --install-clients` 会安装缺少的 Mosh 客户端（macOS 用 Homebrew，Ubuntu/Debian 用 apt）。

只支持终端模式的 OCI Hub 设备包，VM 主机名总是 `oci-hub-<员工ID>`。setup 会为本设备 SSH 配置增加 `<员工ID>-vm` 别名，并在 `~/.ssh/config` 第一行加入 `Include "<本设备 ssh_config 绝对路径>"`，使系统自带的 `ssh`/`mosh` 直接读取本设备配置（主机校验仍然严格）。`~/.ssh` 不存在时以 700 创建，`~/.ssh/config` 不存在时以 600 创建；已有相同 Include 行时只保留一行并移到第一行，其他内容不改动。Include 在 setup 最后一步写入；`~/.ssh` 不可写，或 `~/.ssh/config` 为符号链接、硬链接或不可写时返回 `SSH_CONFIG_UNSAFE`，`~/.ssh` 不被改动（隧道与本设备配置已完成），请本人决定如何处理。之后在本人交互终端直接运行：

```bash
mosh <员工ID>-vm
ssh <员工ID>-vm
```

**确认别名生效：** 员工 ID 取自 setup/verify 输出 JSON 的 `vm_hostname`（`oci-hub-<员工ID>`），例如 `employee='alice'; vm_alias="${employee}-vm"; ssh -G "$vm_alias" | grep -E '^(hostname|user) '`。`hostname` 应是 manifest 里的 `ssh_gateway`（VM 在 VPN 内的连接地址），`user` 应是 `employee`；未定义的别名会原样回显为 hostname。登录后在 VM 里运行 `hostname`，应为 `oci-hub-<员工ID>`。

已用 1.0.0 完成 setup 的设备，更新源码后对同一设备包重跑 setup 即原地升级本设备 `ssh_config` 并加入 Include，无需新设备包。

备选：从本机源码目录运行 `bash ./bootstrap.sh mosh`（SSH 用 `bash ./bootstrap.sh connect`）。它用 `ssh -F <本设备 ssh_config>` 连接 alias，保持严格主机校验；VM 运行原生 mosh-server，开放默认 UDP 60000–61000，不需要指定服务端命令或端口。出现 `MOSH_CLIENT_MISSING` 时重跑 `setup --install-clients`；出现 `INTERACTIVE_TERMINAL_REQUIRED` 时，打开本人的交互终端运行同一命令，不通过管道驱动 Mosh 或记录握手输出。

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
