# plasma-sim-skill

오픈소스만으로 RF 플라즈마 소스(ICP·CCP)를 설계·해석하고 전문가용 HTML 보고서까지 만드는 Claude Code 스킬.

- **ICP 자기일관 모델** — 2D 축대칭 A_φ 전자기 + 아르곤 글로벌 모델, 변압기 결합 반복.
  RF 전력만 넣으면 n₀, T_e, 플라즈마 저항, 결합효율, 코일전류, 인덕턴스, 50 Ω 매칭 커패시터.
- **Meep FDTD 교차검증** — 드루드 플라즈마 속 13.56 MHz 유도장 침투를 콜드플라즈마 이론과 점대점 비교.
- **eduPIC PIC/MCC** — Ar CCP 기준사례 재현(전자 흡수전력 논문 대비 0.2%).

```bash
bash scripts/install.sh       # 최초 1회
bash scripts/run_all.sh       # 약 3~4분, report/ICP_plasma_opensource_report.html
```

자세한 사용법과 주의점은 `SKILL.md`, 식과 가정은 `references/methods.md`.

Meep(GPL)과 eduPIC(GPLv3)은 설치 시 내려받으며 이 저장소에 포함하지 않는다. 이 저장소의 코드는 MIT.
