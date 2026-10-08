"""
garch_panel_regimy.py — generator LV2d (karta 021): panel LV2c plus przesunięcia poziomu wariancji WSPÓLNE dla monet.

Mechanizm: poziom zmienności całego rynku zmienia się skokami (reżimy), o skali, której GARCH(1,1) nie widzi.
Zwrot to r_it = sqrt(L_t) · r_it(LV2c), gdzie L_t jest stałe w reżimie, takie samo dla wszystkich monet i ma
E[L_t] = 1. L nie wchodzi do rekurencji GARCH (rekurencja biegnie na zwrotach bez L), więc `sigma2` wyroczni to
L_t · σ²_it z LV2c, a standaryzowana innowacja r/sqrt(sigma2) zostaje dokładnie taka jak w LV2c (t_ν o wariancji 1).

Reżimy: każdy dzień zaczyna nowy reżim z prawdopodobieństwem 1/`dlugosc` (dzień 0 zawsze); poziom reżimu to
log L = x − amplituda²/2, x ~ N(0, amplituda²) niezależnie między reżimami (pełny powrót do średniej).
`amplituda` jest odchyleniem standardowym log-wariancji poziomu (0,5 → zmienność ±25 % przy 1 odchyleniu).

Własności używane w kalibracji (testy): (a) `amplituda = 0` daje wynik IDENTYCZNY bit w bit z `generuj_panel_lv2c`;
(b) L zależy wyłącznie od (ziarno, amplituda, dlugosc), więc rozkład szeregu pojedynczej monety nie zależy od `rho`
ani `rho_szok` — odsetek dopasowań przy granicy zależy od amplitudy i długości reżimu, a VR od `rho`, `rho_szok`
i (przez skupianie trafień przy skokach poziomu) od amplitudy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from symulacje.garch_panel_wspolny_szok import ALFA, generuj_panel_lv2c

DLUGOSC = 300.0  # średnia długość reżimu w dniach (ok. 7 reżimów na 2 091 dni)
SOL_POZIOMU = 21  # osobny strumień losowań poziomu: losowania LV2c zostają nietknięte


def poziom_wariancji(n_days: int, amplituda: float, dlugosc: float, seed: int) -> np.ndarray:
    """L_t (n_days,), stałe w reżimie, E[L] = 1; `amplituda = 0` daje same jedynki."""
    if n_days < 1:
        raise ValueError("n_days >= 1")
    if not amplituda >= 0.0:
        raise ValueError("amplituda >= 0")
    if not dlugosc >= 1.0:
        raise ValueError("dlugosc >= 1")
    if amplituda == 0.0:
        return np.ones(n_days)
    rng = np.random.default_rng([seed, SOL_POZIOMU])
    nowy = rng.random(n_days) < 1.0 / dlugosc
    nowy[0] = True
    x = rng.standard_normal(n_days) * amplituda
    numer = np.cumsum(nowy) - 1
    return np.exp(x[nowy][numer] - 0.5 * amplituda**2)


def generuj_panel_lv2d(
    n_days: int,
    n_coins: int,
    seed: int = 0,
    nu: float = 5.0,
    rho: float = 0.8,
    rho_szok: float = 0.0,
    persystencja: float | np.ndarray | list[float] | None = None,
    alpha: float = ALFA,
    amplituda: float = 0.0,
    dlugosc: float = DLUGOSC,
    **reszta,
) -> dict[str, pd.DataFrame]:
    """Panele `r`, `sigma2`, `rv` jak w `generuj_panel_lv2c`, pomnożone przez wspólny poziom wariancji."""
    poziom = poziom_wariancji(n_days, amplituda, dlugosc, seed)
    panel = generuj_panel_lv2c(
        n_days,
        n_coins,
        seed=seed,
        nu=nu,
        rho=rho,
        rho_szok=rho_szok,
        persystencja=persystencja,
        alpha=alpha,
        **reszta,
    )
    if amplituda == 0.0:
        return panel
    return {
        "r": panel["r"].mul(np.sqrt(poziom), axis=0),
        "sigma2": panel["sigma2"].mul(poziom, axis=0),
        "rv": panel["rv"].mul(poziom, axis=0),
    }
