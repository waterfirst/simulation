"""주행 데이터에서 위험운전행동을 찾아 점수와 추가 연료·CO2를 계산한다.

판정 기준은 한국교통안전공단(TS)이 운행기록장치(DTG) 분석에 쓰는 공식 기준을 따른다.
  과속    : 제한속도 초과
  장기과속: 제한속도 초과가 3분 이상 지속
  급가속  : 초당 11~25 km/h 가속 (주행 중)
  급출발  : 정지(5km/h 미만)에서 초당 11~25 km/h 가속
  급감속  : 초당 7.5~40 km/h 감속 (주행 중)
  급정지  : 초당 7.5~40 km/h 감속하여 정지

입력 CSV는 열 두 개만 있으면 된다: time(초), speed(km/h)
  - phyphox "Location (GPS)" 내보내기: Time (s), Velocity (m/s)  -> --speed-unit ms
  - OBD-II 앱(Torque 등) 로그: 시간, 속도(km/h)
usage: python drive_score.py data/run1.csv --limit 60 [--speed-unit ms] [--plot figs/run1.png]
"""
import argparse, csv, math, sys

TS = dict(accel_min=11.0, accel_max=25.0,      # km/h per second
          decel_min=7.5, decel_max=40.0,
          stop_speed=5.0, long_speed_sec=180)
# 휘발유 대표값. LHV는 32.2 MJ/L, 가솔린 엔진 평균 열효율 25%, 연소 CO2 2.31 kg/L
FUEL = dict(lhv_mj=32.2, eta=0.25, co2_per_l=2.31, regen=0.70)


def load(path, unit):
    t, v = [], []
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    head = rows[0]
    ti = next((i for i, c in enumerate(head) if "time" in c.lower() or "시간" in c), 0)
    vi = next((i for i, c in enumerate(head)
               if any(k in c.lower() for k in ("velocity", "speed", "속도"))), 1)
    for r in rows[1:]:
        try:
            tt, vv = float(r[ti]), float(r[vi])
        except (ValueError, IndexError):
            continue
        if unit == "ms":
            vv *= 3.6
        t.append(tt); v.append(vv)
    if len(t) < 10:
        sys.exit(f"데이터가 너무 적다({len(t)}행). 열 이름이 time/speed 인지 확인해라.")
    return t, v


