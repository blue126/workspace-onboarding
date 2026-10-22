# Employee Workspace Bootstrap

This is the **public source repository** for the employee workspace client. Anyone can read or download the scripts without a GitHub account. This repository intentionally contains no employee device bundle, private key, company-specific endpoint, or personal Claude sign-in data.

An employee needs one complete ZIP from the administrator. The administrator combines this public source at a reviewed commit with that employee's private device bundle and actual connection sheet. The complete ZIP contains everything needed to set up one device. Downloading this public source by itself is not a working access package.

Supports Windows 10/11, macOS 12+, Ubuntu 22.04+, and Debian 12+. The client uses native PowerShell/Bash; the employee workstation does not need Python or Node.

## Give the package to your local Agent

Extract the complete ZIP from your administrator, open a terminal in the extracted folder, then give this to an Agent that can operate local files and a terminal:

> Read README.md and AGENTS.md. Use the private device bundle included with this employee package. Run check, then setup and verify. Do not print private keys, full connection configuration, or bundle contents. Do not execute scripts from the bundle or change other VPNs. Return control to me for system authorization and personal Claude sign-in. Keep the workspace-login shortcut and workspace-browser daily browser. Report only the sanitized results.

A cloud chat that cannot operate the employee's computer can explain steps but must not claim that it configured the computer. The employee does not need a GitHub account.

## Commands

The complete employee ZIP includes `deployment/device-bundle.zip`, its SHA256 file, and `deployment/README.md` with the employee's actual connection details. Commands below automatically use that private data.

| Action | Windows PowerShell | macOS / Linux |
| --- | --- | --- |
| Check | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 check` | `bash ./bootstrap.sh check` |
| Set up | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 setup -InstallClients` | `bash ./bootstrap.sh setup --install-clients` |
| Verify | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 verify` | `bash ./bootstrap.sh verify` |
| Work terminal | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 connect` | `bash ./bootstrap.sh connect` |
| Transfer files | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 sftp` | `bash ./bootstrap.sh sftp` |
| Disconnect | `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 disconnect` | `bash ./bootstrap.sh disconnect` |

Windows setup and tunnel activation require an elevated PowerShell; Linux setup requires sudo. Authorize the operating system prompts yourself. macOS uses the official WireGuard app; import the configuration shown by setup and approve the system VPN request yourself. The scripts do not collect passwords.

If you are maintaining a client source checkout rather than using the complete employee ZIP, the individual device bundle is absent. The scripts require an explicit external `--bundle` and `--sha256` on Bash, or `-Bundle` and `-Sha256` on PowerShell.

## Claude and the remote browser

After connecting to the VM, run `workspace-login` in the remote terminal. Use the browser address in `deployment/README.md` while the WireGuard connection is active. Claude authorization runs inside the employee VM and is completed by the employee.

For the daily browser, use `workspace-browser start`, `workspace-browser status`, and `workspace-browser stop` on the VM. Its profile and files stay on the VM.

## Detailed guides

- [Windows](docs/manual-windows.md)
- [macOS](docs/manual-macos.md)
- [Ubuntu/Debian](docs/manual-linux.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Administrator package builder](docs/administrator.md)
- [Agent instructions](AGENTS.md)

The employee device bundle is unique to one device. Do not share it or put it in this public repository. Removing a local package does not revoke server access; administrators must revoke a device through the infrastructure process.
