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


def tunnel_for(device):
    # The administrator derives the tunnel name from the device; the bootstrap checks it.
    return "wh-" + hashlib.sha256(("oci-hub:" + device).encode()).hexdigest()[:8]
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
            # Only the unified OCI Hub bundle is supported: Mosh terminal and VM browser entry.
            "schema_version": 2, "tool_version": "2.0.0", "device_id": "ed-fixture-test",
            "vm_hostname": "oci-hub-fixture", "ssh_gateway": "10.77.0.1",
            "wireguard_address": "10.77.0.2/32", "wireguard_endpoint": "203.0.113.10",
            "tunnel_name": tunnel_for("ed-fixture-test"), "profile": "oci-hub", "ssh_user": "employee",
            "ssh_alias": "oci-hub-ed-fixture-test", "access_mode": "mosh", "mosh_ports": "60000:61000",
            # The openssl stub presents b"synthetic DER" as the VM browser certificate.
            "desktop_url": "https://10.77.0.1:8443/", "tls_certificate_sha256": hashlib.sha256(b"synthetic DER").hexdigest(),
            "wireguard_public_key": base64.b64encode(b"a"*32).decode(),
            "client_wireguard_public_key": base64.b64encode(b"b"*32).decode(),
        }
        self.data = {
            "manifest.json": json.dumps(self.manifest).encode(),
            "client-key": self.key.read_bytes(),
            "wg.key": base64.b64encode(b"c"*32) + b"\n",
            "known_hosts": ("10.77.0.1 " + " ".join(self.public) + "\n").encode(),
        }
        # A private HOME keeps setup away from the real ~/.ssh/config.
        self.home = self.path / "home"
        self.home.mkdir()
        self.env = dict(os.environ, PATH=str(self.bin)+os.pathsep+os.environ["PATH"],
                        FIXTURE=str(self.path), FIXTURE_PYTHON=sys.executable,
                        HOME=str(self.home), USERPROFILE=str(self.home))
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
        installed=profile/"EmployeeWorkspace"/"devices"/"oci-hub"/self.manifest["device_id"]
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
 if args==["-v"]:sys.exit(1 if os.environ.get("SUDO_DENIED") else 0)
 if args[:1]==["cat"] and args[1].startswith("/var/run/wireguard/"):
  if not (p/"tunnel-active").exists():sys.exit(1)
  print("utun9");sys.exit(0)
 if os.environ.get("RESET_SUDO_PATH"):os.environ["PATH"]="/usr/bin:/bin:/usr/sbin:/sbin"
 os.execvp(args[0],args)
if name=="bash":
 if args==["--noprofile","--norc","-c","[[ ${BASH_VERSINFO[0]} -ge 4 ]]"]:sys.exit(0)
 assert pathlib.Path(args[0]).name=="wg-quick",args
 os.execv(args[0],args)
if name=="ssh":
 assert args[-1]==m.get("ssh_alias","workspace") and "-tt" in args and len(args)==4,args
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
 assert args[-1]==m.get("ssh_alias","workspace") and "-s" not in args,args
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
elif name=="openssl":
 if args[0]=="s_client":print("synthetic certificate")
 elif args[0]=="x509":pathlib.Path(args[args.index("-out")+1]).write_bytes(b"synthetic DER")
 else:raise AssertionError(args)
elif name=="wg":
 if args==["--version"]:print("wireguard-tools fixture")
 elif args==["show","interfaces"]:
  print(("utun9" if sys.platform=="darwin" else m["tunnel_name"]) if (p/"tunnel-active").exists() else "")
 elif args[-1]=="public-key":print("wrong" if os.environ.get("WRONG_TUNNEL") else ((p/"tunnel-active").read_text().strip() or m["client_wireguard_public_key"]))
 elif args[-1]=="peers":print(m["wireguard_public_key"])
 elif args[-1]=="allowed-ips":print(m["wireguard_public_key"]+"\t"+m["ssh_gateway"]+"/32")
 elif args[-1]=="latest-handshakes":print(m["wireguard_public_key"]+"\t"+str(0 if os.environ.get("STALE_WG") else int(time.time())))
 else:raise AssertionError(args)
elif name=="wg-quick":
 if args==["--help"]:
  if os.environ.get("BROKEN_WG_QUICK"):sys.exit(1)
  print("Usage: wg-quick [ up | down | strip ]")
 elif args[0]=="up":(p/"tunnel-active").write_text(m["client_wireguard_public_key"])
 elif args[0]=="down":(p/"tunnel-active").unlink()
 else:raise AssertionError(args)
elif name=="wireguard-go":sys.exit(0)
elif name=="ifconfig":
 if args==["-a"]:
  print("inet "+m["wireguard_address"].split("/")[0] if os.environ.get("ADDRESS_CONFLICT") else "inet 127.0.0.1")
 else:
  assert len(args)==1 and args[0].startswith("utun"),args
  if args[0]=="utun9":print("inet "+m["wireguard_address"].split("/")[0]+" netmask 0xffffffff")
  else:print("inet 10.200.0.2 netmask 0xffffffff")
elif name=="route":
 assert args==["-n","get",m["ssh_gateway"]],args
 if os.environ.get("ROUTE_CONFLICT"):print("destination: "+m["ssh_gateway"]);print("interface: utun8")
 elif (p/"tunnel-active").exists():print("destination: "+m["ssh_gateway"]);print("interface: utun9")
 else:print("destination: default");print("interface: en0")
elif name=="ip":
 if args[:4]==["-o","-4","addr","show"]:
  if args[-1]==m["tunnel_name"]:print("2: "+m["tunnel_name"]+" inet "+m["wireguard_address"])
 elif args[:4]==["-o","-4","route","get"]:
  assert args[4:]==[m["ssh_gateway"]],args
  if os.environ.get("ROUTE_CONFLICT"):print(m["ssh_gateway"]+" dev other-vpn src 10.200.0.2")
  elif (p/"tunnel-active").exists():print(m["ssh_gateway"]+" dev "+m["tunnel_name"]+" src "+m["wireguard_address"].split("/")[0])
  else:print(m["ssh_gateway"]+" via 192.0.2.1 dev eth0 src 192.0.2.10")
 elif args[:4]==["-4","route","show","match"]:
  print("10.77.0.0/24 dev other-vpn" if os.environ.get("ROUTE_CONFLICT") else "default via 192.0.2.1 dev eth0")
 else:raise AssertionError(args)
