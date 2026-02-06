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
    version = os.environ.get("VERSION", (root_dir / "VERSION").read_text().strip())

    build_tool = resolve_engine()
    if not build_tool:
        print("Podman is required. Install podman or set CONTAINER_ENGINE=podman.")
        sys.exit(1)

    os.chdir(root_dir)

    run([build_tool, "build", "-f", "api/Dockerfile", "-t", f"pdfdiff-turbo-api:{version}", "."])
    run([build_tool, "build", "-f", "api/Dockerfile", "-t", f"pdfdiff-turbo-worker:{version}", "."])
    run([build_tool, "build", "-f", "api/Dockerfile", "-t", f"pdfdiff-turbo-beat:{version}", "."])
    run([build_tool, "build", "-f", "api/Dockerfile", "-t", f"pdfdiff-turbo-flower:{version}", "."])
    run([build_tool, "build", "-f", "admin/Dockerfile", "-t", f"pdfdiff-turbo-admin:{version}", "admin"])
    run([build_tool, "build", "-f", "viewer/Dockerfile", "-t", f"pdfdiff-turbo-viewer:{version}", "viewer"])

    print(f"Built images locally with tag {version}.")


if __name__ == "__main__":
    main()