#!/usr/bin/env python3
import os
import subprocess
import sys
import shutil


def run(cmd, **kwargs):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, **kwargs)


def main():
    if shutil.which("k3s"):
        print("k3s already installed.")
        return

    if not shutil.which("curl"):
        print("curl is required to install k3s.")
        sys.exit(1)

    run(["/bin/sh", "-c", "curl -sfL https://get.k3s.io | sh -s - --write-kubeconfig-mode 644"])

    run(["systemctl", "enable", "k3s"])
    run(["systemctl", "start", "k3s"])

    os.environ["KUBECONFIG"] = "/etc/rancher/k3s/k3s.yaml"
    run(["kubectl", "get", "nodes"])


if __name__ == "__main__":
    main()