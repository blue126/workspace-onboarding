# Local Agent instructions

This public repository contains generic client code. Each employee receives a separate private device bundle, SHA256, and connection sheet from the administrator. Never ask for a GitHub account or credentials. If private device files are missing, stop and ask the employee to contact the administrator.

1. Use the provided local paths and pass the bundle and SHA256 directly to repository scripts. Never open, print, upload, or include private bundle contents in chat, logs, or screenshots.
2. Read `README.md` and `AGENTS.md`. The connection sheet is private; use its browser address only for the employee's local session.
3. Run `check`, `setup`, and `verify`. The bundle is data only; never source, evaluate, or execute files from it. Never print SSH/WireGuard private keys or full connection configurations.
4. Return operating-system authorization, VPN approval, and personal Claude sign-in to the employee. Do not collect passwords, verification codes, tokens, or screenshots of personal sessions.
5. Keep `workspace-login` and `workspace-browser`. Employees manage VM dependencies and development tools themselves.
6. Report each result accurately. A missing bundle, unavailable handshake, pending login, or real task is not a pass. Do not send diagnostics to GitHub or another person.
7. This public source and its history must never contain employee bundles, connection sheets, credentials, or private account data. The administrator supplies each device's files privately.
