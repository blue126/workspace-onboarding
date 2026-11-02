#!/usr/bin/env python3
"""Check the downloaded outer ZIP and the receiving directory before extraction.

Usage: python3 -I scripts/check-outer-zip.py <outer.zip> <receiving-dir>
Prints READY (exit 0) or one 'STOP: ...' line (exit 1). Reads only the ZIP
directory, never file contents, so no key material is touched or printed.
"""
import os
import sys
import zipfile

EXPECTED = ("device-bundle.zip", "device-bundle.sha256", "README.md")
S_IFMT, S_IFREG = 0o170000, 0o100000
DOS_DIRECTORY, DOS_REPARSE = 0x10, 0x400


def regular(info):
    # Same rule as the Windows check: a Unix regular file, or no Unix type at
    # all (the administrator's packer writes 0o600 << 16); never a directory
    # or reparse point, whichever field says so.
    unix_type = (info.external_attr >> 16) & S_IFMT
    dos = info.external_attr & 0xFFFF
    if dos & (DOS_DIRECTORY | DOS_REPARSE):
        return False
    return unix_type in (S_IFREG, 0)


def main(argv):
    if len(argv) != 3:
        print("STOP: usage: check-outer-zip.py <outer.zip> <receiving-dir>")
        return 1
    outer, dest = argv[1], argv[2]
    if not os.path.isfile(outer) or os.path.islink(outer):
        print("STOP: outer ZIP is not a regular file")
        return 1
    try:
        with zipfile.ZipFile(outer) as archive:
            entries = archive.infolist()
    except (OSError, zipfile.BadZipFile, ValueError) as error:
        print("STOP: cannot read outer ZIP (%s)" % type(error).__name__)
        return 1
    names = [entry.filename for entry in entries]
    if len(entries) != 3 or sorted(names) != sorted(EXPECTED):
        print("STOP: unexpected entries")
        return 1
    if not all(regular(entry) for entry in entries):
        print("STOP: not regular files")
        return 1
    conflicts = [name for name in EXPECTED
                 if os.path.lexists(os.path.join(dest, name))]
    if conflicts:
        print("STOP: already in %s: %s" % (dest, " ".join(conflicts)))
        return 1
    print("READY")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
