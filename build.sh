#!/usr/bin/env bash
# Stamp index.html with commit hash and build time before deploy
set -euo pipefail

HASH=$(git rev-parse --short HEAD)
TIME=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

sed -i "s/__COMMIT__/${HASH}/g" index.html
sed -i "s/__BUILD_TIME__/${TIME}/g" index.html

echo "Stamped: ${HASH} @ ${TIME}"
