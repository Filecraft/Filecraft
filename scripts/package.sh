#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
swift build -c release --product Prepare
BIN_DIR="$(swift build -c release --show-bin-path)"
python3 scripts/package.py --binary "$BIN_DIR/Prepare"
