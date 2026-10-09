"""Self-consistent ICP source model: 2D axisymmetric EM (A_phi) + argon global model.

Geometry (r-z, metres):  cylindrical chamber radius R, height H, wafer/chuck at z=0,
quartz window above the chamber, planar spiral coil (concentric loops) above the window,
everything inside a grounded shield box.

EM : (1/r) d/dr(r dA/dr) - A/r^2 + d2A/dz2 + k0^2 eps A = -mu0 J_coil      (e^{jwt})
     eps_plasma = 1 - wp^2 / (w (w - j nu))       ->  absorbed power from Re(sigma)|E|^2
Global (Lieberman & Lichtenberg, 2nd ed., ch. 10): particle balance fixes Te,
     power balance  P_abs = e n0 uB A_eff E_T  fixes n0.
Coupling: P_abs = P_rf * Rp / (Rp + Rcoil);  Rp from the EM solution depends on n0 -> iterate.

The density SHAPE is the lowest diffusion mode J0(2.405 r/R) sin(pi z/H); only its
amplitude is solved. That is the model's main simplification (no transport solve).
"""
import numpy as np
from scipy.sparse import lil_matrix, csr_matrix
from scipy.sparse.linalg import spsolve
from scipy.special import j0
from scipy.optimize import brentq

E, ME, MAR, EPS0, MU0, KB = 1.602176634e-19, 9.1093837e-31, 6.6335e-26, 8.8541878e-12, 4e-7 * np.pi, 1.380649e-23


class Geometry:
    def __init__(self, R=0.15, H=0.10, t_win=0.02, gap_coil=0.008, coil_r=(0.03, 0.06, 0.09, 0.12),
                 coil_w=0.006, eps_win=3.8, box_r=0.22, box_top=0.20, dr=0.002, dz=0.002,
                 kind="planar", coil_z=(0.2, 0.4, 0.6, 0.8)):
        self.__dict__.update(locals()); del self.__dict__["self"]
        self.r = np.arange(0, box_r + dr / 2, dr); self.z = np.arange(0, box_top + dz / 2, dz)
        self.Nr, self.Nz = len(self.r), len(self.z)
        RR, ZZ = np.meshgrid(self.r, self.z, indexing="ij")
        self.RR, self.ZZ = RR, ZZ
        self.plasma = (RR < R) & (ZZ > 0) & (ZZ < H)
        wall = 0.006
        shield = (ZZ <= 0) | (RR >= box_r - 1e-9) | (ZZ >= box_top - 1e-9)
        self.coil = np.zeros_like(RR, dtype=bool); self.coil_id = -np.ones_like(RR, dtype=int)
        if kind == "planar":
            # quartz window on top, metal side wall, flat spiral above the window
            self.window = (RR < R) & (ZZ >= H) & (ZZ <= H + t_win)
            self.metal = ((RR >= R) & (RR <= R + wall) & (ZZ <= H + t_win)) | shield
            loops = [(rc, H + t_win + gap_coil + coil_w / 2) for rc in coil_r]
        else:
            # quartz tube as the side wall, metal lid on top, helix wound around the tube
            self.window = (RR >= R) & (RR <= R + t_win) & (ZZ > 0) & (ZZ < H)
            self.metal = ((RR <= R + t_win) & (ZZ >= H) & (ZZ <= H + wall)) | shield
            rc = R + t_win + gap_coil + coil_w / 2
            loops = [(rc, H * f) for f in coil_z]
        for k, (rc, zc) in enumerate(loops):
            m = (np.abs(RR - rc) <= coil_w / 2) & (np.abs(ZZ - zc) <= coil_w / 2)
            self.coil |= m; self.coil_id[m] = k
        self.n_loops = len(loops)
        self.shape = j0(2.405 * RR / R) * np.sin(np.pi * ZZ / H) * self.plasma
        self.vol = np.pi * R ** 2 * H


def ng_from(p_mtorr, T=300.0):
    return p_mtorr * 0.133322 / (KB * T)


# ---- argon rate coefficients, Lieberman Table 3.3 (Te in eV) ----
def Kiz(Te): return 2.34e-14 * Te ** 0.59 * np.exp(-17.44 / Te)
def Kex(Te): return 2.48e-14 * Te ** 0.33 * np.exp(-12.78 / Te)
def Kel(Te): return 2.336e-14 * Te ** 1.609 * np.exp(0.0618 * np.log(Te) ** 2 - 0.1171 * np.log(Te) ** 3)
def uB(Te): return np.sqrt(E * Te / MAR)


def global_Te(g, ng):
    lam_i = 1 / (ng * 1e-18)
    hL = 0.86 / np.sqrt(3 + g.H / (2 * lam_i)); hR = 0.80 / np.sqrt(4 + g.R / lam_i)
    Aeff = 2 * np.pi * g.R ** 2 * hL + 2 * np.pi * g.R * g.H * hR
    f = lambda Te: Kiz(Te) * ng * g.vol - uB(Te) * Aeff
    return brentq(f, 0.8, 20.0), Aeff


def E_T(Te):
    Ec = 15.76 + Kex(Te) / Kiz(Te) * 12.14 + Kel(Te) / Kiz(Te) * 3 * ME / MAR * Te
    return Ec + 2 * Te + 5.2 * Te


