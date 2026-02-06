#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path
import shutil


def resolve_engine():
    preferred = os.environ.get("CONTAINER_ENGINE")
    if preferred and preferred != "podman":
        return None
    return shutil.which("podman")


def run(cmd, **kwargs):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, **kwargs)


def main():
    root_dir = Path(__file__).resolve().parents[1]
    out_dir = Path(os.environ.get("OUT_DIR", root_dir / "deploy" / "images")).resolve()
    version = os.environ.get("VERSION", (root_dir / "VERSION").read_text().strip())

    build_tool = resolve_engine()
    if not build_tool:
        print("Podman is required. Install podman or set CONTAINER_ENGINE=podman.")
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)

    run([build_tool, "save", "-o", str(out_dir / f"pdfdiff-turbo-api_{version}.tar"), f"pdfdiff-turbo-api:{version}"])
    run([build_tool, "save", "-o", str(out_dir / f"pdfdiff-turbo-worker_{version}.tar"), f"pdfdiff-turbo-worker:{version}"])
    run([build_tool, "save", "-o", str(out_dir / f"pdfdiff-turbo-beat_{version}.tar"), f"pdfdiff-turbo-beat:{version}"])
    run([build_tool, "save", "-o", str(out_dir / f"pdfdiff-turbo-flower_{version}.tar"), f"pdfdiff-turbo-flower:{version}"])
    run([build_tool, "save", "-o", str(out_dir / f"pdfdiff-turbo-admin_{version}.tar"), f"pdfdiff-turbo-admin:{version}"])
    run([build_tool, "save", "-o", str(out_dir / f"pdfdiff-turbo-viewer_{version}.tar"), f"pdfdiff-turbo-viewer:{version}"])

    print(f"Saved images to {out_dir}. Copy these .tar files to the server and run load_images.py there.")


if __name__ == "__main__":
    main()