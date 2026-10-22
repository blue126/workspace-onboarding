# Administrator: per-device private files

Employees use the public [workspace-onboarding GitHub project](https://github.com/blue126/workspace-onboarding) directly; no GitHub account is required. Do not build an all-in-one employee project ZIP.

For each device, privately deliver these files using the administrator's existing secure channel:

- `device-bundle.zip`: the four-file device identity bundle used by the setup scripts.
- `device-bundle.sha256`: the independently recorded lowercase SHA256 of that exact ZIP.
- `connection-sheet.md`: that device's assigned VM and browser connection details.

The source code is shared. These device files are not. Each device receives its own SSH/WireGuard credentials and tunnel address; do not share one bundle between computers, even for the same employee. A missing or mismatched bundle must be reissued from the correct device identity, never copied from another employee.

Keep all private files outside the public Git checkout. `.gitignore` excludes `/deployment/` and ZIP files as an additional guard. Never put bundles or connection sheets in a GitHub issue, release, commit, CI artifact, public object URL, or public repository.

## Bundle format

The importer accepts exactly these four ordinary files at the top level of `device-bundle.zip`:

- `manifest.json`
- `client-key`
- `wg.key`
- `known_hosts`

The separate SHA256 file covers the entire ZIP. The connection sheet carries the actual browser address and employee-specific operating notes. It is private employee data even where it does not contain cryptographic keys.

The employee runs the public GitHub source locally and passes the private bundle path and SHA256 directly to the native setup scripts. The scripts validate and read the bundle without displaying its contents. The private connection sheet is used for the browser step.

## Validation and revocation

GitHub CI uses synthetic credentials; it does not inspect actual device bundles or connect to the company environment. The administrator should verify the exact recipient and device assignment before delivery. Employees complete OS authorization, WireGuard connectivity, their personal Claude sign-in, and a real small project task themselves.

Deleting local private files does not revoke an issued identity. Revoke the device and disable the VM through the infrastructure process.
