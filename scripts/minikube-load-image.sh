#!/bin/sh
set -eu

PROFILE=${MINIKUBE_PROFILE:-aiconfigurator}
IMAGE=${1:-aiconfigurator-portal:local}
CONTEXT=$(kubectl config current-context)

if [ "$CONTEXT" != "$PROFILE" ]; then
  echo "Refusing to load image: kubectl context is '$CONTEXT', expected '$PROFILE'" >&2
  exit 1
fi

case "$IMAGE" in
  */*)
    IMAGE_REF=$IMAGE
    BASE_NAME=${IMAGE%:*}
    ;;
  *)
    IMAGE_REF="docker.io/library/$IMAGE"
    BASE_NAME="docker.io/library/${IMAGE%:*}"
    ;;
esac

IMAGE_TAR=$(mktemp "${TMPDIR:-/tmp}/minikube-image.XXXXXX.tar")
trap 'rm "$IMAGE_TAR"' EXIT HUP INT TERM

docker save "$IMAGE_REF" -o "$IMAGE_TAR"
REMOTE_TAR="/tmp/$(basename "$IMAGE_TAR")"
minikube cp -p "$PROFILE" "$IMAGE_TAR" "$PROFILE:$REMOTE_TAR"
minikube ssh -p "$PROFILE" -- sudo ctr -n k8s.io images rm "$IMAGE_REF" 2>/dev/null || true
minikube ssh -p "$PROFILE" -- sudo ctr -n k8s.io images import \
  --platform linux/amd64 --base-name "$BASE_NAME" "$REMOTE_TAR"
