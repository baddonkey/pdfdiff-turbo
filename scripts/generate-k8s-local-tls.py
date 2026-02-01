#!/usr/bin/env python3
from __future__ import annotations

import base64
import pathlib
import shutil
import subprocess
import sys

HOSTS = [
    "api.pdfdiff-turbo.local",
    "admin.pdfdiff-turbo.local",
    "viewer.pdfdiff-turbo.local",
    "flower.pdfdiff-turbo.local",
]


def main() -> int:
    if shutil.which("mkcert") is None:
        print("mkcert not found. Install mkcert to generate trusted local certs.", file=sys.stderr)
        print("See: https://github.com/FiloSottile/mkcert", file=sys.stderr)
        return 1

    root_dir = pathlib.Path(__file__).resolve().parents[1]
    cert_dir = root_dir / "certs" / "k8s-local"
    cert_dir.mkdir(parents=True, exist_ok=True)

    cert_path = cert_dir / "pdfdiff-local.crt"
    key_path = cert_dir / "pdfdiff-local.key"

    cmd = [
        "mkcert",
        "-install",
    ]
    subprocess.run(cmd, check=True)

    cmd = [
        "mkcert",
        "-cert-file",
        str(cert_path),
        "-key-file",
        str(key_path),
        *HOSTS,
    ]
    subprocess.run(cmd, check=True)

    secret_path = root_dir / "k8s" / "overlays" / "local" / "tls-secret.yaml"

    crt_b64 = base64.b64encode(cert_path.read_bytes()).decode("ascii")
    key_b64 = base64.b64encode(key_path.read_bytes()).decode("ascii")

    secret_yaml = f"""apiVersion: v1
kind: Secret
metadata:
  name: pdfdiff-local-tls
  namespace: pdfdiff
type: kubernetes.io/tls
data:
  tls.crt: {crt_b64}
  tls.key: {key_b64}
"""

    secret_path.write_text(secret_yaml)
    print(f"Wrote {secret_path}")
    print("Apply with: kubectl apply -f k8s/overlays/local/tls-secret.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
