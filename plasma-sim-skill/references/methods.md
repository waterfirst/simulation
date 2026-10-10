# 방법 요약 (보고서 2절과 같은 내용)

## 전자기 (주파수영역, e^{jωt})

```
(1/r)∂/∂r(r ∂A/∂r) − A/r² + ∂²A/∂z² + k₀² ε(r,z) A = −μ₀ J_coil
E_φ = −jωA,   ε_p = 1 − ω_pe²/[ω(ω − jν_m)],   σ = ε₀ω_pe²/(ν_m + jω)
p_abs = ½ Re(σ)|E_φ|²,   R_p = 2 P_abs / I²
```
보존형 5점 차분(r±dr/2 면 플럭스), 축·금속·바깥 칸 A=0, SciPy 희소 복소 직접해.
코일 링마다 단면 셀에 정확히 I가 흐르도록 정규화.

## 글로벌 모델 (Lieberman & Lichtenberg 2판 3·10장)

```
K_iz(T_e) n_g V = u_B A_eff                 → T_e
P_abs = e n₀ u_B A_eff E_T                  → n₀
A_eff = 2πR² h_L + 2πRH h_R
h_L = 0.86/√(3 + H/2λ_i),  h_R = 0.80/√(4 + R/λ_i),  λ_i = 1/(n_g σ_i),  σ_i = 1e-18 m²
E_T = E_c + 2T_e + 5.2T_e
K_iz = 2.34e-14 T^0.59 e^(−17.44/T)   K_ex = 2.48e-14 T^0.33 e^(−12.78/T)
K_el = 2.336e-14 T^1.609 exp(0.0618 ln²T − 0.1171 ln³T)
ν_m ≈ n_g(K_el + K_ex + K_iz)
```

## 결합

```
P_abs = P_rf · R_p/(R_p + R_coil)
n_e = n₀ J₀(2.405 r/R) sin(πz/H)          (형상 가정)
로그공간 0.5 감쇠 반복, |Δn/n| < 2e-3
```

## 확률적(무충돌) 가열

```
nu_stoch = v_te / (4 delta),   v_te = sqrt(e Te / me),  delta = cold_skin(n0, nu)
nu_eff   = nu_m + nu_stoch     (operate(..., stochastic=True), 자기일관 반복 안에서 갱신)
```
전자가 RF 한 주기보다 짧은 시간에 표피층을 지나면 충돌 없이 에너지를 받는다(Lieberman 12장).
`v_te > omega*delta` 일 때, 곧 `nu_m < omega` 인 저압에서 지배적이다. 유체 모델이라 유효 충돌주파수로
접어 넣는 근사이고, 제대로 하려면 비국소(운동론) 전도도가 필요하다.

측정된 보정폭(13.56 MHz, 500 W, R 15 cm · H 10 cm):

| p [mTorr] | nu_m/omega | R_p 증가 | 효율 |
|---|---|---|---|
| 1 | 0.08 | +359% | 13.7 → 42.1% |
| 3 | 0.16 | +103% | 39.8 → 57.3% |
| 10 | 0.38 | +38% | 63.5 → 70.7% |
| 30 | 0.84 | +12% | 77.8 → 79.7% |
| 100 | 2.08 | +1% | 84.8 → 85.0% |

## 압력 영역과 Knudsen 수 (어느 모델이 유효한가)

이 형상(H = 10 cm)에서 중성자 평균자유행로 `lam_n = 1/(sqrt(2) n_g sigma_n)`, 이온 `lam_i = 1/(n_g sigma_i)`:

| p [mTorr] | lam_i [mm] | Kn_i = lam_i/H | 유동 영역(중성자) |
|---|---|---|---|
| 0.5 | 62 | 0.62 | 천이 (DSMC) |
| 1 | 31 | 0.31 | 천이 (DSMC) |
| 10 | 3.1 | 0.03 | slip |
| 100 | 0.3 | 0.003 | 연속체 |

밀도 형상 가정 `J0(2.405 r/R) sin(pi z/H)` 은 **양극성 확산 모드**라 충돌이 지배하는 쪽(10 mTorr 이상)에서만 맞다.
1 mTorr 근처에서는 이온이 생성점에서 기판까지 거의 충돌 없이 가므로 전혀 다른(무충돌) 수송 모델이 필요하다.
글로벌 모델의 h factor가 이미 이 전환을 품고 있다: `h_L = 0.86/sqrt(3 + H/2 lam_i)` 에서 `H/(2 lam_i) = 1/(2 Kn_i)` 이고,
저압에서 0.497(무충돌 한계)로 수렴, 10 mTorr에서 0.197이다. 입자 수지는 전환이 들어가 있고, 빠진 것은 유동장이다.

## 인덕턴스·매칭

```
¼LI² = ¼∫|B|²/μ₀ dV,  B_r = −∂A/∂z,  B_z = (1/r)∂(rA)/∂r
Q = √(R₀/R − 1),  X_s = QR − X_L (음수 → 직렬 C),  X_p = R₀/Q (병렬 C)
```

## Meep

원통 m=0, 단위 a = 1 cm, f = 13.56e6·a/c, Drude(frequency=f_p, gamma=ν/2π, sigma=1),
코일 = E_φ 링 소스, 금속 경계, Courant 0.5, 3주기 램프 후 1주기 24위상 저장 →
`|Σ F_k e^{−2πik/N}|·2/N`.

## 한계

1. 밀도 형상 가정(수송 미해석) → 균일도·비국소 가열 불가
2. T_e 균일, Maxwellian, 단일 ν_m. 비충돌 가열은 `stochastic=True`일 때만 — 끄면 저압 R_p가 크게 과소평가된다(위 표)
3. E-모드·E–H 히스테리시스·코일 정전용량 없음
4. 코일 = 동심 링(3D 나선 비대칭 없음), R_coil 가정값
5. Meep 1e12 고해상도 이탈 미해결

## 참고문헌

1. M. A. Lieberman, A. J. Lichtenberg, *Principles of Plasma Discharges and Materials Processing*, 2nd ed. (2005).
2. A. F. Oskooi et al., *Comput. Phys. Commun.* 181, 687 (2010) — Meep.
3. Z. Donkó et al., *Plasma Sources Sci. Technol.* 30, 095017 (2021) — eduPIC.
