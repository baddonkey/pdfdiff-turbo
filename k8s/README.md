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

## Local (Kind or Minikube)
This overlay exposes services as NodePorts for easy access.

1. Build or load images into your local cluster.
2. Apply the local overlay:
   - kubectl apply -k k8s/overlays/local
3. Get service URLs:
   - kubectl get svc -n pdfdiff

Typical entrypoints:
- API: NodePort on service "api" (port 8000)
- Admin: NodePort on service "admin" (port 80)
- Viewer: NodePort on service "viewer" (port 80)
- Flower: NodePort on service "flower" (port 5555)
- RabbitMQ UI: NodePort on service "rabbitmq" (port 15672)

### Current local setup (Minikube + Podman host network)
This is the working setup used in this repo on Fedora with rootful Podman:
1. Recreate Minikube using the Podman host network:
   - sudo env MINIKUBE_ROOTLESS=false minikube start --driver=podman --network=host --force
2. Apply the local overlay (use minikube’s kubectl when running rootful):
   - sudo minikube kubectl -- apply -k k8s/overlays/local
3. Build images (rootful Podman) to match the local overlay tags:
   - sudo podman build -t localhost/pdfdiff-turbo-api:1.1.0 -f api/Dockerfile .
   - sudo podman build -t localhost/pdfdiff-turbo-worker:1.1.0 -f api/Dockerfile .
   - sudo podman build -t localhost/pdfdiff-turbo-flower:1.1.0 -f api/Dockerfile .
   - sudo podman build -t localhost/pdfdiff-turbo-admin:1.1.2 -f admin/Dockerfile admin
   - sudo podman build -t localhost/pdfdiff-turbo-viewer:1.1.4 -f viewer/Dockerfile viewer
4. Load images into Minikube (stream from Podman):
   - sudo podman save localhost/pdfdiff-turbo-api:1.1.0 | sudo minikube image load -
   - sudo podman save localhost/pdfdiff-turbo-worker:1.1.0 | sudo minikube image load -
   - sudo podman save localhost/pdfdiff-turbo-flower:1.1.0 | sudo minikube image load -
   - sudo podman save localhost/pdfdiff-turbo-admin:1.1.2 | sudo minikube image load -
   - sudo podman save localhost/pdfdiff-turbo-viewer:1.1.4 | sudo minikube image load -

### Local Ingress (recommended for browser access)
This overlay includes a local Ingress definition at k8s/overlays/local/ingress.yaml. To enable it:
1. Enable the ingress addon:
   - minikube addons enable ingress
2. Apply the local ingress resource:
   - kubectl apply -f k8s/overlays/local/ingress.yaml
3. Point DNS to your host LAN IP (example 192.168.1.17) by adding entries on any client machine:
   - 192.168.1.17 api.pdfdiff-turbo.local
   - 192.168.1.17 admin.pdfdiff-turbo.local
   - 192.168.1.17 viewer.pdfdiff-turbo.local
   - 192.168.1.17 flower.pdfdiff-turbo.local

Note: each client machine that should access the Ingress must have these /etc/hosts entries (or equivalent DNS).

If your Minikube is running with the Podman driver, you may need to forward host ports 80/443 to the ingress NodePorts:
1. Find ingress NodePorts:
   - kubectl get svc -n ingress-nginx
2. Forward ports on the host (example NodePorts 31472/30673):
   - sudo firewall-cmd --permanent --add-service=http
   - sudo firewall-cmd --permanent --add-service=https
   - sudo firewall-cmd --permanent --add-forward-port=port=80:proto=tcp:toaddr=<minikube-ip>:toport=<http-nodeport>
   - sudo firewall-cmd --permanent --add-forward-port=port=443:proto=tcp:toaddr=<minikube-ip>:toport=<https-nodeport>
   - sudo firewall-cmd --reload

Then browse using the hostnames above, e.g. http://viewer.pdfdiff-turbo.local

### NodePort access on Minikube + Podman (Fedora)
If your host cannot reach the Minikube IP (e.g., 192.168.49.2), add a **persistent** host route for the Minikube subnet via the podman bridge interface (typically `podman1`). This keeps NodePorts reachable across reboots.

Recommended approach (NetworkManager):
1. Identify the active connection name for your host interface:
   - nmcli -t -f NAME,DEVICE connection show --active
2. Add a static route for 192.168.49.0/24 via podman1 on that connection (replace <CONNECTION_NAME>):
   - nmcli connection modify <CONNECTION_NAME> +ipv4.routes "192.168.49.0/24 podman1"
3. Reconnect the interface (or reboot):
   - nmcli connection down <CONNECTION_NAME> && nmcli connection up <CONNECTION_NAME>

After this, NodePort URLs like `http://<minikube-ip>:<nodeport>` should work consistently.

## Production (cloud)
This overlay adds an Ingress and assumes you have an Ingress controller (nginx) installed.

1. Push images to a container registry (ECR/ACR/GCR).
2. Update image references if needed (or use kustomize images).
3. Set your domain hosts in k8s/overlays/prod/ingress.yaml.
4. Apply the production overlay:
   - kubectl apply -k k8s/overlays/prod

## Configuration
- Base configuration is in k8s/base/configmap.yaml.
- Secrets are in k8s/base/secret.yaml. Replace JWT_SECRET and POSTGRES_PASSWORD.
- PVC sizes are in k8s/base/persistent-volumes.yaml.

## Notes
- The API container runs migrations at startup.
- The /data volume is shared between API and worker via a PVC.
- If you want samples mounted, add a hostPath volume (local) or bake samples into the image.
