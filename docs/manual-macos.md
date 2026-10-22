# macOS

1. Ask your local Agent to clone `https://github.com/blue126/workspace-onboarding` into a new `workspace-onboarding` folder and open it. This public clone does not need a GitHub sign-in.
2. Save the bundle, SHA256, and connection sheet that the administrator sent privately in the project local `deployment/` folder.
3. Confirm the files `deployment/device-bundle.zip`, `deployment/device-bundle.sha256`, and `deployment/README.md` are present.
4. Run `bash ./bootstrap.sh check`, then `bash ./bootstrap.sh setup --install-clients`, and `bash ./bootstrap.sh verify`. Setup opens the official WireGuard App Store page if needed. Import the private tunnel configuration shown by setup and approve the system VPN request yourself.
5. Run `bash ./bootstrap.sh connect`. In the VM run `workspace-login`; use the browser address in `deployment/README.md` to complete Claude sign-in yourself.
6. Use `workspace-browser start` on the VM, `sftp` locally for file transfers, and `disconnect` to stop this device's tunnel.

The scripts automatically read the private bundle and SHA256 from `deployment/`. Never commit this folder.
