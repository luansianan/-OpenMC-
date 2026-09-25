#!/bin/bash
# =============================================================================
#  environment/build_xs.sh - ENDF/B-VIII.0 -> OpenMC HDF5 library
#
#  Usage:
#      wsl -d <distro> -u root -- bash environment/build_xs.sh [--workers N]
#  Environment variables:
#      ENV_PREFIX   default /root/openmc-env
#      ENDF_DIR     default /root/endf/raw
#      XS_DIR       default /root/xs
# =============================================================================
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PREFIX="${ENV_PREFIX:-/root/openmc-env}"

export PATH="$ENV_PREFIX/bin:$PATH"
export ENVF="${ENDF_DIR:-/root/endf/raw}"
export XSD="${XS_DIR:-/root/xs}"

"$ENV_PREFIX/bin/python" "$REPO/environment/build_xs.py" "$@"
echo
echo "set this before running OpenMC:"
echo "  export OPENMC_CROSS_SECTIONS=$XSD/cross_sections.xml"
