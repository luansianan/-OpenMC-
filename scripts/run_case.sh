#!/bin/bash
# =============================================================================
#  scripts/run_case.sh - build the model, run OpenMC, post-process
#
#  run_case.sh <enrichment> <tag> [particles] [batches] [inactive] [threads] [pellet]
#      enrichment : U-235/(U-235+U-238) in %      (default 14.83)
#      tag        : run directory name under $RUN_ROOT
#      pellet     : solid | annular               (default solid)
#
#  Environment variables:
#      REPO       repository root                 (default: parent of this script)
#      RUN_ROOT   where the run directories go    (default: $REPO/runs)
#      ENV_PREFIX conda env prefix                (default /root/openmc-env)
#      OPENMC_CROSS_SECTIONS                      (default /root/xs/cross_sections.xml)
# =============================================================================
set -euo pipefail

REPO="${REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
RUN_ROOT="${RUN_ROOT:-$REPO/runs}"
ENV_PREFIX="${ENV_PREFIX:-/root/openmc-env}"
export PATH="$ENV_PREFIX/bin:$PATH"
export OPENMC_CROSS_SECTIONS="${OPENMC_CROSS_SECTIONS:-/root/xs/cross_sections.xml}"

ENR="${1:?usage: run_case.sh <enrichment> <tag> [particles] [batches] [inactive] [threads] [pellet]}"
TAG="${2:?tag required}"
P=${3:-20000}; B=${4:-45}; I=${5:-10}; T=${6:-12}; PELLET=${7:-solid}
export OMP_NUM_THREADS="$T"

WD="$RUN_ROOT/$TAG"
mkdir -p "$WD"
cd "$WD"

echo "[$TAG] model: enrichment=$ENR % particles=$P batches=$B inactive=$I threads=$T pellet=$PELLET"
python "$REPO/model.py" --enrichment "$ENR" --particles "$P" --batches "$B" \
    --inactive "$I" --pellet "$PELLET" --outdir "$WD" > "$WD/build.log" 2>&1

echo "[$TAG] transport"
openmc --threads "$T" > "$WD/openmc.log" 2>&1

echo "[$TAG] post-processing"
python "$REPO/plot_results.py" "$WD" --enrichment "$ENR" --tag "$TAG" \
    > "$WD/post.log" 2>&1 || true
if grep -q "k_eff =" "$WD/post.log"; then
    grep -h "k_eff =\|paper k_eff" "$WD/post.log"
else
    echo "[$TAG] post-processing failed:"; tail -5 "$WD/post.log"
fi
echo "[$TAG] done -> $WD"
