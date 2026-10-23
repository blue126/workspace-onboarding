# 设备文件交付约定

管理员将本设备的 `device-bundle.zip`、`device-bundle.sha256`、`README.md`（实际连接单）装入一个外层 ZIP，上传 Temp.sh，并通过 HTTP POST 下载核对哈希；通知邮件包含实际链接、外层 SHA256 和加粗的 Agent 提示词。Temp.sh 标注保存三天，这是服务政策，不是管理员可保证的精确到期时间。

员工把链接交给本机 Agent；Agent 获取公共代码，按 [设备包下载](download.md) 下载外层 ZIP，将三份文件放入项目外的 `Downloads/employee-workspace/`。只有找不到首选目录设备文件时，项目内 deployment/ 才作为后备。链接失效时管理员复用原设备身份重新交付，不重新开户或轮换密钥。

包内格式固定为四个顶层普通文件：manifest.json、client-key、wg.key、known_hosts。SHA256 文件描述整个 bundle ZIP。每台设备独立签发，不能共享身份。管理员生成、上传和通知工具保留在管理员私有环境。

公开代码不包含私人链接、真实设备数据或管理员工具。
