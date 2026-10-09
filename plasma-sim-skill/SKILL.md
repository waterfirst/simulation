---
name: plasma-sim-opensource
description: 상용 HFSS·COMSOL 없이 오픈소스만으로 RF 플라즈마 소스(ICP·CCP)를 설치→설계→해석→교차검증→전문가용 HTML 보고서까지 만든다. 자체 2D 축대칭 전자기(A_φ)+아르곤 글로벌 모델 자기일관 ICP 해석기, Meep FDTD(드루드 플라즈마) 교차검증, eduPIC PIC/MCC 기준사례 재현을 묶었다. 사용자가 "플라즈마 시뮬레이션", "ICP 코일 설계", "HFSS 플라즈마", "COMSOL 대체", "RF 코일 매칭", "표피깊이", "플라즈마 소스 설계", "PIC 시뮬레이션", "eduPIC", "Meep 플라즈마", "CCP 시뮬레이션"을 말하거나 코일 배치·압력·전력을 바꿔 n_e·T_e·효율·매칭 커패시터를 보고 싶을 때 사용한다. Use for open-source plasma source simulation (ICP/CCP), coil design, RF matching, and reports.
---

# 오픈소스 플라즈마 소스 시뮬레이션

세 도구가 서로를 검증하는 구조다. 숫자를 보고할 때는 **어느 도구가 무엇을 가정했는지**를 같이 말한다.

| 단계 | 도구 | 푸는 것 | 가정 |
|---|---|---|---|
| ICP 설계 | `scripts/icp/icp_source.py` (자체) | 2D 축대칭 A_φ + 글로벌 모델, 변압기 결합 반복 → n₀, T_e, R_p, 효율, 코일전류, L, 매칭 C | **밀도 형상 가정**(J₀·sin), 크기만 자기일관 |
| 장 검증 | Meep 1.34 FDTD (`scripts/meep`) | 원통 m=0, 균일 Drude 플라즈마, 13.56 MHz 장 침투 | 밀도 균일·고정 |
| 입자 검증 | eduPIC (`scripts/edupic`) | 1D3V PIC/MCC Ar CCP | 1D, 평행판 |

## 1. 설치 (최초 1회, 약 3분)

```bash
export PLASMA_SIM_DIR=~/plasma_sim          # 출력 루트
export MEEP_ENV=$PLASMA_SIM_DIR/envs/meep   # 이미 있으면 그 경로
bash scripts/install.sh                      # numpy/scipy/matplotlib, Meep(conda-forge), eduPIC clone+컴파일
```
micromamba/mamba/conda 중 하나가 있어야 Meep이 깔린다. 한글 폰트(fonts-nanum 등)가 없으면 그림의 한글이 깨진다.

## 2. 전체 실행 (약 3~4분)

```bash
REPORT_AUTHOR="이름" bash scripts/run_all.sh          # ICP → Meep → eduPIC 후처리 → 보고서
STAGES="icp report" bash scripts/run_all.sh          # 일부만
```
결과: `$PLASMA_SIM_DIR/report/ICP_plasma_opensource_report.html` (그림 내장 단일 파일).

eduPIC 본 실행은 **4~5시간**이다. 셸이 끝나도 살아남는 방식으로 띄운다.
```bash
nohup bash scripts/edupic/run_edupic.sh > $PLASMA_SIM_DIR/ccp_run/run.log 2>&1 &
```
끝나면 `STAGES="edupic report" bash scripts/run_all.sh`.

## 3. 설계 변경

`icp_source.py`의 `Geometry(...)`와 `operate(g, p_mTorr, P_rf, R_coil)`가 진입점이다.
- 코일 반경: `Geometry(coil_r=(0.04, 0.08, 0.12))`, 헬리컬: `Geometry(kind="helical", coil_z=(...))`
- 챔버: `R, H, t_win, eps_win`, 격자: `dr, dz` (기본 2 mm)
- 매칭: `l_match(R_p + R_coil, ωL)` → 직렬·병렬 C (L-network, 50 Ω)

## 4. 반드시 지킬 것 (실제로 틀렸던 곳)

1. **표피깊이는 콜드플라즈마 `1/Im(k)`** (`cold_skin()`). 충돌형 √(2/ωμ₀Reσ)는 ν≫ω일 때만 맞다. 10 mTorr Ar은 ν(3.2e7) < ω(8.5e7)이라 2.8 cm로 틀렸었다(정답 1.2 cm).
2. **Meep 진폭은 한 주기 푸리에의 13.56 MHz 성분**으로 잰다. 최대 |E|는 과도성분이 섞여 오판한다.
3. **Meep 검증은 깊이별 점대점 비교**로 판단한다. 단일 지수맞춤 "감쇠길이"는 맞춤 구간에 따라 크게 흔들린다(근거리장 기하감쇠·반사 혼입).
4. 격자가 계산영역을 정확히 나누지 않아도 되도록 바깥 칸은 항상 디리클레다(3 mm 격자에서 경계 버그가 있었다).
5. 유지 최소 전력 아래의 "해 없음"은 E-모드를 뜻할 뿐, 모델에 E-모드는 없다.
6. 밀도 형상 가정 때문에 **웨이퍼 균일도는 이 모델로 주장하지 않는다.**

## 5. 검증 기준값 (이 저장소 기본 설정)

| 항목 | 값 | 비교 |
|---|---|---|
| ICP 10 mTorr·500 W | n₀ 2.14e11 cm⁻³, T_e 2.53 eV, R_p 1.05 Ω, 효율 64%, I 24.7 A | 300 mm Ar ICP 문헌 범위 |
| 격자 3→1 mm | n₀·R_p·효율 ±2%, L ±4%(코일 단면 계단화) | `conv_test.py` |
| Meep 1e11 cm⁻³ | 해상도 5·10 모두 0–3 cm에서 exp(−x/1.76 cm)와 일치 | 그림 6 |
| Meep 1e12 cm⁻³ 해상도 10 | 0.6 cm 이후 이탈, 약 10% 가짜 바닥 | **미해결** |
| eduPIC Ar 10 Pa·250 V | 전자 흡수전력 1.584e3 W/m³ (논문 1.58e3), 이온 3.30e3 (논문 3.28e3) | Donkó et al. PSST 2021 |

## 6. 보고 원칙

- 회사 장비 치수·공정 조건은 넣지 않는다. 공개 문헌 수준 일반 조건만.
- 정정 이력과 미해결 항목을 보고서에 남긴다(감추지 않는다).
- 자세한 식과 가정은 `references/methods.md`.
