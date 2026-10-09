#!/usr/bin/env bash
# eduPIC reference CCP case (Ar 10 Pa, 13.56 MHz, 250 V, 2.5 cm): init, 1500 cycles to converge, 200 measured.
# ~4.7 h on one core of an 8-core laptop. Use a detached runner (nohup / systemd-run) - it outlives the shell.
set -euo pipefail
ROOT=${PLASMA_SIM_DIR:-$HOME/plasma_sim}; cd "$ROOT/ccp_run"
[ -f picdata.bin ] || ./eduPIC 0 > log_init.txt
./eduPIC ${CYCLES:-1500} > log_run.txt 2>&1
./eduPIC ${MEASURE:-200} m > log_meas.txt 2>&1
tail -2 conv.dat; grep -E "Electron density @ center|Mean ion energy at powered|Electron power density" info.txt
