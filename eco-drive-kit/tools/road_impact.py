"""도로 영향평가(안) — 공공도로를 없앨 때의 영향을 점수로 만든다.

왜 필요한가:
  현행 교통영향평가(도시교통정비 촉진법)의 대상은 도로의 '건설'이다.
  도로를 '없애는' 행위는 대상 범위에 뚜렷하게 들어 있지 않다.
  그래서 재건축 과정에서 공공도로가 사라져도 교통 영향을 정량 평가할 법적 장치가 약하다.
  이 프로그램은 그 빈칸을 메우는 평가표를 제안하고, 실제로 계산해 본 것이다.

무엇을 내놓는가:
  1) 항목별 점수와 총점, 그에 따른 '경미한 변경 / 중요 변경' 자동 판정
  2) 우회로 때문에 늘어나는 주행거리를 연간 CO2 로 환산
  3) 보행자가 더 걷게 되는 시간 (스쿨존이면 가중)

배점은 '우리가 제안하는 안'이다. 정답이 아니다.
WEIGHTS 를 바꿔서 결과가 얼마나 흔들리는지 보고, 그 민감도를 보고서에 적어라.

usage: python road_impact.py --template ../data/road_template.csv
       python road_impact.py ../data/road_hyoryeong.csv --plot ../figs/road.png
"""
import argparse, csv, sys

CO2_PER_KM = 0.192          # kg-CO2/km, 휘발유 승용차 대표값 (연비 12 km/L x 2.31 kg/L)
WALK_SPEED = 1.2            # m/s, 보행 속도
DAYS = 365

# 제안 배점 — 합계 100점. 바꿔가며 민감도를 확인해라.
WEIGHTS = dict(
    veh_volume=25,          # 차량 통행량
    ped_volume=20,          # 보행 통행량
    detour=20,              # 우회 거리 증가
    school=15,              # 스쿨존 / 통학로
    alt_route=10,           # 대체 경로 부족
    facility=10,            # 주변 생활시설 접근성
)
THRESHOLD_MAJOR = 50        # 이 점수 이상이면 '중요 변경'으로 분류하자는 제안

FIELDS = [
    ("road_name", "평가 대상 도로 이름", "OO로 OO길"),
    ("length_m", "폐도 구간 길이 [m]", 200),
    ("veh_per_hr", "첨두시 차량 통행량 [대/시] (15분 세서 x4)", 300),
    ("ped_per_hr", "첨두시 보행자 [명/시] (15분 세서 x4)", 200),
    ("detour_m", "우회로 추가 거리 [m] (지도 거리재기)", 400),
    ("is_school_zone", "스쿨존이면 1, 아니면 0", 1),
    ("school_users_per_day", "이 길로 통학하는 학생 수 [명/일] (추정)", 150),
    ("alt_route_count", "대체 경로 개수 (0이면 유일한 길)", 1),
    ("facility_count", "도보 5분 내 생활시설 수 (정류장·상가·병원 등)", 4),
    ("notified", "주민에게 사전 고지되었으면 1, 아니면 0", 0),
]


def make_template(path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["field", "설명", "값"])
        for k, desc, ex in FIELDS:
            w.writerow([k, desc, ex])
    print(f"평가 양식을 만들었다: {path}")
    print("  '값' 칸의 예시 숫자를 너희가 직접 조사한 값으로 바꿔라.")
    print("  통행량은 반드시 직접 세라 - 그게 이 제도 제안의 핵심 근거다.")


def load(path):
    d = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            k = (r.get("field") or "").strip()
            v = (r.get("값") or r.get("value") or "").strip()
            if not k:
                continue
            d[k] = v
    out = {}
    for k, desc, _ in FIELDS:
        if k == "road_name":
            out[k] = d.get(k, "이름없음")
            continue
        try:
            out[k] = float(d.get(k, 0) or 0)
        except ValueError:
            sys.exit(f"'{k}' 값이 숫자가 아니다: {d.get(k)!r}")
    return out


def sat(x, full):
    """0~1 로 포화시킨다. full 이면 만점."""
    return min(1.0, max(0.0, x / full)) if full > 0 else 0.0


