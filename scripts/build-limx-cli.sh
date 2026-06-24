#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SCRATCH_SRC="$PROJECT_DIR/scratch-app"
SCRATCH_OUT="$PROJECT_DIR/scratch-static"
VENDOR_SCRATCH_APP="$PROJECT_DIR/limx-cli/vendor/scratch-app"
TARGET_DIR="${LIMX_SCRATCH_TARGET_DIR:-$PROJECT_DIR/target}"
PID_FILE="$PROJECT_DIR/.scratch-bridge.pid"
LOG_FILE="$PROJECT_DIR/.scratch-bridge.log"
if [ -n "${LIMX_SCRATCH_APP_DIR:-}" ]; then
    SCRATCH_APP_DIR="$LIMX_SCRATCH_APP_DIR"
elif [ -f "$VENDOR_SCRATCH_APP/node_modules/scratch-vm/src/index.js" ]; then
    SCRATCH_APP_DIR="$VENDOR_SCRATCH_APP"
else
    SCRATCH_APP_DIR="$SCRATCH_SRC"
fi

MODE="deploy"
CLEAN=0
CLEAN_DEPS=0
SKIP_BUILD=0
BACKGROUND=0
PULL=0
LISTEN_HOST="${LIMX_SCRATCH_LISTEN_HOST:-0.0.0.0}"
LISTEN_PORT="${LIMX_SCRATCH_LISTEN_PORT:-6080}"
ROBOT_HOST="${LIMX_ROBOT_HOST:-10.192.1.2}"
ROBOT_PORT="${LIMX_ROBOT_PORT:-5000}"
MENU_TIMEOUT="${LIMX_SCRATCH_MENU_TIMEOUT:-5}"
PYTHON_BIN="${LIMX_SCRATCH_PYTHON:-python3}"
NODE_VERSION="${LIMX_SCRATCH_NODE_VERSION:-22.22.0}"
NODE_ARCH="${LIMX_SCRATCH_NODE_ARCH:-}"
NODE_BIN="${LIMX_SCRATCH_NODE:-node}"
NODE_CACHE_DIR="${LIMX_SCRATCH_NODE_CACHE_DIR:-$PROJECT_DIR/.node-runtime}"

usage() {
    cat <<EOF
Usage:
  $0 [deploy|build|target|run|clean] [options]

Modes:
  deploy        Build copyable target, then run bridge from target (default)
  build         Build Scratch static files and copyable target only
  target        Build copyable target only from existing scratch-static/vendor
  run           Run bridge using existing scratch-static
  clean         Remove build outputs and exit

Options:
  --clean                 Clean build outputs before deploy/build
  --clean-deps            Also remove scratch-app/node_modules
  --skip-build            Deploy/run without rebuilding Scratch static files
  --background            Start bridge in background and write logs to $LOG_FILE
  --pull                  Fast-forward pull current git branch before build
  --listen-host HOST      Bridge listen host (default: $LISTEN_HOST)
  --listen-port PORT      Bridge listen port (default: $LISTEN_PORT)
  --robot-host HOST       Robot signaling host (default: $ROBOT_HOST)
  --robot-port PORT       Robot signaling port (default: $ROBOT_PORT)
  --menu-timeout SECONDS  Startup menu preload timeout (default: $MENU_TIMEOUT)
  --scratch-app-dir PATH  scratch-app source for background project runner (default: $SCRATCH_APP_DIR)
  --target-dir PATH       Copyable deployment target directory (default: $TARGET_DIR)
  --python PATH           Python executable (default: $PYTHON_BIN)
  --node PATH             Node executable for local run mode (default: $NODE_BIN)
  --node-version VERSION  Bundled target Node.js version (default: $NODE_VERSION)
  --node-arch ARCH        Bundled target arch: x64 or arm64 (default: host arch)
  -h, --help              Show this help

Examples:
  $0
  $0 --clean --background
  $0 build --target-dir /tmp/limx-cli-target
  /tmp/limx-cli-target/limx-scratch
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        deploy|build|target|run|clean)
            MODE="$1"
            shift
            ;;
        --clean)
            CLEAN=1
            shift
            ;;
        --clean-deps)
            CLEAN=1
            CLEAN_DEPS=1
            shift
            ;;
        --skip-build)
            SKIP_BUILD=1
            shift
            ;;
        --background)
            BACKGROUND=1
            shift
            ;;
        --pull)
            PULL=1
            shift
            ;;
        --listen-host)
            LISTEN_HOST="$2"
            shift 2
            ;;
        --listen-port)
            LISTEN_PORT="$2"
            shift 2
            ;;
        --robot-host)
            ROBOT_HOST="$2"
            shift 2
            ;;
        --robot-port)
            ROBOT_PORT="$2"
            shift 2
            ;;
        --menu-timeout)
            MENU_TIMEOUT="$2"
            shift 2
            ;;
        --scratch-app-dir)
            SCRATCH_APP_DIR="$2"
            shift 2
            ;;
        --target-dir)
            TARGET_DIR="$2"
            shift 2
            ;;
        --python)
            PYTHON_BIN="$2"
            shift 2
            ;;
        --node)
            NODE_BIN="$2"
            shift 2
            ;;
        --node-version)
            NODE_VERSION="$2"
            shift 2
            ;;
        --node-arch)
            NODE_ARCH="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

