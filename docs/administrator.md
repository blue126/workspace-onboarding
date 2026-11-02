# 设备文件交付约定

管理员将本设备的 `device-bundle.zip`、`device-bundle.sha256`、`README.md`（实际连接单）装入一个外层 ZIP，上传到 `cc.willfan.me` 并经管理接口核对哈希。员工在「我的工作区」登录后下载，页面显示有效期、剩余下载次数和外层 SHA256（目前 3 天内有效、最多下载 3 次，用完或过期后包内容删除）。通知邮件只包含问候、使用须知和一句交给 Agent 的提示词，不含下载链接或 SHA256。

Agent 获取公共代码，按 README 引导员工下载，自己在下载目录找到外层 ZIP、检查结构后将三份文件放入项目外的 `Downloads/employee-workspace/`。只有找不到首选目录设备文件时，项目内 deployment/ 才作为后备。失效时管理员复用原设备身份重新发送，不重新开户或轮换密钥。

包内格式固定为四个顶层普通文件：manifest.json、client-key、wg.key、known_hosts。SHA256 文件描述整个 bundle ZIP。每台设备独立签发，不能共享身份。管理员生成、上传和通知工具保留在管理员私有环境。

公开代码不包含私人链接、真实设备数据或管理员工具。
