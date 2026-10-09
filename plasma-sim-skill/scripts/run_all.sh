#!/usr/bin/env bash
# Full pipeline: ICP self-consistent study -> Meep cross-check -> (eduPIC post) -> HTML report.
#   STAGES="icp meep edupic report" (default all but the 4-5 h eduPIC run itself, see run_edupic.sh)
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd)
export PLASMA_SIM_DIR=${PLASMA_SIM_DIR:-$HOME/plasma_sim}; ROOT=$PLASMA_SIM_DIR
MEEP_PY=${MEEP_ENV:-$ROOT/envs/meep}/bin/python
STAGES=${STAGES:-"icp meep edupic report"}
has(){ [[ " $STAGES " == *" $1 "* ]]; }
if has icp; then
  echo "== ICP model"; cd "$ROOT/icp"
  python3 "$S/icp/study.py" | tail -3; python3 "$S/icp/study2.py"; python3 "$S/icp/conv_test.py"; python3 "$S/icp/figs.py"
fi
if has meep; then
  echo "== Meep FDTD (5 densities @ res 5, 2 @ res 10)"; cd "$ROOT/meep"
  for ne in 1e9 1e10 1e11 2.14e11 1e12; do OMP_NUM_THREADS=1 "$MEEP_PY" "$S/meep/icp_meep.py" $ne ne_$ne.npz 5 > log_$ne.txt 2>&1 & done; wait
  for ne in 1e11 1e12; do OMP_NUM_THREADS=1 "$MEEP_PY" "$S/meep/icp_meep.py" $ne r10_$ne.npz 10 > log_r10_$ne.txt 2>&1 & done; wait
  grep -h DONE log_*.txt; "$MEEP_PY" "$S/meep/figs.py" | tail -8
fi
if has edupic; then
  if [ -f "$ROOT/ccp_run/info.txt" ]; then echo "== eduPIC post"; cd "$ROOT/ccp_run" && python3 "$S/edupic/edupic_figs.py" | tail -3
  else echo "== eduPIC: no results yet - run scripts/edupic/run_edupic.sh first (4-5 h)"; fi
fi
if has report; then
  echo "== report"; cd "$ROOT/report"; python3 "$S/report/extra_figs.py"; python3 "$S/report/make_report.py"
  echo "REPORT $ROOT/report/ICP_plasma_opensource_report.html"
fi
