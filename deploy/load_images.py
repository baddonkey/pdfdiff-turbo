#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path
import glob
import shutil


def resolve_importer():
    if shutil.which("k3s"):
        return ["k3s", "ctr", "images", "import"], "k3s"
    if shutil.which("ctr"):
        return ["ctr", "-n", "k8s.io", "images", "import"], "containerd"

    preferred = os.environ.get("CONTAINER_ENGINE")
    if preferred and preferred != "podman":
        return None, None
    if shutil.which("podman"):
        return ["podman", "load", "-i"], "podman"
    return None, None


def run(cmd, **kwargs):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, **kwargs)


def main():
    in_dir = Path(os.environ.get("IN_DIR", os.getcwd())).resolve()

    importer_cmd, importer_name = resolve_importer()
    if not importer_cmd:
        print("No image importer found. Install k3s/ctr or podman, or set CONTAINER_ENGINE=podman.")
        sys.exit(1)

    tarballs = sorted(glob.glob(str(in_dir / "pdfdiff-turbo-*_*.tar")))
    if not tarballs:
        print(f"No tar files found in {in_dir}.")
        sys.exit(1)

    for tarball in tarballs:
        run([*importer_cmd, tarball])

    print(f"Images imported via {importer_name} from {in_dir}.")


if __name__ == "__main__":
    main()