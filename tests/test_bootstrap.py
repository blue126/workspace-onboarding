#!/usr/bin/env python3
"""Credential-free tests of native entry points; no real VPN or SSH servers."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = os.name == "nt"

class Bootstrap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root_temp = tempfile.TemporaryDirectory(prefix="onboarding-synthetic-")
        cls.base = Path(cls.root_temp.name)
        cls.key = cls.base / "fixture-key"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(cls.key)], check=True)
        cls.public = cls.key.with_suffix(".pub").read_text().split()[:2]

    @classmethod
    def tearDownClass(cls):
        cls.root_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="onboarding-case-")
        self.path = Path(self.temp.name)
        self.bin = self.path / "bin"
        self.bin.mkdir()
        self.source_root = ROOT
        self.default_bundle = False
        self.default_state = False
        self.state = self.path / "private state"
        self.package = self.path / "fixture.zip"
        self.manifest = {
            "schema_version": 1, "tool_version": "1.0.0", "device_id": "ed-fixture-test",
            "vm_hostname": "employee-fixture", "ssh_gateway": "10.77.0.1",
            "wireguard_address": "10.77.0.2/32", "wireguard_endpoint": "203.0.113.10",
            "tunnel_name": "ws-1234abcd",
            "wireguard_public_key": base64.b64encode(b"a"*32).decode(),
            "client_wireguard_public_key": base64.b64encode(b"b"*32).decode(),
        }
        self.data = {
            "manifest.json": json.dumps(self.manifest).encode(),
            "client-key": self.key.read_bytes(),
            "wg.key": base64.b64encode(b"c"*32) + b"\n",
            "known_hosts": ("10.77.0.1 " + " ".join(self.public) + "\n").encode(),
        }
        self.env = dict(os.environ, PATH=str(self.bin)+os.pathsep+os.environ["PATH"],
                        FIXTURE=str(self.path), FIXTURE_PYTHON=sys.executable)
        self.bundle()
        if not WINDOWS:
            self.stubs()

    def tearDown(self):
        self.temp.cleanup()

    def bundle(self, entries=None):
        with zipfile.ZipFile(self.package, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, value in (entries or self.data).items():
                archive.writestr(name, value)
        self.digest = hashlib.sha256(self.package.read_bytes()).hexdigest()

    def command(self, action, *extra):
        if WINDOWS:
            shell = os.environ.get("TEST_POWERSHELL", "pwsh")
            bundle_args=[] if self.default_bundle else ["-Bundle", str(self.package), "-Sha256", self.digest]
            return [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(self.source_root/"bootstrap.ps1"),
                    action, *bundle_args, *([] if self.default_state else ["-StateRoot", str(self.state)]), *extra]
        bundle_args=[] if self.default_bundle else ["--bundle", str(self.package), "--sha256", self.digest]
        return ["/bin/bash", str(self.source_root/"bootstrap.sh"), action, *bundle_args,
                *([] if self.default_state else ["--state-root", str(self.state)]), *extra]

    def default_locations(self):
        self.default_bundle=True
        self.source_root=self.path/"public-source"
        self.source_root.mkdir()
        for name in ("bootstrap.sh","bootstrap.ps1"):
            shutil.copyfile(ROOT/name,self.source_root/name)
        shutil.copytree(ROOT/"scripts",self.source_root/"scripts",ignore=shutil.ignore_patterns("__pycache__"))
        profile=self.path/"user-profile"
        profile.mkdir()
        self.env["HOME"]=str(profile)
        self.env["USERPROFILE"]=str(profile)
        primary=profile/"Downloads"/"employee-workspace"
        fallback=self.source_root/"deployment"
        return primary,fallback

    def place_default_bundle(self, directory):
        directory.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(self.package,directory/"device-bundle.zip")
        (directory/"device-bundle.sha256").write_text(self.digest+"\n")
        (directory/"README.md").write_text("Synthetic device connection sheet\n")

    def test_default_install_uses_visible_user_directory_and_preserves_old_state(self):
        primary,_=self.default_locations()
        self.place_default_bundle(primary)
        self.default_state=True
        profile=Path(self.env["USERPROFILE"])
        old=profile/"Library"/"Application Support"/"WorkspaceOnboarding"/"preserve.txt"
        old.parent.mkdir(parents=True)
        old.write_text("existing-user-config")
        self.setup()
        installed=profile/"EmployeeWorkspace"/"devices"/self.manifest["device_id"]
        self.assertTrue((installed/"ssh_config").is_file())
        self.assertIn(str(installed.resolve()).replace("\\","/"),(installed/"ssh_config").read_text())
        self.assertEqual(old.read_text(),"existing-user-config")
        before={p.name:p.read_bytes() for p in installed.iterdir()}
        self.setup()
        self.assertEqual(before,{p.name:p.read_bytes() for p in installed.iterdir()})

    def test_default_download_directory_has_priority(self):
        primary,fallback=self.default_locations()
        self.place_default_bundle(primary)
        self.place_default_bundle(fallback)
        (fallback/"device-bundle.zip").write_bytes(b"wrong-other-device")
        _,report=self.call("check")
        self.assertIn(report["code"],("CHECKED","DEPENDENCY_MISSING"))
        self.assertTrue(report["package_verified"])

    def test_project_fallback_when_download_directory_has_no_device_files(self):
        primary,fallback=self.default_locations()
        primary.mkdir(parents=True)
        self.place_default_bundle(fallback)
        _,report=self.call("check")
        self.assertIn(report["code"],("CHECKED","DEPENDENCY_MISSING"))
        self.assertTrue(report["package_verified"])

    def test_partial_primary_does_not_select_other_fallback_identity(self):
        primary,fallback=self.default_locations()
        primary.mkdir(parents=True)
        (primary/"device-bundle.sha256").write_text(self.digest+"\n")
        self.place_default_bundle(fallback)
        self.call("check",code="PACKAGE_MISSING")

    def test_invalid_primary_digest_does_not_select_fallback(self):
        primary,fallback=self.default_locations()
        self.place_default_bundle(primary)
        self.place_default_bundle(fallback)
        (primary/"device-bundle.sha256").write_text("0"*64+"\n")
        self.call("check",code="PACKAGE_HASH_MISMATCH")

    def test_missing_default_bundle_is_reported(self):
        self.default_locations()
        self.call("check",code="PACKAGE_MISSING")

    def call(self, action, *extra, code=None):
        run = subprocess.run(self.command(action, *extra), env=self.env, capture_output=True, text=True, timeout=100)
        # No private key material or synthetic stderr secrets may reach reports.
        self.assertNotIn(self.key.read_text().strip(), run.stdout+run.stderr)
        self.assertNotIn("PRIVATE_FAILURE_SENTINEL", run.stdout+run.stderr)
        lines = [line for line in run.stdout.splitlines() if line.startswith("{")]
        self.assertTrue(lines, (run.returncode, run.stdout[-400:], run.stderr[-400:]))
        report = json.loads(lines[-1])
        if code:
            self.assertEqual(report["code"], code, (run.returncode, report, run.stderr[-300:]))
        return run, report

    def setup(self):
        switch = "-NoActivate" if WINDOWS else "--no-activate"
        return self.call("setup", switch, code="CONFIGURED")

    def stubs(self):
        dispatch = r'''import json,os,pathlib,shlex,shutil,sys,time
p=pathlib.Path(os.environ["FIXTURE"]);args=sys.argv[1:];name=pathlib.Path(sys.argv[0]).name
m=json.loads((p/"manifest-test.json").read_text())
with (p/"commands.jsonl").open("a") as f:f.write(json.dumps([name,args])+"\n")
if name=="sudo":
 if args==["-n","true"]:sys.exit(1 if os.environ.get("NEEDS_SUDO") else 0)
 if args[:1]==["cat"] and args[1].startswith("/var/run/wireguard/"):
  if not (p/"tunnel-active").exists():sys.exit(1)
  print("utun9");sys.exit(0)
 os.execvp(args[0],args)
if name=="ssh":
 assert args[-1]=="workspace" and "-tt" in args and len(args)==4,args
 data=sys.stdin.read()
 import re
 assert data.count("\n")==1 and "exec python3 -c" in data and "</dev/null" in data,data
 encoded=re.search(r'base64.b64decode\("([A-Za-z0-9+/=]+)"\)',data).group(1)
 import base64
 decoded=base64.b64decode(encoded).decode()
 prefix=re.search(r"WS_[a-f0-9]+",decoded).group()
 scenario=os.environ.get("SSH_SCENARIO","")
 if scenario=="host-key":
  print("Host key verification failed. PRIVATE_FAILURE_SENTINEL",file=sys.stderr);sys.exit(255)
 def emit(line):
  if scenario=="osc":line="\x1b]3008;context=fixture\x07\x1b[32m"+line+"\x1b[0m\x1b]133;D\x1b\\"
  print(line)
 emit(prefix+"_BEGIN")
 for key in ("USER","VM","SUDO","CLI","AUTH"):
  if scenario=="missing-field" and key=="CLI":continue
  value="failed" if key=="VM" and scenario=="wrong-vm" else "passed"
  if key=="AUTH" and scenario=="pending":value="user_action_required"
  if key=="AUTH" and scenario=="auth-invalid":value="unavailable"
  emit(prefix+"_"+key+"="+value)
  if key=="USER" and scenario=="duplicate":emit(prefix+"_USER=passed")
 emit(prefix+"_END")
elif name=="sftp":
 assert args[-1]=="workspace" and "-s" not in args,args
 lines=pathlib.Path(args[args.index("-b")+1]).read_text().splitlines()
 root=p/"remote";root.mkdir(exist_ok=True)
 def remote(value):return root/pathlib.PurePosixPath(value).relative_to("/tmp")
 for line in lines:
  a=shlex.split(line)
  if a[0]=="mkdir":remote(a[1]).mkdir()
  elif a[0]=="put":shutil.copyfile(a[1],remote(a[2]))
  elif a[0]=="get":
   shutil.copyfile(remote(a[1]),a[2])
   if os.environ.get("SFTP_CORRUPT"):pathlib.Path(a[2]).write_text("changed")
  elif a[0]=="rm":remote(a[1]).unlink()
  elif a[0]=="rmdir":remote(a[1]).rmdir()
  else:raise AssertionError(a)
elif name=="wg":
 if args==["show","interfaces"]:
  print(("utun9" if sys.platform=="darwin" else m["tunnel_name"]) if (p/"tunnel-active").exists() else "")
 elif args[-1]=="public-key":print("wrong" if os.environ.get("WRONG_TUNNEL") else m["client_wireguard_public_key"])
 elif args[-1]=="peers":print(m["wireguard_public_key"])
 elif args[-1]=="allowed-ips":print(m["wireguard_public_key"]+"\t"+m["ssh_gateway"]+"/32")
 elif args[-1]=="latest-handshakes":print(m["wireguard_public_key"]+"\t"+str(0 if os.environ.get("STALE_WG") else int(time.time())))
 else:raise AssertionError(args)
elif name=="wg-quick":
 if args[0]=="up":(p/"tunnel-active").touch()
 elif args[0]=="down":(p/"tunnel-active").unlink()
 else:raise AssertionError(args)
elif name=="wireguard-go":sys.exit(0)
elif name=="ifconfig":
 if args==["-a"]:
  print("inet "+m["wireguard_address"].split("/")[0] if os.environ.get("ADDRESS_CONFLICT") else "inet 127.0.0.1")
 else:
  assert args==["utun9"],args
  print("inet "+m["wireguard_address"].split("/")[0]+" netmask 0xffffffff")
elif name=="route":
 assert args==["-n","get",m["ssh_gateway"]],args
 print("destination: "+(m["ssh_gateway"] if os.environ.get("ROUTE_CONFLICT") else "default"))
 print("interface: "+("utun8" if os.environ.get("ROUTE_CONFLICT") else "en0"))
elif name=="ip":
 if args[:4]==["-o","-4","addr","show"]:print("2: "+m["tunnel_name"]+" inet "+m["wireguard_address"])
 elif args[:4]==["-4","route","show","match"]:
  print("10.77.0.0/24 dev other-vpn" if os.environ.get("ROUTE_CONFLICT") else "default via 192.0.2.1 dev eth0")
 else:raise AssertionError(args)
'''
        (self.path/"manifest-test.json").write_text(json.dumps(self.manifest))
        for name in ("ssh", "sftp", "sudo", "wg", "wg-quick", "ip", "wireguard-go", "ifconfig", "route"):
            path = self.bin/name
            path.write_text("#!"+sys.executable+"\n"+dispatch)
            path.chmod(0o755)

    def test_hash_rejected_before_import(self):
        self.package.write_bytes(self.package.read_bytes()+b"changed")
        self.call("setup", code="PACKAGE_HASH_MISMATCH")
        self.assertFalse(self.state.exists())

    def test_traversal_rejected_before_extraction(self):
        values=dict(self.data)
        values["../outside"]=b"no"
        self.bundle(values)
        self.call("setup", code="PACKAGE_UNSAFE")
        self.assertFalse((self.path/"outside").exists())

    def test_unknown_executable_rejected(self):
        self.bundle(dict(self.data, **{"install.sh":b"echo dangerous"}))
        self.call("setup", code="PACKAGE_UNSAFE")

    def test_oversized_entry_rejected(self):
        self.data["manifest.json"]=b"x"*70000
        self.bundle()
        self.call("setup", code="PACKAGE_TOO_LARGE" if not WINDOWS else "PACKAGE_UNSAFE")

    def test_email_username_device_id_needs_no_prefix(self):
        self.manifest['device_id']='zhang171903992'
        self.data['manifest.json']=json.dumps(self.manifest).encode()
        self.bundle()
        self.setup()
        installed=self.state/'zhang171903992'
        self.assertIn('User zhang171903992',(installed/'ssh_config').read_text())
    def test_setup_is_idempotent_and_private(self):
        self.setup()
        installed=self.state/self.manifest["device_id"]
        before={p.name:p.read_bytes() for p in installed.iterdir()}
        self.setup()
        self.assertEqual(before,{p.name:p.read_bytes() for p in installed.iterdir()})
        config=(installed/"ssh_config").read_text()
        self.assertIn("StrictHostKeyChecking yes",config)
        self.assertIn("ProxyCommand none",config)
        self.assertIn("ClearAllForwardings yes",config)
        self.assertNotIn("PostUp",next(installed.glob("ws-*.conf")).read_text())
        if not WINDOWS:
            self.assertEqual(stat.S_IMODE(installed.stat().st_mode),0o700)
            for path in installed.iterdir():self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)

    def test_existing_different_identity_not_overwritten(self):
        self.setup()
        key=self.state/self.manifest["device_id"]/"client-key"
        key.write_text("changed-by-user")
        self.call("setup",code="CONFIG_CONFLICT")
        self.assertEqual(key.read_text(),"changed-by-user")

    def test_manifest_rejects_shell_injection(self):
        self.manifest["vm_hostname"]="employee-x;touch /tmp/unexpected"
        self.data["manifest.json"]=json.dumps(self.manifest).encode()
        self.bundle()
        self.call("setup",code="MANIFEST_INVALID")

    def test_manifest_rejects_unknown_execution_fields(self):
        self.manifest["PostUp"]="echo PRIVATE_FAILURE_SENTINEL"
        self.data["manifest.json"]=json.dumps(self.manifest).encode()
        self.bundle()
        self.call("setup",code="MANIFEST_INVALID")

    @unittest.skipIf(WINDOWS, "Unix permission behavior")
    def test_symlink_archive_entry_rejected(self):
        with zipfile.ZipFile(self.package,"w") as z:
            for name,value in self.data.items():
                if name=="client-key":
                    info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16
                    z.writestr(info,"/etc/passwd")
                else:z.writestr(name,value)
        self.digest=hashlib.sha256(self.package.read_bytes()).hexdigest()
        self.call("setup",code="PACKAGE_UNSAFE")

    @unittest.skipIf(WINDOWS, "Unix command transport fixture")
    def test_verify_pty_sftp_and_redaction(self):
        self.setup()
        (self.path/"tunnel-active").touch()
        _,r=self.call("verify")
        for key in ("ssh_identity","assigned_vm","sudo","cli","sftp_roundtrip","claude_auth"):self.assertEqual(r[key],"passed")
        self.assertEqual(list((self.path/"remote").iterdir()),[])

    @unittest.skipIf(WINDOWS, "Unix terminal framing")
    def test_verify_accepts_osc_bel_st_and_csi_without_shell_changes(self):
        self.setup();(self.path/"tunnel-active").touch();self.env["SSH_SCENARIO"]="osc"
        self.call("verify",code="CONNECTION_VERIFIED")

    @unittest.skipIf(WINDOWS, "Unix terminal framing")
    def test_duplicate_or_missing_records_stop_instead_of_claiming_success(self):
        self.setup();(self.path/"tunnel-active").touch()
        for scenario in ("duplicate","missing-field"):
            self.env["SSH_SCENARIO"]=scenario
            self.call("verify",code="SSH_PROTOCOL_FAILED")

    @unittest.skipIf(WINDOWS, "Unix auth-check failure")
    def test_broken_auth_check_is_not_misreported_as_logged_out(self):
        self.setup();(self.path/"tunnel-active").touch();self.env["SSH_SCENARIO"]="auth-invalid"
        _,report=self.call("verify",code="CLAUDE_AUTH_CHECK_FAILED")
        self.assertEqual(report["claude_auth"],"unavailable")

    @unittest.skipIf(WINDOWS, "Unix command transport fixture")
    def test_wrong_vm_stops_before_sftp(self):
        self.setup();(self.path/"tunnel-active").touch();self.env["SSH_SCENARIO"]="wrong-vm"
        self.call("verify",code="WORKSPACE_ID_MISMATCH")
        calls=[json.loads(x)[0] for x in (self.path/"commands.jsonl").read_text().splitlines()]
        self.assertNotIn("sftp",calls)

    @unittest.skipIf(WINDOWS, "Unix command transport fixture")
    def test_host_key_failure_is_sanitized(self):
        self.setup();(self.path/"tunnel-active").touch();self.env["SSH_SCENARIO"]="host-key"
        self.call("verify",code="SSH_HOST_KEY_MISMATCH")

    @unittest.skipIf(WINDOWS, "Unix command transport fixture")
    def test_personal_authorization_is_not_assumed(self):
        self.setup();(self.path/"tunnel-active").touch()
        self.env["SSH_SCENARIO"]="pending"
        _,r=self.call("verify",code="CLAUDE_AUTH_USER_PENDING")
        self.assertEqual(r["real_task"],"pending")

    @unittest.skipIf(WINDOWS, "Unix CLI route/tunnel behavior")
    def test_route_conflict_not_changed(self):
        self.env["ROUTE_CONFLICT"]="1"
        self.call("setup",code="ROUTE_CONFLICT")
        self.assertFalse((self.path/"tunnel-active").exists())

    @unittest.skipIf(WINDOWS, "Unix CLI route/tunnel behavior")
    def test_foreign_tunnel_not_stopped(self):
        self.setup();(self.path/"tunnel-active").touch();self.env["WRONG_TUNNEL"]="1"
        self.call("disconnect",code="TUNNEL_CONFLICT")
        self.assertTrue((self.path/"tunnel-active").exists())

    @unittest.skipIf(WINDOWS, "Unix CLI handshake behavior")
    def test_stale_handshake_not_passed(self):
        self.setup();(self.path/"tunnel-active").touch();self.env["STALE_WG"]="1"
        self.call("verify",code="NO_RECENT_HANDSHAKE")

    @unittest.skipUnless(sys.platform=="darwin", "macOS CLI interface mapping")
    def test_macos_cli_uses_runtime_utun_mapping_and_is_idempotent(self):
        self.call("setup",code="CONFIGURED")
        self.call("setup",code="CONFIGURED")
        calls=[json.loads(line) for line in (self.path/"commands.jsonl").read_text().splitlines()]
        ups=[args for name,args in calls if name=="wg-quick" and args[0]=="up"]
        self.assertEqual(len(ups),1)
        queries=[args for name,args in calls if name=="wg" and args[-1]=="public-key"]
        self.assertTrue(queries)
        self.assertTrue(all(args[1]=="utun9" for args in queries))

    @unittest.skipUnless(sys.platform=="darwin", "macOS GUI address conflict")
    def test_existing_gui_address_is_not_taken_over(self):
        self.env["ADDRESS_CONFLICT"]="1"
        self.call("setup",code="ROUTE_CONFLICT")
        self.assertFalse((self.path/"tunnel-active").exists())

    @unittest.skipIf(WINDOWS, "Unix sudo handoff")
    def test_noninteractive_sudo_handoff_does_not_start_tunnel(self):
        self.env["NEEDS_SUDO"]="1"
        self.call("setup",code="NEEDS_ADMIN")
        self.assertFalse((self.path/"tunnel-active").exists())

    @unittest.skipIf(WINDOWS, "Unix CLI route/tunnel behavior")
    def test_only_owned_tunnel_started_and_stopped(self):
        self.call("setup",code="CONFIGURED")
        self.assertTrue((self.path/"tunnel-active").exists())
        self.call("disconnect",code="DISCONNECTED")
        self.assertFalse((self.path/"tunnel-active").exists())

if __name__=="__main__":
    unittest.main()
