#!/usr/bin/env bash
# Install everything the plasma-sim workflow needs. Idempotent: re-running skips what exists.
#   PLASMA_SIM_DIR  work/output root            (default ~/plasma_sim)
#   MEEP_ENV        conda env for Meep          (default $PLASMA_SIM_DIR/envs/meep)
set -euo pipefail
ROOT=${PLASMA_SIM_DIR:-$HOME/plasma_sim}; MEEP_ENV=${MEEP_ENV:-$ROOT/envs/meep}
mkdir -p "$ROOT"/{icp,meep,ccp_run,report}
echo "== python deps (numpy scipy matplotlib)"
python3 -c "import numpy, scipy, matplotlib" 2>/dev/null || python3 -m pip install --user numpy scipy matplotlib
echo "== Meep (conda-forge pymeep) -> $MEEP_ENV"
if [ ! -x "$MEEP_ENV/bin/python" ] || ! "$MEEP_ENV/bin/python" -c "import meep" 2>/dev/null; then
  MM=$(command -v micromamba || command -v mamba || command -v conda) || { echo "need micromamba/mamba/conda"; exit 2; }
  "$MM" create -y -q -p "$MEEP_ENV" -c conda-forge python=3.11 "pymeep=*=mpi_mpich_*" matplotlib h5py
fi
"$MEEP_ENV/bin/python" -c "import meep; print('meep', meep.__version__)" 2>&1 | grep '^meep'
echo "== eduPIC (GPLv3, cloned, not vendored)"
[ -d "$ROOT/eduPIC" ] || git clone -q --depth 1 https://github.com/donkozoltan/eduPIC.git "$ROOT/eduPIC"
[ -x "$ROOT/ccp_run/eduPIC" ] || g++ -O3 -march=native -std=c++17 -o "$ROOT/ccp_run/eduPIC" "$ROOT/eduPIC/Cpp/eduPIC.cpp"
echo "== Korean font check"; fc-match -f '%{family}\n' ':lang=ko' || echo "no Korean font: install fonts-nanum or noto-cjk"
echo "READY  root=$ROOT  meep=$MEEP_ENV/bin/python"
