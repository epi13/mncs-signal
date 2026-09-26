#!/usr/bin/env python3
"""Fetch the pinned MNCS executor binary with digest verification.

Downloads the family's pinned executor distribution (published from
mncs-harness; Signal consumes it rather than publishing a second binary),
verifies SHA-256 BEFORE marking it executable, writes it to --dest.
Fails closed on any mismatch. See docs/TOOLCHAIN.md.

Explicit operator/CI action; the check boundary never downloads.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO = "epi13/mncs-harness"
TAG = "toolchain/mncs-executor-066897e"
ASSET = "mncs-executor-linux-x86_64"
DIGEST = "4387bae352b68020a83edbbb312794522a76c9f618cc7548a8f68384c63ecb40"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", default=str(Path.home() / ".local" / "bin" / "mncs-executor"))
    parser.add_argument("--digest", default=DIGEST)
    args = parser.parse_args()
    url = f"https://github.com/{REPO}/releases/download/{TAG}/{ASSET}"
    print(f"downloading {url}")
    try:
        with urllib.request.urlopen(url, timeout=300) as response:
            data = response.read()
    except OSError as exc:
        print(f"download failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
    digest = hashlib.sha256(data).hexdigest()
    if digest != args.digest:
        print(f"DIGEST MISMATCH: got sha256:{digest}, want sha256:{args.digest}; refusing",
              file=sys.stderr)
        raise SystemExit(1)
    dest = Path(os.path.expanduser(args.dest))
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=str(dest.parent), delete=False) as staged:
        staged.write(data)
        staged_path = Path(staged.name)
    staged_path.chmod(staged_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    staged_path.rename(dest)
    print(f"verified sha256:{digest} -> {dest}")


if __name__ == "__main__":
    main()
