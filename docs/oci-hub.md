# OCI Hub 原型接入

管理员明确交付 v2 `oci-hub` 包时，按原生 check/setup/verify/connect 顺序执行。四个包内数据文件保持，manifest 额外声明 profile、employee 用户、独立 alias、目标桌面 URL 和固定叶证书 SHA256。WireGuard 只路由本人目标 VM /32，Endpoint 为 51824，keepalive 15 秒。

相同 device_id 的 v1/v2 状态相互独立。verify 先核对目标 TLS pin，再复用 verify-session 验证 employee、目标 hostname、sudo 与 CLI。证书轮换需管理员重新核对并交付新 pin。

原型测试不是实际 VPN、桌面、Windows 或中国网络验收；真实接入前完成服务端上线门槛。