require_scratch_source() {
    if [ ! -d "$SCRATCH_SRC" ] || [ ! -f "$SCRATCH_SRC/package.json" ]; then
        echo "ERROR: scratch-app source is missing: $SCRATCH_SRC" >&2
        exit 1
    fi
}

clean_outputs() {
    echo "Cleaning build outputs ..."
    rm -rf \
        "$SCRATCH_SRC/build" \
        "$SCRATCH_SRC/dist" \
        "$SCRATCH_OUT" \
        "$VENDOR_SCRATCH_APP" \
        "$TARGET_DIR" \
        "$NODE_CACHE_DIR" \
        "$PROJECT_DIR/dist" \
        "$PROJECT_DIR/limx_cli.egg-info" \
        "$PROJECT_DIR/__pycache__" \
        "$PROJECT_DIR/tests/__pycache__" \
        "$PROJECT_DIR/limx-cli/__pycache__"
    rm -f "$PID_FILE" "$LOG_FILE"
    if [ "$CLEAN_DEPS" -eq 1 ]; then
        echo "Cleaning npm dependencies ..."
        rm -rf "$SCRATCH_SRC/node_modules"
    fi
}

sync_runner_runtime() {
    if [ ! -f "$SCRATCH_SRC/node_modules/scratch-vm/src/index.js" ]; then
        echo "ERROR: scratch-vm dependency is missing under $SCRATCH_SRC/node_modules" >&2
        exit 1
    fi

    echo "Syncing minimal Scratch VM runtime into Python package vendor ..."
    SCRATCH_SRC="$SCRATCH_SRC" VENDOR_SCRATCH_APP="$VENDOR_SCRATCH_APP" "$PYTHON_BIN" - <<'PY'
import json
import os
import shutil
from pathlib import Path

src = Path(os.environ["SCRATCH_SRC"])
dst = Path(os.environ["VENDOR_SCRATCH_APP"])
src_node_modules = src / "node_modules"
dst_node_modules = dst / "node_modules"
if dst.exists():
    shutil.rmtree(dst)
dst_node_modules.mkdir(parents=True, exist_ok=True)

package = {
    "name": "limx-scratch-runner-runtime",
    "private": True,
    "description": "Minimal runtime dependencies for limx-cli/scratch_runner.js",
}
(dst / "package.json").write_text(json.dumps(package, indent=2) + "\n")

seeds = {"scratch-vm", "@turbowarp/scratch-svg-renderer"}
visited = set()
missing = []


def package_path(root: Path, name: str) -> Path:
    if name.startswith("@"):
        scope, package_name = name.split("/", 1)
        return root / scope / package_name
    return root / name


def ignore(_path, names):
    ignored = {
        ".cache",
        ".git",
        ".github",
        ".nyc_output",
        ".vite",
        "coverage",
        "doc",
        "docs",
        "example",
        "examples",
        "test",
        "tests",
        "__tests__",
    }
    ignored.update(name for name in names if name.endswith((".log", ".md", ".map")))
    return ignored


def copy_package(name: str) -> None:
    if name in visited:
        return
    visited.add(name)

    package_src = package_path(src_node_modules, name)
    if not package_src.exists():
        missing.append(name)
        return

    package_dst = package_path(dst_node_modules, name)
    package_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(package_src, package_dst, symlinks=True, ignore=ignore)

    manifest = package_src / "package.json"
    if not manifest.exists():
        return

    try:
        package_json = json.loads(manifest.read_text())
    except Exception:
        return

    dependencies = {}
    for key in ("dependencies", "optionalDependencies"):
        value = package_json.get(key)
        if isinstance(value, dict):
            dependencies.update(value)

    for dependency in sorted(dependencies):
        copy_package(dependency)


for seed in sorted(seeds):
    copy_package(seed)

if missing:
    print("WARNING: missing optional runner package(s): " + ", ".join(sorted(missing)))
print(f"Runtime packages copied: {len(visited) - len(missing)}")
PY
    SCRATCH_APP_DIR="$VENDOR_SCRATCH_APP"
    echo "Runner runtime: $VENDOR_SCRATCH_APP"
}

