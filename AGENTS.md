# 员工本机 Agent 约定

员工提供公开项目地址和本人收到的 OneDrive 私人共享链接，无需 GitHub 账号。

1. 获取公开源码并读取 README/AGENTS；已有目录先核对仓库来源，不覆盖本地文件或重置工作树。
2. 默认接收目录为 macOS/Linux 的 `~/Downloads/employee-workspace/`、Windows 的 `%USERPROFILE%\Downloads\employee-workspace\`。该目录独立于源码；需要时创建。
3. 只从员工提供且本人获授权的 OneDrive 共享读取 `device-bundle.zip`、`device-bundle.sha256`、`README.md`。登录、验证码及权限同意由员工操作，不读取或记录密码、Cookie、令牌或个人页面。
4. 只移动/保存本次下载的三个文件，不搜索其他私密网盘目录，不覆盖已有不同文件。OneDrive 文件夹的外层下载 ZIP 可以解包，但保留内层 device-bundle.zip。
5. 首选目录不存在设备文件时，源码项目的 deployment/ 可作为后备：告诉员工准确位置并等文件就绪。首选目录部分缺失或校验失败时停止对应操作，不静默换用后备身份。
6. 三份文件齐全后运行仓库原生入口 check、setup、verify、connect。设备包由脚本按数据校验处理；Agent 不展开、打印或上传密钥，不执行包内文件。
7. 系统管理员授权、WireGuard VPN 权限及个人 Claude 登录交还员工。保留 VM 内 workspace-login 和 workspace-browser。
8. 按实际结果报告；未就绪/未验证项目不能标为成功。不得自动把诊断材料、私人链接或配置提交到 GitHub 或其他人。
