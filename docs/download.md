# 设备包下载

## 首选：员工在「我的工作区」下载

员工打开 https://cc.willfan.me/me ，用申请时的邮箱和收到的验证码登录，在「设备接入包」卡片点击「下载设备接入包」。登录验证码只发到员工本人邮箱，设备包含员工专属私钥，所以由员工本人经 HTTPS 下载。卡片显示有效期和剩余下载次数；有效期和次数以页面为准（目前为 3 天、最多 3 次），用完或过期后失效，需要发邮件到 hello@willfan.me 请管理员重新发送。

Agent 不代为登录，不索取验证码、Cookie 或令牌。下载完成后，Agent 自己在浏览器默认下载目录（macOS/Linux `~/Downloads`，Windows `%USERPROFILE%\Downloads`）找最近一天内修改的 `device-bundle*.zip`；没有或有多个时才问员工。下载的文件通常名为 `device-bundle.zip`（可能带 `(1)` 等后缀），它是外层 ZIP，里面还有同名的内层 `device-bundle.zip`。

## 备用：用 `/d/<令牌>` 链接下载

只在员工无法登录网站、但手上有管理员给的 `https://cc.willfan.me/d/<令牌>` 链接时使用。每次下载都要一个发到员工邮箱的 6 位验证码（10 分钟内有效），与页面共用同一下载次数。

**这一步由员工本人在自己的终端里完成**：Agent 把下面的命令模板交给员工，并说明“验证码只发到你的邮箱，由你自己输入，不要告诉我”；Agent 不接收、不填写验证码，也不代为运行。员工把 `实际下载链接` 换成自己的链接后运行；下载的文件名以 `device-bundle` 开头，README 第 2 步能找到它。

macOS / Linux（在 `~/Downloads` 内运行）：

```bash
link='实际下载链接'
curl --fail --show-error --max-time 45 -X POST "$link/code"
printf '邮箱里的 6 位验证码: '; read -r code
curl --fail --show-error --max-time 45 -X POST -d "code=$code" "$link" -o "device-bundle-$(date +%Y%m%d%H%M%S).zip"
```

Windows PowerShell（在 `%USERPROFILE%\Downloads` 内运行；用系统 curl.exe，避免 PowerShell 的 curl 别名）：

```powershell
$link='实际下载链接'
curl.exe --fail --show-error --max-time 45 -X POST "$link/code"
$code=Read-Host '邮箱里的 6 位验证码'
curl.exe --fail --show-error --max-time 45 -X POST -d "code=$code" "$link" -o "device-bundle-$(Get-Date -Format yyyyMMddHHmmss).zip"
```

预期：两条 curl 退出码都为 0，第二条得到 ZIP。验证码错误（403）时员工重新获取后再运行；链接失效（410）时停止并联系管理员重新发送，不反复重试。GET 返回的是网页，不能当作 ZIP。员工完成后告诉 Agent 即可，Agent 继续 README 第 2 步。

## 校验与解开（两种方式相同）

**两层 ZIP，名字相同：** 员工下载的 `device-bundle*.zip` 是外层 ZIP，里面恰好三个文件：`device-bundle.zip`（内层设备包，含 manifest 与密钥）、`device-bundle.sha256`、`README.md`（本设备连接单）。完整性校验在内层：bootstrap 的 check/setup 用 device-bundle.sha256 核对内层包，不一致返回 `PACKAGE_HASH_MISMATCH`；Agent 不另算摘要，也不打开内层包。页面上显示的 SHA256 可供员工自行核对，不是必需步骤。

**找到外层 ZIP：** 在下载目录（macOS/Linux `~/Downloads`，Windows `%USERPROFILE%\Downloads`）找最近一天内修改的普通文件 `device-bundle*.zip`（例如 `find ~/Downloads -maxdepth 1 -type f -name 'device-bundle*.zip' -mtime -1`，或 `Get-ChildItem -File -Filter 'device-bundle*.zip'` 加时间筛选）。恰好一个就用它；没有或有多个时才问员工。macOS 终端无权读取“下载”文件夹时，告诉员工这是系统隐私保护，请他在弹窗中允许，或告诉你文件位置。