install_cli() {
    echo "Installing Python CLI package ..."
    cd "$PROJECT_DIR"
    if ! "$PYTHON_BIN" -m pip install --force-reinstall .; then
        echo "pip install failed, falling back to setup.py install --user ..." >&2
        "$PYTHON_BIN" setup.py install --user
    fi
}

normalize_node_arch() {
    case "$1" in
        x64|amd64|x86_64)
            echo "x64"
            ;;
        arm64|aarch64)
            echo "arm64"
            ;;
        *)
            echo "ERROR: unsupported Node.js target architecture: $1 (supported: x64, arm64)" >&2
            exit 1
            ;;
    esac
}

normalize_node_version() {
    case "$1" in
        v*|V*)
            echo "${1#?}"
            ;;
        *)
            echo "$1"
            ;;
    esac
}

download_file() {
    url="$1"
    dest="$2"
    if command -v curl >/dev/null 2>&1; then
        curl -fL "$url" -o "$dest"
    elif command -v wget >/dev/null 2>&1; then
        wget -O "$dest" "$url"
    else
        echo "ERROR: curl or wget is required to download Node.js runtime" >&2
        exit 1
    fi
}

bundle_node_runtime() {
    NODE_VERSION="$(normalize_node_version "$NODE_VERSION")"
    if [ -z "$NODE_ARCH" ]; then
        NODE_ARCH="$(normalize_node_arch "$(uname -m)")"
    else
        NODE_ARCH="$(normalize_node_arch "$NODE_ARCH")"
    fi

    node_dist="node-v$NODE_VERSION-linux-$NODE_ARCH"
    node_url="https://nodejs.org/dist/v$NODE_VERSION/$node_dist.tar.xz"
    node_archive="$NODE_CACHE_DIR/$node_dist.tar.xz"
    node_src="$NODE_CACHE_DIR/$node_dist"

    mkdir -p "$NODE_CACHE_DIR"
    if [ ! -x "$node_src/bin/node" ]; then
        echo "Downloading Node.js v$NODE_VERSION for linux-$NODE_ARCH ..."
        rm -rf "$node_src" "$node_archive"
        download_file "$node_url" "$node_archive"
        tar -xJf "$node_archive" -C "$NODE_CACHE_DIR"
    fi

    echo "Bundling minimal Node.js runtime into target ..."
    rm -rf "$TARGET_DIR/node"
    mkdir -p "$TARGET_DIR/node/bin"
    cp "$node_src/bin/node" "$TARGET_DIR/node/bin/node"
    chmod +x "$TARGET_DIR/node/bin/node"
    printf '%s\n' "v$NODE_VERSION" > "$TARGET_DIR/node/VERSION"

    host_arch="$(normalize_node_arch "$(uname -m)")"
    if [ "$host_arch" = "$NODE_ARCH" ]; then
        "$TARGET_DIR/node/bin/node" --version >/dev/null
    else
        echo "Skipping Node runtime smoke test for non-host architecture linux-$NODE_ARCH"
    fi
}

build_target() {
    if [ ! -f "$SCRATCH_OUT/editor.html" ]; then
        echo "ERROR: Scratch static site is missing. Run build first: $SCRATCH_OUT" >&2
        exit 1
    fi
    if [ ! -f "$VENDOR_SCRATCH_APP/node_modules/scratch-vm/src/index.js" ]; then
        echo "ERROR: Runner vendor is missing. Run build first: $VENDOR_SCRATCH_APP" >&2
        exit 1
    fi

    echo "Building copyable deployment target ..."
    rm -rf "$TARGET_DIR"
    mkdir -p "$TARGET_DIR/python"

    wheelhouse="$(mktemp -d /tmp/limx-cli-wheelhouse.XXXXXX)"
    cleanup_wheelhouse() {
        rm -rf "$wheelhouse"
    }
    trap cleanup_wheelhouse EXIT

    cd "$PROJECT_DIR"
    rm -rf "$PROJECT_DIR/build" "$PROJECT_DIR/dist" "$PROJECT_DIR/limx_cli.egg-info"
    "$PYTHON_BIN" setup.py bdist_wheel -d "$wheelhouse" >/dev/null
    wheel="$(ls "$wheelhouse"/limx_cli-*.whl | head -n 1)"
    "$PYTHON_BIN" -m pip install --upgrade --target "$TARGET_DIR/python" "$wheel"
    if [ ! -f "$TARGET_DIR/python/websocket/__init__.py" ]; then
        echo "ERROR: Python dependency websocket-client was not bundled under $TARGET_DIR/python" >&2
        exit 1
    fi

    cp -r "$SCRATCH_OUT" "$TARGET_DIR/scratch-static"
    bundle_node_runtime

    cat > "$TARGET_DIR/limx-scratch" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -d "$SCRIPT_DIR/python" ]; then
    DIR="$SCRIPT_DIR"
