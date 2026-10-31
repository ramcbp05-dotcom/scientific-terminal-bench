#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$HERE/fixed/stream_stats.py" ./stream_stats.py
echo "applied oracle patch: stream_stats.py"