'''
        (self.path/"manifest-test.json").write_text(json.dumps(self.manifest))
        for name in ("ssh", "sftp", "sudo", "wg", "wg-quick", "ip", "wireguard-go", "ifconfig", "route", "bash", "openssl"):
            path = self.bin/name
            path.write_text("#!"+sys.executable+"\n"+dispatch)
            path.chmod(0o755)

    def install_env(self):
        # Record package-manager calls; keep the host's real Mosh off PATH.
        for name in ("brew","apt-get"):
            path=self.bin/name
            path.write_text("#!"+sys.executable+"\nimport json,os,pathlib,sys\n"
                "with (pathlib.Path(os.environ['FIXTURE'])/'installs.jsonl').open('a') as f:"
                "f.write(json.dumps([pathlib.Path(sys.argv[0]).name,sys.argv[1:]])+'\\n')\n")
            path.chmod(0o755)
        self.env["PATH"]=os.pathsep.join([str(self.bin),"/usr/bin","/bin","/usr/sbin","/sbin"])

    def installs(self):
        log=self.path/"installs.jsonl"
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    @unittest.skipIf(WINDOWS,"Windows uses Mosh in WSL")
    def test_install_clients_installs_missing_mosh(self):
        self.install_env()
        search=self.env["PATH"]+(":/opt/homebrew/bin:/usr/local/bin" if sys.platform=="darwin" else "")
        if shutil.which("mosh",path=search):self.skipTest("host Mosh is on the bootstrap PATH")
        self.call("setup","--no-activate","--install-clients",code="CONFIGURED")
        if sys.platform=="darwin":
            self.assertIn(["brew",["install","mosh"]],self.installs())
        else:
            self.assertIn("mosh",[arg for name,args in self.installs() if name=="apt-get" and args[:2]==["install","-y"] for arg in args])

    @unittest.skipIf(WINDOWS,"Windows uses Mosh in WSL")
    def test_install_clients_keeps_existing_mosh(self):
        self.install_env()
        p=self.bin/"mosh";p.write_text("#!/bin/sh\nexit 0\n");p.chmod(0o755)
        self.call("setup","--no-activate","--install-clients",code="CONFIGURED")
        self.assertFalse([1 for name,args in self.installs() if "mosh" in args])

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
        self.manifest.update(device_id='zhang171903992',ssh_alias='oci-hub-zhang171903992',tunnel_name=tunnel_for('zhang171903992'))
        self.data['manifest.json']=json.dumps(self.manifest).encode()
        self.bundle()
        self.setup()
        installed=self.state/'oci-hub'/'zhang171903992'
        self.assertIn('Host oci-hub-zhang171903992',(installed/'ssh_config').read_text())
    def test_setup_is_idempotent_and_private(self):
        self.setup()
        installed=self.native_state()
        before={p.name:p.read_bytes() for p in installed.iterdir()}
        self.setup()
        self.assertEqual(before,{p.name:p.read_bytes() for p in installed.iterdir()})
        config=(installed/"ssh_config").read_text()
        self.assertIn("StrictHostKeyChecking yes",config)
        self.assertIn("ProxyCommand none",config)
        self.assertIn("ClearAllForwardings yes",config)
        self.assertNotIn("PostUp",next(installed.glob("wh-*.conf")).read_text())
        if not WINDOWS:
            self.assertEqual(stat.S_IMODE(installed.stat().st_mode),0o700)
            for path in installed.iterdir():self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)

    def test_existing_different_identity_not_overwritten(self):
        self.setup()
        key=self.native_state()/"client-key"
        key.write_text("changed-by-user")
        self.call("setup",code="CONFIG_CONFLICT")
        self.assertEqual(key.read_text(),"changed-by-user")

    def reissue(self):
        # The administrator reissues the same device with new keys and a new address.
        self.manifest.update(client_wireguard_public_key=base64.b64encode(b"d"*32).decode(),wireguard_address="10.77.0.3/32")
        self.data["manifest.json"]=json.dumps(self.manifest).encode()
        self.data["wg.key"]=base64.b64encode(b"e"*32)+b"\n"
        self.bundle()
        if not WINDOWS:(self.path/"manifest-test.json").write_text(json.dumps(self.manifest))

    def test_reissued_bundle_replaces_and_archives_previous_install(self):
        self.setup()
        old={q.name:q.read_bytes() for q in self.native_state().iterdir()}
        self.reissue()
        self.call("check",code="REISSUE_READY")
        self.call("verify",code="REISSUE_READY")
        self.setup()
        archives=list((self.native_state().parent/".archive").iterdir())
        self.assertEqual(len(archives),1)
        self.assertEqual(old,{q.name:q.read_bytes() for q in archives[0].iterdir()})
        self.assertIn(json.dumps(self.manifest).encode(),(self.native_state()/"manifest.json").read_bytes())
        # CI Windows has no WireGuard; the reissue state is resolved either way.
        self.call("check",code="DEPENDENCY_MISSING" if WINDOWS else "CHECKED")

    @unittest.skipIf(WINDOWS, "Unix CLI route/tunnel behavior")
    def test_reissue_stops_only_the_previous_tunnel_of_this_device(self):
        self.call("setup",code="CONFIGURED")
        self.reissue()
        self.call("setup",code="CONFIGURED")
        calls=[json.loads(line) for line in (self.path/"commands.jsonl").read_text().splitlines()]
        quick=[args[:1] for name,args in calls if name=="wg-quick" and args[0] in ("up","down")]
        self.assertEqual(quick,[["up"],["down"],["up"]])
        self.assertEqual((self.path/"tunnel-active").read_text(),self.manifest["client_wireguard_public_key"])

    @unittest.skipIf(WINDOWS, "Unix CLI route/tunnel behavior")
    def test_reissue_keeps_a_foreign_tunnel_and_the_previous_install(self):
        self.call("setup",code="CONFIGURED")
        old={q.name:q.read_bytes() for q in self.native_state().iterdir()}
        self.reissue();self.env["WRONG_TUNNEL"]="1"
        self.call("setup",code="TUNNEL_CONFLICT")
        self.assertTrue((self.path/"tunnel-active").exists())
        self.assertEqual(old,{q.name:q.read_bytes() for q in self.native_state().iterdir()})

    def test_manifest_rejects_shell_injection(self):
        self.manifest["vm_hostname"]="employee-x;touch /tmp/unexpected"
        self.data["manifest.json"]=json.dumps(self.manifest).encode()
        self.bundle()
        self.call("setup",code="MANIFEST_INVALID")

    def test_endpoint_accepts_a_dns_name(self):
        self.manifest["wireguard_endpoint"]="ga-example.accelerator.example.com"
        self.data["manifest.json"]=json.dumps(self.manifest).encode()
        self.bundle()
        self.call("setup")
        conf=next(p for p in self.state.rglob("*.conf") if "[Peer]" in p.read_text())
        self.assertIn("Endpoint = ga-example.accelerator.example.com:", conf.read_text())

    def test_endpoint_rejects_names_that_are_not_hostnames(self):
        for bad in ("Ga.Example.com","example","203.0.113.999","ga.example.com:51824","-ga.example.com","ga example.com"):
            with self.subTest(bad=bad):
                self.manifest["wireguard_endpoint"]=bad
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
        # Rejected from archive metadata, whether or not this unzip would extract the link.
        self.call("setup",code="PACKAGE_UNSAFE")
        self.assertFalse(self.state.exists())

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

    @unittest.skipIf(WINDOWS, "Unix terminal authorization with captured logs")
    def test_interactive_sudo_allows_redirected_output(self):
        import pty
        self.env["NEEDS_SUDO"]="1"
        master,slave=pty.openpty()
        try:
            run=subprocess.run(self.command("setup"),env=self.env,stdin=slave,
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=100)
        finally:
            os.close(slave);os.close(master)
        report=json.loads([line for line in run.stdout.splitlines() if line.startswith("{")][-1])
        self.assertEqual(report["code"],"CONFIGURED",run.stderr[-300:])
        self.assertTrue((self.path/"tunnel-active").exists())
        calls=[json.loads(line) for line in (self.path/"commands.jsonl").read_text().splitlines()]
        self.assertIn(["sudo",["-v"]],calls)

    @unittest.skipIf(WINDOWS, "Unix terminal authorization denial")
    def test_interactive_sudo_denial_does_not_start_tunnel(self):
        import pty
        self.env.update(NEEDS_SUDO="1",SUDO_DENIED="1")
        master,slave=pty.openpty()
        try:
            run=subprocess.run(self.command("setup"),env=self.env,stdin=slave,
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=100)
        finally:
            os.close(slave);os.close(master)
        report=json.loads([line for line in run.stdout.splitlines() if line.startswith("{")][-1])
        self.assertEqual(report["code"],"NEEDS_ADMIN")
        self.assertFalse((self.path/"tunnel-active").exists())

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

    @unittest.skipUnless(sys.platform=="darwin", "macOS sudo environment regression")
    def test_macos_explicit_bash_and_userspace_survive_sudo_path_reset(self):
        self.env["RESET_SUDO_PATH"]="1"
        self.call("setup",code="CONFIGURED")
        self.call("disconnect",code="DISCONNECTED")
        calls=[json.loads(line) for line in (self.path/"commands.jsonl").read_text().splitlines()]
        elevated=[args for name,args in calls if name=="sudo" and args[0]=="/usr/bin/env"]
        self.assertEqual(len(elevated),2)
        for args in elevated:
            self.assertEqual(args[2],"WG_QUICK_USERSPACE_IMPLEMENTATION="+str(self.bin/"wireguard-go"))
            self.assertEqual(args[3],str(self.bin/"bash"))
            self.assertEqual(args[4],str(self.bin/"wg-quick"))

    @unittest.skipUnless(sys.platform=="darwin", "macOS executable readiness regression")
    def test_macos_present_but_broken_wg_quick_is_not_ready(self):
        self.env["BROKEN_WG_QUICK"]="1"
        _,result=self.call("check",code="DEPENDENCY_MISSING")
        self.assertFalse(result["client_ready"])
        self.assertFalse((self.path/"tunnel-active").exists())

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

    def hub_manifest(self):
        # The default fixture is already the only supported kind; rebuild after edits.
        self.manifest.update(ssh_alias='oci-hub-'+self.manifest['device_id'],tunnel_name=tunnel_for(self.manifest['device_id']))
        self.data['manifest.json']=json.dumps(self.manifest).encode()
        self.bundle()
        if not WINDOWS:self.stubs()

    def test_retired_v1_terminal_only_and_desktop_only_bundles_are_unsupported(self):
        v1={k:v for k,v in self.manifest.items() if k not in ('profile','ssh_user','ssh_alias','access_mode','mosh_ports','desktop_url','tls_certificate_sha256')}
        v1.update(schema_version=1,tool_version='1.0.0',tunnel_name='ws-1234abcd',vm_hostname='employee-fixture')
        desktop={k:v for k,v in self.manifest.items() if k not in ('access_mode','mosh_ports')}
        terminal={k:v for k,v in self.manifest.items() if k not in ('desktop_url','tls_certificate_sha256')}
        for manifest in (v1,desktop,terminal,dict(self.manifest,access_mode='desktop')):
            self.data['manifest.json']=json.dumps(manifest).encode();self.bundle()
            run,_=self.call('setup',code='MANIFEST_UNSUPPORTED')
            self.assertIn('README',run.stderr)
            self.assertFalse(self.state.exists())

    def test_hub_unknown_profile_and_fields_rejected(self):
        self.hub_manifest();self.manifest['profile']='existing'
        self.data['manifest.json']=json.dumps(self.manifest).encode();self.bundle()
        self.call('setup',code='MANIFEST_UNSUPPORTED')
        self.manifest['profile']='oci-hub';self.manifest['PostUp']='echo no'
        self.data['manifest.json']=json.dumps(self.manifest).encode();self.bundle()
        self.call('setup',code='MANIFEST_INVALID')

    @unittest.skipUnless(WINDOWS,'Windows directory junction contract')
    def test_windows_v2_profile_root_junction_is_rejected(self):
        self.hub_manifest();self.state.mkdir()
        target=self.path/'unrelated-target';target.mkdir();marker=target/'preserve.txt';marker.write_text('preserve user data')
        link=self.state/'oci-hub'
        subprocess.run(['cmd','/c','mklink','/J',str(link),str(target)],check=True,capture_output=True)
        self.call('setup','-NoActivate',code='STATE_PATH_UNSAFE')
        self.assertEqual(marker.read_text(),'preserve user data')
        self.assertEqual(sorted(p.name for p in target.iterdir()),['preserve.txt'])

    @unittest.skipUnless(WINDOWS,'Windows original root junction contract')
    def test_windows_v2_original_root_junction_is_still_rejected(self):
        self.hub_manifest()
        target=self.path/'unrelated-original-target';target.mkdir();marker=target/'preserve.txt';marker.write_text('preserve user data')
        subprocess.run(['cmd','/c','mklink','/J',str(self.state),str(target)],check=True,capture_output=True)
        self.call('setup','-NoActivate',code='STATE_PATH_UNSAFE')
        self.assertEqual(sorted(p.name for p in target.iterdir()),['preserve.txt'])

    def test_v2_schema_and_runtime_accept_unprefixed_device_id(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest('jsonschema unavailable; do not install dependencies automatically')
        self.hub_manifest();self.manifest.update(device_id='alice',ssh_alias='oci-hub-alice',tunnel_name=tunnel_for('alice'))
        schema=json.loads((ROOT/'schemas/bundle-manifest.schema.json').read_text())
        jsonschema.validate(self.manifest,schema)
        for name in ('bundle-manifest.oci-hub-mosh.example.json',):
            jsonschema.validate(json.loads((ROOT/'examples'/name).read_text()),schema)
        self.data['manifest.json']=json.dumps(self.manifest).encode();self.bundle()
        self.setup()
        self.assertTrue((self.state/'oci-hub'/'alice'/'ssh_config').exists())
        bad=dict(self.manifest,device_id='alice;bad')
        with self.assertRaises(jsonschema.ValidationError):jsonschema.validate(bad,schema)

    def mosh_manifest(self):
        self.hub_manifest()

    def test_invalid_mosh_ports_and_vm_browser_identity_rejected(self):
        self.mosh_manifest();good=dict(self.manifest)
        changes=[dict(mosh_ports=p) for p in ('59999:60000','60039:60030','60030:61001','60030:60039;id','60030:60039','60000:60999')]
        # The tunnel name is derived from the device, not just shaped like one.
        changes+=[dict(tunnel_name='wh-1234abcd'),dict(tunnel_name=tunnel_for('someone-else'))]
        # The VM browser entry is this VM's overlay on 8443 with a lowercase SHA256 pin.
        changes+=[dict(desktop_url='https://10.77.0.9:8443/'),dict(desktop_url='http://10.77.0.1:8443/'),dict(desktop_url='https://10.77.0.1:443/'),
                  dict(tls_certificate_sha256='A'*64),dict(tls_certificate_sha256='a'*63),dict(viewer_url='https://10.77.0.1:8443/')]
        for change in changes:
            self.manifest=dict(good,**change);self.data['manifest.json']=json.dumps(self.manifest).encode();self.bundle()
            self.call('check',code='MANIFEST_INVALID')

    @unittest.skipIf(WINDOWS,'TLS fixture uses Unix openssl stub; Windows needs a synthetic TLS server')
    def test_verify_checks_the_vm_browser_tls_pin_before_ssh(self):
        self.mosh_manifest();_,report=self.call('setup',code='CONFIGURED')
        self.assertEqual((report['desktop_url'],report['desktop_tls_sha256'],report['desktop_tls']),('https://10.77.0.1:8443/',self.manifest['tls_certificate_sha256'],'pending'))
        _,report=self.call('verify',code='CONNECTION_VERIFIED');self.assertEqual(report['desktop_tls'],'passed')
        commands=[json.loads(line) for line in (self.path/'commands.jsonl').read_text().splitlines()]
        self.assertIn(['openssl',['s_client','-connect','10.77.0.1:8443','-servername','10.77.0.1']],commands)
        # A different certificate stops before the SSH session and is never reported as passed.
        self.manifest['tls_certificate_sha256']='b'*64;self.data['manifest.json']=json.dumps(self.manifest).encode();self.bundle();self.stubs()
        self.state=self.path/'second state';self.call('setup',code='CONFIGURED')
        (self.path/'commands.jsonl').unlink()
        _,report=self.call('verify',code='TLS_PIN_FAILED');self.assertEqual(report['desktop_tls'],'failed')
        commands=[json.loads(line)[0] for line in (self.path/'commands.jsonl').read_text().splitlines()]
        self.assertNotIn('ssh',commands)

    def test_terminal_mosh_needs_interactive_terminal_or_wsl(self):
        self.mosh_manifest();self.setup()
        if WINDOWS:
            self.call('mosh',code='MOSH_WSL_REQUIRED');return
        for program in ('mosh','mosh-client'):
            p=self.bin/program;p.write_text('#!/bin/sh\nexit 0\n');p.chmod(0o755)
        self.call('mosh',code='INTERACTIVE_TERMINAL_REQUIRED')

    @unittest.skipIf(WINDOWS,'POSIX interactive terminal fixture')
    def test_terminal_mosh_launcher_reads_ports_and_alias_from_approved_bundle(self):
        import pty, shlex
        self.state=self.path/"private ' $(false)"
        self.mosh_manifest();self.setup()
        p=self.bin/'mosh';p.write_text('#!/usr/bin/env python3\nimport json,os,pathlib,sys\n(pathlib.Path(os.environ["FIXTURE"])/"mosh-args.json").write_text(json.dumps(sys.argv[1:]))\n');p.chmod(0o755)
        p=self.bin/'mosh-client';p.write_text('#!/bin/sh\nexit 0\n');p.chmod(0o755)
        (self.path/'tunnel-active').touch()
        master,slave=pty.openpty()
        try:
            result=subprocess.run(self.command('mosh'),env=self.env,stdin=slave,stdout=slave,stderr=subprocess.PIPE,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
        finally:os.close(slave);os.close(master)
        args=json.loads((self.path/'mosh-args.json').read_text())
        # Native mosh-server with the default UDP range: no custom server or port.
        self.assertFalse([a for a in args if a.startswith(('--server','--port'))],args)
        self.assertEqual(args[-1],'oci-hub-'+self.manifest['device_id'])
        ssh_command=next(arg[len('--ssh='):] for arg in args if arg.startswith('--ssh='))
        expected=str((self.state/'oci-hub'/self.manifest['device_id']/'ssh_config').resolve())
        self.assertEqual(shlex.split(ssh_command),['ssh','-F',expected])

    def test_terminal_schema_accepts_existing_vm_hostname(self):
        try:import jsonschema
        except ImportError:self.skipTest('jsonschema unavailable; do not install automatically')
        self.mosh_manifest()
        schema=json.loads((ROOT/'schemas/bundle-manifest.schema.json').read_text())
        jsonschema.validate(self.manifest,schema)
        example=json.loads((ROOT/'examples/bundle-manifest.oci-hub-mosh.example.json').read_text())
        jsonschema.validate(example,schema)

    def fake_mosh(self):
        # Records arguments and the locale it was started with; never connects.
        p=self.bin/'mosh';p.write_text('#!/usr/bin/env python3\nimport json,os,pathlib,sys\n'
            'env={k:v for k,v in os.environ.items() if k.startswith(("LC_","LANG"))}\n'
            '(pathlib.Path(os.environ["FIXTURE"])/"mosh-run.json").write_text(json.dumps({"args":sys.argv[1:],"env":env}))\n');p.chmod(0o755)
        p=self.bin/'mosh-client';p.write_text('#!/bin/sh\nexit 0\n');p.chmod(0o755)

    def run_in_pty(self, action):
        import pty
        master,slave=pty.openpty()
        try:
            return subprocess.run(self.command(action),env=self.env,stdin=slave,stdout=slave,stderr=subprocess.PIPE,text=True,timeout=20)
        finally:os.close(slave);os.close(master)

    def commands(self):
        log=self.path/'commands.jsonl'
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def network_changes(self):
        # Readiness probes (--version/--help) are fine; anything else touches the network.
        return [[name,args] for name,args in self.commands()
                if name in ('sudo','ssh','sftp') or (name in ('wg','wg-quick') and args not in (['--version'],['--help']))]

    @unittest.skipIf(WINDOWS,'POSIX interactive terminal fixture')
    def test_mosh_sends_only_c_utf8_locale(self):
        self.setup();self.fake_mosh();(self.path/'tunnel-active').touch()
        # macOS Terminal defaults plus values the VM does not have.
        self.env.update(LC_CTYPE='UTF-8',LANG='zh_CN.UTF-8',LC_ALL='en_US.UTF-8',LC_MESSAGES='UTF-8',LANGUAGE='zh_CN')
        result=self.run_in_pty('mosh')
        self.assertEqual(result.returncode,0,result.stderr)
        run=json.loads((self.path/'mosh-run.json').read_text())
        self.assertEqual(run['env'],{'LANG':'C.UTF-8'})
        self.assertNotIn('LANGUAGE',run['env'])
        self.assertEqual(run['args'][-1],self.manifest['ssh_alias'])

    @unittest.skipIf(WINDOWS,'POSIX interactive terminal fixture')
    def test_mosh_without_local_c_utf8_stops_before_connecting(self):
        self.setup();self.fake_mosh();(self.path/'tunnel-active').touch()
        p=self.bin/'locale';p.write_text('#!/bin/sh\nprintf "C\\nPOSIX\\nen_US.ISO8859-1\\n"\n');p.chmod(0o755)
        result=self.run_in_pty('mosh')
        self.assertEqual(result.returncode,2,result.stderr)
        self.assertIn('C.UTF-8',result.stderr)
        self.assertFalse((self.path/'mosh-run.json').exists())

    @unittest.skipIf(WINDOWS,'Unix CLI route/tunnel behavior')
    def test_tunnel_down_after_reboot_is_reported_without_sudo(self):
        # Setup once activated the tunnel; a reboot removed it (no tunnel-active).
        self.setup();self.fake_mosh()
        (self.path/'commands.jsonl').unlink(missing_ok=True)
        for action in ('connect','sftp'):
            run=subprocess.run(self.command(action),env=self.env,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=30)
            self.assertEqual(run.returncode,3,run.stderr)
            self.assertEqual(json.loads(run.stdout.splitlines()[-1])['code'],'TUNNEL_DOWN')
            self.assertIn('bash ./bootstrap.sh setup',run.stderr)
        result=self.run_in_pty('mosh')
        self.assertEqual(result.returncode,3,result.stderr)
        self.assertIn('bash ./bootstrap.sh setup',result.stderr)
        self.assertFalse((self.path/'mosh-run.json').exists())
        # No elevation, no tunnel change and no connection attempt.
        self.assertEqual(self.network_changes(),[])
        # The printed recovery command restores only this device's tunnel.
        self.call('setup',code='CONFIGURED')
        self.assertTrue((self.path/'tunnel-active').exists())
        self.assertEqual(self.run_in_pty('mosh').returncode,0)

    @unittest.skipIf(WINDOWS,'Unix CLI route/tunnel behavior')
    def test_connect_with_live_tunnel_reaches_ssh(self):
        self.setup();(self.path/'tunnel-active').touch();(self.path/'commands.jsonl').unlink(missing_ok=True)
        subprocess.run(self.command('connect'),env=self.env,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=30)
        calls=self.commands()
        self.assertIn('ssh',[name for name,_ in calls])
        self.assertNotIn('sudo',[name for name,_ in calls])
        self.assertFalse([1 for name,args in calls if name=='wg-quick' and args!=['--help']])

    @unittest.skipIf(WINDOWS,'Unix CLI route/tunnel behavior')
    def test_connect_through_another_vpn_route_is_a_conflict(self):
        self.setup();self.env['ROUTE_CONFLICT']='1';(self.path/'commands.jsonl').unlink(missing_ok=True)
        run=subprocess.run(self.command('connect'),env=self.env,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=30)
        self.assertEqual(json.loads(run.stdout.splitlines()[-1])['code'],'ROUTE_CONFLICT')
        self.assertEqual(self.network_changes(),[])

    @unittest.skipIf(WINDOWS,'Unix CLI route/tunnel behavior')
    def test_verify_distinguishes_down_from_foreign_tunnel(self):
        self.setup()
        _,r=self.call('verify',code='TUNNEL_DOWN');self.assertEqual(r['sftp_roundtrip'],'pending')
        (self.path/'tunnel-active').touch();self.env['WRONG_TUNNEL']='1'
        self.call('verify',code='TUNNEL_CONFLICT')
        # disconnect still refuses to stop a tunnel it does not own.
        self.call('disconnect',code='TUNNEL_CONFLICT')
        self.assertTrue((self.path/'tunnel-active').exists())

    @unittest.skipIf(WINDOWS,'Unix ssh_config Include')
    def test_ssh_config_sets_a_locale_the_vm_has(self):
        self.setup()
        config=(self.native_state()/'ssh_config').read_text()
        self.assertIn('    SetEnv LANG=C.UTF-8 LC_ALL=C.UTF-8\n',config)
        ssh=shutil.which('ssh',path=os.environ['PATH'])
        run=subprocess.run([ssh,'-G','-F',str(self.user_config()),'fixture-vm'],capture_output=True,text=True,timeout=20)
        self.assertEqual(run.returncode,0,run.stderr)
        setenv=[v for line in run.stdout.splitlines() if line.startswith('setenv ') for v in line.split()[1:]]
        self.assertEqual(sorted(setenv),['LANG=C.UTF-8','LC_ALL=C.UTF-8'])

    @unittest.skipIf(WINDOWS,'Unix ssh_config Include')
    def test_1_3_0_ssh_config_upgrades_to_setenv_without_conflict(self):
        self.setup()
        installed=self.native_state()/'ssh_config';current=installed.read_text()
        previous=current.replace('    SetEnv LANG=C.UTF-8 LC_ALL=C.UTF-8\n','')
        self.assertNotEqual(previous,current)
        installed.write_text(previous);installed.chmod(0o600)
        user=self.user_config().read_bytes()
        (self.path/'tunnel-active').touch()
        self.call('check',code='CHECKED')
        self.call('verify',code='CONNECTION_VERIFIED')
        self.assertEqual(installed.read_text(),previous)
        self.call('setup',code='CONFIGURED')
        self.assertEqual(installed.read_text(),current)
        self.assertEqual(stat.S_IMODE(installed.stat().st_mode),0o600)
        self.assertEqual(self.user_config().read_bytes(),user)
        # A hand edit of the SetEnv line is not an earlier release: still a conflict.
        installed.write_text(current.replace('LC_ALL=C.UTF-8','LC_ALL=zh_CN.UTF-8'))
        self.call('setup','--no-activate',code='CONFIG_CONFLICT')

    def native_state(self):
        return self.state/'oci-hub'/self.manifest['device_id']

    def user_config(self):
        return self.home/'.ssh'/'config'

    def include_line(self):
        return 'Include "'+str((self.native_state()/'ssh_config').resolve())+'"'

    def resolve_host(self, host):
        # The real client, not the PATH stub; -F keeps system and account config out.
        ssh=shutil.which('ssh',path=os.environ['PATH'])
        run=subprocess.run([ssh,'-G','-F',str(self.user_config()),host],capture_output=True,text=True,timeout=20)
        self.assertEqual(run.returncode,0,run.stderr)
        values={}
        for line in run.stdout.splitlines():
            key,_,value=line.partition(' ')
            values.setdefault(key,value)
        return values

    @unittest.skipIf(WINDOWS,'Unix ssh_config Include')
    def test_alias_fresh_install_creates_private_include_that_resolves(self):
        self.hub_manifest();self.setup()
        config=(self.native_state()/'ssh_config').read_text()
        self.assertEqual(config.splitlines()[0],'Host oci-hub-'+self.manifest['device_id']+' fixture-vm')
        self.assertEqual(stat.S_IMODE((self.home/'.ssh').stat().st_mode),0o700)
        self.assertEqual(stat.S_IMODE(self.user_config().stat().st_mode),0o600)
        self.assertEqual(self.user_config().read_text(),self.include_line()+'\n')
        resolved=self.resolve_host('fixture-vm')
        state=self.native_state().resolve()
        self.assertEqual(resolved['hostname'],'10.77.0.1')
        self.assertEqual(resolved['user'],'employee')
        self.assertEqual(resolved['identityfile'],str(state/'client-key'))
        self.assertEqual(resolved['userknownhostsfile'],str(state/'known_hosts'))

    @unittest.skipIf(WINDOWS,'Unix ssh_config Include')
    def test_alias_upgrades_1_0_0_ssh_config_only_on_setup(self):
        self.hub_manifest();self.setup()
        installed=self.native_state()/'ssh_config'
        current=installed.read_text()
        legacy='Host oci-hub-'+self.manifest['device_id']+'\n'+current.split('\n',1)[1].replace('    SetEnv LANG=C.UTF-8 LC_ALL=C.UTF-8\n','')
        installed.write_text(legacy);self.user_config().unlink()
        # Other commands keep using the 1.0.0 config: a full verify passes against it unchanged.
        (self.path/'tunnel-active').touch()
        self.call('check',code='CHECKED')
        self.call('verify',code='CONNECTION_VERIFIED')
        self.assertEqual(installed.read_text(),legacy)
        self.assertFalse(self.user_config().exists())
        self.setup()
        self.assertEqual(installed.read_text(),current)
        self.assertEqual(stat.S_IMODE(installed.stat().st_mode),0o600)
        self.assertEqual(self.user_config().read_text(),self.include_line()+'\n')

    @unittest.skipIf(WINDOWS,'Unix ssh_config Include')
    def test_alias_rerun_changes_nothing(self):
        self.hub_manifest();self.setup()
        before={p.name:p.read_bytes() for p in self.native_state().iterdir()}
        user=self.user_config().read_bytes()
        self.setup()
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.native_state().iterdir()})
        self.assertEqual(self.user_config().read_bytes(),user)

    @unittest.skipIf(WINDOWS,'Unix ssh_config Include')
    def test_alias_tampered_ssh_config_conflicts_and_writes_nothing(self):
        self.hub_manifest();self.setup()
        installed=self.native_state()/'ssh_config'
        installed.write_text(installed.read_text().replace('ConnectTimeout 10','ConnectTimeout 99'))
        tampered=installed.read_bytes();self.user_config().unlink()
        self.call('setup','--no-activate',code='CONFIG_CONFLICT')
        self.assertEqual(installed.read_bytes(),tampered)
        self.assertFalse(self.user_config().exists())

    @unittest.skipIf(WINDOWS,'Unix ssh_config Include')
    def test_alias_include_precedes_existing_user_hosts_without_changing_them(self):
        (self.home/'.ssh').mkdir(mode=0o700)
        original='Host fixture-vm other\n    HostName 192.0.2.5\n    User bob\n\nHost *\n    ServerAliveInterval 30\n'
        self.user_config().write_text(original);self.user_config().chmod(0o644)
        before=self.resolve_host('other')
        self.hub_manifest();self.setup()
        self.assertEqual(self.user_config().read_text(),self.include_line()+'\n'+original)
        self.assertEqual(stat.S_IMODE(self.user_config().stat().st_mode),0o644)
        self.assertEqual(self.resolve_host('other'),before)
        resolved=self.resolve_host('fixture-vm')
        self.assertEqual((resolved['hostname'],resolved['user']),('10.77.0.1','employee'))

    @unittest.skipIf(WINDOWS,'Unix symlink behavior')
    def test_alias_symlinked_user_config_is_rejected_untouched(self):
        (self.home/'.ssh').mkdir(mode=0o700)
        target=self.path/'dotfiles-config';target.write_text('Host keep\n')
        self.user_config().symlink_to(target)
        self.hub_manifest()
        self.call('setup','--no-activate',code='SSH_CONFIG_UNSAFE')
        self.assertTrue(self.user_config().is_symlink())
        self.assertEqual(target.read_text(),'Host keep\n')
        self.assertEqual([p.name for p in (self.home/'.ssh').iterdir()],['config'])
        # The device itself is still configured; only the Include is refused.
        self.assertTrue((self.native_state()/'ssh_config').is_file())

    def assert_ssh_unchanged(self, before):
        self.assertEqual({p.name:p.read_bytes() for p in (self.home/'.ssh').iterdir()},before)

    @unittest.skipIf(WINDOWS or os.geteuid()==0,'Unix permission behavior')
    def test_alias_non_writable_ssh_dir_is_rejected_untouched(self):
        ssh_dir=self.home/'.ssh';ssh_dir.mkdir(mode=0o700);ssh_dir.chmod(0o500)
        try:
            self.hub_manifest()
            self.call('setup','--no-activate',code='SSH_CONFIG_UNSAFE')
            self.assert_ssh_unchanged({})
        finally:ssh_dir.chmod(0o700)

    @unittest.skipIf(WINDOWS or os.geteuid()==0,'Unix permission behavior')
    def test_alias_non_writable_user_config_is_rejected_untouched(self):
        (self.home/'.ssh').mkdir(mode=0o700)
        self.user_config().write_text('Host keep\n');self.user_config().chmod(0o400)
        self.hub_manifest()
        self.call('setup','--no-activate',code='SSH_CONFIG_UNSAFE')
        self.assert_ssh_unchanged({'config':b'Host keep\n'})
        self.assertEqual(stat.S_IMODE(self.user_config().stat().st_mode),0o400)

    @unittest.skipIf(WINDOWS,'Unix hard link behavior')
    def test_alias_hard_linked_user_config_is_rejected_untouched(self):
        (self.home/'.ssh').mkdir(mode=0o700)
        self.user_config().write_text('Host keep\n')
        other=self.path/'dotfiles-config';os.link(self.user_config(),other)
        self.hub_manifest()
        self.call('setup','--no-activate',code='SSH_CONFIG_UNSAFE')
        self.assert_ssh_unchanged({'config':b'Host keep\n'})
        self.assertEqual(self.user_config().stat().st_nlink,2)

    @unittest.skipIf(WINDOWS,'Unix ssh_config Include')
    def test_alias_include_after_host_block_moves_to_line_one(self):
        self.hub_manifest()
        (self.home/'.ssh').mkdir(mode=0o700)
        self.user_config().write_text('Host other\n    User bob\n'+self.include_line()+'\n')
        self.setup()
        self.assertEqual(self.user_config().read_text(),self.include_line()+'\nHost other\n    User bob\n')
        self.setup()
        self.assertEqual(self.user_config().read_text().count('Include'),1)

    @unittest.skipIf(WINDOWS,'Unix ssh_config Include')
    def test_alias_mosh_mode_with_oci_hub_hostname(self):
        self.mosh_manifest();self.manifest['vm_hostname']='oci-hub-fixture'
        self.data['manifest.json']=json.dumps(self.manifest).encode();self.bundle();self.stubs()
        self.setup()
        self.assertEqual((self.native_state()/'ssh_config').read_text().splitlines()[0],'Host oci-hub-'+self.manifest['device_id']+' fixture-vm')
        self.assertEqual(self.user_config().read_text(),self.include_line()+'\n')
        resolved=self.resolve_host('fixture-vm')
        self.assertEqual((resolved['hostname'],resolved['user']),('10.77.0.1','employee'))

    def test_vm_hostname_must_be_an_oci_hub_employee_id(self):
        for host in ('employee-fixture','oci-hub-'+'a'*21,'oci-hub-9abc'):
            self.manifest['vm_hostname']=host
            self.data['manifest.json']=json.dumps(self.manifest).encode();self.bundle()
            self.call('check',code='MANIFEST_INVALID')

    @unittest.skipIf(WINDOWS,'Unix ssh_config Include')
    def test_alias_follows_vm_hostname_not_device_id(self):
        self.manifest.update(device_id='laptop-2',ssh_alias='oci-hub-laptop-2',tunnel_name=tunnel_for('laptop-2'),vm_hostname='oci-hub-'+'a'*20)
        self.data['manifest.json']=json.dumps(self.manifest).encode();self.bundle();self.stubs()
        self.setup()
        self.assertEqual((self.native_state()/'ssh_config').read_text().splitlines()[0],'Host oci-hub-laptop-2 '+'a'*20+'-vm')

    def test_reports_carry_non_secret_device_identity(self):
        self.mosh_manifest();self.manifest['vm_hostname']='oci-hub-fixture'
        self.data['manifest.json']=json.dumps(self.manifest).encode();self.bundle()
        if not WINDOWS:self.stubs()
        _,report=self.setup()
        self.assertEqual((report['device_id'],report['vm_hostname']),(self.manifest['device_id'],'oci-hub-fixture'))
        self.assertEqual((report['desktop_url'],report['desktop_tls_sha256']),(self.manifest['desktop_url'],self.manifest['tls_certificate_sha256']))
        self.package.write_bytes(b'not a zip')
        _,report=self.call('check',code='PACKAGE_HASH_MISMATCH')
        self.assertNotIn('device_id',report);self.assertNotIn('desktop_url',report)

    @unittest.skipUnless(WINDOWS,'Windows ssh_config Include')
    def test_windows_alias_and_include_in_user_profile(self):
        self.hub_manifest();self.setup()
        config=(self.native_state()/'ssh_config').read_text()
        self.assertEqual(config.splitlines()[0],'Host oci-hub-'+self.manifest['device_id']+' fixture-vm')
        # The script writes the long path; the runner's TEMP may be an 8.3 short name.
        include='Include "'+os.path.realpath(str(self.native_state())).replace('\\','/')+'/ssh_config"'
        self.assertEqual(self.user_config().read_text().splitlines(),[include])
        self.user_config().write_bytes(('Host other\n    User someone\n'+include+'\n').encode())
        self.setup()
        self.assertEqual(self.user_config().read_text().splitlines(),[include,'Host other','    User someone'])
        before=self.user_config().read_bytes();self.setup()
        self.assertEqual(self.user_config().read_bytes(),before)
        # First but duplicated later: rewritten once, other lines kept.
        self.user_config().write_bytes((include+'\nHost other\n'+include+'\n').encode())
        self.setup()
        self.assertEqual(self.user_config().read_text().splitlines(),[include,'Host other'])

    @unittest.skipUnless(WINDOWS,'Windows ssh_config alias')
    def test_windows_alias_follows_vm_hostname_not_device_id(self):
        self.manifest.update(device_id='laptop-2',ssh_alias='oci-hub-laptop-2',tunnel_name=tunnel_for('laptop-2'),vm_hostname='oci-hub-'+'a'*20)
        self.data['manifest.json']=json.dumps(self.manifest).encode();self.bundle()
        _,report=self.setup()
        self.assertEqual((report['device_id'],report['vm_hostname']),('laptop-2','oci-hub-'+'a'*20))
        self.assertEqual((self.native_state()/'ssh_config').read_text().splitlines()[0],'Host oci-hub-laptop-2 '+'a'*20+'-vm')

    @unittest.skipUnless(WINDOWS,'Windows ssh_config upgrade')
    def test_windows_pre_alias_ssh_config_upgrades_on_setup(self):
        self.hub_manifest();self.setup()
        installed=self.native_state()/'ssh_config';current=installed.read_bytes()
        installed.write_bytes(b'Host oci-hub-'+self.manifest['device_id'].encode()+b'\n'+current.split(b'\n',1)[1])
        # check accepts the pre-alias file (the runner may lack WireGuard, hence either code).
        _,report=self.call('check');self.assertIn(report['code'],('CHECKED','DEPENDENCY_MISSING'))
        self.setup()
        self.assertEqual(installed.read_bytes(),current)

    @unittest.skipIf(WINDOWS,'Unix ssh_config Include')
    def test_alias_include_first_but_duplicated_is_deduplicated(self):
        self.hub_manifest();self.setup()
        line=self.include_line()
        self.user_config().write_text(line+'\nHost other\n'+line+'\n')
        self.setup()
        self.assertEqual(self.user_config().read_text(),line+'\nHost other\n')

class OuterZipCheck(unittest.TestCase):
    """scripts/check-outer-zip.py, exactly as README step 2 runs it."""
    NAMES=("device-bundle.zip","device-bundle.sha256","README.md")

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="outer-zip-")
        self.path=Path(self.temp.name);self.dest=self.path/"employee-workspace"

    def tearDown(self):
        self.temp.cleanup()

    def outer(self,attrs=None,names=NAMES):
        # attrs maps a name to its full 32-bit external attribute.
        target=self.path/"device-bundle.zip"
        with zipfile.ZipFile(target,"w") as archive:
            for name in names:
                info=zipfile.ZipInfo(name,(1980,1,1,0,0,0))
                info.external_attr=(attrs or {}).get(name,0o600<<16)
                archive.writestr(info,b"synthetic")
        return target

    def check(self,outer):
        run=subprocess.run([sys.executable,"-I",str(ROOT/"scripts/check-outer-zip.py"),str(outer),str(self.dest)],
                           capture_output=True,text=True,timeout=20)
        lines=run.stdout.splitlines()
        self.assertEqual(len(lines),1,run.stdout+run.stderr)
        self.assertEqual(run.returncode,0 if lines[0]=="READY" else 1)
        return lines[0]

    def test_readme_runs_this_exact_command(self):
        command='python3 -I scripts/check-outer-zip.py "<外层ZIP>" "$HOME/Downloads/employee-workspace"'
        for doc in ("README.md","docs/download.md"):self.assertIn(command,(ROOT/doc).read_text(encoding="utf-8"))

    def test_administrator_and_regular_entries_are_ready(self):
        self.assertEqual(self.check(self.outer()),"READY")
        regular={name:(stat.S_IFREG|0o600)<<16 for name in self.NAMES}
        self.assertEqual(self.check(self.outer(regular)),"READY")

    def test_non_regular_types_and_dos_bits_are_rejected(self):
        for attr in ((stat.S_IFDIR|0o700)<<16,(stat.S_IFLNK|0o777)<<16,0o030000<<16,(stat.S_IFIFO|0o600)<<16,
                     0x10,0x400,((stat.S_IFREG|0o600)<<16)|0x400,((stat.S_IFREG|0o600)<<16)|0x10):
            self.assertEqual(self.check(self.outer({"README.md":attr})),"STOP: not regular files",oct(attr))

    def test_wrong_names_and_unreadable_zip_stop(self):
        self.assertEqual(self.check(self.outer(names=self.NAMES[:2])),"STOP: unexpected entries")
        self.assertEqual(self.check(self.outer(names=self.NAMES+("extra",))),"STOP: unexpected entries")
        self.assertEqual(self.check(self.outer(names=("device-bundle.zip","README.md","README.md"))),"STOP: unexpected entries")
        self.assertEqual(self.check(self.outer(names=("device-bundle.zip","device-bundle.sha256","sub/README.md"))),"STOP: unexpected entries")
        broken=self.path/"broken.zip";broken.write_bytes(b"<html>not a zip</html>")
        self.assertTrue(self.check(broken).startswith("STOP: cannot read outer ZIP"))

    def test_existing_receiving_files_stop_before_extraction(self):
        self.dest.mkdir();(self.dest/"README.md").write_text("previous delivery")
        self.assertEqual(self.check(self.outer()),"STOP: already in "+str(self.dest)+": README.md")

if __name__=="__main__":
    unittest.main()
