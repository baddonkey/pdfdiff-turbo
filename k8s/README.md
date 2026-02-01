# Kubernetes deployment

This folder contains Kustomize manifests for local and production deployments.

## Image expectations
These manifests reference the same image names used in docker-compose:
- pdfdiff-turbo-api:1.1.0
- pdfdiff-turbo-worker:1.1.0
- pdfdiff-turbo-flower:1.1.0
- pdfdiff-turbo-admin:1.1.0
- pdfdiff-turbo-viewer:1.1.0

Build and push these images to a registry that your cluster can access, or load them into your local cluster (Kind/Minikube).

## Local (Minikube + Podman rootful, from scratch)
This is the working setup used in this repo on Fedora with rootful Podman.

### Prerequisites
- Podman installed
- Minikube installed
- mkcert installed (for trusted local HTTPS)

### 1) Start Minikube (rootful Podman + host networking)
- sudo env MINIKUBE_ROOTLESS=false minikube start --driver=podman --network=host --force

### 2) Build and load images into Minikube
Build images (rootful Podman) to match the local overlay tags:
- sudo podman build -t localhost/pdfdiff-turbo-api:1.1.0 -f api/Dockerfile .
- sudo podman build -t localhost/pdfdiff-turbo-worker:1.1.0 -f api/Dockerfile .
- sudo podman build -t localhost/pdfdiff-turbo-flower:1.1.0 -f api/Dockerfile .
- sudo podman build -t localhost/pdfdiff-turbo-admin:1.1.3 -f admin/Dockerfile admin
- sudo podman build -t localhost/pdfdiff-turbo-viewer:1.1.3 -f viewer/Dockerfile viewer

Load images into Minikube (stream from Podman):
- sudo podman save localhost/pdfdiff-turbo-api:1.1.0 | sudo minikube image load -
- sudo podman save localhost/pdfdiff-turbo-worker:1.1.0 | sudo minikube image load -
- sudo podman save localhost/pdfdiff-turbo-flower:1.1.0 | sudo minikube image load -
- sudo podman save localhost/pdfdiff-turbo-admin:1.1.3 | sudo minikube image load -
- sudo podman save localhost/pdfdiff-turbo-viewer:1.1.3 | sudo minikube image load -

### 3) Deploy the stack
- sudo minikube kubectl -- apply -k k8s/overlays/local

### 4) Enable Ingress + trusted HTTPS
Enable the ingress addon:
- sudo minikube addons enable ingress

Install mkcert (Fedora):
- sudo dnf install -y mkcert

Generate trusted local TLS and apply the secret:
- python scripts/generate-k8s-local-tls.py
- sudo minikube kubectl -- apply -f k8s/overlays/local/tls-secret.yaml

Apply the local ingress resource:
- sudo minikube kubectl -- apply -f k8s/overlays/local/ingress.yaml

### 5) Expose Ingress to your LAN (required for other machines)
Get the ingress NodePorts:
- sudo minikube kubectl -- get svc -n ingress-nginx

Forward host ports 80/443 to the ingress NodePorts (example NodePorts 32365/31459):
- sudo firewall-cmd --permanent --add-service=http
- sudo firewall-cmd --permanent --add-service=https
- sudo firewall-cmd --permanent --add-masquerade
- sudo firewall-cmd --permanent --add-forward-port=port=80:proto=tcp:toaddr=<minikube-ip>:toport=<http-nodeport>
- sudo firewall-cmd --permanent --add-forward-port=port=443:proto=tcp:toaddr=<minikube-ip>:toport=<https-nodeport>
- sudo firewall-cmd --reload

Get the Minikube IP (for the forward rules above):
- sudo minikube ip

### 6) DNS/hosts entries on each client machine
Point DNS to your host LAN IP (example 192.168.1.17) by adding entries on any client machine:
- 192.168.1.17 api.pdfdiff-turbo.local
- 192.168.1.17 admin.pdfdiff-turbo.local
- 192.168.1.17 viewer.pdfdiff-turbo.local
- 192.168.1.17 flower.pdfdiff-turbo.local

Then browse using the hostnames above, e.g. https://viewer.pdfdiff-turbo.local

## Production (cloud)
This overlay adds an Ingress and assumes you have an Ingress controller (nginx) installed.

1. Push images to a container registry (ECR/ACR/GCR).
2. Update image references if needed (or use kustomize images).
3. Set your domain hosts in k8s/overlays/prod/ingress.yaml.
4. Set your email in k8s/overlays/prod/letsencrypt-clusterissuer.yaml.
5. Install cert-manager in the cluster.
6. Apply the production overlay:
   - kubectl apply -k k8s/overlays/prod

## Configuration
- Base configuration is in k8s/base/configmap.yaml.
- Secrets are in k8s/base/secret.yaml. Replace JWT_SECRET and POSTGRES_PASSWORD.
- PVC sizes are in k8s/base/persistent-volumes.yaml.

## Notes
- The API container runs migrations at startup.
- The /data volume is shared between API and worker via a PVC.
- If you want samples mounted, add a hostPath volume (local) or bake samples into the image.
