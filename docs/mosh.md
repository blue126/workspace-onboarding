# Mosh 终端试用：员工本机 Agent 指引

本次目标是体验打字、退格、Ctrl-C 和短暂断网后的恢复。**无需登录 Claude 即可完成终端试用。** Mosh 用于交互终端，文件传输继续使用仓库的 SFTP 入口。

## 1. 确认接入和设备身份

先按 README 检查已有设备包与已安装配置。同一设备复用原身份；原 ZIP 已删除但已安装配置完整时，不必重做 setup。缺少必要文件时，从员工提示词提供的私人下载链接按 [下载指引](download.md) 恢复；缺少链接或链接失效时请管理员补发，不重新开户或生成密钥。

保持本设备 WireGuard 开启，先完成 [标准连接验证](verification.md)。Claude 待登录不阻止终端试用；网络、身份、VM 或 SFTP 验证失败时先报告失败。

从当前设备实际使用的 `ssh_config` 读取 `workspace` 的有效 `User` 和 `HostName`；默认配置在 `~/EmployeeWorkspace/devices/<device_id>/ssh_config`，旧路径沿用现有配置。不要通过员工姓名猜设备账号，不扫描其他人的配置，不打印私钥。

管理员必须在员工复制给 Agent 的提示词中提供 Mosh 服务端命令及本设备端口范围。**Agent 看不到员工的邮件：不得要求它参考邮件正文、附件说明或“下表”。** 同一人使用多份设备身份时，每份身份的端口可能不同。没有匹配参数就停止并索取，不套用其他设备端口。真实员工账号、下载链接和端口分配不写入公开仓库。

## 2. 安装本机客户端

Agent 负责检查和执行安装，系统提权、密码及重启由本人确认。未获得软件安装授权时先取得授权；已明确允许安装本次必要客户端时不重复询问。已有可用 Mosh 时跳过安装。

| 当前连接环境 | 检查与安装 |
| --- | --- |
| macOS | 检查 `mosh --version`；缺失时执行 `brew install mosh`。Homebrew 缺失时按其官方指引引导用户授权安装，并确认 PATH 生效。 |
| Ubuntu / Debian | 检查 `mosh --version`；缺失时执行 `sudo apt-get update && sudo apt-get install -y mosh`。其他 Linux 使用其发行版包管理器。 |
| Windows | 在 PowerShell 用 `wsl --list --verbose` 检查 WSL；没有可用 Ubuntu 时，引导用户在管理员 PowerShell 执行 `wsl --install -d Ubuntu`，按要求重启并完成首次 Linux 用户设置。在 WSL Ubuntu 中执行上述 apt 安装命令；之后从该 Ubuntu 终端运行 Mosh。 |

在实际运行 Mosh 的 macOS、Linux 或 WSL 环境检查：

```bash
mosh --version
command -v mosh-client
```

预期：两条命令退出 0，分别显示版本和可执行文件路径。失败时停止，不把“已下载”当成“已安装”。

Windows 继续使用原生 WireGuard 隧道；不要在 WSL 重复执行 VPN setup。先确认 WSL 内也能连接网关 SSH。按当前设备身份把 SSH 配置、私钥和 known_hosts 适配到 WSL 用户自己的 Linux 目录，私钥权限 `600`，修正配置中的绝对路径；保留主机校验，不使用权限过宽的 `/mnt/c` 私钥。只处理这一份明确指定的设备配置。WSL 的实际 SSH/UDP 路径必须验证，安装成功不等于连接成功。

## 3. 连接本人 VM

下面是 Agent 的命令模板。把变量替换为本机实际路径和管理员给该设备分配的范围；交给用户时不得留下占位符。

```bash
ssh_config='/absolute/path/to/this-device/ssh_config'
mosh_ports='START:END'

# 只查看生效的账号与网关，不读取私钥内容。
ssh -G -F "$ssh_config" workspace | awk '$1 == "user" || $1 == "hostname"'

# 预期退出 0，输出 Mosh 服务端版本。仅测试已批准的启动命令。
ssh -F "$ssh_config" -T workspace employee-mosh --version

# 在交互终端运行，不附加任意远端命令。
mosh --ssh="ssh -F \"$ssh_config\"" \
  --server=employee-mosh --port="$mosh_ports" workspace
```

`employee-mosh` 是网关识别的受限启动命令；它固定进入此设备绑定的 VM。不要在员工 VM 内寻找或安装这个同名文件，不修改服务端策略。保留现有 SSH 密钥和严格主机校验；使用已分配的完整端口范围。

沿用 Mosh 默认的 IP 发现方式。不要添加远端 `sh -c` 探测、ProxyJump、服务器端口转发或自制 ssh 垫片；出现 `Access denied.` 时停止，记录脱敏后的账号、请求的端口范围和错误文字交给管理员。握手中的会话密钥不得写入报告或聊天。

## 4. 固定验证与交接

| 检查 | 标准动作 | 预期结果 |
| --- | --- | --- |
| 安装 | 上述版本与路径命令 | 退出 0，客户端可用。 |
| 服务端启动入口 | 上述 `employee-mosh --version` | 退出 0，显示版本；无 Access denied。 |
| Mosh 会话 | 上述交互命令；进入后运行 `whoami`、`hostname` | 用户为 `employee`，主机名与设备包分配的 VM 一致。 |
| 操作体验 | 本人对比同网络下 SSH / Mosh 的打字、退格和 Ctrl-C | 本人反馈流畅程度与异常；Agent 不代填体验结论。 |
| 恢复 | 保存工作后，本人短暂断网并恢复网络，保持同一 Mosh 客户端窗口 | 网络和 WireGuard 恢复后会话继续；记录实际恢复结果。 |

退出远端 shell 用 `exit`；紧急退出 Mosh 可按 `Ctrl-^`（通常为 Ctrl+Shift+6），松开后按 `.`。主动退出客户端后再次运行启动命令会建立新会话，不保证恢复已退出的 shell。

Agent 验证后生成本设备可重复使用的启动脚本或快捷命令，写清在哪个本机终端运行，并提供 SSH 回退入口。报告安装、连接、目标 VM 和本人体验各自的实际结果；Claude 登录和浏览器体验为可选后续任务，不主动打开登录流程。

参考：[Mosh 安装与使用](https://mosh.org/)、[Homebrew mosh](https://formulae.brew.sh/formula/mosh)、[微软 WSL 安装](https://learn.microsoft.com/en-us/windows/wsl/install)。
