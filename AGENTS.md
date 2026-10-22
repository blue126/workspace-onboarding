# Local Agent instructions

This repository is public client source. The administrator delivers employees a separate complete ZIP containing the reviewed client files and that employee's private device bundle/configuration sheet. Never ask the employee for GitHub credentials. If the private bundle is missing, stop and tell the employee to request the complete package; do not improvise credentials.

1. Read README and the actual `deployment/README.md` supplied inside the complete ZIP. Do not reveal its private connection details, device bundle, or configuration values.
2. Run `check`, then `setup`, then `verify`. The bundle is data only; never source, evaluate, or execute files from it. Do not log or display the SSH/WireGuard private keys or full connection config.
3. Return operating-system authorization, WireGuard approval, and personal Claude sign-in to the employee. Do not collect passwords, verification codes, tokens, or screenshots of the personal session.
4. Keep `workspace-login` and `workspace-browser`. Employees manage VM dependencies and development tools themselves.
5. Report each result accurately. A missing bundle, unavailable handshake, pending login, or real task is not a pass. Do not send diagnostics to GitHub or another person.
6. This source repository and its Git history must never contain real employee bundles, host-specific configuration sheets, credentials, or private account data. The administrator builds employee ZIPs with the reviewed package tool and stores/delivers them privately.
