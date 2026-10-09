import json, time, numpy as np
from icp_source import Geometry, operate, solve_em, inductance
rows = []
for d in (0.003, 0.002, 0.0015, 0.001):
    t = time.time(); g = Geometry(dr=d, dz=d); r = operate(g, 10, 500)
    L = inductance(g, solve_em(g, r["n0"], r["nu"])["A"])
    rows.append(dict(dx_mm=d * 1e3, cells=g.Nr * g.Nz, n0=r["n0"], Rp=r["Rp"], eta=r["eta"], I=r["I"], L_uH=L * 1e6, sec=time.time() - t))
    print(f"dx={d*1e3:.1f}mm cells={g.Nr*g.Nz:6d} n0={r['n0']:.4e} Rp={r['Rp']:.4f} eta={r['eta']:.4f} I={r['I']:.3f} L={L*1e6:.4f}uH {time.time()-t:.1f}s")
json.dump(rows, open("conv_test.json", "w"), indent=1)
