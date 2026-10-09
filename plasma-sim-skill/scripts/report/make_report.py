import base64, json, html, os
from pathlib import Path
B = Path(os.environ.get("PLASMA_SIM_DIR", Path.home() / "plasma_sim"))
img = lambda p: "data:image/png;base64," + base64.b64encode(Path(p).read_bytes()).decode()
E = B/"ccp_run/figs"
K = json.load(open(E/"key.json"))
INF = {l.split("=")[0].strip(): l.split("=")[1].split("[")[0].strip() for l in open(B/"ccp_run/info.txt") if "=" in l}
ER = dict(pe=f"{float(INF['Electron power density (average)']):.3e} W/m³", pi=f"{float(INF['Ion power density (average)']):.3e} W/m³", ji=f"{float(INF['Ion flux at powered electrode'])*1.602e-19:.2f} A/m²", ee=f"{K['Ee_bulk_eV']:.2f} eV", ei=f"{K['Ei_local_max_eV']:.1f} eV", nc=f"{K['n_center_m3']:.2e} m⁻³ ({K['n_center_m3']/1e6:.1e} cm⁻³)", sh=f"{K['smax_pow_mm']:.1f} mm", if_=f"{K['IFED_mean_eV']:.1f} eV")
S = json.load(open(B/"icp/study.json")); S2 = json.load(open(B/"icp/study2.json")); CV = json.load(open(B/"icp/conv_test.json"))
sw = S["sweep"]; pl, he = S2["planar"], S2["helical"]
def row(*c): return "<tr>" + "".join(f"<td>{x}</td>" for x in c) + "</tr>"
sweep_rows = "".join(row(f"{p} mTorr", f"{rs[0]['Te']:.2f}", *[f"{x['n0']/1e6:.2e}" for x in rs if x['P'] in (80, 200, 500, 1200)],
                         *[f"{x['eta']*100:.0f}%" for x in rs if x['P'] in (500,)]) for p, rs in sw.items())
conv_rows = "".join(row(f"{c['dx_mm']:.1f} mm", f"{c['cells']:,}", f"{c['n0']/1e6:.3e}", f"{c['Rp']:.3f}", f"{c['eta']*100:.1f}%", f"{c['L_uH']:.3f}", f"{c['sec']:.1f} s") for c in CV)
des_rows = "".join(row(k, ", ".join(f"{x*100:g}" for x in d["coil"]), f"{d['n0']/1e6:.2e}", f"{d['Rp']:.2f}", f"{d['eta']*100:.0f}%", f"{d['I']:.1f}") for k, d in S["designs"].items())

CSS = """body{font:15.5px/1.7 -apple-system,'Noto Sans KR','Nanum Gothic',sans-serif;color:#18202a;margin:0;background:#fff}
.w{max-width:1000px;margin:0 auto;padding:46px 26px 90px}h1{font-size:28px;margin:0 0 6px}h2{font-size:21px;margin:44px 0 8px;border-bottom:2px solid #18202a;padding-bottom:5px}
h3{font-size:17px;margin:26px 0 6px}.sub{color:#5a6570;font-size:14px}table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px}
th,td{border-bottom:1px solid #dde2e7;padding:6px 9px;text-align:right}th:first-child,td:first-child{text-align:left}th{background:#f3f5f7}
.eq{background:#f6f8fa;border-left:3px solid #3b6ea5;padding:10px 14px;font-family:'DejaVu Sans Mono',monospace;font-size:13.5px;white-space:pre-wrap;margin:10px 0}
.box{border:1px solid #dde2e7;border-left:4px solid #3b6ea5;padding:12px 16px;margin:16px 0;background:#fbfcfd}.warn{border-left-color:#b3261e;background:#fff7f6}
.ok{border-left-color:#1b7f3b;background:#f6fbf7}figure{margin:16px 0}figure img{width:100%;border:1px solid #e3e7eb}figcaption{font-size:13px;color:#5a6570;margin-top:5px}
code{background:#f1f3f5;padding:1px 5px;border-radius:3px;font-size:13px}.k{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:18px 0}
.k div{border:1px solid #dde2e7;border-radius:6px;padding:10px 12px}.k b{display:block;font-size:20px}.k span{font-size:12.5px;color:#5a6570}
ol li,ul li{margin:4px 0}@media print{.w{padding:0}h2{page-break-after:avoid}figure{page-break-inside:avoid}}"""

H = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>오픈소스 기반 ICP 플라즈마 소스 설계·해석 보고서</title><style>{CSS}</style></head><body><div class="w">
<h1>오픈소스 기반 ICP 플라즈마 소스 설계·해석</h1>
<div class="sub">13.56 MHz 아르곤 ICP · 2D 축대칭 전자기 + 글로벌 모델 자기일관 결합 · Meep FDTD 교차검증 · eduPIC PIC/MCC 재현 · 2026-10-10 · {os.environ.get('REPORT_AUTHOR', '')}</div>

<div class="box"><b>요지.</b> 상용 HFSS 대신 무료 도구로 ICP 소스를 설계·해석했다. (1) 자체 작성 2D 축대칭 A<sub>φ</sub> 주파수영역 해석기와
아르곤 글로벌 모델을 변압기 결합으로 묶어 RF 전력만으로 n<sub>0</sub>, T<sub>e</sub>, R<sub>p</sub>, 결합효율, 코일전류, 인덕턴스, 매칭 커패시터를 자기일관으로 구한다.
(2) 전자기장 부분은 오픈소스 FDTD(Meep 1.34, 원통좌표 m=0, Drude 매질)로 독립 검증했다. (3) 입자 수준 PIC/MCC 코드 eduPIC으로 원 논문의 CCP 기준 사례를 재현했다(전자·이온 흡수 전력 0.2·0.7% 차).
<b>밀도 분포의 형상은 가정</b>(확산 기본모드)했고 크기만 자기일관이므로, 웨이퍼 균일도 예측에는 쓰지 않는다. 회사 장비 조건은 사용하지 않았다.</div>

<div class="k"><div><b>{pl['n0']/1e6:.2e}</b><span>n₀ (cm⁻³) · 10 mTorr, 500 W</span></div><div><b>{sw['10'][0]['Te']:.2f} eV</b><span>T<sub>e</sub> (입자 균형)</span></div>
<div><b>{pl['Rp']:.2f} Ω · {pl['eta']*100:.0f}%</b><span>R<sub>p</sub> · 결합효율 (R<sub>coil</sub>=0.6 Ω 가정)</span></div><div><b>{pl['Cs_pF']:.0f} / {pl['Cp_pF']:.0f} pF</b><span>L-매칭 직렬/병렬 C (50 Ω)</span></div></div>

<h2>1. 대상과 조건</h2>
<ul><li>원통 챔버 R = 15 cm, H = 10 cm(척 z=0, 접지), 석영 창 2 cm(ε<sub>r</sub>=3.8), 금속 측벽 6 mm, 전체를 접지 차폐함(r 22 cm × z 20 cm)으로 둘러쌈.</li>
<li>평면 코일: 동심 링 4개(r = 3, 6, 9, 12 cm), 단면 6 mm 정사각, 창 위 8 mm, 직렬(동일 전류). 헬리컬 비교안: 측벽을 석영관으로 바꾸고 관 바깥 r=18.1 cm에 4턴.</li>
<li>Ar, T<sub>gas</sub>=300 K, 13.56 MHz, R<sub>coil</sub>=0.6 Ω(코일·배선 저항, 가정값).</li></ul>

<h2>2. 방법</h2>
<h3>2.1 전자기: 축대칭 A<sub>φ</sub> 헬름홀츠 방정식 (e<sup>jωt</sup>)</h3>
<div class="eq">(1/r)∂/∂r(r ∂A/∂r) − A/r² + ∂²A/∂z² + k₀² ε(r,z) A = −μ₀ J_coil
E_φ = −jω A,      ε_plasma = 1 − ω_pe² / [ω(ω − jν_m)],      σ = ε₀ ω_pe² / (ν_m + jω)
p_abs(r,z) = ½ Re(σ)|E_φ|²,   P_abs = ∫ p_abs 2πr dr dz,   R_p = 2P_abs / I²   (I: 코일 피크전류)</div>
<ul><li>이산화: 균일 격자 2 mm(기본), r 방향은 r±dr/2 면 플럭스를 쓰는 보존형 5점 차분. 축(r=0), 금속, 계산영역 바깥 칸은 A=0(디리클레).</li>
<li>코일 각 링은 단면 격자 셀에 균일 전류밀도로 정확히 I가 흐르도록 정규화. 희소 복소 직접해(SciPy SuperLU), 11,211 미지수, 1회 해 ≈0.15 s.</li>
<li>k₀² 항은 13.56 MHz에서 형상 대비 무시할 만하나 그대로 포함. 정전(용량성) 결합은 이 m=0 TE 정식화에 없다.</li></ul>

