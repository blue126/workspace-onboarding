# Windows 10 / 11

1. Ask your local Agent to clone `https://github.com/blue126/workspace-onboarding` into a new `workspace-onboarding` folder and open it. This public clone does not need a GitHub sign-in.
2. Save the bundle, SHA256, and connection sheet that the administrator sent privately in the project local `deployment/` folder.
3. Confirm the files `deployment/device-bundle.zip`, `deployment/device-bundle.sha256`, and `deployment/README.md` are present.
4. Run `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 check`, then setup with `-InstallClients`, and verify using the same entry point.
5. If verification passes, run connect. In the VM run `workspace-login`; use the browser address from `deployment/README.md` to complete Claude sign-in yourself.
6. Use `sftp` for file transfers and `disconnect` to stop this device's tunnel.

The scripts automatically read the private bundle and SHA256 from `deployment/`. Tunnel activation and some client installation actions require an elevated PowerShell and Windows UAC. Approve them yourself; do not provide an administrator password to the Agent.
