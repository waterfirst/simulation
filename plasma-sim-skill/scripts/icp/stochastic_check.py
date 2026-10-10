"""How much does collisionless (stochastic) heating change the ICP answer?

Runs the self-consistent model twice per pressure -- ohmic only, and with
nu_eff = nu_m + v_te/(4*delta) folded into the same iteration -- and prints the gap.
The ohmic-only Drude model is weakest where nu_m < omega, i.e. at low pressure,
so this is the quickest way to see where its numbers stop being trustworthy.

usage: python stochastic_check.py [p_mTorr ...]
"""
import sys
import numpy as np
from icp_source import Geometry, operate

PS = [float(x) for x in sys.argv[1:]] or [1.0, 3.0, 5.0, 10.0, 30.0, 100.0]
P_RF, W = 500.0, 2 * np.pi * 13.56e6
g = Geometry()
print(f"13.56 MHz, {P_RF:.0f} W, R={g.R*100:.0f} cm H={g.H*100:.0f} cm, omega={W:.2e} rad/s\n")
print(f"{'p[mTorr]':>8} {'nu_m':>9} {'nu_stoch':>9} {'nu_m/w':>7} "
      f"{'Rp ohmic':>9} {'Rp +stoc':>9} {'dRp':>7} {'eta ohmic':>10} {'eta +stoc':>10} {'dn0':>6}")
for p in PS:
    a = operate(g, p, P_RF)
    b = operate(g, p, P_RF, stochastic=True)
    print(f"{p:8.1f} {a['nu_m']:9.2e} {b['nu_stoch']:9.2e} {a['nu_m']/W:7.2f} "
          f"{a['Rp']:9.3f} {b['Rp']:9.3f} {(b['Rp']/a['Rp']-1)*100:+6.0f}% "
          f"{a['eta']*100:9.1f}% {b['eta']*100:9.1f}% {(b['n0']/a['n0']-1)*100:+5.0f}%")
print("\nnu_m/w < 1 is the collisionless side: there the ohmic-only model underestimates Rp and the\n"
      "coupling efficiency. The correction shrinks as pressure rises and nu_m overtakes omega.")
