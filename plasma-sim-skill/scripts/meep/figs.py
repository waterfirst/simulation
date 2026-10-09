import numpy as np, matplotlib, subprocess
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys as _s, pathlib as _p; _s.path.insert(0, str(_p.Path(__file__).resolve().parents[1])); import _plotfont  # noqa
from matplotlib.colors import LogNorm
from matplotlib.patches import Rectangle
C = 2.99792458e8
cases = ["1e9", "1e10", "1e11", "1e12"]
D = {c: dict(np.load(f"ne_{c}.npz")) for c in cases + ["2.14e11"]}
for c, d in D.items():
    F = d["frames"]; N = F.shape[0]
    d["amp"] = np.abs((F * np.exp(-2j * np.pi * np.arange(N) / N)[:, None, None]).sum(0)) * 2 / N

def skin(ne_cm3, nu=3.2e7, f=13.56e6):
    w = 2 * np.pi * f; wp2 = (2 * np.pi * 8.98e3) ** 2 * ne_cm3
    eps = 1 - wp2 / (w * (w - 1j * nu))
    k = w / C * np.sqrt(eps + 0j)
    return 1 / abs(k.imag) * 100                             # cm

def deco(a, d):
    R, H, TW, zc = float(d["R"]), float(d["H"]), float(d["TW"]), float(d["z_coil"])
    a.add_patch(Rectangle((0, H), R, TW, fc="none", ec="c", lw=1.3))
    a.add_patch(Rectangle((R, 0), 0.6, H + TW, fc="0.55", ec="0.3"))
    for rc in (3, 6, 9, 12): a.add_patch(Rectangle((rc - .3, zc - .3), .6, .6, fc="orange", ec="k"))
    a.set_xlim(0, 22); a.set_ylim(0, 20); a.set_xlabel("r (cm)"); a.set_ylabel("z (cm)")

# Fig A: amplitude maps
fig, ax = plt.subplots(1, 4, figsize=(20, 5))
for a, c in zip(ax, cases):
    d = D[c]; amp = d["amp"] / d["amp"].max()
    im = a.imshow(np.maximum(amp, 1e-4), origin="lower", extent=[0, 22, 0, 20], cmap="viridis", norm=LogNorm(1e-3, 1), aspect="auto")
    deco(a, d); a.set_title(f"nₑ = {float(c):.0e} cm⁻³   (이론 표피깊이 {skin(float(c)):.1f} cm)", fontsize=11)
fig.colorbar(im, ax=ax, shrink=.85, label="|E_φ| (정규화, 로그)")
fig.suptitle("Meep FDTD · ICP 코일의 13.56 MHz 유도 전기장이 플라즈마 속으로 들어가는 깊이 — 밀도가 높을수록 창 아래 얇은 층에 갇힌다", fontsize=13)
fig.savefig("meep_fig1_maps.png", dpi=120, bbox_inches="tight")

# Fig B: depth profile at r = 8 cm, below the window
fig, a = plt.subplots(figsize=(8.5, 5.2)); rows = []
for c in cases + ["2.14e11"]:
    d = D[c]; res = int(d["res"]); amp = d["amp"]
    ir = int(8 * res); iz_win = int(float(d["H"]) * res)
    prof = amp[:iz_win, ir][::-1]; depth = np.arange(len(prof)) / res
    prof = prof / prof[0]
    m = (depth > 0.2) & (depth < 2.5) & (prof > 1e-5)
    L = -1 / np.polyfit(depth[m], np.log(prof[m]), 1)[0]
    rows.append((float(c), L, skin(float(c))))
    if c != "2.14e11":
        a.semilogy(depth, prof, lw=2, label=f"{float(c):.0e} cm⁻³ : Meep {L:.2f} cm / 이론 {skin(float(c)):.2f} cm" + ("  (격자 2.8칸, 해상도 부족)" if c == "1e12" else ""))
a.set_xlabel("창 아래 깊이 (cm)"); a.set_ylabel("|E_φ| / |E_φ(창)|"); a.set_ylim(1e-4, 1.5); a.grid(alpha=.3, which="both")
a.set_title("r = 8 cm 깊이별 감쇠 (13.56 MHz 성분) — Meep vs 콜드플라즈마 이론\n저밀도 두 곡선은 플라즈마가 아니라 코일 근거리장의 기하학적 감쇠"); a.legend(fontsize=9)
fig.tight_layout(); fig.savefig("meep_fig2_depth.png", dpi=130)
print("single-exponential fit 0.2-2.5 cm (window-sensitive; judge by the pointwise plot):  ne, Meep, theory")
for r in rows: print(f"  {r[0]:.2e}  {r[1]:.2f}  {r[2]:.2f}")

# Animation: signed E_phi over one RF period, 4 densities
fr = {c: D[c]["frames"] for c in cases}
lim = {c: np.abs(fr[c]).max() * 0.35 for c in cases}
import os; os.makedirs("anim", exist_ok=True)
for k in range(24):
    fig, ax = plt.subplots(1, 4, figsize=(20, 5))
    for a, c in zip(ax, cases):
        a.imshow(fr[c][k], origin="lower", extent=[0, 22, 0, 20], cmap="RdBu_r", vmin=-lim[c], vmax=lim[c], aspect="auto")
        deco(a, D[c]); a.set_title(f"nₑ = {float(c):.0e} cm⁻³", fontsize=12)
    fig.suptitle(f"E_φ(t) 한 RF 주기 (13.56 MHz, 위상 {k*15:3d}°) — Meep FDTD", fontsize=13)
    fig.savefig(f"anim/f{k:02d}.png", dpi=80, bbox_inches="tight"); plt.close(fig)
subprocess.run("ffmpeg -y -v error -stream_loop 5 -framerate 16 -i anim/f%02d.png -vf 'scale=trunc(iw/2)*2:trunc(ih/2)*2' "
               "-c:v libx264 -pix_fmt yuv420p -crf 20 meep_anim.mp4", shell=True, check=True)
print("ok")
