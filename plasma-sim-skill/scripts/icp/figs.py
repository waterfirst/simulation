import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys as _s, pathlib as _p; _s.path.insert(0, str(_p.Path(__file__).resolve().parents[1])); import _plotfont  # noqa
from matplotlib.colors import LogNorm
from matplotlib.patches import Rectangle
from icp_source import Geometry, operate
S = json.load(open("study.json"))

# --- Fig 1: geometry + fields at 10 mTorr / 500 W ---
g = Geometry(); r = operate(g, 10, 500)
fig, ax = plt.subplots(1, 3, figsize=(17, 5.4))
ext = [0, g.box_r * 100, 0, g.box_top * 100]
def deco(a):
    a.add_patch(Rectangle((0, g.H * 100), g.R * 100, g.t_win * 100, fc="none", ec="c", lw=1.4))
    a.add_patch(Rectangle((g.R * 100, 0), 0.6, (g.H + g.t_win) * 100, fc="0.5", ec="0.3"))
    for rc in g.coil_r:
        zc = (g.H + g.t_win + g.gap_coil + g.coil_w / 2) * 100
        a.add_patch(Rectangle((rc * 100 - 0.3, zc - 0.3), 0.6, 0.6, fc="orange", ec="k"))
    a.set_xlabel("r (cm)"); a.set_ylabel("z (cm)"); a.set_xlim(0, g.box_r * 100); a.set_ylim(0, g.box_top * 100)
im0 = ax[0].imshow((r["ne"] / 1e6).T, origin="lower", extent=ext, aspect="auto", cmap="magma")
deco(ax[0]); ax[0].set_title("전자밀도 (cm⁻³)  — 자기일관 해"); fig.colorbar(im0, ax=ax[0])
im1 = ax[1].imshow(np.abs(r["E"]).T, origin="lower", extent=ext, aspect="auto", cmap="viridis")
deco(ax[1]); ax[1].set_title("유도 전기장 |E_φ| (V/m)"); fig.colorbar(im1, ax=ax[1])
pd = np.where(r["pden"] > 0, r["pden"], np.nan)
im2 = ax[2].imshow(pd.T, origin="lower", extent=ext, aspect="auto", cmap="inferno",
                   norm=LogNorm(vmin=np.nanmax(pd) * 1e-3, vmax=np.nanmax(pd)))
deco(ax[2]); ax[2].set_title(f"흡수 전력밀도 (W/m³)  표피깊이 {r['skin']*100:.1f} cm"); fig.colorbar(im2, ax=ax[2])
fig.suptitle(f"ICP 소스 · Ar 10 mTorr · RF 500 W · 13.56 MHz  →  n₀={r['n0']/1e6:.2e} cm⁻³, Tₑ={r['Te']:.2f} eV, "
             f"Rₚ={r['Rp']:.2f} Ω, 효율 {r['eta']*100:.0f}%, 코일 {r['I']:.1f} A", fontsize=12)
fig.tight_layout(); fig.savefig("fig1_fields.png", dpi=130)

# --- Fig 2: operating curves ---
fig, ax = plt.subplots(1, 3, figsize=(17, 4.8))
for p, rows in S["sweep"].items():
    P = [x["P"] for x in rows]
    ax[0].loglog(P, [max(x["n0"], 1e12) / 1e6 for x in rows], "o-", label=f"{p} mTorr (Tₑ={rows[0]['Te']:.2f} eV)")
    ax[1].semilogx(P, [x["eta"] * 100 for x in rows], "o-", label=f"{p} mTorr")
    ax[2].semilogx(P, [x["I"] for x in rows], "o-", label=f"{p} mTorr")
ax[0].set_title("전자밀도 vs RF 전력 — 유지 최소 전력(H모드 문턱)"); ax[0].set_ylabel("n₀ (cm⁻³)")
ax[1].set_title("전력 전달효율 Rₚ/(Rₚ+R_coil)"); ax[1].set_ylabel("%")
ax[2].set_title("필요 코일 전류 (피크)"); ax[2].set_ylabel("A")
for a in ax: a.set_xlabel("RF 전력 (W)"); a.grid(alpha=.3, which="both"); a.legend(fontsize=9)
ax[0].set_ylim(1e8, 2e12)
fig.tight_layout(); fig.savefig("fig2_curves.png", dpi=130)

# --- Fig 3: coil layout comparison ---
fig, ax = plt.subplots(1, 2, figsize=(14, 4.8), gridspec_kw=dict(width_ratios=[1.6, 1]))
names, etas, outer = [], [], []
for name, d in S["designs"].items():
    rr, pr = np.array(d["prof_r"]), np.array(d["prof"])
    ax[0].plot(rr * 100, pr, lw=2, label=f"{name}  코일 {', '.join(f'{c*100:g}' for c in d['coil'])} cm")
    w = pr * rr; frac = w[rr > 0.075].sum() / w.sum()
    names.append(name); etas.append(d["eta"] * 100); outer.append(frac * 100)
ax[0].set_title("창 아래 1 cm 흡수전력 반경 분포 (정규화)"); ax[0].set_xlabel("r (cm)"); ax[0].legend(fontsize=9); ax[0].grid(alpha=.3)
x = np.arange(len(names)); ax[1].bar(x - 0.2, etas, 0.4, label="전력 전달효율 %"); ax[1].bar(x + 0.2, outer, 0.4, label="r>7.5cm 흡수 비율 %")
ax[1].set_xticks(x); ax[1].set_xticklabels([n.split(" ")[0] + "\n" + n.split(" ", 1)[1] for n in names], fontsize=9)
for i, (e, o) in enumerate(zip(etas, outer)):
    ax[1].text(i - 0.2, e + 1, f"{e:.0f}", ha="center"); ax[1].text(i + 0.2, o + 1, f"{o:.0f}", ha="center")
ax[1].legend(fontsize=9); ax[1].set_title("코일 배치 비교 (10 mTorr, 500 W)")
fig.tight_layout(); fig.savefig("fig3_coils.png", dpi=130)
print("ok")
