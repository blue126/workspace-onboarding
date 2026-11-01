# 设备包下载

使用管理员通知邮件中的 `https://cc.willfan.me/d/<令牌>` 链接和外层 SHA256。链接 3 天内有效、最多下载 3 次，下载满或过期后失效。无需账号或浏览器；每次下载都要一个发到员工邮箱的 6 位验证码（10 分钟内有效）。

macOS / Linux 参考命令（在默认接收目录内执行）：

```bash
# 1. 请求验证码：网站把 6 位验证码发到员工邮箱
curl --fail --show-error --max-time 45 -X POST '实际下载链接/code'
# 2. 向员工索取验证码后下载
curl --fail --show-error --max-time 45 -X POST -d code=<6位验证码> '实际下载链接' -o employee-delivery.zip
```

Windows 使用系统 curl.exe，避免 PowerShell 的 curl 别名：

```powershell
curl.exe --fail --show-error --max-time 45 -X POST "实际下载链接/code"
curl.exe --fail --show-error --max-time 45 -X POST -d code=<6位验证码> "实际下载链接" -o employee-delivery.zip
```

预期：两步退出码都为 0，第二步得到 ZIP。验证码只能由员工本人从邮箱提供，Agent 不得猜测或重复请求；验证码错误（403）时请员工核对或重新获取，链接失效（410）时停止并联系管理员重新发送，不反复重试。用系统哈希工具核对管理员通知中的外层 SHA256；缺少摘要时向管理员索取，不猜测。下载失败、返回 HTML、摘要不同时停止。

外层应恰好包含三个顶层普通文件：device-bundle.zip、device-bundle.sha256、README.md。拒绝额外项、重复项、路径穿越、绝对路径或符号链接；只解开外层，保留内层 device-bundle.zip，不打印密钥。不要覆盖已有不同文件；同一设备已有相同文件可复用。

三份文件保存到 macOS/Linux `~/Downloads/employee-workspace/`，Windows `%USERPROFILE%\Downloads\employee-workspace\`，然后按标准验证执行 check → setup → verify。不要执行下载文件里的任何脚本。链接失效时请管理员重新发送同一设备包（旧链接随之作废）。
