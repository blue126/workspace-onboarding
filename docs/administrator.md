# Administrator: fixed per-device file location

Employees use the public [workspace-onboarding GitHub project](https://github.com/blue126/workspace-onboarding) directly; no GitHub account is required. Do not build an all-in-one employee project ZIP.

For each device, privately supply these files:

- `device-bundle.zip`: that device's four-file SSH/WireGuard identity bundle.
- `device-bundle.sha256`: the independently recorded lowercase SHA256 of that exact bundle.
- `README.md`: that device's actual VM, gateway, and browser connection sheet.

The employee places them in the checkout's pre-created `deployment/` folder with exactly these names:

```text
deployment/
  .gitkeep
  device-bundle.zip
  device-bundle.sha256
  README.md
```

`.gitignore` ignores all files in this directory except the empty tracked `.gitkeep`. The bootstrap scripts default to `deployment/device-bundle.zip` and `deployment/device-bundle.sha256`; the local Agent reads `deployment/README.md` for the browser address. Missing or mismatched files must stop setup and be reissued by the administrator. Never commit or upload this directory.

Each computer receives its own SSH/WireGuard credentials and tunnel address, even if multiple computers belong to one employee. The bundle must contain exactly these four ordinary files at its top level:

- `manifest.json`
- `client-key`
- `wg.key`
- `known_hosts`

The SHA256 file covers the full ZIP. Never copy a bundle between devices. Deliver its files through the administrator's private channel, not a GitHub issue, public release, CI artifact, or public object URL.

## Validation and revocation

GitHub CI uses synthetic credentials; it does not inspect actual device bundles or connect to the company environment. The administrator should verify the recipient and device assignment before delivery. Employees complete OS authorization, WireGuard connectivity, personal Claude sign-in, and a small real project task themselves.

Deleting local files does not revoke an issued identity. Revoke the device and disable the VM through the infrastructure process.
