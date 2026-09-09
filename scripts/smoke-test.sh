#!/bin/sh
set -eu

repo_dir="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$repo_dir"

image="${AICONFIGURATOR_IMAGE:-aiconfigurator-web:local}"
target="${AICONFIGURATOR_DOCKER_TARGET:-smoke}"
model="${AICONFIGURATOR_MODEL:-Qwen/Qwen3-32B-FP8}"
gpus="${AICONFIGURATOR_GPUS:-32}"
system="${AICONFIGURATOR_SYSTEM:-h200_sxm}"
output_dir="${SMOKE_OUTPUT_DIR:-.tmp/task-000}"
case "$output_dir" in
    /*) ;;
    *) output_dir="$repo_dir/$output_dir" ;;
esac

mkdir -p "$output_dir/artifacts"

build_log="$output_dir/build.log"
build_runtime_file="$output_dir/build-runtime-ms.txt"
reference_stdout="$output_dir/reference.stdout.log"
reference_stderr="$output_dir/reference.stderr.log"
artifact_stdout="$output_dir/artifact.stdout.log"
artifact_stderr="$output_dir/artifact.stderr.log"
reference_runtime_file="$output_dir/reference-runtime-ms.txt"
reference_status_file="$output_dir/reference-exit-status.txt"
artifact_runtime_file="$output_dir/artifact-runtime-ms.txt"
artifact_status_file="$output_dir/artifact-exit-status.txt"
overall_status_file="$output_dir/exit-status.txt"
commands_file="$output_dir/commands.txt"
files_file="$output_dir/artifact-files.txt"

build_command="docker build --platform linux/amd64 --target $target --load -t $image ."
reference_command="docker run --rm --platform linux/amd64 $image cli default --model $model --total-gpus $gpus --system $system"
artifact_command="docker run --rm --platform linux/amd64 --mount type=bind,src=$output_dir/artifacts,dst=/tmp/aiconfigurator-run $image cli default --model $model --total-gpus $gpus --system $system --save-dir /tmp/aiconfigurator-run"

{
    printf '%s\n' "$build_command"
    printf '%s\n' "$reference_command"
    printf '%s\n' "$artifact_command"
} > "$commands_file"

echo "[TASK-000] Building $image"
echo "$build_command"
build_start_ns="$(python3 -c 'import time; print(time.monotonic_ns())')"
set +e
sh -c "$build_command" > "$build_log" 2>&1
build_status=$?
set -e
build_end_ns="$(python3 -c 'import time; print(time.monotonic_ns())')"
printf '%s\n' "$(( (build_end_ns - build_start_ns) / 1000000 ))" > "$build_runtime_file"
printf '%s\n' "$build_status" > "$output_dir/build-exit-status.txt"
if [ "$build_status" -ne 0 ]; then
    echo "Docker image build failed with exit status $build_status. See $build_log."
    exit "$build_status"
fi

run_smoke() {
    command="$1"
    stdout_file="$2"
    stderr_file="$3"
    runtime_file="$4"
    status_file="$5"
    start_ns="$(python3 -c 'import time; print(time.monotonic_ns())')"
    set +e
    sh -c "$command" > "$stdout_file" 2> "$stderr_file"
    command_status=$?
    set -e
    end_ns="$(python3 -c 'import time; print(time.monotonic_ns())')"
    runtime_ms=$(( (end_ns - start_ns) / 1000000 ))
    printf '%s\n' "$runtime_ms" > "$runtime_file"
    printf '%s\n' "$command_status" > "$status_file"
    return "$command_status"
}

echo "[TASK-000] Running reference smoke test"
echo "$reference_command"
if ! run_smoke "$reference_command" "$reference_stdout" "$reference_stderr" "$reference_runtime_file" "$reference_status_file"; then
    command_status="$(sed -n '1p' "$reference_status_file")"
    printf '%s\n' "$command_status" > "$overall_status_file"
    echo "Reference smoke test failed with exit status $command_status."
    exit "$command_status"
fi

echo "[TASK-000] Running artifact smoke test"
echo "$artifact_command"
if ! run_smoke "$artifact_command" "$artifact_stdout" "$artifact_stderr" "$artifact_runtime_file" "$artifact_status_file"; then
    command_status="$(sed -n '1p' "$artifact_status_file")"
    printf '%s\n' "$command_status" > "$overall_status_file"
    echo "Artifact smoke test failed with exit status $command_status."
    exit "$command_status"
fi

find "$output_dir/artifacts" -type f -print | sort > "$files_file"
printf '%s\n' "0" > "$overall_status_file"

echo "[TASK-000] Smoke test passed"
echo "Reference exit status: $(sed -n '1p' "$reference_status_file")"
echo "Reference runtime (ms): $(sed -n '1p' "$reference_runtime_file")"
echo "Artifact exit status: $(sed -n '1p' "$artifact_status_file")"
echo "Artifact runtime (ms): $(sed -n '1p' "$artifact_runtime_file")"
echo "Artifacts:"
sed 's/^/  /' "$files_file"
