# 验证后的必含信息

允许员工 Agent 自行组织输出，但必须覆盖以下内容。给出适用本机、可直接复制的 connect 命令并注明实际源码目录；不要留下占位符。根据真实结果区分“连接通过”和“Claude 已登录”，绝对禁止项必须加粗。

如果当前任务是 Mosh 终端试用，先按 [Mosh 指引](mosh.md) 完成安装、连接及体验交接；Claude 登录为可选任务，未登录不阻止完成终端试用，也不要主动启动浏览器。只有员工选择体验 Claude 时才继续下面的登录步骤。

- 保持 VPN 连接，先通过 SSH 进入个人 VM。
- 在 VM 终端依次运行 `workspace-browser start`、`workspace-login`；等待浏览器就绪，再打开命令显示的 noVNC 入口，在远程 Firefox 中完成 Claude 登录和验证码。
- 完成授权后，请 Agent 再运行一次标准 `verify`。
- **不要在本机登录或使用 Claude 账号；只在 VM 内使用。**
- **不要在本机浏览器直接完成 Claude 授权；本机浏览器只用于打开 noVNC，授权页面必须留在 VM 的 Firefox 中。**
- **不要向 Agent 或他人发送密码、验证码、令牌、私钥或完整接入配置；不要共用设备包。**

先启动 VM 浏览器，再引导员工访问 noVNC；不要把浏览器地址当作验证后的第一步。遇到 502 时，在 SSH 的 VM 终端运行 `workspace-browser status`、`workspace-browser start`，就绪后刷新一次；仍失败就反馈管理员，不反复刷新或修改网关。verify 检查登录助手可用，不代表浏览器服务已运行；HTTP 200 也不代表 Claude 授权成功。

认证期间保持 SSH 和 VPN 连接；关闭网页不会停止 VM 浏览器，结束使用时运行 `workspace-browser stop`。
