#!/usr/bin/env python3
import os
import subprocess


def run(cmd, **kwargs):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, **kwargs)


def main():
    os.environ.setdefault("KUBECONFIG", "/etc/rancher/k3s/k3s.yaml")

    run(["kubectl", "-n", "pdfdiff", "get", "pods", "-o", "wide"])
    run(["kubectl", "-n", "pdfdiff", "get", "svc"])
    run(["kubectl", "-n", "pdfdiff", "get", "ingress"])
    run(["kubectl", "-n", "pdfdiff", "get", "certificates"])


if __name__ == "__main__":
    main()