def solve_em(g, n0, nu, f=13.56e6, I=1.0):
    """Return A_phi (complex), E_phi, absorbed power density, Rp for coil current I (A peak)."""
    w = 2 * np.pi * f; k0 = w / 299792458.0
    ne = n0 * g.shape
    wp2 = ne * E ** 2 / (EPS0 * ME)
    eps = np.ones((g.Nr, g.Nz), complex)
    eps[g.plasma] = 1 - wp2[g.plasma] / (w * (w - 1j * nu))
    eps[g.window] = g.eps_win
    J = np.zeros((g.Nr, g.Nz)); acoil = g.coil_w ** 2
    J[g.coil] = I / acoil * (g.dr * g.dz) / (g.dr * g.dz)   # uniform current density in each loop
    # each loop must carry exactly I: renormalise per loop on the grid
    for k in range(g.n_loops):
        m = g.coil_id == k; J[m] = I / (m.sum() * g.dr * g.dz)
    Nr, Nz, dr, dz = g.Nr, g.Nz, g.dr, g.dz
    idx = lambda i, j: i * Nz + j
    A = lil_matrix((Nr * Nz, Nr * Nz), dtype=complex); b = np.zeros(Nr * Nz, complex)
    for i in range(Nr):
        r = g.r[i]
        for j in range(Nz):
            p = idx(i, j)
            if i == 0 or i == Nr - 1 or j == 0 or j == Nz - 1 or g.metal[i, j]:   # outer cells are always the shield
                A[p, p] = 1.0; continue
            rp, rm = r + dr / 2, r - dr / 2
            cE, cW = rp / (r * dr * dr), rm / (r * dr * dr)
            cN = cS = 1 / (dz * dz)
            A[p, idx(i + 1, j)] = cE; A[p, idx(i - 1, j)] = cW
            A[p, idx(i, j + 1)] = cN; A[p, idx(i, j - 1)] = cS
            A[p, p] = -(cE + cW + cN + cS) - 1 / r ** 2 + k0 ** 2 * eps[i, j]
            b[p] = -MU0 * J[i, j]
    Aphi = spsolve(csr_matrix(A), b).reshape(Nr, Nz)
    Ephi = -1j * w * Aphi
    sigma = np.zeros((Nr, Nz), complex)
    sigma[g.plasma] = EPS0 * wp2[g.plasma] / (nu + 1j * w)
    pden = 0.5 * np.real(sigma) * np.abs(Ephi) ** 2          # W/m^3
    P = np.sum(pden * 2 * np.pi * g.RR * dr * dz)
    Rp = 2 * P / I ** 2
    return dict(A=Aphi, E=Ephi, pden=pden, P=P, Rp=Rp, ne=ne)


def operate(g, p_mtorr, P_rf, R_coil=0.6, f=13.56e6, n_guess=1e16, it=40, verbose=False):
    ng = ng_from(p_mtorr)
    Te, Aeff = global_Te(g, ng)
    nu = ng * (Kel(Te) + Kex(Te) + Kiz(Te))                  # electron-neutral momentum-ish collision freq
    n0 = n_guess
    for k in range(it):
        em = solve_em(g, n0, nu, f)
        eta = em["Rp"] / (em["Rp"] + R_coil)
        P_abs = P_rf * eta
        n_new = P_abs / (E * uB(Te) * Aeff * E_T(Te))
        if verbose: print(f"  it{k:2d} n0={n0:.3e} Rp={em['Rp']:.3f} eta={eta:.3f} -> n={n_new:.3e}")
        if abs(n_new - n0) / n0 < 2e-3: n0 = n_new; break
        n0 = np.exp(0.5 * np.log(n0) + 0.5 * np.log(max(n_new, 1e12)))   # damped in log space
    em = solve_em(g, n0, nu, f)
    I_coil = np.sqrt(2 * P_rf / (em["Rp"] + R_coil))
    scale = I_coil ** 2                                        # fields were solved for I = 1 A
    return dict(p=p_mtorr, P_rf=P_rf, Te=Te, nu=nu, n0=n0, Rp=em["Rp"], eta=em["Rp"] / (em["Rp"] + R_coil),
                I=I_coil, pden=em["pden"] * scale, E=em["E"] * I_coil, ne=em["ne"], iters=k + 1,
                skin=cold_skin(n0, nu, f))


def cold_skin(n0, nu, f=13.56e6):
    """Cold-plasma skin depth 1/Im(k) - valid for any nu/w (the collisional formula is not, at nu < w)."""
    w = 2 * np.pi * f; wp2 = n0 * E ** 2 / (EPS0 * ME)
    k = w / 299792458.0 * np.sqrt(1 - wp2 / (w * (w - 1j * nu)) + 0j)
    return 1 / abs(k.imag)


def inductance(g, A, I=1.0):
    """Coil inductance from time-averaged magnetic energy: 1/4 L I^2 = 1/4 int |B|^2/mu0 dV."""
    dA_dz = np.gradient(A, g.dz, axis=1)
    rA = g.RR * A
    Bz = np.gradient(rA, g.dr, axis=0) / np.where(g.RR > 0, g.RR, np.inf)
    Br = -dA_dz
    w = np.sum((np.abs(Br) ** 2 + np.abs(Bz) ** 2) / MU0 * 2 * np.pi * g.RR * g.dr * g.dz)
    return w / I ** 2


def l_match(R, X, f=13.56e6, R0=50.0):
    """L-network (shunt C at generator, series C at the coil) matching R+jX to R0 (needs R < R0)."""
    w = 2 * np.pi * f
    Q = np.sqrt(R0 / R - 1)
    Xs = Q * R - X                      # series element must make total series reactance +Q R ... (negative -> capacitor)
    Xp = R0 / Q
    Cs = 1 / (w * -Xs) if Xs < 0 else np.nan
    Cp = 1 / (w * Xp)
    return dict(Q=Q, Cs_pF=Cs * 1e12, Cp_pF=Cp * 1e12)
