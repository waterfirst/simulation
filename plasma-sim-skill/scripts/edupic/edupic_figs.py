import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys as _s, pathlib as _p; _s.path.insert(0, str(_p.Path(__file__).resolve().parents[1])); import _plotfont  # noqa
import os; os.makedirs("figs", exist_ok=True)
L, NG, T = 0.025, 400, 1 / 13.56e6
x = np.linspace(0, L, NG); dx = x[1] - x[0]
xt = lambda n: np.loadtxt(n)                                     # (space 400, time 200)
ne_xt, ni_xt = xt("ne_xt.dat"), xt("ni_xt.dat")
NT = ne_xt.shape[1]; tt = np.arange(NT) / NT

def brinkmann(ne, ni, side=0):
    """Sheath edge s: int_0^s ne dx = int_s^{L/2} (ni - ne) dx (Brinkmann 2007), measured from one electrode."""
    h = NG // 2
    a, b = (ne[:h], ni[:h]) if side == 0 else (ne[::-1][:h], ni[::-1][:h])
    lhs = np.cumsum(a) * dx; rhs = (np.cumsum((b - a)[::-1]) * dx)[::-1]
    return x[np.argmin(np.abs(lhs - rhs))]
s_pow = np.array([brinkmann(ne_xt[:, k], ni_xt[:, k], 0) for k in range(NT)])
s_gnd = np.array([brinkmann(ne_xt[:, k], ni_xt[:, k], 1) for k in range(NT)])

d = np.loadtxt("density.dat"); c = np.loadtxt("conv.dat"); ee = np.loadtxt("eepf.dat"); fi = np.loadtxt("ifed.dat")
meanee = xt("meanee_xt.dat"); meanei = xt("meanei_xt.dat")
ctr = slice(NG // 2 - 10, NG // 2 + 10)
eb = np.average(meanee[ctr], weights=ne_xt[ctr] + 1e-30)
mi_edge = max(meanei[:8].max(), meanei[-8:].max())
nc = d[NG // 2, 1]
res = dict(n_center_m3=nc, smax_pow_mm=s_pow.max() * 1e3, smax_gnd_mm=s_gnd.max() * 1e3,
           Ee_bulk_eV=float(eb), Ei_local_max_eV=float(mi_edge), IFED_mean_eV=float((fi[:, 0] * fi[:, 1]).sum() / fi[:, 1].sum()))
json.dump(res, open("figs/key.json", "w"), indent=1); print(res)

# Fig 1: convergence + time-averaged densities
fig, ax = plt.subplots(1, 2, figsize=(13, 4.4))
ax[0].plot(c[:, 0], c[:, 1], label="전자"); ax[0].plot(c[:, 0], c[:, 2], label="이온"); ax[0].axvline(1501, ls="--", c="k", lw=1)
ax[0].text(1520, c[:, 1].max() * 0.5, "측정 200주기", fontsize=9); ax[0].set_xlabel("RF 주기"); ax[0].set_ylabel("초입자 수"); ax[0].legend(); ax[0].grid(alpha=.3)
ax[0].set_title("수렴 이력 (논문: ≈1500 주기에서 수렴)")
ax[1].plot(d[:, 0] * 1e3, d[:, 1], label="전자 nₑ"); ax[1].plot(d[:, 0] * 1e3, d[:, 2], label="이온 nᵢ")
ax[1].axvspan(0, s_pow.max() * 1e3, color="0.85"); ax[1].axvspan((L - s_gnd.max()) * 1e3, L * 1e3, color="0.85")
ax[1].set_xlabel("전극으로부터 거리 (mm)  [0 = 구동 전극]"); ax[1].set_ylabel("밀도 (m⁻³)"); ax[1].legend(); ax[1].grid(alpha=.3)
ax[1].set_title(f"시간평균 밀도 · 중앙 nₑ = {nc:.2e} m⁻³ · 회색 = 최대 시스 폭")
fig.tight_layout(); fig.savefig("figs/p1_density.png", dpi=125)

# Fig 2: EEPF + IFED
fig, ax = plt.subplots(1, 2, figsize=(13, 4.4))
m = ee[:, 1] > 0
ax[0].semilogy(ee[m, 0], ee[m, 1]); ax[0].set_xlim(0, 30); ax[0].set_xlabel("전자 에너지 (eV)"); ax[0].set_ylabel("EEPF (eV⁻³ᐟ²)")
ax[0].set_title("방전 중앙 EEPF — 저에너지 차가운 전자군 + 고에너지 꼬리 (두 온도, 비맥스웰)")
from matplotlib.ticker import FuncFormatter
ax[0].yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"1e{int(round(np.log10(v)))}" if v > 0 else "")); ax[0].grid(alpha=.3, which="both")
ax[1].plot(fi[:, 0], fi[:, 1], label="구동 전극"); ax[1].plot(fi[:, 0], fi[:, 2], label="접지 전극", alpha=.7)
ax[1].set_xlabel("이온 에너지 (eV)"); ax[1].set_ylabel("IFEDF (정규화)"); ax[1].legend(); ax[1].grid(alpha=.3)
ax[1].set_title(f"이온 플럭스 에너지 분포 — 전하교환 봉우리열 · 평균 {res['IFED_mean_eV']:.1f} eV")
fig.tight_layout(); fig.savefig("figs/p2_eepf_ifed.png", dpi=125)

# Fig 3: spatio-temporal maps with sheath edges
maps = [("ne_xt.dat", "전자 밀도 (m⁻³)", "viridis"), ("pot_xt.dat", "전위 (V)", "RdBu_r"),
        ("powere_xt.dat", "전자 흡수 전력밀도 (W/m³)", "RdBu_r"), ("ioniz_xt.dat", "이온화율 (m⁻³s⁻¹)", "inferno")]
fig, ax = plt.subplots(1, 4, figsize=(20, 4.6))
for a, (fn, lab, cm) in zip(ax, maps):
    A = xt(fn)
    kw = dict(origin="lower", aspect="auto", extent=[0, 1, 0, L * 1e3], cmap=cm)
    if cm == "RdBu_r":
        v = np.percentile(np.abs(A), 99.5); kw.update(vmin=-v, vmax=v)
    im = a.imshow(A, **kw); fig.colorbar(im, ax=a)
    a.plot(tt, s_pow * 1e3, c="0.6", lw=1.3); a.plot(tt, (L - s_gnd) * 1e3, c="0.6", lw=1.3)
    a.set_title(lab); a.set_xlabel("t / T_RF"); a.set_ylabel("x (mm)")
fig.suptitle("한 RF 주기 시공간 분포 · 회색선 = 시스 경계 (Brinkmann 기준) · Ar 10 Pa, 13.56 MHz, 250 V, 2.5 cm", fontsize=12)
fig.tight_layout(); fig.savefig("figs/p3_xt.png", dpi=110)
print("ok")
