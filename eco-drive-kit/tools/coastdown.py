"""관성주행(coast-down) 데이터에서 공기저항계수 Cd·A 와 구름저항 Crr 을 역산한다.

자동차 회사가 실제로 쓰는 방법이다. 평지 직선에서 목표 속도까지 가속한 뒤 동력을 끊고
(차는 중립, 자전거는 페달 정지) 관성으로만 굴러가며 속도가 떨어지는 모양을 보면,
속도에 비례하지 않는 성분(구름저항)과 속도 제곱에 비례하는 성분(공기저항)이 분리된다.

    m dv/dt = -(Crr·m·g + ½·ρ·Cd·A·v²)

입력 CSV: time(초), speed  — phyphox "Location (GPS)" 그대로 쓰면 된다(m/s).
usage: python coastdown.py data/coast1.csv --mass 85 --unit ms [--plot figs/coast.png]
       python coastdown.py --demo        # 합성 데이터로 동작 확인
"""
import argparse, csv, math, sys
import numpy as np
from scipy.optimize import curve_fit

RHO, G = 1.225, 9.81            # 공기밀도 [kg/m3] (20도 1기압), 중력가속도


def v_model(t, v0, crr, k):
    """m dv/dt = -(crr·m·g + k·v²) 의 해석해. k = ½ρ·CdA."""
    a = crr * G                                  # [m/s2]
    if k <= 0 or a <= 0:
        return np.full_like(t, v0)
    w = math.sqrt(a * k)
    r = math.sqrt(k / a)
    ph = math.atan(v0 * r)
    arg = ph - w * np.asarray(t, float)
    arg = np.clip(arg, 1e-9, math.pi / 2 - 1e-9)  # 정지 이후는 0으로 잘린다
    return np.tan(arg) / r


def fit(t, v, mass):
    t = np.asarray(t, float) - t[0]
    v = np.asarray(v, float)
    p, cov = curve_fit(lambda tt, v0, crr, kk: v_model(tt, v0, crr, kk / mass),
                       t, v, p0=[v[0], 0.01, 0.3 * mass], bounds=(
                           [v[0] * 0.5, 1e-4, 1e-4], [v[0] * 1.5, 0.2, 10.0 * mass]), maxfev=40000)
    v0, crr, K = p                               # K = ½ρ·CdA  [kg/m]
    err = np.sqrt(np.diag(cov))
    CdA = 2 * K / RHO
    res = v - v_model(t, v0, crr, K / mass)
    return dict(v0=v0, crr=crr, K=K, CdA=CdA, CdA_err=2 * err[2] / RHO, crr_err=err[1],
                rmse=float(np.sqrt(np.mean(res ** 2))), t=t, v=v,
                fit=v_model(t, v0, crr, K / mass))


