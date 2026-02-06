#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path


def run(cmd, **kwargs):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, **kwargs)


def resolve_k8s_prod_dir(start_dir: Path) -> Path:
    override = os.environ.get("K8S_PROD_DIR")
    if override:
        return Path(override).expanduser().resolve()

    for parent in [start_dir, *start_dir.parents]:
        candidate = parent / "k8s-prod"
        if candidate.exists():
            return candidate

    return start_dir / "k8s-prod"


def main():
    root_dir = Path(__file__).resolve().parents[1]
    os.environ.setdefault("KUBECONFIG", "/etc/rancher/k3s/k3s.yaml")
    k8s_prod_dir = resolve_k8s_prod_dir(root_dir)

    run(["kubectl", "apply", "-k", str(k8s_prod_dir)])

    run(["kubectl", "-n", "pdfdiff", "rollout", "status", "deployment/postgres", "--timeout=180s"])
    run(["kubectl", "-n", "pdfdiff", "rollout", "status", "deployment/rabbitmq", "--timeout=180s"])
    run(["kubectl", "-n", "pdfdiff", "rollout", "status", "deployment/api", "--timeout=180s"])
    run(["kubectl", "-n", "pdfdiff", "rollout", "status", "deployment/worker", "--timeout=180s"])
    run(["kubectl", "-n", "pdfdiff", "rollout", "status", "deployment/beat", "--timeout=180s"])
    run(["kubectl", "-n", "pdfdiff", "rollout", "status", "deployment/admin", "--timeout=180s"])
    run(["kubectl", "-n", "pdfdiff", "rollout", "status", "deployment/viewer", "--timeout=180s"])


if __name__ == "__main__":
    main()