<h3>2.2 글로벌 모델 (Lieberman &amp; Lichtenberg 2판, 3·10장)</h3>
<div class="eq">입자 균형:  K_iz(T_e) n_g V = u_B(T_e) A_eff      →  T_e  (전력과 무관)
전력 균형:  P_abs = e n₀ u_B A_eff E_T(T_e)            →  n₀
A_eff = 2πR² h_L + 2πRH h_R,  h_L = 0.86/(3+H/2λ_i)^½,  h_R = 0.80/(4+R/λ_i)^½,  λ_i = 1/(n_g σ_i), σ_i = 1×10⁻¹⁸ m²
E_T = E_c + 2T_e + 5.2T_e,   E_c = 15.76 + (K_ex/K_iz)·12.14 + (K_el/K_iz)(3m/M)T_e
K_iz = 2.34e-14 T_e^0.59 e^(−17.44/T_e),  K_ex = 2.48e-14 T_e^0.33 e^(−12.78/T_e),
K_el = 2.336e-14 T_e^1.609 exp(0.0618 ln²T_e − 0.1171 ln³T_e)   [m³/s, T_e in eV]
ν_m ≈ n_g (K_el + K_ex + K_iz)</div>

<h3>2.3 결합(변압기 모델)과 반복</h3>
<div class="eq">P_abs = P_rf · R_p(n₀) / (R_p(n₀) + R_coil)
n_e(r,z) = n₀ · J₀(2.405 r/R) · sin(πz/H)      ← 형상 가정(최저 확산 모드), 크기 n₀만 미지수
반복:  n₀ → EM 해 → R_p → P_abs → 글로벌 → n₀_new,  로그공간 0.5 감쇠,  |Δn/n| &lt; 2×10⁻³ 수렴 (보통 10–15회, 약 2 s)</div>
<p>R<sub>p</sub>가 n₀에 대해 단조증가 후 포화(표피효과)하므로, 해가 존재하려면 P<sub>rf</sub>가 문턱 이상이어야 한다 → <b>유지 최소 전력</b>(H-모드 문턱)이 자연스럽게 나온다. E-모드(용량성) 방전은 모델에 없으므로 문턱 아래는 "해 없음"으로만 해석한다.</p>

<h3>2.4 인덕턴스와 매칭</h3>
<div class="eq">¼ L I² = ¼ ∫ |B|²/μ₀ dV,   B_r = −∂A/∂z,  B_z = (1/r)∂(rA)/∂r
Z_load = (R_p + R_coil) + jωL,   L-매칭(발전기측 병렬 C_p, 코일측 직렬 C_s):  Q = (R₀/R − 1)^½,  X_s = QR − X_L,  X_p = R₀/Q</div>

<h2>3. 결과</h2>
<h3>3.1 기준점 — 10 mTorr, 500 W, 평면 코일</h3>
<figure><img src="{img(B/'icp/fig1_fields.png')}"><figcaption>그림 1. 좌: 자기일관 n<sub>e</sub>(형상 가정). 중: |E<sub>φ</sub>|. 우: 흡수 전력밀도(로그). 창 아래 도넛형 표피층 가열. 표피깊이는 콜드플라즈마식 1/Im(k)로 1.2 cm.</figcaption></figure>

<h3>3.2 운전 곡선 — 유지 최소 전력과 결합효율</h3>
<figure><img src="{img(B/'icp/fig2_curves.png')}"><figcaption>그림 2. 압력 5·10·30 mTorr. n₀가 전력 문턱 아래에서 급락(해 없음 영역). 압력 증가 → ν 증가 → R<sub>p</sub>·효율 증가, 문턱 감소.</figcaption></figure>
<table><tr><th>압력</th><th>T<sub>e</sub> (eV)</th><th>n₀ @80 W</th><th>@200 W</th><th>@500 W</th><th>@1200 W</th><th>효율 @500 W</th></tr>{sweep_rows}</table>

<h3>3.3 평면 코일 배치 비교</h3>
<figure><img src="{img(B/'icp/fig3_coils.png')}"><figcaption>그림 3. 창 아래 1 cm 흡수전력의 반경분포와 결합효율. 바깥 배치가 효율·가장자리 가열 모두 유리.</figcaption></figure>
<table><tr><th>배치</th><th>링 반경 (cm)</th><th>n₀ (cm⁻³)</th><th>R<sub>p</sub> (Ω)</th><th>효율</th><th>I (A)</th></tr>{des_rows}</table>

