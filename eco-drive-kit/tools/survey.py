"""우리 동네 교차로를 직접 조사해서 '연동하면 얼마나 줄어드는가'를 계산한다.

대상 지역이 정해졌다면, 남이 만든 숫자가 아니라
**너희가 스톱워치로 잰 신호 주기**로 계산해야 한다. 그게 이 탐구의 고유한 데이터다.

조사 양식(data/survey_template.csv):
  name      교차로 이름 (너희가 붙인 것)
  cycle_s   신호 한 바퀴 주기 [초]      - 스톱워치로 3회 재서 평균
  green_s   직진 초록 시간 [초]         - 보행 신호 말고 차량 직진
  dist_m    다음 교차로까지 거리 [m]    - 카카오맵/네이버지도 거리재기
  vlim_kmh  제한속도 [km/h]            - 표지판
  veh_hr    시간당 통과 차량 [대/시]    - 5분간 세서 x12 (선택)

usage: python survey.py ../data/survey_bangbae.csv --plot ../figs/survey.png
       python survey.py --template ../data/survey_template.csv   # 양식만 만들기
"""
import argparse, csv, sys
import numpy as np
import glosa as G

M, ETA, LHV, CO2 = 1400.0, 0.25, 32.2e6, 2.31
DAYS = 250            # 평일 기준 연간 일수


def make_template(path):
    rows = [["name", "cycle_s", "green_s", "dist_m", "vlim_kmh", "veh_hr"],
            ["예시-1번교차로", 120, 45, 350, 50, 900],
            ["예시-2번교차로", 120, 40, 420, 50, 900],
            ["예시-3번교차로", 150, 50, 300, 50, 700]]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows(rows)
    print(f"조사 양식을 만들었다: {path}")
    print("  예시 줄은 지우고 너희가 직접 잰 값을 넣어라.")
    print("  주기·초록은 스톱워치로 3회 재서 평균, 거리는 지도 거리재기.")


