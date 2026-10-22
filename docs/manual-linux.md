# Ubuntu / Debian

1. Open the public [`workspace-onboarding` project](https://github.com/blue126/workspace-onboarding) in your local Agent; no GitHub sign-in is required.
2. Ask the administrator for this device's `device-bundle.zip`, its SHA256, and private connection sheet. Do not share them with another computer.
3. Set the private bundle path and digest in the current terminal session:

```bash
BUNDLE="$HOME/Downloads/employee-device/device-bundle.zip"
SHA256="paste-the-SHA256-supplied-by-admin"
```

4. Run `bash ./bootstrap.sh check --bundle "$BUNDLE" --sha256 "$SHA256"`, then setup with `--install-clients`, and verify using the same two arguments.
5. If verification passes, connect using the same bundle arguments. In the VM run `workspace-login`; open the browser address from your private connection sheet and complete personal Claude sign-in.
6. Use `sftp` with the same bundle arguments for transfers. Use `disconnect` to turn off this device's tunnel without removing its configuration.

Setup installs missing WireGuard tools, OpenSSH, jq, unzip, and iproute2. Sudo authorization is handled by you. Existing VPN or route conflicts stop setup rather than changing another VPN.
