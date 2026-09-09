#!/bin/sh
set -eu

image="${PORTAL_IMAGE:-aiconfigurator-portal:local}"
platform="${PORTAL_PLATFORM:-linux/amd64}"
host_port="${PORTAL_HOST_PORT:-18000}"
container_id=""
tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/aiconfigurator-container-check.XXXXXX")"

cleanup() {
    if [ -n "$container_id" ]; then
        docker rm --force "$container_id" >/dev/null 2>&1 || true
    fi
    rm -rf "$tmp_dir"
}
trap cleanup EXIT INT TERM

container_id="$(docker run --detach --rm \
    --platform "$platform" \
    --publish "127.0.0.1:${host_port}:8000" \
    "$image")"

attempt=0
until curl --fail --silent "http://127.0.0.1:${host_port}/live" >"$tmp_dir/live.json"; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 30 ]; then
        docker logs "$container_id" >&2 || true
        echo "Portal container did not become live" >&2
        exit 1
    fi
    sleep 1
done

curl --fail --silent "http://127.0.0.1:${host_port}/ready" >"$tmp_dir/ready.json"
curl --fail --silent "http://127.0.0.1:${host_port}/metrics" >"$tmp_dir/metrics.txt"
grep -q "http_server" "$tmp_dir/metrics.txt"

echo "Portal container check passed"
echo "  image: $image"
echo "  platform: $platform"
echo "  live: $(sed -n '1p' "$tmp_dir/live.json")"
echo "  ready: $(sed -n '1p' "$tmp_dir/ready.json")"
