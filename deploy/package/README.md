# PDFDiff Turbo deployment package

This folder creates a self-contained deployment bundle with Kubernetes manifests and pre-built images for a single-VM Minikube deployment.

## What the bundle contains
- k8s manifests (base + overlays)
- Podman image tar files
- Load script for Minikube

## A) Build the deployment bundle (build machine)

Requirements on the build machine:
- Linux with Podman
- Internet access (for base image pulls)

Steps:
1) Build and package:
```bash
chmod +x deploy/package/build-and-package.sh
./deploy/package/build-and-package.sh
```
To also create the fully air‑gapped bundle (downloads .deb files, kubectl, and minikube):
```bash
AIRGAP=1 ./deploy/package/build-and-package.sh
```
2) Collect the bundle:
- The output is created at deploy/package/out/pdfdiff-turbo-deploy_<VERSION>.tar.gz
- The air‑gapped output is deploy/package/out/pdfdiff-turbo-airgap_<VERSION>.tar.gz

## B) Install Kubernetes on a Debian VM (target machine)

These steps install Podman, kubectl, and Minikube on Debian 11/12.

1) Base packages:
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release conntrack socat ebtables ethtool
```

2) Install Podman:
```bash
sudo apt-get update
sudo apt-get install -y podman
```

3) Install kubectl:
```bash
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.29/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
sudo chmod a+r /etc/apt/keyrings/kubernetes-apt-keyring.gpg

echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.29/deb/ /" | sudo tee /etc/apt/sources.list.d/kubernetes.list > /dev/null
sudo apt-get update
sudo apt-get install -y kubectl
```

4) Install Minikube:
```bash
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

## C) Deploy on the Debian VM (target machine)

1) Copy the bundle to the VM and extract:
```bash
tar -xzf pdfdiff-turbo-deploy_<VERSION>.tar.gz
cd bundle
```

2) Start Minikube with Podman:
```bash
minikube start --driver=podman
```

3) Load images into Minikube:
```bash
chmod +x load-into-minikube.sh
./load-into-minikube.sh
```

4) Deploy the stack:
```bash
kubectl apply -k k8s/overlays/local
```

5) Enable ingress:
```bash
minikube addons enable ingress
```

6) (Optional) TLS for local hostnames
If you want trusted TLS on the VM, install mkcert and generate the TLS secret:
```bash
sudo apt-get install -y mkcert
mkcert -install
python3 scripts/generate-k8s-local-tls.py
kubectl apply -f k8s/overlays/local/tls-secret.yaml
kubectl apply -f k8s/overlays/local/ingress.yaml
```

7) Access services
- Viewer: https://viewer.pdfdiff-turbo.local
- Admin: https://admin.pdfdiff-turbo.local
- API: https://api.pdfdiff-turbo.local
- Flower: https://flower.pdfdiff-turbo.local

Add /etc/hosts entries on your client machine:
- <vm-ip> api.pdfdiff-turbo.local
- <vm-ip> admin.pdfdiff-turbo.local
- <vm-ip> viewer.pdfdiff-turbo.local
- <vm-ip> flower.pdfdiff-turbo.local

## Notes
- Default credentials are in the root README.
- If you change VERSION, update k8s/overlays/local/kustomization.yaml image tags accordingly.

---

# Fully air‑gapped install (no internet on the target VM)

This section assumes you already built the bundle on a machine with internet.

## 1) Prepare offline artifacts (on an internet‑connected build machine)

### A. Download Debian packages
Create a folder to hold .deb files:
```bash
mkdir -p offline-debs
```

Download packages (and dependencies) for Podman + prerequisites:
```bash
sudo apt-get update
sudo apt-get install -y apt-rdepends

pkgs=(ca-certificates curl gnupg lsb-release conntrack socat ebtables ethtool)
podman_pkgs=(podman)

apt-rdepends ${pkgs[@]} ${podman_pkgs[@]} | grep -E '^\w' | sort -u > offline-debs/package-list.txt
cd offline-debs
xargs -a package-list.txt apt-get download
```

Optional (if you want mkcert on the target):
```bash
apt-rdepends mkcert | grep -E '^\w' | sort -u > mkcert-list.txt
xargs -a mkcert-list.txt apt-get download
```

### B. Download kubectl and minikube binaries
```bash
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
curl -LO https://dl.k8s.io/release/v1.29.0/bin/linux/amd64/kubectl
curl -LO https://dl.k8s.io/release/v1.29.0/bin/linux/amd64/kubectl.sha256
```

### C. Collect everything into one transfer bundle
```bash
VERSION=$(cat VERSION)
tar -czf pdfdiff-turbo-airgap_${VERSION}.tar.gz \
	deploy/package/out/pdfdiff-turbo-deploy_${VERSION}.tar.gz \
	offline-debs \
	minikube-linux-amd64 \
	kubectl \
	kubectl.sha256
```

Copy pdfdiff-turbo-airgap_<VERSION>.tar.gz to the target VM (USB, SCP over a controlled link, etc.).

## 2) Install on the air‑gapped Debian VM (no internet)

### A. Install Podman and prerequisites from .deb files
```bash
tar -xzf pdfdiff-turbo-airgap_<VERSION>.tar.gz
cd offline-debs
sudo dpkg -i ./*.deb || sudo apt-get -f install -y
```

Download and install the Podman .deb packages from the build machine.

### B. Install kubectl and Minikube binaries
```bash
cd ..
sha256sum -c kubectl.sha256
sudo install kubectl /usr/local/bin/kubectl
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

### C. Deploy from the bundle
```bash
tar -xzf deploy/package/out/pdfdiff-turbo-deploy_<VERSION>.tar.gz
cd bundle
minikube start --driver=podman
chmod +x load-into-minikube.sh
./load-into-minikube.sh
kubectl apply -k k8s/overlays/local
minikube addons enable ingress
```

### D. (Optional) Local TLS in air‑gapped mode
If you included mkcert .deb files, install them from offline-debs and run:
```bash
mkcert -install
python3 scripts/generate-k8s-local-tls.py
kubectl apply -f k8s/overlays/local/tls-secret.yaml
kubectl apply -f k8s/overlays/local/ingress.yaml
```

## Air‑gapped notes
- Keep the package list consistent with the target Debian version.
- If dpkg reports missing dependencies, re‑run the apt‑rdepends download on the build machine and re‑copy.
- The deployment bundle already contains all container images as tar files; no registry access is needed.
