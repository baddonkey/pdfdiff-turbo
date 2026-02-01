#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(cat "${ROOT_DIR}/VERSION")"
OUT_DIR="${ROOT_DIR}/deploy/package/out"
ENGINE="${CONTAINER_ENGINE:-podman}"
BUILD_JOBS="${BUILD_JOBS:-1}"
AIRGAP="${AIRGAP:-0}"

if ! command -v "${ENGINE}" >/dev/null 2>&1; then
  echo "Container engine '${ENGINE}' not found. Set CONTAINER_ENGINE=podman." >&2
  exit 1
fi

mkdir -p "${OUT_DIR}/images"

build_image() {
  local name="$1"
  local dockerfile="$2"
  local context="$3"
  "${ENGINE}" build --jobs="${BUILD_JOBS}" -t "localhost/${name}:${VERSION}" -f "${dockerfile}" "${context}"
}

save_image() {
  local name="$1"
  "${ENGINE}" save "localhost/${name}:${VERSION}" -o "${OUT_DIR}/images/${name}_${VERSION}.tar"
}

build_image "pdfdiff-turbo-api" "${ROOT_DIR}/api/Dockerfile" "${ROOT_DIR}"
build_image "pdfdiff-turbo-worker" "${ROOT_DIR}/api/Dockerfile" "${ROOT_DIR}"
build_image "pdfdiff-turbo-flower" "${ROOT_DIR}/api/Dockerfile" "${ROOT_DIR}"
build_image "pdfdiff-turbo-admin" "${ROOT_DIR}/admin/Dockerfile" "${ROOT_DIR}/admin"
build_image "pdfdiff-turbo-viewer" "${ROOT_DIR}/viewer/Dockerfile" "${ROOT_DIR}/viewer"

save_image "pdfdiff-turbo-api"
save_image "pdfdiff-turbo-worker"
save_image "pdfdiff-turbo-flower"
save_image "pdfdiff-turbo-admin"
save_image "pdfdiff-turbo-viewer"

rm -rf "${OUT_DIR}/bundle"
mkdir -p "${OUT_DIR}/bundle"

cp -a "${ROOT_DIR}/k8s" "${OUT_DIR}/bundle/"
cp -a "${ROOT_DIR}/deploy/package/load-into-minikube.sh" "${OUT_DIR}/bundle/"
cp -a "${ROOT_DIR}/deploy/package/README.md" "${OUT_DIR}/bundle/"
cp -a "${OUT_DIR}/images" "${OUT_DIR}/bundle/"

tar -C "${OUT_DIR}" -czf "${OUT_DIR}/pdfdiff-turbo-deploy_${VERSION}.tar.gz" bundle

echo "Package created: ${OUT_DIR}/pdfdiff-turbo-deploy_${VERSION}.tar.gz"

if [[ "${AIRGAP}" == "1" ]]; then
  AIRGAP_DIR="${OUT_DIR}/airgap"
  OFFLINE_DEBS_DIR="${AIRGAP_DIR}/offline-debs"
  mkdir -p "${OFFLINE_DEBS_DIR}"

  if ! command -v apt-get >/dev/null 2>&1; then
    echo "apt-get not found. Airgap bundle generation requires a Debian/Ubuntu build host." >&2
    exit 1
  fi

  sudo apt-get update
  sudo apt-get install -y apt-rdepends

  pkgs=(ca-certificates curl gnupg lsb-release conntrack socat ebtables ethtool)
  podman_pkgs=(podman)

  apt-rdepends ${pkgs[@]} ${podman_pkgs[@]} | grep -E '^\w' | sort -u > "${OFFLINE_DEBS_DIR}/package-list.txt"
  (cd "${OFFLINE_DEBS_DIR}" && xargs -a package-list.txt apt-get download)

  # Optional mkcert package list for offline TLS setup
  apt-rdepends mkcert | grep -E '^\w' | sort -u > "${OFFLINE_DEBS_DIR}/mkcert-list.txt" || true
  (cd "${OFFLINE_DEBS_DIR}" && xargs -a mkcert-list.txt apt-get download) || true

  curl -L -o "${AIRGAP_DIR}/minikube-linux-amd64" https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
  curl -L -o "${AIRGAP_DIR}/kubectl" https://dl.k8s.io/release/v1.29.0/bin/linux/amd64/kubectl
  curl -L -o "${AIRGAP_DIR}/kubectl.sha256" https://dl.k8s.io/release/v1.29.0/bin/linux/amd64/kubectl.sha256

  tar -C "${OUT_DIR}" -czf "${OUT_DIR}/pdfdiff-turbo-airgap_${VERSION}.tar.gz" \
    "bundle" \
    "airgap/offline-debs" \
    "airgap/minikube-linux-amd64" \
    "airgap/kubectl" \
    "airgap/kubectl.sha256"

  echo "Air‑gapped package created: ${OUT_DIR}/pdfdiff-turbo-airgap_${VERSION}.tar.gz"
fi
