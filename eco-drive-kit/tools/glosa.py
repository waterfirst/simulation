"""신호 연동 주행(GLOSA) 시뮬레이터 — '시스템'이 개인보다 얼마나 더 줄이는가.

GLOSA(Green Light Optimal Speed Advisory)는 앞쪽 신호의 점멸 시각을 차에 알려주어
"지금 48 km/h로 가면 안 멈추고 통과한다"를 안내하는 기술이다. 유럽·일본에서 이미 상용화됐다.

여기서는 같은 도로를 세 가지 방식으로 달려보고 정지 횟수·제동 에너지·통행 시간을 비교한다.
  naive : 제한속도로 달리다 빨간불이면 멈춘다 (지금의 도심 주행)
  glosa : 다음 신호를 초록에 통과할 수 있는 속도로 미리 조절한다
  green : 신호 자체를 차량 흐름에 맞춰 연동한다 (green wave, 인프라 개선)

usage: python glosa.py --signals 8 --plot ../figs/glosa.png
"""
import argparse
import numpy as np

M, ETA, LHV, CO2 = 1400.0, 0.25, 32.2e6, 2.31     # kg, 엔진효율, J/L, kg-CO2/L


def is_green(t, cycle, green, offset):
    return ((t - offset) % cycle) < green


def next_green_window(t0, cycle, green, offset, k=3):
    """t0 이후에 열리는 초록 구간들을 (시작, 끝)으로 돌려준다."""
    n = int((t0 - offset) // cycle)
    out = []
    for i in range(n, n + k + 2):
        g0, g1 = offset + i * cycle, offset + i * cycle + green
        if g1 > t0:
            out.append((max(g0, t0), g1))
        if len(out) >= k:
            break
    return out


def advise(d, t, v_lim, cycle, green, offset, v_min_frac=0.45):
    """GLOSA: 이 신호를 '멈추지 않고' 통과할 수 있는 권장속도. 없으면 None.

    제한속도로 달려 초록이면 그대로 간다. 못 맞추면 다음 초록에 맞춰 속도를 낮춘다
    - 이것이 GLOSA의 핵심이다. 빨리 가서 서는 대신, 천천히 가서 안 선다.
    """
    v_min = v_lim * v_min_frac
    for g0, g1 in next_green_window(t, cycle, green, offset):
        t_early, t_late = g0 - t, g1 - t - 1.0                 # 초록 끝 1초 전까지만 노린다
        if t_late <= 0:
            continue
        v_need_fast = d / max(t_early, 1e-6)                   # 초록 시작에 딱 도착하는 속도
        v_need_slow = d / t_late                               # 초록 끝에 겨우 도착하는 속도
        lo, hi = max(v_need_slow, v_min), min(v_need_fast, v_lim)
        if lo <= hi:
            return hi                                          # 가능한 범위에서 가장 빠른 속도
    return None


def drive(mode, n_sig, spacing, v_lim, cycle, green, offset_step, a_cmf=1.5, dt=0.2):
    """신호 n개를 지난다. GLOSA는 구간에 들어갈 때 권장속도를 한 번 정하고 유지한다."""
    x, v, t = 0.0, v_lim, 0.0
    stops, e_brake = 0, 0.0
    traj = [(0.0, 0.0, v)]
    for k in range(n_sig):
        xs = (k + 1) * spacing
        off = k * offset_step
        target = v_lim
        if mode == "glosa":
            rec = advise(xs - x, t, v_lim, cycle, green, off)
            target = rec if rec is not None else v_lim
        while x < xs:
            d = xs - x
            v += float(np.clip(target - v, -a_cmf * dt, a_cmf * dt))
            v = max(v, 0.5)
            tta = d / v
            if not is_green(t + tta, cycle, green, off) and d < v ** 2 / (2 * 3.0) + 4:
                e_brake += 0.5 * M * v ** 2                     # 정지 = 운동에너지를 열로 버림
                stops += 1
                t += v / 3.0
                x = xs; v = 0.0
                traj.append((t, x, v))
                while not is_green(t, cycle, green, off):
                    t += dt
                traj.append((t, x, v))
                break
            x += v * dt; t += dt
            traj.append((t, x, v))
        v = max(v, 0.5)
    return dict(stops=stops, e_brake=e_brake, time=t, dist=n_sig * spacing,
                traj=np.array(traj))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--signals", type=int, default=8)
    ap.add_argument("--spacing", type=float, default=400.0, help="신호 간격 [m]")
    ap.add_argument("--vlim", type=float, default=50.0, help="제한속도 [km/h]")
    ap.add_argument("--cycle", type=float, default=90.0, help="신호 주기 [s]")
    ap.add_argument("--green", type=float, default=40.0, help="초록 시간 [s]")
    ap.add_argument("--plot")
    a = ap.parse_args()
    vl = a.vlim / 3.6
    modes = [("naive", "지금 방식 (제한속도로 달리다 멈춤)", 0.0),
             ("glosa", "GLOSA (차에 권장속도 안내)", 0.0),
             ("naive", "연동신호 green wave (인프라 개선)", a.spacing / vl)]
    print(f"\n신호 {a.signals}개 · 간격 {a.spacing:.0f} m · 제한 {a.vlim:.0f} km/h · 주기 {a.cycle:.0f}s(초록 {a.green:.0f}s)\n")
    print(f"{'방식':<34}{'정지':>5}{'제동에너지':>12}{'연료':>9}{'CO2':>9}{'통행시간':>10}{'평균속도':>10}")
    res = []
    for mode, label, off in modes:
        r = drive(mode, a.signals, a.spacing, vl, a.cycle, a.green, off)
        L = r["e_brake"] / (ETA * LHV)
        res.append((label, r, L))
        print(f"{label:<34}{r['stops']:>4}회{r['e_brake']/1000:>10.0f} kJ"
              f"{L*1000:>7.0f} mL{L*CO2*1000:>7.0f} g{r['time']:>9.0f} s"
              f"{r['dist']/r['time']*3.6:>9.1f} km/h")
    base = res[0]
    print()
    print("  '지금 방식' 대비:")
    for label, r, L in res[1:]:
        dl = (1 - L / (base[2] or 1)) * 100
        dt_ = (1 - r["time"] / base[1]["time"]) * 100
        print(f"    {label:<32} 제동 연료 {dl:.0f}% 절감, 통행시간 {dt_:.0f}% 단축, "
              f"정지 {base[1]['stops']}회 → {r['stops']}회")
    print()

    if a.plot:
        import matplotlib; matplotlib.use("Agg")
        import _plotfont  # noqa
        import matplotlib.pyplot as plt
        fig = plt.figure(figsize=(12.6, 5.4))
        gs = fig.add_gridspec(2, 2, width_ratios=[1.75, 1], hspace=.45, wspace=.25)
        axA, axB = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[1, 0])
        axC = fig.add_subplot(gs[:, 1])
        cols = ["#888", "#1f77b4", "#2ca02c"]
        tmax = max(r["time"] for _, r, _ in res)
        tt = np.arange(0, tmax, 1.0)

        def draw_signals(ax, off_step):
            for k in range(a.signals):
                xs = (k + 1) * a.spacing / 1000
                g = np.array([is_green(x, a.cycle, a.green, k * off_step) for x in tt])
                ax.scatter(tt[g], np.full(g.sum(), xs), s=.7, color="#2ca02c", alpha=.3)
                ax.scatter(tt[~g], np.full((~g).sum(), xs), s=.7, color="#d62728", alpha=.3)

        draw_signals(axA, 0.0)                       # 기존 신호 타이밍
        for (label, r, L), c in zip(res[:2], cols[:2]):
            axA.plot(r["traj"][:, 0], r["traj"][:, 1] / 1000, color=c, lw=1.7, label=label)
        axA.set(ylabel="위치 [km]", title="현재 신호 타이밍 — 운전 방식만 바꿨을 때")
        axA.legend(fontsize=8, loc="upper left"); axA.grid(lw=.3, alpha=.4)

        draw_signals(axB, modes[2][2])               # 연동된 신호 타이밍
        axB.plot(res[2][1]["traj"][:, 0], res[2][1]["traj"][:, 1] / 1000,
                 color=cols[2], lw=1.7, label=res[2][0])
        axB.set(xlabel="시간 [s]", ylabel="위치 [km]",
                title="신호를 연동했을 때 — 초록 띠가 차의 속도에 맞춰 이동한다")
        axB.legend(fontsize=8, loc="upper left"); axB.grid(lw=.3, alpha=.4)
        axA.set_xlim(0, tmax); axB.set_xlim(0, tmax)

        lb = ["지금 방식", "GLOSA", "연동신호"]
        fu = [r[2] * 1000 for r in res]
        b = axC.bar(lb, fu, color=cols)
        axC.bar_label(b, fmt="%.0f mL", fontsize=9)
        for i, (_, r, _) in enumerate(res):
            axC.text(i, fu[i] * .5 if fu[i] > 5 else 3, f"정지 {r['stops']}회\n{r['time']:.0f}초",
                     ha="center", fontsize=8, color="w" if fu[i] > 20 else "#333")
        axC.set(ylabel="제동으로 버린 연료 [mL]", title="같은 3.2 km를 달렸을 때")
        axC.tick_params(axis="x", labelsize=9); axC.grid(axis="y", lw=.3, alpha=.4)
        fig.suptitle("개인의 운전 습관보다 신호 시스템이 더 크게 줄인다", y=1.0)
        fig.savefig(a.plot, dpi=130, bbox_inches="tight")
        print(f"  그래프 저장: {a.plot}\n")


if __name__ == "__main__":
    main()
