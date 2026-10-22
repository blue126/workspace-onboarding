# Ubuntu / Debian

使用管理员发放的完整员工接入 ZIP；单独下载的公开源码不含设备身份。首版支持 Ubuntu 22.04+、Debian 12+，要求 Bash、sudo 和可用的官方软件源。

```bash
bash ./bootstrap.sh check
bash ./bootstrap.sh setup --install-clients
bash ./bootstrap.sh verify
bash ./bootstrap.sh connect
```

setup 会安装缺少的 WireGuard tools、OpenSSH、jq、unzip、iproute2，将包内身份导入本人私有目录，再用该目录内生成的 wg-quick 配置启用。sudo 认证交给本人，不以 root 身份运行整个脚本。只准备文件不激活可用 setup --no-activate。

脚本仅添加工作入口的 /32 路由，不改 DNS 或默认路由。既有 VPN／路由冲突会停止并报告，不覆盖。同名隧道需同时匹配设备公钥、服务端公钥、AllowedIPs 和本机地址才能视为已配置或停用。

进入 VM 后继续使用 workspace-login、workspace-browser。文件传输用 `bash ./bootstrap.sh sftp`。结束接入时运行 `bash ./bootstrap.sh disconnect`，只关闭归属匹配的本设备隧道，保留所有已安装配置。
