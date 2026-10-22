# Windows 10 / 11

1. Open the public [`workspace-onboarding` project](https://github.com/blue126/workspace-onboarding) in your local Agent; no GitHub sign-in is required.
2. Ask the administrator for this device's `device-bundle.zip`, its SHA256, and private connection sheet.
3. In PowerShell, set the bundle path and digest using the files you received:

```powershell
$Bundle = "$env:USERPROFILE\Downloads\employee-device\device-bundle.zip"
$Sha256 = "paste-the-SHA256-supplied-by-admin"
```

4. Run `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 check -Bundle $Bundle -Sha256 $Sha256`, then setup with `-InstallClients`, and verify using the same bundle arguments.
5. If verification passes, connect. In the VM run `workspace-login`; use your private connection sheet's browser address to complete Claude sign-in yourself.
6. Use `sftp` for file transfer. Run `disconnect` to stop this device's tunnel.

Tunnel service activation and some client installation actions require an elevated PowerShell and Windows UAC. Approve them yourself; do not provide an administrator password to the Agent. The installer verifies the official WireGuard Authenticode signature.