elif [ -d "$SCRIPT_DIR/limx-cli.bin/python" ]; then
    DIR="$SCRIPT_DIR/limx-cli.bin"
else
    echo "ERROR: Cannot locate limx-cli runtime bundle near $SCRIPT_DIR" >&2
    exit 1
fi
PYTHON_BIN="${LIMX_SCRATCH_PYTHON:-python3}"
BUNDLED_NODE="$DIR/node/bin/node"

export PYTHONPATH="$DIR/python${PYTHONPATH:+:$PYTHONPATH}"
if [ -x "$BUNDLED_NODE" ]; then
    export LIMX_SCRATCH_NODE="$BUNDLED_NODE"
    export PATH="$DIR/node/bin:$PATH"
fi

exec "$PYTHON_BIN" -m limx-cli.scratch_bridge \
    --static-dir "$DIR/scratch-static" \
    "$@"
SH
    chmod +x "$TARGET_DIR/limx-scratch"

    cat > "$TARGET_DIR/limx-cli" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -d "$SCRIPT_DIR/python" ]; then
    DIR="$SCRIPT_DIR"
elif [ -d "$SCRIPT_DIR/limx-cli.bin/python" ]; then
    DIR="$SCRIPT_DIR/limx-cli.bin"
else
    echo "ERROR: Cannot locate limx-cli runtime bundle near $SCRIPT_DIR" >&2
    exit 1
fi
PYTHON_BIN="${LIMX_SCRATCH_PYTHON:-python3}"
BUNDLED_NODE="$DIR/node/bin/node"

export PYTHONPATH="$DIR/python${PYTHONPATH:+:$PYTHONPATH}"
if [ -x "$BUNDLED_NODE" ]; then
    export LIMX_SCRATCH_NODE="$BUNDLED_NODE"
    export PATH="$DIR/node/bin:$PATH"
fi

exec "$PYTHON_BIN" -m limx-cli.cli "$@"
SH
    chmod +x "$TARGET_DIR/limx-cli"

    cat > "$TARGET_DIR/README.txt" <<EOF
LimX CLI copyable target

Requirements on target machine:
- python3
- no system Node.js required; a linux-$NODE_ARCH Node.js v$NODE_VERSION runtime is bundled under ./node

Run Scratch bridge:
  ./limx-scratch

Open:
  http://<target-machine-ip>:6080/editor.html

Run CLI:
  ./limx-cli --robot-host <robot-ip> state mode
EOF

    echo "Target directory: $TARGET_DIR"
    echo "Target size: $(du -sh "$TARGET_DIR" | cut -f1)"
}

pull_latest() {
    echo "Pulling latest git changes ..."
    cd "$PROJECT_DIR"
    git pull --ff-only
}

build_static() {
    require_scratch_source
    echo "Installing frontend dependencies ..."
    cd "$SCRATCH_SRC"
    npm install --legacy-peer-deps

    echo "Building Scratch static site ..."
    NODE_ENV=production npm run build

    echo "Copying build output to $SCRATCH_OUT ..."
    rm -rf "$SCRATCH_OUT"
    cp -r "$SCRATCH_SRC/build" "$SCRATCH_OUT"

    sync_runner_runtime

    echo "Scratch static files: $SCRATCH_OUT"
    echo "Size: $(du -sh "$SCRATCH_OUT" | cut -f1)"
    echo "Runtime vendor size: $(du -sh "$VENDOR_SCRATCH_APP" | cut -f1)"
}

