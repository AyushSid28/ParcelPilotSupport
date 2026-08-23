#!/usr/bin/env bash
set -euo pipefail
# Native Render build: Python API + Vite UI. Not Docker.
python -m pip install --upgrade pip
pip install ./backend

NODE_VERSION=20.18.1
if ! command -v npm >/dev/null 2>&1; then
  curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" | tar -xJ
  export PATH="$PWD/node-v${NODE_VERSION}-linux-x64/bin:$PATH"
fi
npm --prefix web ci
npm --prefix web run build
