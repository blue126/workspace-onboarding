# Administrator: build one private employee ZIP

The public `blue126/workspace-onboarding` repository contains reusable client scripts and guides only. It must never contain `deployment/`, employee keys, host-specific connection sheets, employee identity data, or copies of another repository's Git history. Each employee needs one complete ZIP combining a reviewed public source commit with one device's private bundle and actual connection sheet. GitHub accounts are not required for employees.

## Build an employee ZIP

Use a clean, reviewed clone/checkout of the public source repository. Keep the bundle, its independently recorded SHA256 file, the connection sheet, and output ZIP outside the checkout, in directories private to the administrator. The package builder reads only tracked generic files and these explicit inputs; it refuses to build from a dirty tracked tree or accept files stored inside the public checkout.

```bash
python3 scripts/package-employee.py \
  --bundle /secure/employee/device-bundle.zip \
  --sha256-file /secure/employee/device-bundle.sha256 \
  --config-sheet /secure/employee/connection-sheet.md \
  --output /secure/delivery/employee-workspace.zip
```

Use a new private output location for every employee/device. The tool verifies the recorded SHA256, archive entry names, and manifest shape before packaging. It writes a single flat ZIP with the client README/AGENTS, platform scripts and guides, that device's `deployment/device-bundle.zip`, `deployment/device-bundle.sha256`, and `deployment/README.md`. Its console output contains only the output location, file count, and final ZIP SHA256; it never prints bundle or config-sheet contents.

Deliver the complete ZIP directly to its assigned employee through the administrator's existing private file-delivery method. Do not attach employee bundles to a GitHub release, issue, CI job, public object URL, or this public repository. If a bundle is missing, stop and obtain the correct per-device bundle; do not reuse another employee's identity.

## Bundle format

The existing importer accepts exactly four ordinary files at the top level of the device bundle:

- `manifest.json`
- `client-key`
- `wg.key`
- `known_hosts`

The sibling SHA256 file covers the complete bundle ZIP. The administrator's connection sheet includes that employee/device's assigned VM, gateway, WireGuard and browser details. It is private employee data even if the values are not cryptographic keys.

## Validation boundary

Repository CI uses synthetic credentials and excludes `deployment/`. It does not enter the company VPN or inspect actual employee packages. Before delivery, the administrator checks the generated ZIP and confirms it contains only the intended device package. The employee completes system authorization, WireGuard connectivity, personal Claude sign-in, and a real small project task on their own computer.

Deleting the ZIP, code repository, or local files does not revoke an already issued device identity. Revoke devices and disable VMs through the infrastructure process. Preserve any existing approved device package only for its assigned user.
