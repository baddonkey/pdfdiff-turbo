#!/usr/bin/env python3
import os
import subprocess


def run(cmd, **kwargs):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, **kwargs)


def run_capture(cmd):
    print("+", " ".join(cmd))
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def main():
    os.environ.setdefault("KUBECONFIG", "/etc/rancher/k3s/k3s.yaml")

    version = os.environ.get("CERT_MANAGER_VERSION", "v1.14.5")

    run(["kubectl", "apply", "-f", f"https://github.com/cert-manager/cert-manager/releases/download/{version}/cert-manager.crds.yaml"])
    ns_yaml = run_capture(["kubectl", "create", "namespace", "cert-manager", "--dry-run=client", "-o", "yaml"])
    run(["kubectl", "apply", "-f", "-"], input=ns_yaml, text=True)
    run(["kubectl", "apply", "-f", f"https://github.com/cert-manager/cert-manager/releases/download/{version}/cert-manager.yaml"])

    run(["kubectl", "-n", "cert-manager", "rollout", "status", "deployment/cert-manager", "--timeout=180s"])
    run(["kubectl", "-n", "cert-manager", "rollout", "status", "deployment/cert-manager-webhook", "--timeout=180s"])
    run(["kubectl", "-n", "cert-manager", "rollout", "status", "deployment/cert-manager-cainjector", "--timeout=180s"])


if __name__ == "__main__":
    main()