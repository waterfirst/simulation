"""에너지 자립형 교통 인프라 — 무엇까지 자급자족이 되나?

다음 두 질문에 답하는 도구다:
  "분산전원으로 충전 인프라에 전력을 얼마나 공급할 수 있나?"
  "압전 하베스터는 얼마나 생산하고, 남는 전력이 있나?"

방법: 발전원을 '면적당 평균 전력 [W/m2]' 으로 통일하고,
      부하를 '평균 소비 전력 [W]' 으로 통일한 뒤 나눈다.
      단위를 통일하면 6자리 차이가 한눈에 보인다.

출처(2차 — 너희가 1차 확인할 것):
  서울 태양광 1 kW 설비 = 하루 3.554 kWh (서울시 에너지정보), 설비이용률 약 15.5%
  보도용 압전 하베스터 실측 평균 약 3.1 mW/타일 (논문 리뷰값)
usage: python energy_budget.py [--solar-area 2] [--plot ../figs/energy.png]
"""
import argparse

SEOUL_KWH_PER_KW_DAY = 3.554      # 서울 태양광 1kW 설비의 하루 발전량
PANEL_KW_PER_M2 = 0.20            # 패널 효율 20% -> 1 m2 = 0.2 kW 설비
RHO = 1.225                       # 공기밀도
PIEZO_MW_PER_TILE = 3.1           # 타일 1장 실측 평균 [mW]
PIEZO_TILES_PER_M2 = 4            # 1 m2 에 타일 4장

# 교통 인프라 부하 — (이름, 정격 W, 하루 가동시간 h)
LOADS = [
    ("CCTV 1대",              15,  24),
    ("LED 보행신호등 1면",      20,  24),
    ("버스정류장 안내단말",      60,  20),
    ("소형 전광 안내판(VMS)",   100,  24),
    ("LED 가로등 1기",         100,  12),
    ("대형 전광 안내판(VMS)",  1500,  24),
    ("EV 완속충전기 1기",      7000,   4),
    ("EV 급속충전기 1기",     50000,   2),
]


def solar_w_per_m2():
    """1 m2 태양광의 24시간 평균 전력 [W]"""
    kwh_day = PANEL_KW_PER_M2 * SEOUL_KWH_PER_KW_DAY
    return kwh_day * 1000 / 24


def wind_w_per_m2(v, cp=0.35):
    """날개 면적 1 m2 소형 풍력의 평균 전력 [W]. 도심 평균풍속은 보통 2~3 m/s."""
    return 0.5 * RHO * v ** 3 * cp


