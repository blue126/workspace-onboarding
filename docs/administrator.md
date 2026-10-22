# 设备文件交付约定

管理员通过 OneDrive 为指定员工生成7天免登录只读链接，交付本设备的 `device-bundle.zip`、`device-bundle.sha256`、`README.md`（实际连接单），并在通知邮件中提供公开 GitHub 项目地址和本人共享链接。

员工把链接交给本机 Agent；Agent 获取公共代码、从该共享下载三个文件，保存到项目外的 `Downloads/employee-workspace/`。只有找不到首选目录设备文件时，项目内 deployment/ 才作为后备。

包内格式固定为四个顶层普通文件：manifest.json、client-key、wg.key、known_hosts。SHA256 文件描述整个 bundle ZIP。每台设备独立签发，不能共享身份。管理员生成、上传和通知工具保留在管理员私有环境。

公开代码不包含私人链接、真实设备数据或管理员工具。
