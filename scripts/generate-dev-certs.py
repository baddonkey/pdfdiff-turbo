#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import subprocess
import sys


def main() -> int:
    root_dir = pathlib.Path(__file__).resolve().parents[1]
    cert_dir = root_dir / "certs"
    cert_dir.mkdir(parents=True, exist_ok=True)

    key_path = cert_dir / "localhost.key"
    crt_path = cert_dir / "localhost.crt"

    cmd = [
        "openssl",
        "req",
        "-x509",
        "-nodes",
        "-newkey",
        "rsa:2048",
        "-days",
        "365",
        "-keyout",
        str(key_path),
        "-out",
        str(crt_path),
        "-subj",
        "/CN=localhost",
        "-addext",
        "subjectAltName=DNS:localhost,IP:127.0.0.1",
    ]

    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        print("openssl not found. Please install OpenSSL and retry.", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"openssl failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode

    print(f"Generated: {crt_path}")
    print(f"Generated: {key_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
