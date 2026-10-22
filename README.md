# Employee Workspace Bootstrap

Public client source: [blue126/workspace-onboarding](https://github.com/blue126/workspace-onboarding). Employees can access it without a GitHub account. This repository contains generic code only; it contains no employee identity or credentials.

The administrator sends each device package, SHA256, and actual connection sheet privately. The employee saves those files in the local `deployment/` folder; the Agent finds them by their fixed names.

- `deployment/device-bundle.zip`
- `deployment/device-bundle.sha256`
- `deployment/README.md` (the private connection sheet)

These local files are ignored by Git and must never be committed. Each computer gets its own device bundle and addresses, including additional computers used by the same employee.

Supports Windows 10/11, macOS 12+, Ubuntu 22.04+, and Debian 12+. VM project tools and dependencies are managed by the employee.

## Give this to your local Agent

If the public project is not already open locally, ask the Agent to clone it into a new `workspace-onboarding` folder in its current working directory. The public repository can be cloned without a GitHub account. Then save the three private files sent by the administrator into that clone’s `deployment/` folder.

> 请先克隆 https://github.com/blue126/workspace-onboarding 到本机，再让我把管理员私发的本设备文件放入项目 deployment/，然后按 README.md/AGENTS.md 完成接入；系统授权和 Claude 登录交给我。

Never paste bundle contents, private keys, or full WireGuard configuration into the Agent chat. If a file is missing, report its name and stop; the employee can follow up with the administrator.

## Setup

All commands automatically use the files in `deployment/`; do not add the device bundle or SHA256 to command arguments.

macOS / Ubuntu / Debian:

```bash
bash ./bootstrap.sh check
bash ./bootstrap.sh setup --install-clients
bash ./bootstrap.sh verify
bash ./bootstrap.sh connect
```

Windows PowerShell 5.1 or 7:

```powershell
powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 check
powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 setup -InstallClients
powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 verify
powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 connect
```

Windows setup and tunnel activation may require an elevated PowerShell. Linux setup may require sudo. Approve system prompts yourself; the scripts do not collect passwords. macOS uses the official WireGuard app, and you approve its VPN permission yourself.

For file transfer, use `sftp`. To disconnect, use `disconnect`; this keeps the device configuration on your computer.

## Claude and the VM browser

After connecting to the VM, run `workspace-login` in its terminal. Use the browser address in the private `deployment/README.md` connection sheet while WireGuard is active. Complete Claude authorization yourself inside the VM.

For the daily VM browser, use `workspace-browser start`, `workspace-browser status`, and `workspace-browser stop`.

## Guides

- [Windows](docs/manual-windows.md)
- [macOS](docs/manual-macos.md)
- [Ubuntu/Debian](docs/manual-linux.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Administrator and private device bundle](docs/administrator.md)
- [Agent instructions](AGENTS.md)

Deleting local files does not revoke server access. Administrators must revoke a device through the infrastructure process.