<h3>3.4 평면 vs 헬리컬, 진공장 vs 플라즈마 부하장, 매칭</h3>
<figure><img src="{img(B/'icp/fig4_webinar_compare.png')}"><figcaption>그림 4. 상용 툴 웨비나(Singularity Engineering, 2020)는 빈 진공 챔버의 장 균일도만 본다. 평면 코일은 창 아래 1 cm에서 진공장과 부하장이 거의 같지만, 헬리컬은 플라즈마 부하 시 가장자리 3–4 cm에 가열이 갇혀 진공장 기반 판단이 중심 가열을 과대평가한다.</figcaption></figure>
<table><tr><th></th><th>평면</th><th>헬리컬</th></tr>
{row("L 코일 단독 (µH)", f"{pl['L_free_uH']:.2f}", f"{he['L_free_uH']:.2f}")}{row("L 빈 챔버 (µH)", f"{pl['L_vac_uH']:.2f}", f"{he['L_vac_uH']:.2f}")}
{row("L 플라즈마 부하 (µH)", f"{pl['L_plasma_uH']:.2f}", f"{he['L_plasma_uH']:.2f}")}{row("Z_load", pl['Z'], he['Z'])}
{row("R_p (Ω) / 효율", f"{pl['Rp']:.2f} / {pl['eta']*100:.0f}%", f"{he['Rp']:.2f} / {he['eta']*100:.0f}%")}{row("n₀ (cm⁻³)", f"{pl['n0']/1e6:.2e}", f"{he['n0']/1e6:.2e}")}
{row("매칭 직렬 C_s / 병렬 C_p (pF)", f"{pl['Cs_pF']:.0f} / {pl['Cp_pF']:.0f}", f"{he['Cs_pF']:.0f} / {he['Cp_pF']:.0f}")}</table>
<p>챔버 금속에 의한 이미지 전류로 L이 8–9% 감소하고, 플라즈마(변압기 2차측) 부하로 추가 5–6% 감소한다. 코일 단독값으로 매칭을 잡으면 운전점에서 어긋난다.</p>

<h2>4. 독립 검증 — Meep FDTD</h2>
<p>같은 형상을 Meep 1.34(원통좌표 m=0, 금속 경계, 균일 Drude 플라즈마 f<sub>p</sub>, γ=ν/2π, ν=3.2×10⁷ s⁻¹)로 시간영역 계산했다. 코일은 E<sub>φ</sub> 링 전류원, 3주기 램프 후 1주기 24위상을 저장하고
<b>13.56 MHz 푸리에 성분</b>만으로 진폭을 구한다(최대값 사용 시 과도성분이 섞여 오판했던 것을 확인함).</p>
<figure><img src="{img(B/'meep/meep_fig1_maps.png')}"><figcaption>그림 5. 밀도 10⁹–10¹² cm⁻³에서 유도장 침투. 밀도 증가에 따라 창 아래로 갇힘.</figcaption></figure>
<figure><img src="{img('val_meep_pointwise.png')}"><figcaption>그림 6. r = 8 cm 깊이분포의 점대점 비교. 10¹¹: 해상도 5·10 모두 0–3 cm에서 이론과 일치. 10¹²: 해상도 5는 1 cm까지 일치 후 ~1% 잡음바닥, 해상도 10은 0.6 cm 이후 이탈하고 ~10% 바닥 — <b>미해결 수치 문제</b>.</figcaption></figure>
<div class="box warn"><b>정정 2건.</b> (1) 초기 ICP 보고에서 표피깊이를 √(2/ωμ₀Reσ)로 2.8 cm라 했으나, 이 식은 ν≫ω에서만 유효하다. 10 mTorr는 ν(3.2×10⁷) &lt; ω(8.5×10⁷)이므로 콜드플라즈마 1/Im(k)=1.2 cm가 맞다(장 해 자체는 복소 σ를 써서 영향 없음).
(2) Meep 감쇠를 단일 지수맞춤 길이로 보고했을 때 1.72 vs 1.76 cm처럼 "정확히 일치"했지만, 맞춤 구간에 따라 크게 변했다. 근거리장 기하감쇠·바닥 반사가 섞여 순수 지수가 아니므로 점대점 비교(그림 6)를 기준으로 삼는다.</div>