def demo(n=60, mass=85.0, CdA=0.45, crr=0.006, v0=11.0, noise=0.12, seed=0):
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 40, n)
    v = v_model(t, v0, crr, RHO * CdA / 2 / mass) + rng.normal(0, noise, n)
    return t, np.maximum(v, 0), dict(CdA=CdA, crr=crr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?"); ap.add_argument("--mass", type=float, default=85.0,
                                                       help="차량+탑승자 총질량 [kg]")
    ap.add_argument("--unit", choices=["ms", "kmh"], default="ms")
    ap.add_argument("--vmin", type=float, default=1.5, help="이 속도 미만은 버린다 [m/s]")
    ap.add_argument("--plot"); ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()

    truth = None
    if a.demo:
        t, v, truth = demo(mass=a.mass)
        print("[데모] 합성 데이터로 역산한다. 정답 CdA=%.3f, Crr=%.4f" % (truth["CdA"], truth["crr"]))
    else:
        if not a.csv:
            sys.exit("CSV 경로를 주거나 --demo 를 써라.")
        t, v = [], []
        with open(a.csv, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        h = rows[0]
        ti = next((i for i, c in enumerate(h) if "time" in c.lower() or "시간" in c), 0)
        vi = next((i for i, c in enumerate(h) if any(k in c.lower()
                   for k in ("velocity", "speed", "속도"))), 1)
        for r in rows[1:]:
            try:
                tt, vv = float(r[ti]), float(r[vi])
            except (ValueError, IndexError):
                continue
            if a.unit == "kmh":
                vv /= 3.6
            t.append(tt); v.append(vv)
        t, v = np.array(t), np.array(v)
        k = v >= a.vmin
        if k.sum() < 8:
            sys.exit("쓸 수 있는 점이 너무 적다. --vmin 을 낮추거나 더 긴 구간을 재라.")
        t, v = t[k], v[k]

    r = fit(t, v, a.mass)
    print(f"\n=== 관성주행 역산 결과 (총질량 {a.mass:.0f} kg) ===")
    print(f"  공기저항  Cd·A = {r['CdA']:.3f} ± {r['CdA_err']:.3f} m²")
    print(f"  구름저항  Crr  = {r['crr']:.4f} ± {r['crr_err']:.4f}")
    print(f"  시작속도 {r['v0']*3.6:.1f} km/h,  맞춤 RMSE {r['rmse']:.3f} m/s")
    if truth:
        print(f"  [검증] CdA 오차 {abs(r['CdA']/truth['CdA']-1)*100:.1f}%, "
              f"Crr 오차 {abs(r['crr']/truth['crr']-1)*100:.1f}%")
    for v_kmh in (20, 40, 60, 80, 100):
        vv = v_kmh / 3.6
        fa = 0.5 * RHO * r["CdA"] * vv ** 2
        fr = r["crr"] * a.mass * G
        print(f"  {v_kmh:4d} km/h → 공기저항 {fa:6.1f} N, 구름저항 {fr:5.1f} N, "
              f"공기 비중 {fa/(fa+fr)*100:4.0f}%, 저항 극복 출력 {(fa+fr)*vv/1000:5.2f} kW")
    print()

    if a.plot:
        import matplotlib; matplotlib.use("Agg")
        import _plotfont  # noqa
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(11, 3.9))
        ax[0].plot(r["t"], r["v"] * 3.6, "o", ms=3, color="#888", label="측정")
        ax[0].plot(r["t"], r["fit"] * 3.6, "-", color="#d62728", lw=1.6,
                   label=f"맞춤 CdA={r['CdA']:.3f} m², Crr={r['crr']:.4f}")
        ax[0].set(xlabel="시간 [s]", ylabel="속도 [km/h]", title="관성주행 감속 곡선")
        ax[0].legend(fontsize=8); ax[0].grid(lw=.3, alpha=.5)
        vv = np.linspace(0, 120, 100) / 3.6
        fa = 0.5 * RHO * r["CdA"] * vv ** 2
        fr = np.full_like(vv, r["crr"] * a.mass * G)
        ax[1].plot(vv * 3.6, fr, label="구름저항 (속도 무관)", color="#2ca02c")
        ax[1].plot(vv * 3.6, fa, label="공기저항 (속도²)", color="#1f77b4")
        ax[1].plot(vv * 3.6, fa + fr, "--", label="합계", color="k", lw=1)
        x = np.interp(0, fa - fr, vv) * 3.6
        ax[1].axvline(x, color="#d62728", ls=":", lw=1)
        ax[1].text(x + 2, max(fa) * .6, f"{x:.0f} km/h부터\n공기저항이 더 크다", fontsize=8, color="#d62728")
        ax[1].set(xlabel="속도 [km/h]", ylabel="저항력 [N]", title="속도에 따른 저항 분해")
        ax[1].legend(fontsize=8); ax[1].grid(lw=.3, alpha=.5)
        fig.tight_layout(); fig.savefig(a.plot, dpi=130, bbox_inches="tight")
        print(f"  그래프 저장: {a.plot}\n")


if __name__ == "__main__":
    main()
