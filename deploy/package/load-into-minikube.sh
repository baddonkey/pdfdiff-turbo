#!/usr/bin/env bash
set -euo pipefail

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGES_DIR="${BUNDLE_DIR}/images"

if ! command -v minikube >/dev/null 2>&1; then
  echo "minikube not found on PATH." >&2
  exit 1
fi

if [[ ! -d "${IMAGES_DIR}" ]]; then
  echo "Images directory not found: ${IMAGES_DIR}" >&2
  exit 1
fi

for image_tar in "${IMAGES_DIR}"/*.tar; do
  echo "Loading ${image_tar} into Minikube..."
  minikube image load "${image_tar}"
done

echo "All images loaded."
