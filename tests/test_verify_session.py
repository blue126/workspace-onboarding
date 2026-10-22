#!/usr/bin/env python3
"""Exercise the real verification payload through a real local canonical PTY."""
import base64
import errno
import os
from pathlib import Path
import re
import select
import shlex
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]

@unittest.skipIf(os.name == 'nt', 'POSIX PTY and Bash watchdog')
class Session(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='verify-pty-')
        self.path = Path(self.tmp.name)
        self.bin = self.path / 'bin'
        self.bin.mkdir()
        stub = '''import json,os,pathlib,sys
name=pathlib.Path(sys.argv[0]).name
if name=='id':print('employee')
elif name=='hostname':print('employee-fixture')
elif name=='claude':
 # A consumer of all stdin reproduced the old queued-command loss.
 assert sys.stdin.read()==''
 print('PRIVATE_AUTH_SENTINEL',file=sys.stderr)
 if os.environ.get('BROKEN_AUTH'):print('invalid-json');sys.exit(3)
 pending=bool(os.environ.get('PENDING_AUTH'))
 print(json.dumps({'loggedIn':not pending,'authMethod':'none' if pending else 'claude.ai'}))
 sys.exit(1 if pending else 0)
'''
        for name in ('id', 'hostname', 'sudo', 'claude', 'workspace-login', 'workspace-browser'):
            p=self.bin/name
            p.write_text('#!'+sys.executable+'\n'+stub)
            p.chmod(0o755)
        self.env=dict(os.environ,PATH=str(self.bin)+os.pathsep+os.environ['PATH'],
                      PS0='\x1b]3008;fixture\x07',PS1='fixture> ')

    def tearDown(self):
        self.tmp.cleanup()

    def exercise(self):
        import pty
        program=(ROOT/'scripts/verify-session.py').read_text().replace('__PREFIX__','WS_fixture').replace('__VM__','employee-fixture')
        encoded=base64.b64encode(program.encode()).decode()
        self.assertLess(len(encoded),3500)
        command='stty -echo; exec '+shlex.quote(sys.executable)+" -c 'import base64;exec(base64.b64decode(\""+encoded+"\"))' </dev/null\n"
        self.assertLess(len(command.encode()),4096)
        master,slave=pty.openpty()
        process=subprocess.Popen(['/bin/bash','--noprofile','--norc','-i'],stdin=slave,stdout=slave,stderr=slave,env=self.env)
        os.close(slave)
        output=bytearray()
        try:
            os.write(master,command.encode())
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                if select.select([master],[],[],.1)[0]:
                    try:chunk=os.read(master,65536)
                    except OSError as error:
                        if error.errno==errno.EIO:break
                        raise
                    if not chunk:break
                    output.extend(chunk)
                elif process.poll() is not None:break
            process.wait(timeout=1)
            self.assertEqual(process.returncode,0)
        finally:
            if process.poll() is None:process.kill();process.wait()
            os.close(master)
        decoded=output.decode(errors='replace').replace('\r','')
        self.assertNotIn('PRIVATE_AUTH_SENTINEL',decoded)
        self.assertIn('\nWS_fixture_END\n',decoded)
        for field in ('USER','VM','SUDO','CLI'):
            self.assertIn('WS_fixture_'+field+'=passed',decoded)
        return decoded

    @unittest.skipUnless(sys.platform.startswith("linux"), "Target VM uses Linux canonical PTY; macOS canonical buffer is 1024 bytes")
    def test_single_line_finishes_despite_greedy_cli_stdin(self):
        self.assertIn('WS_fixture_AUTH=passed',self.exercise())

    @unittest.skipUnless(sys.platform.startswith("linux"), "Target VM uses Linux canonical PTY; macOS canonical buffer is 1024 bytes")
    def test_logged_out_exit_one_is_an_expected_user_action(self):
        self.env['PENDING_AUTH']='1'
        self.assertIn('WS_fixture_AUTH=user_action_required',self.exercise())

    @unittest.skipUnless(sys.platform.startswith("linux"), "Target VM uses Linux canonical PTY; macOS canonical buffer is 1024 bytes")
    def test_invalid_auth_output_is_an_error_not_a_login_request(self):
        self.env['BROKEN_AUTH']='1'
        self.assertIn('WS_fixture_AUTH=unavailable',self.exercise())

    def test_watchdog_actually_bounds_a_stalled_process(self):
        source=(ROOT/'scripts/unix.sh').read_text()
        function=source[source.index('run_bounded() {'):source.index('normalize_terminal() {')]
        script='stage='+shlex.quote(str(self.path))+'\n'+function+'\nrun_bounded 1 sleep 10\n'
        start=time.monotonic()
        result=subprocess.run(['/bin/bash','-c',script],capture_output=True,text=True,timeout=4)
        self.assertEqual(result.returncode,124)
        self.assertLess(time.monotonic()-start,4)

if __name__=='__main__':unittest.main()
