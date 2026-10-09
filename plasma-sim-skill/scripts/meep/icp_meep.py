"""ICP RF field penetration into plasma with Meep (open-source FDTD), cylindrical m=0.

Same layout as the in-house ICP model: chamber R=15 cm, H=10 cm, quartz window 2 cm,
4-turn planar coil above it, grounded walls. Plasma = uniform Drude medium (cold plasma,
the same approximation HFSS uses). One run per electron density.

usage: python icp_meep.py <ne_cm3> <out.npz>
"""
import sys, numpy as np
import meep as mp

ne_cm3 = float(sys.argv[1]); OUT = sys.argv[2]
C = 2.99792458e8; A = 0.01                      # Meep length unit a = 1 cm
f_rf = 13.56e6 * A / C                          # 13.56 MHz in Meep units
nu = 3.2e7                                      # collision frequency [1/s] (10 mTorr Ar, from the ICP model)
fp = 8.98e3 * np.sqrt(ne_cm3) * A / C           # plasma frequency in Meep units
gamma = nu / (2 * np.pi) * A / C

R, H, TW, GAP, CW = 15.0, 10.0, 2.0, 0.8, 0.6
SR, SZ = 22.0, 20.0
zc = lambda zp: zp - SZ / 2                     # physical z (0 = chuck) -> Meep z (centred cell)
res = int(sys.argv[3]) if len(sys.argv) > 3 else 5

plasma = mp.Medium(epsilon=1.0, E_susceptibilities=[mp.DrudeSusceptibility(frequency=fp, gamma=gamma, sigma=1.0)])
geom = [
    mp.Block(center=mp.Vector3(R / 2, 0, zc(H / 2)), size=mp.Vector3(R, mp.inf, H), material=plasma),
    mp.Block(center=mp.Vector3(R / 2, 0, zc(H + TW / 2)), size=mp.Vector3(R, mp.inf, TW), material=mp.Medium(epsilon=3.8)),
    mp.Block(center=mp.Vector3(R + 0.3, 0, zc((H + TW) / 2)), size=mp.Vector3(0.6, mp.inf, H + TW), material=mp.metal),
]
z_coil = H + TW + GAP + CW / 2
src = [mp.Source(mp.ContinuousSource(frequency=f_rf, width=0.5 / f_rf), component=mp.Ep,
                 center=mp.Vector3(rc, 0, zc(z_coil)), size=mp.Vector3(CW, 0, CW))
       for rc in (3.0, 6.0, 9.0, 12.0)]

sim = mp.Simulation(cell_size=mp.Vector3(SR, 0, SZ), dimensions=mp.CYLINDRICAL, m=0, resolution=res,
                    geometry=geom, sources=src, boundary_layers=[], Courant=0.5)
T = 1 / f_rf
sim.run(until=3 * T)                            # ramp + settle
frames, NF = [], 24
for k in range(NF):                             # one RF period, 24 phases
    sim.run(until=T / NF)
    frames.append(sim.get_array(center=mp.Vector3(SR / 2, 0, 0), size=mp.Vector3(SR, 0, SZ), component=mp.Ep))
F = np.array(frames)                            # (NF, Nr, Nz)
amp = np.abs(F).max(0)
np.savez_compressed(OUT, frames=F, amp=amp, ne=ne_cm3, fp=fp, f_rf=f_rf, nu=nu, res=res, SR=SR, SZ=SZ,
                    R=R, H=H, TW=TW, z_coil=z_coil)
print("DONE", ne_cm3, F.shape, float(amp.max()))