**检查规则：** 恰好三个条目，名字恰好是上面三个、不重复、都在顶层；每个条目按完整的 32 位外部属性判断，高 16 位的 Unix 类型必须是普通文件（`0100000`）或未设置（`0`，管理员的打包工具写 `0o600 << 16`），且低 16 位不含 DOS 目录（`0x10`）或重解析点（`0x400`）属性；接收目录（macOS/Linux `~/Downloads/employee-workspace/`，Windows `%USERPROFILE%\Downloads\employee-workspace\`）里还没有这三个文件。`zipinfo` 只显示 8 位 DOS 属性、看不到重解析点，所以 macOS/Linux 用 python3 脚本。

macOS / Linux（在源码目录运行，只读）：

```bash
python3 -I scripts/check-outer-zip.py "<外层ZIP>" "$HOME/Downloads/employee-workspace"
```

Windows PowerShell（只读，规则相同）：

```powershell
Get-ChildItem "$env:USERPROFILE\Downloads" -File -Filter 'device-bundle*.zip' | Where-Object LastWriteTime -gt (Get-Date).AddDays(-1)
$outer='<上面找到的唯一文件的完整路径>'
$dest="$env:USERPROFILE\Downloads\employee-workspace"
$expected=@('device-bundle.zip','device-bundle.sha256','README.md')
Add-Type -AssemblyName System.IO.Compression.FileSystem
# Regular file: Unix type bits (high 16 bits) are 0x8000 or unset (0), and no
# directory (0x10) or reparse-point (0x400) attribute. Everything else is rejected.
$regular={ param($e) $t=(($e.ExternalAttributes -shr 16) -band 0xF000); (($t -eq 0x8000) -or ($t -eq 0)) -and -not ($e.ExternalAttributes -band 0x410) }
$entries=$null
try { $zip=[IO.Compression.ZipFile]::OpenRead($outer); try { $entries=@($zip.Entries) } finally { $zip.Dispose() } } catch { 'STOP: cannot read outer ZIP' }
if($entries -ne $null) {
    $names=@($entries | ForEach-Object FullName | Where-Object { $expected -ccontains $_ } | Select-Object -Unique)
    $conflicts=@($expected | Where-Object { Test-Path -LiteralPath (Join-Path $dest $_) })
    if($entries.Count -ne 3 -or $names.Count -ne 3) { 'STOP: unexpected entries' }
    elseif(@($entries | Where-Object { -not (& $regular $_) }).Count -ne 0) { 'STOP: not regular files' }
    elseif($conflicts.Count -ne 0) { "STOP: already in ${dest}: $conflicts" }
    else { 'READY' }
}
```

两边的校验结果都是一行 `READY` 或下面某个 `STOP`（Windows 的查找步骤会先列出候选 ZIP，那不是校验结果）：

| 输出 | 处理 |
| --- | --- |
| `STOP: cannot read outer ZIP` / `STOP: unexpected entries` / `STOP: not regular files` | 停止，请员工联系管理员。 |
| `STOP: already in …` | 不要解开。向员工说明“接收目录里有上一次的设备文件，新旧混在一起会让脚本用错身份”，请他同意后把这些文件移到备份目录，再重新检查。不覆盖也不复用。 |

**解开（只在 `READY` 之后）：** 只解开外层的三个文件到接收目录，不覆盖已有文件。macOS / Linux：

```bash
mkdir -p "$HOME/Downloads/employee-workspace" && unzip -n "<外层ZIP>" device-bundle.zip device-bundle.sha256 README.md -d "$HOME/Downloads/employee-workspace"
```

Windows（接着上面的检查，`$outer`、`$dest` 已设置）：

```powershell
New-Item -ItemType Directory -Force $dest | Out-Null
$zip=[IO.Compression.ZipFile]::OpenRead($outer)
try { foreach($e in $zip.Entries) { [IO.Compression.ZipFileExtensions]::ExtractToFile($e,(Join-Path $dest $e.FullName),$false) } } finally { $zip.Dispose() }
```

然后回到 README 运行 check → setup → verify。不要执行下载文件里的任何脚本。设备包内含 WireGuard 与 SSH 私钥：提醒员工不要转发、上传、提交到任何仓库或贴进聊天；Agent 自身不得输出私钥内容。
