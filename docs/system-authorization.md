# 系统授权

优先由员工 Agent 执行配置，员工只完成系统授权。工具不支持交互或明确拒绝控制终端时，使用下面的人工降级步骤。不要索取密码或修改 sudoers。

## macOS

优先使用 Agent 自带的可交互终端。工具不支持用户输入时，自动打开系统 Terminal，并在同一会话顺序执行 setup、verify；避免在另一个会话反复请求 sudo。

以下是 AppleScript 参考。把源码的实际绝对路径作为参数传入；不要把私钥、密码或完整 VPN 配置放入命令。

```bash
osascript - "$PWD" <<'APPLESCRIPT'
on run argv
    set repoPath to item 1 of argv
    set setupCommand to "cd " & quoted form of repoPath & " && /bin/bash ./bootstrap.sh setup --install-clients && /bin/bash ./bootstrap.sh verify"
    tell application "Terminal"
        activate
        do script setupCommand
    end tell
end run
APPLESCRIPT
```

只让本人在新终端输入密码或确认 macOS 的自动化授权。不要通过聊天传递密码。由 Agent 等待该会话结束并核对标准 JSON 结果；工具无法读取该终端结果时，请员工仅反馈最终结果码，不索取终端全文。

打开终端不代表配置成功。拒绝/取消授权时停止；不要新开多个终端重复运行，也不要把已完成的 setup 说成 verify 已通过。

### 工具权限拒绝时

如果 Agent 的执行环境明确拒绝 sudo，且不能创建本人可输入的终端，或操作 Terminal 返回权限错误，应停止自动化提权尝试。由 Agent 给出一条使用实际源码路径的 `setup && verify` 命令，让本人在系统 Terminal 中以普通用户运行；密码只在该终端输入。完成后让 Agent 继续核对标准结果和 Mosh 测试。不得修改 sudoers、收集密码或绕过工具权限策略。

`NEEDS_ADMIN` 表示尚未取得必要授权，可能是没有交互输入、授权被取消或 sudo 被拒绝，不能直接解释为“密码没输入”。输出接 `tee` 保存日志时，只要标准输入仍连接本人终端，就应允许 sudo 正常请求授权；重定向标准错误不代表缺少交互终端。

## Windows / Linux

Windows 由 Agent 发起管理员 PowerShell，由本人确认 UAC，再完成 setup、verify。Linux 由 Agent 创建本人可输入密码的交互会话并完成这两个步骤。授权后继续使用同一会话；不要依赖另一个终端的 sudo 缓存。

这里授权的是员工本机建立 VPN 所需的系统操作，与 VM 内 employee 的 sudo 权限分别处理。