<h2>5. 수치 수렴</h2>
<table><tr><th>격자</th><th>셀 수</th><th>n₀ (m⁻³)</th><th>R<sub>p</sub> (Ω)</th><th>효율</th><th>L (µH)</th><th>시간</th></tr>{conv_rows}</table>
<p>n₀·R<sub>p</sub>·효율은 1–2% 이내. L은 ±4%로 비단조 — 코일 단면(6 mm)의 계단 근사가 지배하므로 격자 감소로 줄지 않는다. 수렴 시험 중 격자 3 mm에서 바깥 경계가 금속으로 지정되지 않는 <b>경계 처리 버그</b>를 발견·수정했다(2 mm 결과는 경계가 정확히 맞아 영향 없음).</p>

<h2>6. 입자 시뮬레이션 — eduPIC 기준 사례 재현</h2>
<p>eduPIC(Donkó et al., PSST 30, 095017, 2021) C++ 판을 수정 없이 컴파일(g++ -O3)해 논문 표 2의 기본 사례를 돌렸다:
1D3V 정전 PIC/MCC, Ar, 평행판 CCP L=25 mm, p=10 Pa, T<sub>g</sub>=350 K, 13.56 MHz, V<sub>0</sub>=250 V, 격자 400, 주기당 4000 스텝, 초입자 가중 7×10⁴.
초기화 → 1500주기 수렴 → 200주기 측정(논문은 측정 1000주기). 총 4.7시간(단일 코어).
안정성 지표 ω<sub>pe</sub>Δt=0.090, Δx/λ<sub>D</sub>=0.72, ν<sub>e</sub>Δt=0.013, ν<sub>i</sub>Δt<sub>i</sub>=0.020 — 모두 코드 기준 이내.
양 전극의 이온·전자 플럭스가 0.4% 안에서 일치해 정상상태로 판단했다.</p>
<table><tr><th>항목</th><th>논문 (Donkó 2021)</th><th>본 실행</th><th>비고</th></tr>
<tr><td>시공간 평균 전자 흡수 전력</td><td>1.58×10³ W/m³</td><td>{ER["pe"]}</td><td>0.2% 차</td></tr>
<tr><td>시공간 평균 이온 흡수 전력</td><td>3.28×10³ W/m³</td><td>{ER["pi"]}</td><td>0.7% 차</td></tr>
<tr><td>전극 이온 전류밀도</td><td>≈0.4 A/m²</td><td>{ER["ji"]}</td><td>eΓ<sub>i</sub></td></tr>
<tr><td>벌크 전자 평균에너지</td><td>1.5–2 eV</td><td>{ER["ee"]}</td><td>중앙 ±0.6 mm, n<sub>e</sub> 가중</td></tr>
<tr><td>전극 부근 이온 평균에너지 최대</td><td>≈20 eV</td><td>{ER["ei"]}</td><td>국부 평균(⟨ε<sub>i</sub>⟩<sub>x,t</sub>)</td></tr>
<tr><td>수렴 주기</td><td>≈1500</td><td>1500</td><td>초입자 수 정체</td></tr>
<tr><td>중앙 전자밀도</td><td>(그림 10, 수치 미기재)</td><td>{ER["nc"]}</td><td>info.txt</td></tr>
<tr><td>최대 시스 폭</td><td>(그림 11 회색선)</td><td>{ER["sh"]}</td><td>Brinkmann 기준, 양측 대칭</td></tr>
<tr><td>이온 플럭스-에너지 평균 (전극)</td><td>—</td><td>{ER["if_"]}</td><td>IFEDF 1차 모멘트</td></tr></table>
<p>논문이 수치로 밝힌 항목은 모두 1% 이내 또는 범위 안에 들어와, 도구 설치와 실행 절차가 원 논문을 재현함을 확인했다.</p>
<figure><img src="{img(E/'p1_density.png')}"><figcaption>그림 7. 좌: 초입자 수 수렴 이력(1500주기 이후 측정). 우: 시간평균 n<sub>e</sub>, n<sub>i</sub>. 회색은 최대 시스 영역.</figcaption></figure>
<figure><img src="{img(E/'p2_eepf_ifed.png')}"><figcaption>그림 8. 좌: 방전 중앙 시간평균 EEPF — 저에너지 차가운 전자군과 고에너지 꼬리의 두 온도 구조(저압 Ar CCP의 전형). 우: 양 전극 IFEDF — 시스 내 전하교환 충돌에 의한 봉우리열, 대칭 방전이라 두 전극이 일치.</figcaption></figure>
<figure><img src="{img(E/'p3_xt.png')}"><figcaption>그림 9. 한 RF 주기의 시공간 분포(전자밀도, 전위, 전자 흡수 전력, 이온화율)와 시스 경계. 전자 가열은 팽창 시스 가장자리에서 양(+), 수축 시 음(−). 이온화도 팽창 시스 근처에 집중 — α-모드. 논문 그림 11과 같은 구조.</figcaption></figure>