def load(path):
    out = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if not r.get("name") or r["name"].startswith("예시"):
                continue
            try:
                out.append(dict(name=r["name"], cycle=float(r["cycle_s"]), green=float(r["green_s"]),
                                dist=float(r["dist_m"]), vlim=float(r["vlim_kmh"]),
                                veh=float(r.get("veh_hr") or 0)))
            except ValueError:
                print(f"  건너뜀(숫자 아님): {r.get('name')}")
    if not out:
        sys.exit("쓸 수 있는 줄이 없다. --template 으로 양식을 만들어 채워라.")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?"); ap.add_argument("--template")
    ap.add_argument("--plot")
    a = ap.parse_args()
    if a.template:
        make_template(a.template); return
    if not a.csv:
        sys.exit("CSV 경로를 주거나 --template 을 써라.")

    S = load(a.csv)
    n = len(S)
    spacing = float(np.mean([s["dist"] for s in S]))
    cycle = float(np.mean([s["cycle"] for s in S]))
    green = float(np.mean([s["green"] for s in S]))
    vlim = float(np.mean([s["vlim"] for s in S])) / 3.6
    veh = float(np.mean([s["veh"] for s in S if s["veh"] > 0] or [0]))

    print(f"\n=== 조사한 교차로 {n}개 ===")
    for s in S:
        print(f"  {s['name']:<16} 주기 {s['cycle']:5.0f}s  초록 {s['green']:4.0f}s "
              f"({s['green']/s['cycle']*100:3.0f}%)  다음까지 {s['dist']:4.0f} m  제한 {s['vlim']:.0f}")
    print(f"\n  평균: 주기 {cycle:.0f}s · 초록 {green:.0f}s · 간격 {spacing:.0f} m · 제한 {vlim*3.6:.0f} km/h")

    modes = [("naive", "현재", 0.0), ("glosa", "GLOSA 안내", 0.0),
             ("naive", "신호 연동", spacing / vlim)]
    res = []
    print(f"\n=== 이 구간({n}개 교차로, {n*spacing/1000:.1f} km)을 차 한 대가 지날 때 ===")
    print(f"  {'방식':<12}{'정지':>5}{'버린연료':>10}{'CO2':>8}{'통행시간':>9}")
    for mode, label, off in modes:
        r = G.drive(mode, n, spacing, vlim, cycle, green, off)
        L = r["e_brake"] / (ETA * LHV)
        res.append((label, r, L))
        print(f"  {label:<12}{r['stops']:>4}회{L*1000:>8.0f} mL{L*CO2*1000:>6.0f} g{r['time']:>8.0f} s")

    base = res[0]
    # GLOSA 가 통하는 조건: 속도를 늦춰 벌 수 있는 도착시각 폭이 빨간불 길이보다 커야 한다
    vmin_frac = 0.45
    window = spacing / vlim * (1 / vmin_frac - 1)        # 늦춰서 벌 수 있는 시간 [s]
    red = cycle - green
    need_d = vlim * red / (1 / vmin_frac - 1)
    print(f"\n=== GLOSA 가 이 지역에서 통하나? ===")
    print(f"  속도를 {vlim*3.6:.0f} → {vlim*vmin_frac*3.6:.0f} km/h 로 늦추면 도착을 {window:.0f}초 미룰 수 있다.")
    print(f"  그런데 빨간불은 {red:.0f}초다.")
    if window >= red:
        print(f"  → {window:.0f} ≥ {red:.0f} 이므로 대부분의 빨간불을 피할 수 있다. GLOSA 가 통한다.")
    else:
        print(f"  → {window:.0f} < {red:.0f} 이므로 초록에 맞추려면 {spacing/ (red+spacing/vlim) *3.6:.0f} km/h 이하로")
        print(f"    기어가야 한다. 현실적이지 않아서 GLOSA 효과가 거의 없다.")
        print(f"  * 이 지역에서 GLOSA 가 통하려면 교차로 간격이 {need_d:.0f} m 이상이거나,")
        print(f"    신호 주기가 {green + window:.0f}초 이하여야 한다 (현재 {cycle:.0f}초).")
    print(f"  ** 이것이 '왜 우리 동네는 GLOSA 보다 신호 연동이 답인가'의 근거다.")

    print(f"\n=== 지역 단위로 키우면 (평일 {DAYS}일 기준) ===")
    if veh <= 0:
        print("  시간당 통과 차량(veh_hr)을 안 적었다. 5분간 세서 x12 하면 된다.")
        print("  그 값을 넣으면 '우리 동네에서 연간 CO2 몇 톤'까지 나온다.")
    else:
        daily = veh * 12                      # 하루 12시간 통행으로 가정
        for label, r, L in res[1:]:
            dco2 = (base[2] - L) * CO2        # 대당 절감 kg
            print(f"  {label:<12} 하루 {daily:,.0f}대 기준  "
                  f"연간 {dco2*daily*DAYS/1000:6.1f} 톤-CO2 절감")
        print(f"\n  (가정: 하루 12시간 통행, 평일 {DAYS}일, 승용차 {M:.0f} kg, 엔진효율 {ETA*100:.0f}%)")
        print("   이 가정들은 너희가 바꿔서 민감도를 확인해 봐라 — 그게 보고서의 '한계' 절이 된다.")
    print()

    if a.plot:
        import matplotlib; matplotlib.use("Agg")
        import _plotfont  # noqa
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 3, figsize=(13, 3.9))
        nm = [s["name"] for s in S]
        ax[0].barh(nm, [s["green"]/s["cycle"]*100 for s in S], color="#2ca02c")
        ax[0].set(xlabel="직진 초록 비율 [%]", title="교차로별 초록 시간 비중")
        ax[0].grid(axis="x", lw=.3, alpha=.4); ax[0].tick_params(labelsize=8)
        ax[1].bar([r[0] for r in res], [r[2]*1000 for r in res], color=["#888", "#1f77b4", "#2ca02c"])
        for i, r in enumerate(res):
            ax[1].text(i, r[2]*1000, f"{r[2]*1000:.0f} mL", ha="center", va="bottom", fontsize=9)
        ax[1].set(ylabel="버린 연료 [mL]", title="차 한 대가 이 구간을 지날 때")
        ax[1].grid(axis="y", lw=.3, alpha=.4); ax[1].tick_params(labelsize=9)
        ax[2].bar([r[0] for r in res], [r[1]["time"] for r in res], color=["#888", "#1f77b4", "#2ca02c"])
        for i, r in enumerate(res):
            ax[2].text(i, r[1]["time"], f"{r[1]['time']:.0f}s\n정지 {r[1]['stops']}회",
                       ha="center", va="bottom", fontsize=8)
        ax[2].set(ylabel="통행 시간 [s]", title="같은 구간 통과 시간")
        ax[2].grid(axis="y", lw=.3, alpha=.4); ax[2].tick_params(labelsize=9)
        fig.suptitle(f"우리가 직접 조사한 교차로 {n}개 — 연동했을 때의 효과", y=1.02)
        fig.tight_layout(); fig.savefig(a.plot, dpi=130, bbox_inches="tight")
        print(f"  그래프 저장: {a.plot}\n")


if __name__ == "__main__":
    main()
