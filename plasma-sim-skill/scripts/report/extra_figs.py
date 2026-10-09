import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys as _s, pathlib as _p; _s.path.insert(0, str(_p.Path(__file__).resolve().parents[1])); import _plotfont  # noqa
C = 2.99792458e8
import os
from pathlib import Path
B = Path(os.environ.get("PLASMA_SIM_DIR", Path.home() / "plasma_sim"))
M = str(B / "meep") + "/"
def skin(ne, nu=3.2e7, f=13.56e6):
    w = 2*np.pi*f; wp2 = (2*np.pi*8.98e3)**2*ne; k = w/C*np.sqrt(1-wp2/(w*(w-1j*nu))+0j); return 1/abs(k.imag)*100
def prof(fn):
    d = np.load(fn); F = d["frames"]; res = int(d["res"]); N = F.shape[0]
    A = np.abs((F*np.exp(-2j*np.pi*np.arange(N)/N)[:, None, None]).sum(0))*2/N
    p = A[:10*res, 8*res][::-1]; return np.arange(len(p))/res, p/p[0]
fig, ax = plt.subplots(1, 2, figsize=(13, 4.8))
for a, ne in zip(ax, ("1e11", "1e12")):
    for fn, lab, st in ((f"ne_{ne}.npz", "Meep 해상도 5 px/cm", "o-"), (f"r10_{ne}.npz", "Meep 해상도 10 px/cm", "s-")):
        x, p = prof(M + fn); a.semilogy(x, p, st, ms=3, lw=1.2, label=lab)
    xd = np.linspace(0, 6, 100); d = skin(float(ne))
    a.semilogy(xd, np.exp(-xd/d), "k--", lw=2, label=f"콜드플라즈마 이론 exp(−x/δ), δ={d:.2f} cm")
    a.set_ylim(1e-3, 1.3); a.set_xlim(0, 6); a.grid(alpha=.3, which="both"); a.legend(fontsize=9)
    a.set_title(f"nₑ = {float(ne):.0e} cm⁻³ · r = 8 cm · 13.56 MHz 성분"); a.set_xlabel("창 아래 깊이 (cm)"); a.set_ylabel("|E_φ| / |E_φ(창)|")
fig.tight_layout(); fig.savefig("val_meep_pointwise.png", dpi=125)

c = np.loadtxt(B / "ccp_run" / "conv.dat")
fig, a = plt.subplots(figsize=(8, 4))
a.plot(c[:, 0], c[:, 1], label="전자 수 (초입자)"); a.plot(c[:, 0], c[:, 2], label="이온 수 (초입자)")
a.set_xlabel("RF 주기"); a.set_ylabel("초입자 수"); a.grid(alpha=.3); a.legend()
a.set_title(f"eduPIC 수렴 이력 (예비, {int(c[-1,0])} 주기까지) — 아직 정상상태 아님")
fig.tight_layout(); fig.savefig("edupic_conv.png", dpi=125)
print("ok", int(c[-1, 0]))
