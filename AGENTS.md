# Local Agent instructions

## Start from the public project

If this repository is not already open in the local workspace, clone `https://github.com/blue126/workspace-onboarding.git` into a new `workspace-onboarding` folder in the current working directory, then use that folder as the project workspace. Public cloning needs no GitHub login. If that destination already exists, do not overwrite or reset it; verify it is this repository first.

After cloning, the employee saves the administrator-sent device bundle, SHA256 file, and connection sheet in the existing `deployment/` folder.

This public repository contains generic client code. Administrators separately provide each device's bundle, SHA256, and connection sheet. Never ask for a GitHub account or credentials.

1. Look for `deployment/device-bundle.zip`, `deployment/device-bundle.sha256`, and `deployment/README.md`. The administrator sends them privately to the employee. If a file is missing, report its filename and stop.
2. Use the files at those paths directly; the setup scripts default to them. Never open, print, upload, or include private bundle contents in chat, logs, or screenshots.
3. Read the root `README.md` and this file. The private `deployment/README.md` is the connection sheet; use its browser address only for the employee's local session.
4. Run `check`, `setup`, then `verify`. The bundle is data only; never source, evaluate, or execute files from it. Never print SSH/WireGuard private keys or full connection configurations.
5. Return operating-system authorization, VPN approval, and personal Claude sign-in to the employee. Do not collect passwords, verification codes, tokens, or screenshots of personal sessions.
6. Keep `workspace-login` and `workspace-browser`. Employees manage VM dependencies and development tools themselves.
7. Report each result accurately. A missing bundle, unavailable handshake, pending login, or real task is not a pass. Do not send diagnostics to GitHub or another person.
8. Never commit any content in `deployment/`. Its contents are unique per device.
