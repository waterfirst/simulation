"""급가속 제한 알고리즘 — '탐지'가 아니라 '제어'다.

drive_score.py 는 이미 일어난 급가속을 센다. 이 프로그램은 그것을 **애초에 막는** 쪽이다.
운전자가 밟은 양(요구 가속도)을 받아서, 제어기가 허용 가속도로 바꿔 내보낸다.

네 가지를 비교한다:
  none    제한 없음 (지금의 보통 차)
  fixed   가속도 상한 + 변화율(저크) 상한 — 가장 단순한 방식
  ecomap  페달 응답 곡선을 눕힌다 (에코 모드가 실제로 하는 일)
  cold    **냉간시동 적응형** — 촉매가 데워지기 전에는 더 세게 제한하고, 데워지면 푼다

왜 cold 가 핵심인가:
  삼원촉매는 약 300도가 넘어야 제대로 일한다. 그 전에 급가속하면 정화되지 않은 배기가
  그대로 나간다. 그래서 EHC(전기 가열 촉매) 같은 기술이 따로 있는 것이다.
  -> 제한을 '항상 똑같이' 걸 게 아니라 '촉매가 찰 때까지만 세게' 걸면,
     불편은 줄이면서 배출은 크게 줄일 수 있다. 이것이 이 과제의 제안이다.

usage: python accel_limiter.py --plot ../figs/limiter.png
       python accel_limiter.py --csv ../data/demo_rough.csv --plot ../figs/limiter.png
"""
import argparse, csv
import numpy as np

DT = 0.2
M = 1400.0
LHV, ETA, CO2_L = 32.2e6, 0.25, 2.31
TAU_CAT = 45.0          # 촉매 승온 시정수 [s] (냉간시동 후 이 정도면 대부분 활성)
COLD_MULT = 8.0         # 냉간일 때 유해배출 배수 (단순화한 대리지표)
TS_ACCEL = 11 / 3.6     # 교통안전공단 급가속 기준 [m/s2]

PRESETS = dict(
    none=dict(a_max=9.9, jerk=99.0, map_k=1.0, cold_a=9.9),
    fixed=dict(a_max=2.0, jerk=1.5, map_k=1.0, cold_a=2.0),
    ecomap=dict(a_max=9.9, jerk=2.5, map_k=0.55, cold_a=9.9),
    cold=dict(a_max=2.6, jerk=2.0, map_k=0.85, cold_a=1.1),
)
KO = dict(none="제한 없음", fixed="고정 상한", ecomap="에코 페달맵", cold="냉간 적응형")


