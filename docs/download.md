# 设备包下载

使用管理员通知中的 Temp.sh 链接和外层 SHA256。无需账号或浏览器；使用 HTTP POST，普通 GET 可能只得到 HTML 页面。

macOS / Linux 参考命令（在默认接收目录内执行）：

```bash
curl --fail --show-error --max-time 45 -X POST '实际下载链接' -o employee-delivery.zip
```

Windows 使用系统 curl.exe，避免 PowerShell 的 curl 别名：

```powershell
curl.exe --fail --show-error --max-time 45 -X POST "实际下载链接" -o employee-delivery.zip
```

预期：退出码 0，得到 ZIP。用系统哈希工具核对管理员通知中的外层 SHA256；缺少摘要时向管理员索取，不猜测。下载失败、返回 HTML、摘要不同或过期时停止，不反复重试。

外层应恰好包含三个顶层普通文件：device-bundle.zip、device-bundle.sha256、README.md。拒绝额外项、重复项、路径穿越、绝对路径或符号链接；只解开外层，保留内层 device-bundle.zip，不打印密钥。不要覆盖已有不同文件；同一设备已有相同文件可复用。

三份文件保存到 macOS/Linux `~/Downloads/employee-workspace/`，Windows `%USERPROFILE%\Downloads\employee-workspace\`，然后按标准验证执行 check → setup → verify。不要执行下载文件里的任何脚本。Temp.sh 标注保存三天，失效时请管理员重新交付同一设备包。
