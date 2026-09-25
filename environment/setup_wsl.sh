#!/bin/bash
# =============================================================================
#  environment/setup_wsl.sh
#
#  Install OpenMC + NJOY2016 inside a WSL (or native Linux) environment using
#  micromamba.  Written for the constraint encountered on Windows: conda-forge
#  publishes OpenMC only for linux-64 / osx-64, and the minimal Ubuntu WSL
#  image has no bzip2, so micromamba's .tar.bz2 must be unpacked with Python.
#
#  Usage (from Windows):
#      wsl -d <distro> -u root -- bash environment/setup_wsl.sh
#  Environment variables (optional):
#      MAMBA_PREFIX   default /root/mamba
#      ENV_PREFIX     default /root/openmc-env
#      MICROMAMBA     default /root/micromamba
# =============================================================================
set -euo pipefail

MAMBA_PREFIX="${MAMBA_PREFIX:-/root/mamba}"
ENV_PREFIX="${ENV_PREFIX:-/root/openmc-env}"
MICROMAMBA="${MICROMAMBA:-/root/micromamba}"

echo "== 1/3  micromamba =="
if [ ! -x "$MICROMAMBA" ]; then
  curl -L --retry 3 -o /root/mm.tar.bz2 \
      https://micro.mamba.pm/api/micromamba/linux-64/latest
  # the base image may not ship bzip2 -> use Python's tarfile(bz2)
  python3 - <<'PY'
import tarfile
t = tarfile.open('/root/mm.tar.bz2', 'r:bz2')
for m in t.getmembers():
    if m.isfile() and m.name.endswith('micromamba'):
        m.name = 'micromamba'
        t.extract(m, '/root')
t.close()
print('micromamba extracted')
PY
  chmod +x "$MICROMAMBA"
fi
"$MICROMAMBA" --version

echo "== 2/3  OpenMC =="
export MAMBA_ROOT_PREFIX="$MAMBA_PREFIX"
if [ ! -x "$ENV_PREFIX/bin/openmc" ]; then
  "$MICROMAMBA" create -y -p "$ENV_PREFIX" -c conda-forge \
      python=3.12 openmc numpy matplotlib pandas h5py uncertainties
fi
"$ENV_PREFIX/bin/openmc" --version

echo "== 3/3  NJOY2016 =="
"$MICROMAMBA" install -y -p "$ENV_PREFIX" -c conda-forge njoy2016
"$ENV_PREFIX/bin/njoy" --version 2>&1 | head -2 || true

echo
echo "done.  Activate with:"
echo "  export PATH=$ENV_PREFIX/bin:\$PATH"
echo "  export OPENMC_CROSS_SECTIONS=/root/xs/cross_sections.xml"
