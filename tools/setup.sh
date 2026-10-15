#!/bin/sh
# Reproduce the project-local toolchain. Never installs system-wide packages.
set -eu
cd "$(dirname "$0")/.."
TASK_OS=$(uname -s)
TASK_ARCH=$(uname -m)
case "$TASK_OS:$TASK_ARCH" in
 Darwin:arm64) TASK_GBDK_ARCHIVE=gbdk-macos-arm64.tar.gz ;;
 Darwin:x86_64) TASK_GBDK_ARCHIVE=gbdk-macos.tar.gz ;;
 Linux:aarch64|Linux:arm64) TASK_GBDK_ARCHIVE=gbdk-linux-arm64.tar.gz ;;
 Linux:x86_64) TASK_GBDK_ARCHIVE=gbdk-linux64.tar.gz ;;
 *) echo 'Install GBDK-2020 4.5.0 from its official release and set GBDK_HOME.'; exit 1 ;;
esac
if [ ! -x tools/gbdk/bin/lcc ]; then
 TASK_DOWNLOAD=$(mktemp -d)
 trap 'rm -rf "$TASK_DOWNLOAD"' EXIT HUP INT TERM
 curl -fL "https://github.com/gbdk-2020/gbdk-2020/releases/download/4.5.0/$TASK_GBDK_ARCHIVE" -o "$TASK_DOWNLOAD/gbdk.tar.gz"
 tar -xzf "$TASK_DOWNLOAD/gbdk.tar.gz" -C tools
fi
if [ -z "${PYTHON_BIN:-}" ]; then
 if command -v python3.12 >/dev/null 2>&1; then PYTHON_BIN=python3.12; else PYTHON_BIN=python3; fi
fi
"$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3,12), "Emulator dependencies require Python 3.12 or newer"'
if [ ! -x tools/emulator-venv/bin/python ]; then "$PYTHON_BIN" -m venv tools/emulator-venv; fi
tools/emulator-venv/bin/python -m pip install -r tests/requirements-emulator.txt
make assets
make
