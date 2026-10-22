# Employee Workspace Bootstrap

Public client source: [blue126/workspace-onboarding](https://github.com/blue126/workspace-onboarding). Employees can access it without a GitHub account. This repository contains only generic code and guides; it contains no employee identity or credentials.

The administrator separately supplies each device's private `device-bundle.zip`, its SHA256, and the device's connection sheet. Keep those files outside this public source checkout. The same employee's other computers need their own device bundle and addresses.

Supports Windows 10/11, macOS 12+, Ubuntu 22.04+, and Debian 12+. The client uses native PowerShell/Bash. The VM's project tools and dependencies are managed by the employee.

## Give this to your local Agent

After the Agent has opened this public repository in the local workspace, provide the local paths to the private device bundle and connection sheet, plus the SHA256 value.

> 请使用 https://github.com/blue126/workspace-onboarding 和管理员私下提供的本设备接入包，按 README.md、AGENTS.md 完成本机接入与验证；遇到系统授权或 Claude 登录时交给我操作。

Do not paste the bundle contents, private keys, or full WireGuard configuration into the Agent chat.

## Setup

The examples use shell variables so the bundle path and SHA256 only need to be supplied once per terminal session.

macOS / Ubuntu / Debian:

```bash
BUNDLE="$HOME/Downloads/employee-device/device-bundle.zip"
SHA256="paste-the-SHA256-supplied-by-admin"

bash ./bootstrap.sh check --bundle "$BUNDLE" --sha256 "$SHA256"
bash ./bootstrap.sh setup --bundle "$BUNDLE" --sha256 "$SHA256" --install-clients
bash ./bootstrap.sh verify --bundle "$BUNDLE" --sha256 "$SHA256"
bash ./bootstrap.sh connect --bundle "$BUNDLE" --sha256 "$SHA256"
```

Windows PowerShell 5.1 or 7:

```powershell
$Bundle = "$env:USERPROFILE\Downloads\employee-device\device-bundle.zip"
$Sha256 = "paste-the-SHA256-supplied-by-admin"

powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 check -Bundle $Bundle -Sha256 $Sha256
powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 setup -Bundle $Bundle -Sha256 $Sha256 -InstallClients
powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 verify -Bundle $Bundle -Sha256 $Sha256
powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 connect -Bundle $Bundle -Sha256 $Sha256
```

Windows setup and tunnel activation may require an elevated PowerShell. Linux setup may require sudo. Authorize system prompts yourself; the scripts do not collect passwords. macOS uses the official WireGuard app, and you approve its VPN permission yourself.

For file transfer, use `sftp` with the same bundle parameters. To disconnect, use `disconnect`; this keeps the device configuration on your computer.

## Claude and the VM browser

After connecting to the VM, run `workspace-login` in its terminal. Use the browser address in your private connection sheet while WireGuard is active. Complete Claude authorization yourself inside the VM.

For the daily VM browser, use `workspace-browser start`, `workspace-browser status`, and `workspace-browser stop`.

## Guides

- [Windows](docs/manual-windows.md)
- [macOS](docs/manual-macos.md)
- [Ubuntu/Debian](docs/manual-linux.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Administrator and private device bundle](docs/administrator.md)
- [Agent instructions](AGENTS.md)

Never commit device bundles, connection sheets, or employee credentials to this public repository. Removing a local bundle does not revoke server access; administrators must revoke the device through the infrastructure process.
