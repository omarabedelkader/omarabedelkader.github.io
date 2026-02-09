#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$ROOT_DIR/runner"

shopt -s nullglob
scripts=( "$SCRIPTS_DIR"/*.sh )

if (( ${#scripts[@]} == 0 )); then
  echo "No .sh files found in: $SCRIPTS_DIR"
  exit 0
fi

for script in "${scripts[@]}"; do
  echo "==> Running $(basename "$script")"
  ( cd "$ROOT_DIR" && bash "$script" )
done
