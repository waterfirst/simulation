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
2. T_e 균일, Maxwellian, 단일 ν_m, 비충돌 가열 없음(저압 R_p 과소평가 가능)
3. E-모드·E–H 히스테리시스·코일 정전용량 없음
4. 코일 = 동심 링(3D 나선 비대칭 없음), R_coil 가정값
5. Meep 1e12 고해상도 이탈 미해결

## 참고문헌

1. M. A. Lieberman, A. J. Lichtenberg, *Principles of Plasma Discharges and Materials Processing*, 2nd ed. (2005).
2. A. F. Oskooi et al., *Comput. Phys. Commun.* 181, 687 (2010) — Meep.
3. Z. Donkó et al., *Plasma Sources Sci. Technol.* 30, 095017 (2021) — eduPIC.
