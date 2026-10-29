# macOS

1. 把 README 中的一句话提示词和邮件里的本人 Temp.sh 链接交给本机 Agent。
2. Agent 从公开 GitHub 取得项目，按 [设备包下载](download.md) 用 HTTP POST 下载，核对外层 SHA256 后仅解开外层 ZIP，得到三份设备文件。无需网盘账号；链接过期时联系管理员。
3. 首选保存位置：`~/Downloads/employee-workspace/`。文件名必须为 device-bundle.zip、device-bundle.sha256、README.md。
4. 首选目录没有设备文件时，Agent 可提示你把文件放在已下载项目的 deployment/；首选文件校验失败时不能改用另一份身份。
5. Agent 按项目 README 执行 check、setup、verify、connect；使用 CLI 自动安装、生成配置并启用隧道，不需要 App 导入。由 Agent 创建交互终端并执行配置，本人只输入 sudo 密码，按 [系统授权](system-authorization.md) 继续。
6. 先通过 SSH 进入 VM，依次运行 workspace-browser start、workspace-login；浏览器就绪后再打开 noVNC，在 VM Firefox 中由本人完成 Claude 授权。日常使用 workspace-browser start/status/stop，文件传输用 sftp。

项目源码：`~/EmployeeWorkspace/onboarding/`。setup 的运行配置默认在 `~/EmployeeWorkspace/devices/<device_id>/`，可以从个人主目录直接找到。已有旧配置保留，参见 README 的旧目录说明。

## CLI 接入

由员工本机 Agent 检测环境、安装依赖并运行：

```bash
bash ./bootstrap.sh setup --install-clients
```

使用 Homebrew 的 `wireguard-tools`，其依赖包含 `wireguard-go` 和新版 Bash。缺少 Homebrew 时，由 Agent 参考[官方指引](https://brew.sh/)安装后继续，无需员工自行配置 VPN。

macOS 系统自带 Bash 3.2，不能用于运行 `wg-quick`。bootstrap 会单独选择 Bash 4+，在 sudo 之后显式设置工具 PATH 和 `wireguard-go` 绝对路径，不依赖登录 shell、`brew shellenv` 或 sudo 保留用户环境。`check` 会执行版本与只读帮助检查；通过只表示客户端可执行，不代表已获系统授权或隧道已连通。

若旧版出现 `Version mismatch: bash 3 detected`，先保留设备包和已有配置，更新公开项目后重跑原 setup 命令；不要重新开户、轮换密钥或修改其他 VPN。不要直接执行 `sudo wg-quick` 绕过项目入口。

系统授权由本人完成；不要收集密码。已有同设备 App 隧道时，先由本人确认停用，再启用 CLI，避免重复地址。不修改其他 VPN。

启用使用 `setup`，断开使用 `disconnect`。实现参考：[WireGuard CLI](https://www.wireguard.com/install/)、[Homebrew 软件包](https://formulae.brew.sh/formula/wireguard-tools)。

## Mosh 终端试用

已获管理员开通的设备按 [Mosh 客户端安装、连接与验证](mosh.md) 操作。Agent 负责安装和配置，系统授权由本人确认；端口取自当前设备的管理员通知。终端试用无需登录 Claude。
