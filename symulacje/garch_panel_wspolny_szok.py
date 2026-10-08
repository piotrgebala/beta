"""
garch_panel_wspolny_szok.py — generator LV2c (karta 019): panel jak `garch_panel.generuj_panel` plus dwa nowe elementy.

(i) WSPÓLNY SZOK ZMIENNOŚCI. Mnożnik skali dnia m_it = (ν − 2) / χ²_ν w LV2 jest niezależny między monetami. Tu
    jego brzegi zostają dokładnie takie same (każda moneta ma innowację t_ν o wariancji 1), ale zależność między
    monetami wprowadza kopuła gaussowska o parametrze `rho_szok`: w dniu krachu duży mnożnik pada na kilka monet
    naraz i żadna moneta nie umie go przewidzieć ze swojej własnej przeszłości.
(ii) TRWAŁOŚĆ BLISKA GRANICY. `persystencja` (α + β) może być wektorem po monetach, do 0,9999; `alpha` (współczynnik
    ARCH, domyślnie 0,08 jak w LV2) jest drugim pokrętłem odsetka dopasowań przy granicy.

Dzięki kopule rozkład szeregu POJEDYNCZEJ monety nie zależy od `rho` ani `rho_szok`: odsetek dopasowań GARCH przy
granicy, ν̂ i persystencja zależą tylko od `persystencja`, a zależność trafień (VR) tylko od `rho` i `rho_szok`.
Kalibracja obu celów rozdziela się więc na dwie osobne.

Parytet z LV2: przy `rho_szok = 0` i `persystencja = None` wynik jest IDENTYCZNY bit w bit z
`generuj_panel(..., rho=rho)` dla tego samego ziarna (dodatkowe losowania następują dopiero po losowaniach LV2).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import gammaincinv, ndtr

ALFA = 0.08
BETA_LV2 = 0.90  # persystencja LV2 = ALFA + BETA_LV2 = 0,98
PERS_LV2 = 0.98
KLAMRA_U = 1e-15  # obcięcie kwantyla kopuły (prawdopodobieństwo ≤ 1e-15 na losowanie)


def mnoznik_skali(w: np.ndarray, nu: float) -> np.ndarray:
    """m = (ν − 2) / Q, Q ~ χ²_ν z kwantyla ndtr(−w): duże w daje małe Q, czyli duży mnożnik skali."""
    u = np.clip(ndtr(-w), KLAMRA_U, 1.0 - KLAMRA_U)
    return (nu - 2.0) / (2.0 * gammaincinv(0.5 * nu, u))


def generuj_panel_lv2c(
    n_days: int,
    n_coins: int,
    seed: int = 0,
    nu: float = 5.0,
    rho: float = 0.8,
    rho_szok: float = 0.0,
    persystencja: float | np.ndarray | list[float] | None = None,
    alpha: float = ALFA,
    daily_vol: float = 0.04,
    m_intraday: int = 288,
    burn: int = 500,
    start: str = "2021-01-01",
) -> dict[str, pd.DataFrame]:
    """Panele `r`, `sigma2`, `rv` jak w `generuj_panel`; `persystencja` None = LV2 (0,98 wszystkie monety)."""
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha w (0, 1)")
    if nu <= 2:
        raise ValueError("nu musi być > 2 (skończona wariancja)")
    if not 0.0 <= rho <= 1.0:
        raise ValueError("rho w [0, 1]")
    if not 0.0 <= rho_szok <= 1.0:
        raise ValueError("rho_szok w [0, 1]")
    if persystencja is None:
        beta = BETA_LV2 if alpha == ALFA else PERS_LV2 - alpha  # 0,90 dosłownie: parytet bit w bit
        if beta <= 0.0:
            raise ValueError("alpha musi być < 0,98 przy persystencji LV2")
    else:
        pers = np.broadcast_to(np.asarray(persystencja, dtype=float), (n_coins,))
        if (pers <= alpha).any() or (pers >= 1.0).any():
            raise ValueError("persystencja w (alpha, 1)")
        beta = pers - alpha
    rng = np.random.default_rng(seed)
    total = n_days + burn
    f = rng.standard_normal(total)
    e = rng.standard_normal((total, n_coins))
    z = np.sqrt(rho) * f[:, None] + np.sqrt(1.0 - rho) * e
    m = (nu - 2.0) / rng.chisquare(nu, size=(total, n_coins))
    g = rng.chisquare(m_intraday, size=(total, n_coins)) / m_intraday
    if rho_szok > 0.0:
        fm = rng.standard_normal(total)
        em = rng.standard_normal((total, n_coins))
        m = mnoznik_skali(np.sqrt(rho_szok) * fm[:, None] + np.sqrt(1.0 - rho_szok) * em, nu)
    var_bar = daily_vol**2
    omega = var_bar * (1.0 - alpha - beta)
    r = np.empty((total, n_coins))
    s2 = np.empty((total, n_coins))
    var = np.full(n_coins, var_bar)
    for t in range(total):
        s2[t] = var
        r[t] = np.sqrt(var * m[t]) * z[t]
        var = omega + alpha * r[t] ** 2 + beta * var
    rv = s2 * m * g
    idx = pd.date_range(start, periods=n_days, freq="D", tz="UTC")
    cols = [f"C{i:02d}USDT" for i in range(n_coins)]

    def df(a):
        return pd.DataFrame(a[burn:], index=idx, columns=cols)

    return {"r": df(r), "sigma2": df(s2), "rv": df(rv)}
