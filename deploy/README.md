# Deploy (k3s single-node)

This folder contains the scripts needed to build images on a local machine and install on a remote server.

## Local machine: build + export images

Prereqs:
- Podman

Install (Linux):
- Fedora: `sudo dnf install -y podman`

1) Build images (tags from VERSION):
- `python deploy/build.py`

2) Save images to tar files (default: deploy/images):
- `python deploy/save_images.py`

3) Copy the tar files to the server:
- `deploy/images/pdfdiff-turbo-*_*.tar`

Optional env vars:
- `VERSION` (override VERSION file)
- `OUT_DIR` (override deploy/images)
- `CONTAINER_ENGINE` (defaults to podman)

## Remote server: install + deploy

Prereqs:
- Podman
- kubectl
- k3s (installed by script below)

Install (Fedora):
- Podman: `sudo dnf install -y podman`
- kubectl: `sudo dnf install -y kubernetes-client`

1) Install k3s:
- `sudo python deploy/install_k3s.py`

2) Install cert-manager:
- `sudo python deploy/install_cert_manager.py`

3) Load image tar files (run in folder with the tar files):
- `sudo python /path/to/deploy/load_images.py`

Notes:
- `load_images.py` imports into k3s/containerd when available; use sudo for k3s.
 - Flower UI is not exposed via the prod ingress. Use `kubectl -n pdfdiff port-forward svc/flower 5555:5555` if needed.
 - Local access (from the k3s server): `kubectl -n pdfdiff port-forward svc/flower 5555:5555`
 - SSH tunnel from your machine: `ssh -L 5555:127.0.0.1:5555 <user>@<server>` then open http://localhost:5555

4) Deploy:
- `sudo python deploy/deploy.py`

5) Verify:
- `sudo python deploy/verify.py`

6) Uninstall (if needed):
- `sudo python deploy/uninstall.py`

Optional env vars:
- `IN_DIR` (folder with image tars for `load_images.py`)
- `CERT_MANAGER_VERSION` (defaults to v1.14.5)
- `KUBECONFIG` (defaults to /etc/rancher/k3s/k3s.yaml)
- `K8S_PROD_DIR` (path to k8s-prod if not next to deploy/)