def smooth(v, w=3):
    """GPS 속도는 튄다. 이동평균으로 다듬지 않으면 가짜 급가속이 잡힌다.

    단, 과하게 다듬으면 진짜 급출발·급정지까지 뭉개진다(1초 동안 일어나는 일이다).
    1 Hz 데이터는 다듬지 말고, 10 Hz 이상 가속도계 데이터만 다듬어라 - main()이 자동 판단한다.
    """
    out = []
    for i in range(len(v)):
        lo, hi = max(0, i - w // 2), min(len(v), i + w // 2 + 1)
        out.append(sum(v[lo:hi]) / (hi - lo))
    return out


def analyze(t, v, limit):
    """위험운전행동을 센다. 과속은 '샘플 수'가 아니라 '연속 구간 1건'으로 센다."""
    ev = {k: [] for k in ("과속", "장기과속", "급가속", "급출발", "급감속", "급정지")}
    over = []                                        # 과속 구간 (시작, 끝)
    start = None
    for i in range(1, len(t)):
        dt = t[i] - t[i - 1]
        if dt <= 0 or dt > 3:                        # 샘플이 끊긴 구간은 건너뛴다
            continue
        a = (v[i] - v[i - 1]) / dt                   # km/h per second
        if TS["accel_min"] <= a <= TS["accel_max"]:
            ev["급출발" if v[i - 1] < TS["stop_speed"] else "급가속"].append(t[i])
        if -TS["decel_max"] <= a <= -TS["decel_min"]:
            ev["급정지" if v[i] < TS["stop_speed"] else "급감속"].append(t[i])
        if v[i] > limit:
            start = t[i] if start is None else start
        elif start is not None:
            over.append((start, t[i - 1])); start = None
    if start is not None:
        over.append((start, t[-1]))
    for s0, s1 in over:
        ev["과속"].append(s0)
        if s1 - s0 >= TS["long_speed_sec"]:
            ev["장기과속"].append(s0)
    ev["_over_spans"] = over
    ev["_over_sec"] = sum(b - a for a, b in over)
    return ev


def summarize(t, v, ev, limit, mass):
    """제동으로 버린 운동에너지를 연료로 환산한다.

    브레이크는 운동에너지를 열로 버린다. 그 에너지는 원래 연료를 태워 만든 것이므로
    (엔진 열효율 eta 를 거쳐 나온 것이므로) 버린 에너지 / (eta x LHV) 가 낭비된 연료다.
    회생제동이 있는 전기차라면 이 중 상당분을 되찾는다 - 그 차이가 이 과제의 핵심이다.
    """
    dur = t[-1] - t[0]
    dist = e_brake = e_brake_harsh = 0.0
    harsh_t = set(ev["급감속"]) | set(ev["급정지"])
    for i in range(1, len(t)):
        dt = t[i] - t[i - 1]
        if not (0 < dt <= 3):
            continue
        dist += (v[i] + v[i - 1]) / 2 / 3600 * dt
        v1, v2 = v[i - 1] / 3.6, v[i] / 3.6                   # m/s
        if v2 < v1:                                            # 감속 = 에너지 버림
            de = 0.5 * mass * (v1 ** 2 - v2 ** 2)
            e_brake += de
            if t[i] in harsh_t:
                e_brake_harsh += de
    n_harsh = sum(len(ev[k]) for k in ("급가속", "급출발", "급감속", "급정지"))
    per100 = n_harsh / dist * 100 if dist > 0 else 0
    j_per_l = FUEL["lhv_mj"] * 1e6 * FUEL["eta"]               # 1 L 로 바퀴에 전달되는 에너지 [J]
    waste_l = e_brake / j_per_l
    waste_harsh_l = e_brake_harsh / j_per_l
    saved_l = waste_l * FUEL["regen"]                          # 회생제동으로 되찾을 수 있는 양
    pen_over = min(25, ev["_over_sec"] / max(dur, 1) * 100 * 0.5)      # 과속 시간 비율로 최대 25점 감점
    score = max(0, 100 / (1 + per100 / 20) - pen_over - len(ev["장기과속"]) * 5)
    return dict(dur=dur, dist=dist, vmax=max(v), vavg=dist / (dur / 3600) if dur else 0,
                n_harsh=n_harsh, per100=per100, score=score, mass=mass,
                e_brake=e_brake, e_brake_harsh=e_brake_harsh,
                harsh_share=e_brake_harsh / e_brake * 100 if e_brake else 0,
                waste_l=waste_l, waste_harsh_l=waste_harsh_l, saved_l=saved_l,
                waste_co2=waste_l * FUEL["co2_per_l"], saved_co2=saved_l * FUEL["co2_per_l"],
                per_km_l=waste_l / dist if dist else 0,
                over_sec=ev["_over_sec"], over_pct=ev["_over_sec"] / dur * 100 if dur else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv"); ap.add_argument("--limit", type=float, default=60.0)
    ap.add_argument("--speed-unit", choices=["kmh", "ms"], default="kmh")
    ap.add_argument("--plot"); ap.add_argument("--no-smooth", action="store_true")
    ap.add_argument("--mass", type=float, default=1400.0, help="차량 총질량 [kg]")
    ap.add_argument("--smooth-window", type=int, default=3)
    a = ap.parse_args()
    t, v = load(a.csv, a.speed_unit)
    dts = sorted(t[i] - t[i - 1] for i in range(1, len(t)))
    dt_med = dts[len(dts) // 2]
    if not a.no_smooth and dt_med < 0.5:            # 고속 샘플링일 때만 다듬는다
        w = max(3, int(round(0.4 / dt_med)) | 1)
        v = smooth(v, w)
        print(f"  [전처리] 샘플 간격 {dt_med:.2f}s → 이동평균 {w}점 적용")
    else:
        print(f"  [전처리] 샘플 간격 {dt_med:.2f}s → 평활화 없음 (급출발·급정지를 뭉개지 않기 위해)")
    ev = analyze(t, v, a.limit)
    s = summarize(t, v, ev, a.limit, a.mass)

    print(f"\n=== 주행 요약 ({a.csv}) ===")
    print(f"  주행시간 {s['dur']:.0f} s   거리 {s['dist']:.2f} km   "
          f"평균 {s['vavg']:.1f} km/h   최고 {s['vmax']:.1f} km/h   (제한 {a.limit:.0f})")
    print(f"\n=== 위험운전행동 (교통안전공단 기준) ===")
    for k in ("과속", "장기과속", "급가속", "급출발", "급감속", "급정지"):
        extra = f"   (총 {s['over_sec']:.0f}초, 주행시간의 {s['over_pct']:.0f}%)" if k == "과속" else ""
        print(f"  {k:6s} {len(ev[k]):4d}회{extra}")
    print(f"\n  급가속·급출발·급감속·급정지 합계 {s['n_harsh']}회  →  100 km당 {s['per100']:.1f}회")
    print(f"\n=== 환경 영향 — 제동으로 버린 에너지 (차량 {s['mass']:.0f} kg 가정) ===")
    print(f"  총 제동 에너지      {s['e_brake']/1000:9.1f} kJ   (이 중 급감속·급정지 {s['harsh_share']:.0f}%)")
    print(f"  연료 환산           {s['waste_l']*1000:9.1f} mL   = {s['per_km_l']*1000:.0f} mL/km")
    print(f"  CO2 환산            {s['waste_co2']*1000:9.0f} g")
    print(f"  회생제동 적용 시 회수 {s['saved_l']*1000:9.1f} mL  (CO2 {s['saved_co2']*1000:.0f} g 절감)")
    print(f"\n  에코 점수 {s['score']:.0f} / 100\n")

    if a.plot:
        import matplotlib; matplotlib.use("Agg")
        import _plotfont  # noqa
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True,
                               gridspec_kw={"height_ratios": [2, 1]})
        ax[0].plot(t, v, lw=1.1, color="#1f77b4", label="속도")
        ax[0].axhline(a.limit, color="gray", ls="--", lw=.9, label=f"제한 {a.limit:.0f} km/h")
        col = {"급가속": "#d62728", "급출발": "#ff7f0e", "급감속": "#9467bd", "급정지": "#8c564b"}
        for k, c in col.items():
            if ev[k]:
                ax[0].plot(ev[k], [v[min(range(len(t)), key=lambda i: abs(t[i] - x))] for x in ev[k]],
                           "v" if "감" in k or "정" in k else "^", color=c, ms=6, ls="", label=f"{k} {len(ev[k])}")
        ax[0].set(ylabel="속도 [km/h]", title=f"주행 분석 — 에코 점수 {s['score']:.0f}/100")
        ax[0].legend(fontsize=8, ncol=3); ax[0].grid(lw=.3, alpha=.5)
        acc = [0] + [(v[i] - v[i - 1]) / max(t[i] - t[i - 1], 1e-6) for i in range(1, len(t))]
        ax[1].plot(t, acc, lw=.9, color="#2ca02c")
        for y, lab in ((11, "급가속 11"), (-7.5, "급감속 -7.5")):
            ax[1].axhline(y, color="#d62728", ls=":", lw=.9)
            ax[1].text(t[0], y, f" {lab}", fontsize=7, color="#d62728", va="bottom")
        ax[1].set(xlabel="시간 [s]", ylabel="가속도 [km/h per s]", ylim=(-20, 20)); ax[1].grid(lw=.3, alpha=.5)
        fig.tight_layout(); fig.savefig(a.plot, dpi=130, bbox_inches="tight")
        print(f"  그래프 저장: {a.plot}\n")


if __name__ == "__main__":
    main()