def piezo_w_per_m2():
    return PIEZO_TILES_PER_M2 * PIEZO_MW_PER_TILE / 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wind-speed", type=float, default=2.5, help="도심 평균 풍속 [m/s]")
    ap.add_argument("--solar-area", type=float, default=0, help="가진 패널 면적으로 계산 [m2]")
    ap.add_argument("--plot")
    a = ap.parse_args()

    S, W, P = solar_w_per_m2(), wind_w_per_m2(a.wind_speed), piezo_w_per_m2()
    print(f"\n{'='*62}\n  발전원 비교 — 1 m2 당 24시간 평균 전력\n{'='*62}")
    print(f"  태양광   {S:9.2f} W/m2   (서울 {SEOUL_KWH_PER_KW_DAY} kWh/kW/일, 패널 {PANEL_KW_PER_M2*1000:.0f} W/m2)")
    print(f"  소형풍력 {W:9.2f} W/m2   (풍속 {a.wind_speed} m/s, Cp {0.35})")
    print(f"  압전     {P:9.4f} W/m2   (타일 {PIEZO_TILES_PER_M2}장 x {PIEZO_MW_PER_TILE} mW)")
    print(f"\n  태양광 : 풍력 : 압전 = {S/P:,.0f} : {W/P:,.0f} : 1")
    print(f"  → 같은 전력을 얻으려면 압전은 태양광의 약 {S/P:,.0f}배 면적이 필요하다.")

    print(f"\n{'='*62}\n  부하별 — 자급자족에 필요한 발전 면적\n{'='*62}")
    print(f"  {'부하':<22}{'평균W':>8}{'태양광':>10}{'풍력':>10}{'압전타일':>12}")
    rows = []
    for name, rated, hrs in LOADS:
        avg = rated * hrs / 24
        a_s, a_w = avg / S, avg / W
        tiles = avg / (PIEZO_MW_PER_TILE / 1000)
        rows.append((name, avg, a_s, a_w, tiles))
        ts = f"{tiles/1000:,.0f}천장" if tiles >= 1000 else f"{tiles:,.0f}장"
        print(f"  {name:<22}{avg:>8.0f}{a_s:>9.1f}㎡{a_w:>9.1f}㎡{ts:>12}")

    print(f"\n{'='*62}\n  판정\n{'='*62}")
    for name, avg, a_s, a_w, tiles in rows:
        if a_s <= 3:
            v = "✅ 자급자족 쉽다 (정류장 지붕 한 칸)"
        elif a_s <= 20:
            v = "🟡 가능하다 (전용 패널 설치 필요)"
        elif a_s <= 100:
            v = "🟠 어렵다 (주차장 캐노피 규모 + 축전지)"
        else:
            v = "🔴 국소 분산전원으로는 무리 (계통 전력 필요)"
        print(f"  {name:<22} 태양광 {a_s:6.1f} ㎡  {v}")

    if a.solar_area > 0:
        tot = S * a.solar_area
        print(f"\n  [보유 패널 {a.solar_area} ㎡ = 평균 {tot:.0f} W]")
        for name, avg, *_ in rows:
            n = tot / avg
            if n >= 1:
                print(f"    {name:<22} {n:5.1f}개 동시 운용 가능")
            else:
                print(f"    {name:<22} 부족 (필요량의 {n*100:.0f}%)")
    print()

    if a.plot:
        import matplotlib; matplotlib.use("Agg")
        import _plotfont  # noqa
        import matplotlib.pyplot as plt
        import numpy as np
        fig, ax = plt.subplots(1, 3, figsize=(14, 4.2))
        ax[0].bar(["태양광", "소형풍력", "압전"], [S, W, P],
                  color=["#f5a623", "#4a90d9", "#d0021b"])
        ax[0].set_yscale("log")
        for i, v in enumerate([S, W, P]):
            ax[0].text(i, v * 1.3, f"{v:.3g} W", ha="center", fontsize=10)
        ax[0].set(ylabel="1 ㎡당 평균 전력 [W] — 로그 눈금",
                  title="발전원 비교 (세로축이 로그다)")
        ax[0].grid(axis="y", lw=.3, alpha=.4, which="both")

        nm = [r[0] for r in rows]; need = [r[2] for r in rows]
        c = ["#2ca02c" if x <= 3 else "#f5a623" if x <= 20 else "#ff7f0e" if x <= 100 else "#d62728"
             for x in need]
        ax[1].barh(nm, need, color=c); ax[1].set_xscale("log")
        for i, v in enumerate(need):
            ax[1].text(v * 1.15, i, f"{v:,.1f}㎡", va="center", fontsize=8)
        ax[1].axvline(3, color="#2ca02c", ls="--", lw=1)
        ax[1].text(3, -0.85, "정류장 지붕 크기", fontsize=8, color="#2ca02c", ha="center")
        ax[1].set(xlabel="필요한 태양광 면적 [㎡] — 로그 눈금", title="부하별 필요 면적",
                  ylim=(-1.4, len(nm) - 0.4))
        ax[1].tick_params(labelsize=8); ax[1].grid(axis="x", lw=.3, alpha=.4, which="both")

        vs = np.linspace(1, 8, 60)
        ax[2].plot(vs, [wind_w_per_m2(v) for v in vs], color="#4a90d9", lw=2, label="소형풍력")
        ax[2].axhline(S, color="#f5a623", lw=2, ls="--", label=f"태양광 {S:.0f} W/㎡")
        ax[2].axvline(a.wind_speed, color="#888", ls=":", lw=1)
        v_eq = (S / (0.5 * RHO * 0.35)) ** (1/3)
        ax[2].plot([v_eq], [S], "o", color="#d62728", ms=8)
        ax[2].annotate(f"풍속 {v_eq:.1f} m/s 는 돼야\n태양광과 같아진다",
                       (v_eq, S), textcoords="offset points", xytext=(-100, 12),
                       fontsize=8.5, color="#d62728")
        ax[2].set(xlabel="풍속 [m/s]", ylabel="1 ㎡당 평균 전력 [W]",
                  title="도심 풍력이 불리한 이유 (전력 ∝ 풍속³)")
        ax[2].legend(fontsize=8); ax[2].grid(lw=.3, alpha=.4)
        fig.suptitle("에너지 자립형 교통 인프라 — 어디까지 되나", y=1.02)
        fig.tight_layout(); fig.savefig(a.plot, dpi=130, bbox_inches="tight")
        print(f"  그래프 저장: {a.plot}\n")


if __name__ == "__main__":
    main()
