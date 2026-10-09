import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys as _s, pathlib as _p; _s.path.insert(0, str(_p.Path(__file__).resolve().parents[1])); import _plotfont  # noqa
from matplotlib.colors import LogNorm
from icp_source import Geometry, operate, solve_em, inductance, l_match, ng_from, global_Te, Kel, Kex, Kiz
f, Rc = 13.56e6, 0.6
w = 2 * np.pi * f
ng = ng_from(10); Te, _ = global_Te(Geometry(), ng); nu = ng * (Kel(Te) + Kex(Te) + Kiz(Te))
res, maps = {}, {}
for kind in ("planar", "helical"):
    g = Geometry(kind=kind)
    # coil alone in a big empty shield box (what you get if you simulate only the coil)
    gf = Geometry(kind=kind); shield = (gf.ZZ <= 0) | (gf.RR >= gf.box_r - 1e-9) | (gf.ZZ >= gf.box_top - 1e-9)
    gf.metal = shield; gf.window[:] = False; gf.plasma[:] = False; gf.shape[:] = 0
    L_free = inductance(gf, solve_em(gf, 0, nu)["A"])
    vac = solve_em(g, 0, nu); L_vac = inductance(g, vac["A"])
    op = operate(g, 10, 500, R_coil=Rc)
    em = solve_em(g, op["n0"], nu); L_p = inductance(g, em["A"])
    R_tot = em["Rp"] + Rc; X = w * L_p
    m = l_match(R_tot, X)
    zi = np.argmin(np.abs(g.z - ((g.H - 0.01) if kind == "planar" else g.H / 2)))
    inside = g.r < g.R
    pv = np.abs(vac["E"][:, zi])[inside]; pp = np.abs(em["E"][:, zi])[inside]
    res[kind] = dict(L_free_uH=L_free * 1e6, L_vac_uH=L_vac * 1e6, L_plasma_uH=L_p * 1e6, Rp=em["Rp"], eta=op["eta"],
                     n0=op["n0"], I=op["I"], Z=f"{R_tot:.2f} + j{X:.0f} ohm", Cs_pF=m["Cs_pF"], Cp_pF=m["Cp_pF"], Q=m["Q"])
    maps[kind] = dict(g=g, vac=np.abs(vac["E"]), pden=op["pden"], r=g.r[inside] * 100, pv=pv / pv.max(), pp=pp / pp.max(), zi=g.z[zi] * 100)
    print(f"{kind:8} L: 코일단독 {L_free*1e6:.2f} uH | 챔버(빈) {L_vac*1e6:.2f} uH | 플라즈마 {L_p*1e6:.2f} uH  "
          f"Rp={em['Rp']:.2f} eta={op['eta']:.2f} n0={op['n0']/1e6:.2e}cm-3 I={op['I']:.1f}A  Z={R_tot:.2f}+j{X:.0f}  "
          f"Cseries={m['Cs_pF']:.0f}pF Cshunt={m['Cp_pF']:.0f}pF")
json.dump(res, open("study2.json", "w"), ensure_ascii=False, indent=1, default=float)

fig, ax = plt.subplots(2, 3, figsize=(18, 10.5))
for row, kind in enumerate(("planar", "helical")):
    M = maps[kind]; g = M["g"]; ext = [0, g.box_r * 100, 0, g.box_top * 100]
    a = ax[row, 0]; im = a.imshow(M["vac"].T, origin="lower", extent=ext, aspect="auto", cmap="viridis")
    a.set_title(f"{'평면' if kind=='planar' else '헬리컬'} 코일 · 빈 챔버 |E_φ|  (웨비나가 보는 장)")
    a = ax[row, 1]; pd = np.where(M["pden"] > 0, M["pden"], np.nan)
    a.imshow(pd.T, origin="lower", extent=ext, aspect="auto", cmap="inferno", norm=LogNorm(np.nanmax(pd) * 1e-3, np.nanmax(pd)))
    a.set_title(f"플라즈마 켜짐 · 흡수 전력밀도 (10 mTorr, 500 W)")
    for a in ax[row, :2]:
        for mk, col in ((g.window, "c"), (g.metal & (g.RR < g.box_r - 0.003) & (g.ZZ > 0) & (g.ZZ < g.box_top - 0.003), "w"), (g.coil, "orange")):
            a.contour(g.r * 100, g.z * 100, mk.T.astype(float), levels=[0.5], colors=col, linewidths=1.2)
        a.set_xlabel("r (cm)"); a.set_ylabel("z (cm)")
    a = ax[row, 2]
    a.plot(M["r"], M["pv"], lw=2.2, label="빈 챔버 (플라즈마 없음)")
    a.plot(M["r"], M["pp"], lw=2.2, label="플라즈마 켜짐 (2×10¹¹ cm⁻³대)")
    a.set_title(f"z = {M['zi']:.0f} cm 반경 분포 |E_φ| (정규화)"); a.set_xlabel("r (cm)"); a.grid(alpha=.3); a.legend()
fig.suptitle("웨비나 재현 + 확장 — 평면 vs 헬리컬 코일, 빈 챔버 장 vs 플라즈마가 켜진 장", fontsize=14)
fig.tight_layout(); fig.savefig("fig4_webinar_compare.png", dpi=115)
print("fig ok")
