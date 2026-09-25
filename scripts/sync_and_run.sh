#!/bin/bash
# =============================================================================
#  scripts/sync_and_run.sh - copy the repo into the Linux filesystem and run one case
#
#  Why: on WSL1 a few files on /mnt/c (drvfs) became unreadable/non-executable, so
#  the code is copied into the Linux filesystem first.  Results are written back to
#  the repository's runs/ directory.
#
#  Usage:
#      wsl -d <distro> -u root -- bash scripts/sync_and_run.sh [pellet] [enrichment] \
#              [particles] [batches] [inactive] [threads]
# =============================================================================
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-/root/openmc-lfr}"

mkdir -p "$WORK"
cp -f "$SRC/model.py" "$SRC/plot_results.py" "$WORK/"
rm -rf "$WORK/scripts"
cp -r "$SRC/scripts" "$WORK/scripts"
chmod +x "$WORK/scripts/"*.sh 2>/dev/null || true

PELLET=${1:-solid}; ENR=${2:-14.83}; P=${3:-20000}; B=${4:-45}; I=${5:-10}; T=${6:-12}
echo "repo  : $SRC"
echo "work  : $WORK"
REPO="$WORK" RUN_ROOT="$SRC/runs" \
    bash "$WORK/scripts/run_case.sh" "$ENR" "prod_$PELLET" "$P" "$B" "$I" "$T" "$PELLET"
