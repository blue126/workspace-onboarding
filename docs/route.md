# 换线路

本页写给员工电脑上的 AI 助手。员工复制给你的话类似：

> 请阅读 https://github.com/blue126/workspace-onboarding 的 docs/route.md，把我这台电脑的 RemoteCC 隧道改用加速线路。

本设备的隧道有两条线路，只差 Endpoint 的地址，端口相同：

| 线路 | 地址 |
| --- | --- |
| 加速线路 | `ga-hvt7fapy.tencentcloudga012.com` |
| 普通线路 | `159.13.46.201` |

[README](../README.md) 的规则同样适用：失败即停，不收集秘密，私钥不出现在任何输出里。**不要手工修改隧道的 `.conf`**：bootstrap 每次运行都会把它和设备包核对，手改过就会报 `CONFIG_CONFLICT`。换线路只用下面的 `route`。

## 第 1 步：更新源码

- **需求：** 按 [README 第 1 步](../README.md#第-1-步取得源码) 把 `~/EmployeeWorkspace/onboarding`（Windows：`%USERPROFILE%\EmployeeWorkspace\onboarding`）更新到远端 `main`。
- **验收：** 源码目录的 `VERSION` 不低于 `1.6.0`。
- **可能遇到的问题：** 这台电脑还没接入过 → 不是换线路，按 README 从头接入。

## 第 2 步：改用加速线路前，确认当前网络已接入

- **需求：** 加速线路只接受员工接入过的网络。请员工打开 https://cc.willfan.me/me ，确认「网络状态」一行的按钮显示「已接入」；显示「接入网络」时先点一下，等它变成「已接入」。
- **改回普通线路时跳过这一步。**

## 第 3 步：route

在源码目录原样运行，把 `<地址>` 换成上表的地址：

| 系统 | 命令 |
| --- | --- |
| macOS / Linux | `bash ./bootstrap.sh route --endpoint <地址>` |
| Windows（管理员 PowerShell） | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 route -Endpoint <地址>` |

- **说明：** route 和 check、verify 一样读取设备包，确认这台电脑装的是这个设备包，再保存新地址；隧道正在运行时立即切换。macOS / Linux 需要员工在自己的终端输入 sudo 密码，Windows 在管理员窗口运行，见 [系统授权](system-authorization.md)。setup 时用过 `--bundle`/`--sha256`/`--state-root`（Windows `-Bundle`/`-Sha256`/`-StateRoot`）的，带上同样的参数。
- **验收：** 输出 `ROUTE_CHANGED`。已经在这条线路上时也输出 `ROUTE_CHANGED`，什么都不变。
- **可能遇到的问题：**
  - `PACKAGE_MISSING` → 设备包不在 `~/Downloads/employee-workspace/`，按 [设备包下载](download.md) 请员工重新下载并解开到原位置，再运行。
  - `REISSUE_READY` → 管理员已换发这台设备的新包。按 README 第 3 步运行 setup 和 verify，不再运行 route；新包自带当前推荐的线路。
  - `CONFIG_CONFLICT` → 隧道配置除 Endpoint 以外还被改过。停止，请员工联系管理员；不要自己恢复文件。之前手工改过 Endpoint 的，route 会直接修好，不报这个代码。
  - `TUNNEL_CONFLICT` → 正在运行的隧道不属于这台设备；什么都没改，按 [故障处理](troubleshooting.md) 处理。
  - `ROUTE_APPLY_FAILED` → 新地址已保存，但运行中的隧道没切过去。运行 `disconnect`，再运行 `connect`。
  - `ROUTE_WRITE_FAILED` → 没能保存，原配置不变；把代码报告给管理员。

## 第 4 步：verify

- **需求：** 按 [README 第 3 步](../README.md#第-3-步check--setup--verify) 运行 verify。
- **验收：** `CONNECTION_VERIFIED` 或 `CLAUDE_AUTH_USER_PENDING`。把结果告诉员工：现在用的是哪条线路。
- **可能遇到的问题：**
  - `TUNNEL_DOWN` → 隧道没在运行，运行 `connect` 后再 verify。
  - 改用加速线路后 `NO_RECENT_HANDSHAKE` 或 `SSH_CONNECTION_FAILED` → 请员工回到 https://cc.willfan.me/me 确认当前网络显示「已接入」，再 verify；还不通过，改回普通线路，verify 通过后请员工发邮件到 hello@willfan.me 说明情况。
  - 其他 `code` → [故障处理](troubleshooting.md)。

之后 connect、setup、verify 都沿用选好的线路；管理员换发新包后以新包为准。
