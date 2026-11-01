# 设备文件交付约定

管理员将本设备的 `device-bundle.zip`、`device-bundle.sha256`、`README.md`（实际连接单）装入一个外层 ZIP，上传到 `cc.willfan.me` 并经管理接口核对哈希；通知邮件包含一次性下载链接、外层 SHA256 和加粗的 Agent 提示词。链接 3 天内有效、最多下载 3 次，每次下载前须用发到员工邮箱的验证码，下载满或过期后包内容删除。

员工把链接交给本机 Agent；Agent 获取公共代码，按 [设备包下载](download.md) 下载外层 ZIP，将三份文件放入项目外的 `Downloads/employee-workspace/`。只有找不到首选目录设备文件时，项目内 deployment/ 才作为后备。链接失效时管理员复用原设备身份重新发送（旧链接随即作废），不重新开户或轮换密钥。

包内格式固定为四个顶层普通文件：manifest.json、client-key、wg.key、known_hosts。SHA256 文件描述整个 bundle ZIP。每台设备独立签发，不能共享身份。管理员生成、上传和通知工具保留在管理员私有环境。

公开代码不包含私人链接、真实设备数据或管理员工具。
