# eco-drive-kit — 고등학교 교통·에너지 탐구 도구 모음

설치 없이 **Google Colab**에서 바로 돌릴 수 있다. 노트북: [`colab_start.ipynb`](colab_start.ipynb)

| 도구 | 하는 일 |
|---|---|
| `drive_score.py` | 주행 기록에서 과속·급가속·급제동을 세고 버린 에너지를 연료·CO2로 환산 (교통안전공단 기준) |
| `accel_limiter.py` | 급가속 **제한** 알고리즘 4종 비교 (냉간시동 적응형 포함) |
| `coastdown.py` | 관성주행 데이터로 공기저항계수 Cd·A 와 구름저항 역산 |
| `windtunnel.py` | 2D 격자볼츠만 가상 풍동. 차 모양별 항력 비교 |
| `glosa.py` | 신호 연동 주행 시뮬. 개인 운전 vs 시스템 개선 비교 |
| `survey.py` | 직접 조사한 교차로 신호 주기로 지역 단위 효과 계산 |
| `road_impact.py` | 도로 폐지 영향평가(안) — 점수화 + 우회 CO2 |
| `energy_budget.py` | 태양광·풍력·압전으로 교통 인프라가 어디까지 자립하나 |

## 바로 써보기
```bash
pip install numpy scipy matplotlib
cd tools
python drive_score.py ../data/demo_rough.csv --limit 60 --plot out.png
python accel_limiter.py --plot out2.png
python energy_budget.py
```

모든 가정값은 각 파일 맨 위 상수에 있다. **바꿔가며 결론이 유지되는지 확인하는 것이 탐구다.**

판정 기준은 한국교통안전공단 운행기록장치 분석 기준을 따랐다.
수치 출처는 각 파일 docstring에 적어 뒀고, **전부 2차 자료이므로 인용 전 1차 확인이 필요하다.**