def score(d):
    s = {}
    s["veh_volume"] = WEIGHTS["veh_volume"] * sat(d["veh_per_hr"], 500)
    s["ped_volume"] = WEIGHTS["ped_volume"] * sat(d["ped_per_hr"], 400)
    s["detour"] = WEIGHTS["detour"] * sat(d["detour_m"], 500)
    s["school"] = WEIGHTS["school"] * (1.0 if d["is_school_zone"] >= 1 else sat(d["school_users_per_day"], 200))
    s["alt_route"] = WEIGHTS["alt_route"] * (1.0 if d["alt_route_count"] <= 0 else sat(2 - d["alt_route_count"], 2))
    s["facility"] = WEIGHTS["facility"] * sat(d["facility_count"], 6)
    return s


def impact(d):
    """우회로가 만드는 실제 부담."""
    det_km = d["detour_m"] / 1000
    veh_day = d["veh_per_hr"] * 12                       # 첨두시 기준 x12시간 (보수적 가정)
    co2_yr = det_km * veh_day * DAYS * CO2_PER_KM / 1000  # 톤/년
    walk_sec = d["detour_m"] / WALK_SPEED
    ped_day = d["ped_per_hr"] * 12
    walk_hr_yr = walk_sec * ped_day * DAYS / 3600
    return dict(det_km=det_km, veh_day=veh_day, co2_yr=co2_yr,
                walk_sec=walk_sec, ped_day=ped_day, walk_hr_yr=walk_hr_yr,
                school_sec_day=walk_sec * d["school_users_per_day"] * 2 / 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?"); ap.add_argument("--template")
    ap.add_argument("--plot")
    a = ap.parse_args()
    if a.template:
        make_template(a.template); return
    if not a.csv:
        sys.exit("CSV 경로를 주거나 --template 을 써라.")

    d = load(a.csv)
    s = score(d)
    total = sum(s.values())
    imp = impact(d)

    print(f"\n{'='*58}\n  도로 영향평가(안) — {d['road_name']}\n{'='*58}")
    print(f"\n[항목별 점수]  (제안 배점, 합계 100)")
    KO = dict(veh_volume="차량 통행량", ped_volume="보행 통행량", detour="우회 거리 증가",
              school="스쿨존·통학로", alt_route="대체 경로 부족", facility="생활시설 접근성")
    for k, v in s.items():
        bar = "█" * int(v / 2) + "·" * int((WEIGHTS[k] - v) / 2)
        print(f"  {KO[k]:<14} {v:5.1f} / {WEIGHTS[k]:<3}  {bar}")
    print(f"  {'총점':<14} {total:5.1f} / 100")

    verdict = "중요 변경" if total >= THRESHOLD_MAJOR else "경미한 변경"
    print(f"\n[자동 분류]  {total:.1f}점 → 제안 기준 {THRESHOLD_MAJOR}점 → **{verdict}**")
    if verdict == "중요 변경":
        print("  → 공청회·직접 고지·이의제기 기간이 의무화되어야 하는 사안.")
    if d["notified"] < 1:
        print("  ※ 그런데 실제로는 주민 사전 고지가 없었다고 기록되어 있다.")

    print(f"\n[우회로가 만드는 실제 부담]")
    print(f"  차량: 1대당 {imp['det_km']*1000:.0f} m 추가 × 하루 {imp['veh_day']:,.0f}대")
    print(f"        → 연간 추가 CO2  {imp['co2_yr']:.1f} 톤")
    print(f"  보행: 1인당 {imp['walk_sec']:.0f}초 추가 × 하루 {imp['ped_day']:,.0f}명")
    print(f"        → 연간 추가 보행시간 {imp['walk_hr_yr']:,.0f} 시간")
    if d["is_school_zone"] >= 1:
        print(f"  통학: 학생 1명당 매일 왕복 {imp['walk_sec']*2/60:.1f}분 추가 "
              f"(학생 {d['school_users_per_day']:.0f}명 합계 하루 {imp['school_sec_day']/60:.1f}시간)")
        print(f"        ※ 교육환경보호구역 내 도로였다면 이 항목은 점수가 아니라 '요건'으로 다뤄야 한다")

    print(f"\n[이 평가표의 한계 — 보고서에 반드시 적어라]")
    print(f"  · 배점은 우리가 정한 것이다. 법적 근거가 없다.")
    print(f"  · 통행량 12시간 환산, CO2 {CO2_PER_KM} kg/km 는 가정이다.")
    print(f"  · 우회 중 발생하는 정체 심화는 넣지 않았다 (실제 영향은 이보다 클 수 있다).")
    print(f"  · WEIGHTS 를 바꿔 총점이 {THRESHOLD_MAJOR}점 선을 넘나드는지 확인해라.\n")

    if a.plot:
        import matplotlib; matplotlib.use("Agg")
        import _plotfont  # noqa
        import matplotlib.pyplot as plt
        import numpy as np
        fig, ax = plt.subplots(1, 3, figsize=(13.5, 4.0))
        ks = list(s.keys())
        ax[0].barh([KO[k] for k in ks], [s[k] for k in ks], color="#06c")
        ax[0].barh([KO[k] for k in ks], [WEIGHTS[k] - s[k] for k in ks],
                   left=[s[k] for k in ks], color="#ddd")
        ax[0].set(xlabel="점수", title=f"항목별 점수 (총 {total:.0f}/100)")
        ax[0].tick_params(labelsize=9); ax[0].grid(axis="x", lw=.3, alpha=.4)

        # 민감도: 배점을 ±50% 흔들면 총점이 어디까지 움직이나
        lo = hi = 0.0
        for k in ks:
            frac = s[k] / WEIGHTS[k] if WEIGHTS[k] else 0
            lo += WEIGHTS[k] * 0.5 * frac; hi += WEIGHTS[k] * 1.5 * frac
        ax[1].barh([0], [total], color="#06c", height=.32)
        ax[1].errorbar([total], [0], xerr=[[total - lo], [hi - total]],
                       fmt="none", ecolor="#333", capsize=9, lw=1.6)
        ax[1].axvline(THRESHOLD_MAJOR, color="#d62728", ls="--", lw=1.5)
        ax[1].text(THRESHOLD_MAJOR, -0.78, f"중요변경 기준 {THRESHOLD_MAJOR}점",
                   fontsize=9, color="#d62728", ha="center")
        ax[1].text(total, 0.30, f"{total:.0f}점", fontsize=11, ha="center", color="#06c", weight="bold")
        ax[1].text(lo, -0.30, f"{lo:.0f}", fontsize=8, ha="center", color="#555")
        ax[1].text(hi, -0.30, f"{hi:.0f}", fontsize=8, ha="center", color="#555")
        ax[1].set(xlim=(0, 100), ylim=(-1.0, 0.75), xlabel="총점", yticks=[],
                  title="배점을 ±50% 흔들어도 기준을 넘나?")
        ax[1].grid(axis="x", lw=.3, alpha=.4)

        dets = np.linspace(0, 800, 50)
        co2 = dets / 1000 * imp["veh_day"] * DAYS * CO2_PER_KM / 1000
        ax[2].plot(dets, co2, color="#2ca02c", lw=2)
        ax[2].plot([d["detour_m"]], [imp["co2_yr"]], "o", color="#d62728", ms=9)
        ax[2].annotate(f"{d['road_name']}\n{imp['co2_yr']:.0f} 톤/년",
                       (d["detour_m"], imp["co2_yr"]), textcoords="offset points",
                       xytext=(10, -18), fontsize=9, color="#d62728")
        ax[2].set(xlabel="우회 추가 거리 [m]", ylabel="연간 추가 CO2 [톤]",
                  title="우회가 길어질수록")
        ax[2].grid(lw=.3, alpha=.4)
        fig.suptitle(f"도로 영향평가(안) 적용 — {d['road_name']}", y=1.02)
        fig.tight_layout(); fig.savefig(a.plot, dpi=130, bbox_inches="tight")
        print(f"  그래프 저장: {a.plot}\n")


if __name__ == "__main__":
    main()
