# Ubuntu / Debian

1. Ask your local Agent to clone `https://github.com/blue126/workspace-onboarding` into a new `workspace-onboarding` folder and open it. This public clone does not need a GitHub sign-in.
2. Save the bundle, SHA256, and connection sheet that the administrator sent privately in the project local `deployment/` folder.
3. Confirm these files exist: `deployment/device-bundle.zip`, `deployment/device-bundle.sha256`, and `deployment/README.md`.
4. Run `bash ./bootstrap.sh check`, then `bash ./bootstrap.sh setup --install-clients`, and `bash ./bootstrap.sh verify`.
5. If verification passes, run `bash ./bootstrap.sh connect`. In the VM run `workspace-login`; use the browser address from `deployment/README.md` to complete Claude sign-in yourself.
6. Use `sftp` for transfers and `disconnect` to stop this device's tunnel.

The bootstrap scripts read the bundle and digest from `deployment/` automatically. Setup installs missing WireGuard tools, OpenSSH, jq, unzip, and iproute2. Sudo authorization is handled by you. Existing VPN or route conflicts stop setup rather than changing another VPN.