stop_existing_bridge() {
    if [ -f "$PID_FILE" ]; then
        old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
        if [ -n "${old_pid:-}" ] && kill -0 "$old_pid" 2>/dev/null; then
            echo "Stopping existing bridge pid $old_pid ..."
            kill "$old_pid" 2>/dev/null || true
            sleep 1
        fi
        rm -f "$PID_FILE"
    fi

    BRIDGE_LISTEN_PORT="$LISTEN_PORT" "$PYTHON_BIN" - <<'PY'
import os
import signal
import time

listen_port = os.environ.get("BRIDGE_LISTEN_PORT", "6080")
default_port = "6080"
current_pid = os.getpid()
stopped = []

for pid in os.listdir("/proc"):
    if not pid.isdigit() or int(pid) == current_pid:
        continue
    cmdline_path = os.path.join("/proc", pid, "cmdline")
    try:
        raw = open(cmdline_path, "rb").read()
    except OSError:
        continue
    if not raw:
        continue
    parts = [p.decode("utf-8", "ignore") for p in raw.split(b"\0") if p]
    text = " ".join(parts)
    if "limx-cli.scratch_bridge" not in text and "limx-scratch" not in text and "scratch_bridge" not in text:
        continue
    if "--listen-port" in parts:
        idx = parts.index("--listen-port")
        if idx + 1 >= len(parts) or parts[idx + 1] != listen_port:
            continue
    elif listen_port != default_port:
        continue
    try:
        os.kill(int(pid), signal.SIGTERM)
        stopped.append(pid)
    except OSError:
        pass

if stopped:
    print("Stopping bridge process(es): " + " ".join(stopped))
    time.sleep(1)
PY
}

run_bridge() {
    if [ ! -f "$SCRATCH_OUT/editor.html" ]; then
        echo "ERROR: Scratch static site is missing. Run build/deploy first: $SCRATCH_OUT" >&2
        exit 1
    fi

    stop_existing_bridge

    args=(
        -m limx-cli.scratch_bridge
        --listen-host "$LISTEN_HOST"
        --listen-port "$LISTEN_PORT"
        --robot-host "$ROBOT_HOST"
        --robot-port "$ROBOT_PORT"
        --menu-timeout "$MENU_TIMEOUT"
        --static-dir "$SCRATCH_OUT"
        --scratch-app-dir "$SCRATCH_APP_DIR"
        --node "$NODE_BIN"
    )

    echo "Bridge: http://127.0.0.1:$LISTEN_PORT/editor.html"
    echo "Robot signaling: $ROBOT_HOST:$ROBOT_PORT"
    cd "$PROJECT_DIR"

    if [ "$BACKGROUND" -eq 1 ]; then
        echo "Starting bridge in background ..."
        nohup "$PYTHON_BIN" "${args[@]}" >"$LOG_FILE" 2>&1 &
        echo "$!" > "$PID_FILE"
        echo "PID: $(cat "$PID_FILE")"
        echo "Log: $LOG_FILE"
    else
        exec "$PYTHON_BIN" "${args[@]}"
    fi
}

run_target_bridge() {
    if [ ! -x "$TARGET_DIR/limx-scratch" ]; then
        echo "ERROR: Target runner is missing. Run build first: $TARGET_DIR/limx-scratch" >&2
        exit 1
    fi

    echo "Bridge: http://127.0.0.1:$LISTEN_PORT/editor.html"
    echo "Robot signaling: $ROBOT_HOST:$ROBOT_PORT"
    echo "Target: $TARGET_DIR"

    args=(
        --listen-host "$LISTEN_HOST"
        --listen-port "$LISTEN_PORT"
        --robot-host "$ROBOT_HOST"
        --robot-port "$ROBOT_PORT"
        --menu-timeout "$MENU_TIMEOUT"
    )

    if [ "$BACKGROUND" -eq 1 ]; then
        echo "Starting target bridge in background ..."
        nohup "$TARGET_DIR/limx-scratch" "${args[@]}" >"$LOG_FILE" 2>&1 &
        echo "$!" > "$PID_FILE"
        echo "PID: $(cat "$PID_FILE")"
        echo "Log: $LOG_FILE"
    else
        exec "$TARGET_DIR/limx-scratch" "${args[@]}"
    fi
}

if [ "$CLEAN" -eq 1 ] || [ "$MODE" = "clean" ]; then
    require_scratch_source
    clean_outputs
fi

case "$MODE" in
    clean)
        echo "Clean complete."
        ;;
    build)
        if [ "$PULL" -eq 1 ]; then
            pull_latest
        fi
        build_static
        build_target
        ;;
    target)
        build_target
        ;;
    run)
        if [ -x "$TARGET_DIR/limx-scratch" ]; then
            run_target_bridge
        else
            run_bridge
        fi
        ;;
    deploy)
        if [ "$PULL" -eq 1 ]; then
            pull_latest
        fi
        if [ "$SKIP_BUILD" -eq 0 ]; then
            build_static
        fi
        build_target
        run_target_bridge
        ;;
esac
