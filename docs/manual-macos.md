# macOS

1. Open the public [`workspace-onboarding` project](https://github.com/blue126/workspace-onboarding) in your local Agent; no GitHub sign-in is required.
2. Ask the administrator for this device's `device-bundle.zip`, its SHA256, and private connection sheet.
3. In Terminal, set the bundle path and digest using the files you received, then run check, setup, and verify with the same arguments:

```bash
BUNDLE="$HOME/Downloads/employee-device/device-bundle.zip"
SHA256="paste-the-SHA256-supplied-by-admin"

bash ./bootstrap.sh check --bundle "$BUNDLE" --sha256 "$SHA256"
bash ./bootstrap.sh setup --bundle "$BUNDLE" --sha256 "$SHA256" --install-clients
bash ./bootstrap.sh verify --bundle "$BUNDLE" --sha256 "$SHA256"
```

Setup opens the official WireGuard App Store page if needed. Import the private tunnel configuration shown by setup and approve the system VPN request yourself.
5. Connect using the same bundle arguments. In the VM run `workspace-login`; use your private connection sheet's browser address to complete Claude sign-in yourself.
6. Use `workspace-browser start` on the VM for daily browsing and `sftp` locally for file transfers. Run `disconnect` to stop this device's tunnel.

The public repository contains no employee credentials. The employee Agent must not read or display private bundle contents.
