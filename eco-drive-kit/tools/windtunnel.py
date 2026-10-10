"""2D 풍동 — 격자 볼츠만(D2Q9)으로 차 모양에 따른 공기 흐름과 항력을 비교한다.

실제 풍동 없이 "모양을 바꾸면 항력이 얼마나 달라지는가"를 눈으로 보고 숫자로 비교하는 도구다.
절대값을 믿는 용도가 아니다(2D·저레이놀즈수). 같은 조건에서 모양끼리 비교할 때만 의미가 있다.

usage: python windtunnel.py --shape sedan --steps 6000 --plot ../figs/wt_sedan.png
       python windtunnel.py --compare --plot ../figs/wt_compare.png
"""
import argparse
import numpy as np

NX, NY = 360, 120
C = np.array([[0, 0], [1, 0], [0, 1], [-1, 0], [0, -1],
              [1, 1], [-1, 1], [-1, -1], [1, -1]])
W = np.array([4/9] + [1/9]*4 + [1/36]*4)
OPP = np.array([0, 3, 4, 1, 2, 7, 8, 5, 6])


def shape_mask(name):
    """차 단면을 격자 위에 그린다. y=0 이 지면."""
    m = np.zeros((NX, NY), bool)
    x, y = np.meshgrid(np.arange(NX), np.arange(NY), indexing="ij")
    x0, g = 90, 14                                  # 앞범퍼 위치, 지상고
    L, H = 120, 34                                  # 길이, 높이
    if name == "box":                               # 각진 박스 (버스·트럭)
        m = (x >= x0) & (x < x0 + L) & (y >= g) & (y < g + H)
    elif name == "sedan":                           # 앞 경사 + 완만한 뒤
        body = (x >= x0) & (x < x0 + L) & (y >= g) & (y < g + H * 0.55)
        xr = (x - x0) / L
        roof = (xr > 0.22) & (xr < 0.80) & (y >= g + H * 0.55) & \
               (y < g + H * 0.55 + H * 0.45 * np.sin(np.pi * np.clip((xr - 0.22) / 0.58, 0, 1)))
        m = body | roof
    elif name == "teardrop":                        # 물방울 (뒤를 길게 뺀 형상)
        xr = np.clip((x - x0) / L, 0, 1)
        half = H / 2 * np.sqrt(np.clip(1 - ((xr - 0.3) / 0.3) ** 2, 0, 1)) * (xr <= 0.3) + \
               H / 2 * (1 - np.clip((xr - 0.3) / 0.7, 0, 1)) ** 0.7 * (xr > 0.3)
        m = (x >= x0) & (x < x0 + L) & (y >= g) & (y < g + np.maximum(half, 0) * 2)
    elif name == "boxtail":                         # 박스인데 뒤만 깎음 (보트테일)
        xr = (x - x0) / L
        top = np.where(xr < 0.7, H, H * (1 - (xr - 0.7) / 0.3 * 0.55))
        m = (x >= x0) & (x < x0 + L) & (y >= g) & (y < g + top)
    else:
        raise SystemExit(f"모르는 모양: {name}")
    m[:, 0] = True                                  # 지면
    return m


def run(mask, steps=6000, u0=0.075, tau=0.56, every=0):
    f = np.ones((NX, NY, 9)) * W
    rho, ux, uy = np.ones((NX, NY)), np.full((NX, NY), u0), np.zeros((NX, NY))
    f = W * rho[..., None] * (1 + 3*(C[:, 0]*ux[..., None] + C[:, 1]*uy[..., None]))
    drag_hist = []
    for s in range(steps):
        f[0, :, [1, 5, 8]] = (W[[1, 5, 8]] * (1 + 3*u0))[:, None]      # 입구: 일정 속도
        f[-1, :, [3, 6, 7]] = f[-2, :, [3, 6, 7]]                       # 출구: 그대로 흘려보냄
        rho = f.sum(2)
        ux = (f @ C[:, 0]) / rho
        uy = (f @ C[:, 1]) / rho
        ux[mask] = uy[mask] = 0
        cu = 3 * (C[:, 0] * ux[..., None] + C[:, 1] * uy[..., None])
        feq = W * rho[..., None] * (1 + cu + 0.5*cu**2 - 1.5*(ux**2 + uy**2)[..., None])
        fout = f - (f - feq) / tau
        fout[mask] = f[mask][:, OPP]                                    # 벽: 되튕김
        for i in range(9):
            f[:, :, i] = np.roll(np.roll(fout[:, :, i], C[i, 0], 0), C[i, 1], 1)
        if s > steps * 0.5 and s % 20 == 0:
            # 항력 = 벽에서 주고받은 운동량 (momentum exchange)
            d = 0.0
            for i in range(1, 9):
                sh = np.roll(np.roll(mask, -C[i, 0], 0), -C[i, 1], 1)
                nb = sh & ~mask
                d += (C[i, 0] * (fout[nb][:, i] + f[nb][:, OPP[i]])).sum()
            drag_hist.append(d)
    speed = np.sqrt(ux**2 + uy**2)
    speed[mask] = np.nan
    return dict(drag=float(np.mean(drag_hist[-20:])), speed=speed, ux=ux, uy=uy, mask=mask,
                area=float(mask[:, 1:].sum(1).max()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shape", default="sedan", choices=["box", "sedan", "teardrop", "boxtail"])
    ap.add_argument("--steps", type=int, default=6000)
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--plot")
    a = ap.parse_args()
    names = ["box", "boxtail", "sedan", "teardrop"] if a.compare else [a.shape]
    KO = {"box": "각진 박스", "boxtail": "뒤를 깎은 박스", "sedan": "세단형", "teardrop": "물방울형"}
    res = {}
    for n in names:
        r = run(shape_mask(n), a.steps)
        res[n] = r
        print(f"  {KO[n]:12s} 항력(상대) {r['drag']:9.3f}   정면높이 {r['area']:3.0f} 격자")
    base = res[names[0]]["drag"]
    print(f"\n  {KO[names[0]]} 를 100 으로 두면:")
    for n in names:
        print(f"    {KO[n]:12s} {res[n]['drag']/base*100:5.1f}")
    if a.plot:
        import matplotlib; matplotlib.use("Agg")
        import _plotfont  # noqa
        import matplotlib.pyplot as plt
        k = len(names)
        fig, axes = plt.subplots(k, 1, figsize=(11, 2.3*k + .6))
        axes = np.atleast_1d(axes)
        vmax = np.nanmax([np.nanmax(res[n]["speed"]) for n in names])
        for ax, n in zip(axes, names):
            r = res[n]
            im = ax.imshow(r["speed"].T, origin="lower", cmap="viridis", vmin=0, vmax=vmax,
                           aspect="auto", interpolation="bilinear")
            ax.contour(r["mask"].T, levels=[.5], colors="w", linewidths=1)
            ax.set(title=f"{KO[n]} — 상대 항력 {r['drag']/base*100:.0f}", xticks=[], yticks=[])
        fig.colorbar(im, ax=axes.tolist(), label="속도 (격자 단위)", fraction=.02)
        fig.suptitle("2D 풍동 — 밝을수록 빠름. 차 뒤의 어두운 영역(후류)이 클수록 항력이 크다", y=.995)
        fig.savefig(a.plot, dpi=130, bbox_inches="tight")
        print(f"\n  그래프 저장: {a.plot}")


if __name__ == "__main__":
    main()
