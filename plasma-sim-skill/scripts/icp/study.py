import json, numpy as np
from icp_source import Geometry, operate
out = {}
g = Geometry()
sweep = {}
for p in (5, 10, 30):
    rows = []
    for P in (30, 50, 80, 120, 200, 300, 500, 800, 1200):
        r = operate(g, p, P, n_guess=3e16)
        rows.append(dict(P=P, n0=r["n0"], Te=r["Te"], Rp=r["Rp"], eta=r["eta"], I=r["I"], skin=r["skin"]))
    sweep[p] = rows
out["sweep"] = sweep
designs = {"안쪽 집중 (2-8 cm)": (0.02, 0.04, 0.06, 0.08), "균등 (3-12 cm)": (0.03, 0.06, 0.09, 0.12),
           "바깥 집중 (6-13.5 cm)": (0.06, 0.09, 0.12, 0.135)}
dres = {}
for name, cr in designs.items():
    gd = Geometry(coil_r=cr)
    r = operate(gd, 10, 500)
    zi = np.argmin(np.abs(gd.z - (gd.H - 0.01)))            # 1 cm under the window
    prof = r["pden"][:, zi]; rr = gd.r
    inside = rr < gd.R
    pr = prof[inside]; rw = rr[inside]
    # radial uniformity of deposited power over the wafer radius (|r| < 0.15): (max-min)/(max+min)
    unif = (pr[rw < 0.14].max() - pr[rw < 0.14].min()) / (pr[rw < 0.14].max() + pr[rw < 0.14].min())
    r_peak = rw[np.argmax(pr)]
    dres[name] = dict(coil=cr, n0=r["n0"], Rp=r["Rp"], eta=r["eta"], I=r["I"], r_peak=r_peak, nonunif=unif,
                      prof_r=rw.tolist(), prof=(pr / pr.max()).tolist())
    print(f"{name:20} n0={r['n0']:.2e} Rp={r['Rp']:.2f} eta={r['eta']:.2f} I={r['I']:.1f}A peak@{r_peak*100:.1f}cm nonunif={unif:.2f}")
out["designs"] = dres
json.dump(out, open("study.json", "w"), ensure_ascii=False, indent=1, default=float)
for p, rows in sweep.items():
    print(f"--- {p} mTorr  Te={rows[0]['Te']:.2f} eV")
    for x in rows: print(f"  P={x['P']:5d} W  n0={x['n0']:.2e}  Rp={x['Rp']:.3f}  eta={x['eta']:.2f}  I={x['I']:.1f} A")
