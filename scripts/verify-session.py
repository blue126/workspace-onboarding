"""Fixed read-only VM checks, sent as one encoded command over the PTY."""
import json
import shutil
import subprocess

prefix = '__PREFIX__'
vm = '__VM__'

def run(args, timeout=3):
    try:
        return subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None

def ok(result, value=None):
    return result is not None and result.returncode == 0 and (value is None or result.stdout.strip() == value)

def emit(key, value):
    print(prefix + '_' + key + '=' + value, flush=True)

print('\n' + prefix + '_BEGIN', flush=True)
emit('USER', 'passed' if ok(run(['id', '-un']), 'employee') else 'failed')
emit('VM', 'passed' if ok(run(['hostname']), vm) else 'failed')
emit('SUDO', 'passed' if ok(run(['sudo', '-n', 'true'])) else 'failed')
cli = all(shutil.which(c) for c in ('claude', 'workspace-login', 'workspace-browser'))
emit('CLI', 'passed' if cli and ok(run(['workspace-login', '--check'], 5)) else 'failed')
auth = 'unavailable'
result = run(['claude', 'auth', 'status'], 20) if cli else None
try:
    data = json.loads(result.stdout) if result is not None and result.returncode in (0, 1) else {}
    if data.get('loggedIn') is False:
        auth = 'user_action_required'
    elif data.get('loggedIn') is True:
        auth = 'passed' if data.get('authMethod') == 'claude.ai' else 'user_action_required'
except (ValueError, AttributeError):
    pass
emit('AUTH', auth)
print(prefix + '_END', flush=True)
