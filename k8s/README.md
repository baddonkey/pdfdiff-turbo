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