def drive_route(p, n_stop=5, seg_m=400.0, v_tgt=50/3.6, a_brake=2.0, wait_s=8.0):
    """같은 경로(정지 n회, 구간 seg_m)를 이 제어기로 달린다.

    운전자의 요구는 동일하다: 목표속도까지 '가능한 한 빨리' 올리고, 순항하고, 세워라.
    제어기는 **가속만** 제한한다(제동 제한은 위험하다).
    제어기가 다르면 같은 거리를 가는 데 걸리는 시간이 달라진다 - 그게 운전자가 치르는 값이다.
    """
    t = 0.0; v = 0.0; a_prev = 0.0
    e_brake = 0.0; e_drive = 0.0; emis = 0.0
    harsh = 0; in_harsh = False
    ts, vs = [0.0], [0.0]
    for k in range(n_stop):
        x = 0.0
        while True:
            d_left = seg_m - x
            d_stop = v * v / (2 * a_brake)               # 지금 속도에서 서는 데 필요한 거리
            if d_left <= d_stop:                          # 제동 구간
                a = -a_brake
            elif v < v_tgt - 0.05:                        # 가속 구간 - 여기만 제한된다
                a_dem = 3.5                               # 운전자가 세게 밟음
                a = a_dem * p["map_k"]
                cold = np.exp(-t / TAU_CAT)
                a = min(a, p["cold_a"] * cold + p["a_max"] * (1 - cold))
                # 저크 제한 때문에 가속을 즉시 끊을 수 없다.
                # 최대 저크로 줄여도 목표속도를 넘지 않을 만큼만 허용한다.
                a = min(a, np.sqrt(max(0.0, 2 * p["jerk"] * (v_tgt - v))), (v_tgt - v) / DT)
            else:
                a = 0.0
            a = float(np.clip(a, a_prev - p["jerk"] * DT, a_prev + p["jerk"] * DT))
            v_new = max(0.0, v + a * DT)
            x += (v + v_new) / 2 * DT
            if a > 0:
                e_drive += M * a * v_new * DT
                emis += a * v_new * (1 + (COLD_MULT - 1) * np.exp(-t / TAU_CAT)) * (1 + 1.5 * a) * DT
            elif a < 0:
                e_brake += 0.5 * M * (v * v - v_new * v_new)
            rate = (v_new - v) / DT
            if rate > TS_ACCEL and not in_harsh:
                harsh += 1; in_harsh = True
            elif rate <= TS_ACCEL:
                in_harsh = False
            v = v_new; a_prev = a; t += DT
            ts.append(t); vs.append(v)
            if v <= 0.01 and d_left <= d_stop:
                break
            if t > 3000:
                break
        for _ in range(int(wait_s / DT)):                 # 신호 대기
            t += DT; ts.append(t); vs.append(0.0)
        a_prev = 0.0
    fuel = (e_drive + e_brake) / (ETA * LHV)
    tv, vv = np.array(ts), np.array(vs)
    dist_real = float(np.sum((vv[1:] + vv[:-1]) / 2 * np.diff(tv)))
    return dict(t=tv, v=vv, time=t, dist=dist_real, dist_nom=n_stop * seg_m,
                harsh=harsh, e_brake=e_brake, emis=emis,
                fuel=fuel, co2=fuel * CO2_L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stops", type=int, default=5)
    ap.add_argument("--seg", type=float, default=400.0, help="정지 간 거리 [m]")
    ap.add_argument("--vtgt", type=float, default=50.0, help="목표 속도 [km/h]")
    ap.add_argument("--plot")
    a = ap.parse_args()

    res = {n: drive_route(p, a.stops, a.seg, a.vtgt / 3.6) for n, p in PRESETS.items()}
    base = res["none"]
    print(f"\n  경로: 정지 {a.stops}회 × {a.seg:.0f} m = {base['dist_nom']/1000:.1f} km, 목표 {a.vtgt:.0f} km/h")
    print(f"  (네 제어기 모두 **같은 거리**를 간다. 다른 것은 걸린 시간이다.)")
    print(f"\n{'='*74}\n  급가속 제한 알고리즘 비교\n{'='*74}")
    print(f"  {'방식':<12}{'급가속':>7}{'최고속도':>9}{'실주행':>9}{'통행시간':>9}{'연료':>8}{'유해배출':>8}{'시간손실':>9}")
    for n in PRESETS:
        r = res[n]
        dt_ = (r["time"] / base["time"] - 1) * 100
        print(f"  {KO[n]:<12}{r['harsh']:>6}회{r['v'].max()*3.6:>8.1f}k{r['dist']:>8.0f}m"
              f"{r['time']:>8.0f}s{r['fuel']*1000:>6.0f}mL{r['emis']/base['emis']*100:>7.0f}%{dt_:>8.1f}%")

    print(f"\n{'='*74}\n  '제한 없음' 대비\n{'='*74}")
    for n in ("fixed", "ecomap", "cold"):
        r = res[n]
        print(f"  {KO[n]:<12} 급가속 {base['harsh']}→{r['harsh']}회 · "
              f"유해배출 {(1-r['emis']/base['emis'])*100:3.0f}% 감소 · "
              f"연료 {(1-r['fuel']/base['fuel'])*100:3.0f}% 절감 · "
              f"시간 {(r['time']-base['time']):+.0f}초 ({(r['time']/base['time']-1)*100:+.0f}%)")

    best = min(("fixed", "ecomap", "cold"),
               key=lambda n: (res[n]["emis"] / base["emis"]) * (res[n]["time"] / base["time"]))
    print(f"""
{'='*74}
  해석 — 발표에서 이렇게 말해라
{'='*74}
  · 제한을 걸면 유해배출은 줄지만 **시간이 더 걸린다**. 공짜가 아니다.
  · 배출 감소와 시간 손실을 함께 보면 **{KO[best]}**이 가장 균형이 좋다.
  · 냉간 적응형이 유리한 이유: 삼원촉매는 약 300도가 넘어야 일한다.
    데워지기 전({TAU_CAT:.0f}초 안팎) 급가속은 정화 안 된 배기를 그대로 내보낸다.
    그래서 **그 구간만 세게 막고 나머지는 푸는** 것이 불편 대비 효과가 가장 크다.
  · 이것이 EHC(전기 가열 촉매)와 같은 문제를 **제어 소프트웨어로** 푸는 접근이다.
    하드웨어 추가 없이 되므로 기존 차에도 적용할 수 있다 - 이 점을 강조해라.

  ※ 안전 — 제한에는 반드시 해제(킥다운)가 있어야 한다.
     고속도로 합류·추월·긴급 회피에서 가속이 막히면 그게 더 위험하다.
     실제 에코 모드도 페달을 끝까지 밟으면 풀린다.

  ※ 유해배출은 **대리지표**다. 실제 배출 모델이 아니다.
     냉간 배수 {COLD_MULT:.0f}배, 시정수 {TAU_CAT:.0f}초는 가정이며 파일 맨 위에서 바꿀 수 있다.
     바꿔가며 결론이 유지되는지 확인해라.
""")

    if a.plot:
        import matplotlib; matplotlib.use("Agg")
        import _plotfont  # noqa
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 3, figsize=(14, 4.2))
        cols = dict(none="#888", fixed="#d62728", ecomap="#1f77b4", cold="#2ca02c")
        for n in PRESETS:
            ax[0].plot(res[n]["t"], res[n]["v"] * 3.6, color=cols[n], lw=1.5, label=KO[n])
        ax[0].set(xlabel="시간 [s]", ylabel="속도 [km/h]", title="같은 경로, 다른 제어기")
        ax[0].legend(fontsize=8); ax[0].grid(lw=.3, alpha=.4)

        nm = [KO[n] for n in PRESETS]
        em = [res[n]["emis"] / base["emis"] * 100 for n in PRESETS]
        ds = [(res[n]["time"] / base["time"] - 1) * 100 for n in PRESETS]
        x = np.arange(len(nm))
        b1 = ax[1].bar(x - .2, em, .4, label="유해배출 (기준 100)", color="#d62728")
        b2 = ax[1].bar(x + .2, [100 + d for d in ds], .4, label="통행시간 (기준 100)", color="#1f77b4")
        ax[1].bar_label(b1, fmt="%.0f", fontsize=8); ax[1].bar_label(b2, fmt="%.0f", fontsize=8)
        ax[1].set(xticks=x, ylabel="상대값 [%]", title="배출은 내려가고 시간은 얼마나 드나")
        ax[1].set_xticklabels(nm, fontsize=8.5); ax[1].legend(fontsize=8)
        ax[1].grid(axis="y", lw=.3, alpha=.4)

        tt = np.linspace(0, 200, 200)
        ax[2].plot(tt, 1 + (COLD_MULT - 1) * np.exp(-tt / TAU_CAT), color="#d62728", lw=2)
        ax[2].axhline(1, color="#888", ls="--", lw=1)
        ax[2].axvline(TAU_CAT, color="#2ca02c", ls=":", lw=1.5)
        ax[2].text(TAU_CAT + 4, COLD_MULT * .6, f"촉매 승온\n시정수 {TAU_CAT:.0f}초",
                   fontsize=9, color="#2ca02c")
        ax[2].set(xlabel="시동 후 경과 시간 [s]", ylabel="유해배출 배수 (대리지표)",
                  title="냉간시동 구간을 노리는 이유")
        ax[2].grid(lw=.3, alpha=.4)
        fig.suptitle("급가속 제한 알고리즘 — 탐지가 아니라 제어", y=1.02)
        fig.tight_layout(); fig.savefig(a.plot, dpi=130, bbox_inches="tight")
        print(f"  그래프 저장: {a.plot}\n")


if __name__ == "__main__":
    main()