<h2>7. 한계</h2>
<ol><li><b>밀도 형상 가정</b>: 수송(확산·대류·이온 관성)을 풀지 않아 균일도·국부 가열 효과(비국소 전자수송) 반영 불가.</li>
<li>T<sub>e</sub> 공간 균일, Maxwellian EEDF, 단일 ν<sub>m</sub>. 저압에서 비충돌(확률적) 가열 미포함 → 5 mTorr 이하에서 R<sub>p</sub> 과소평가 가능.</li>
<li>E-모드(용량성 결합)·E–H 히스테리시스 미포함. 코일 정전용량·자기공진 미포함.</li>
<li>코일을 동심 링으로 근사(나선의 방위각 비대칭은 3D 필요). R<sub>coil</sub>=0.6 Ω 가정, 매칭 회로 기생성분 무시.</li>
<li>Meep 고밀도(10¹²) 고해상도 이탈 원인 미해결. 가스 가열·준안정 단계 이온화 미포함.</li>
<li>eduPIC는 1D CCP 기준 사례 재현이며 ICP 모델과 직접 결합하지 않았다(검증 대상이 다름). 2차전자방출·표면반응 미포함(원 코드 사양).</li></ol>

<h2>8. 전문가께 여쭙고 싶은 점</h2>
<ol><li>밀도 형상을 가정하는 변압기 모델 + 2D 장 해석의 조합이, 설계 초기의 코일 배치·매칭 선정 용도로 어디까지 쓸 만한지.</li>
<li>5 mTorr 이하에서 비충돌 가열을 넣는 가장 실용적인 근사(유효 충돌주파수 ν<sub>eff</sub> = ν<sub>m</sub> + ν<sub>stoc</sub> 등)는 무엇이 적절한지.</li>
<li>다음 단계로 유체 수송(드리프트-확산 + 전자 에너지식)을 붙일 때 추천하는 오픈소스(Zapdos/MOOSE 등) 또는 검증 사례.</li>
<li>Meep 10¹² cm⁻³ 고해상도 결과의 가짜 바닥 원인(드루드 분산 FDTD의 저주파 안정성, 램프 시간 부족 등)에 대한 견해.</li></ol>

<h2>9. 재현</h2>
<div class="eq">~/plasma_sim/icp/icp_source.py        자기일관 ICP 모델 (Geometry, solve_em, operate, inductance, l_match)
~/plasma_sim/icp/study.py · study2.py · conv_test.py · figs.py
~/plasma_sim/meep/icp_meep.py  &lt;n_e cm⁻³&gt; &lt;out.npz&gt; [res]     (Meep 1.34, micromamba env)
~/plasma_sim/ccp_run/   eduPIC:  ./eduPIC 0 ; ./eduPIC 1500 ; ./eduPIC 200 m ; python3 figs.py
의존성: Python 3.12, NumPy, SciPy, Matplotlib / Meep 1.34(conda-forge pymeep) / g++ -O3 (eduPIC)</div>

<h2>참고</h2>
<ol><li>M. A. Lieberman, A. J. Lichtenberg, <i>Principles of Plasma Discharges and Materials Processing</i>, 2nd ed., Wiley (2005), ch. 3, 10, 12.</li>
<li>A. F. Oskooi et al., "MEEP: A flexible free-software package for electromagnetic simulations by the FDTD method," <i>Comput. Phys. Commun.</i> 181, 687 (2010).</li>
<li>Z. Donkó et al., "eduPIC: an introductory particle based code for radio-frequency plasma simulation," <i>Plasma Sources Sci. Technol.</i> 30, 095017 (2021). github.com/donkozoltan/eduPIC</li>
<li>Singularity Engineering, "RF coil for plasma system with ANSYS HFSS" (webinar, 2020).</li></ol>
</div></body></html>"""
Path("ICP_plasma_opensource_report.html").write_text(H, encoding="utf-8")
print("written", round(len(H)/1024), "KB")
