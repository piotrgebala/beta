"""
k_prim_blokowy.py — karta 026: test zbiorczy K′ = reguła K, w której błąd składowych A (pokrycie) i C (ogon ES)
pochodzi z bootstrapu blokowego (kołowego) zamiast losowania pojedynczych dni. Składowa B (skupianie) zostaje
z losowania dni, bo jej statystyka jest odporna na zależność przy H0. Zero I/O.
"""

from __future__ import annotations

import numpy as np

from symulacje.moc_var_es import (
    LAG_KLASTER,
    _t_boot,
    p_boot,
    t_klaster,
    t_srednia,
    wklady_dzienne,
)

ALFA = 0.05


def indeksy_blokowe(n: int, dlugosc: int, boot: int, rng: np.random.Generator) -> np.ndarray:
    """Bootstrap blokowy kołowy: (boot × n) indeksów dni; bloki o długości `dlugosc` zaczynają się
    w losowym dniu, szereg jest zawinięty. `dlugosc` = 1 daje zwykłe losowanie dni."""
    if not (1 <= dlugosc <= n) or boot < 1 or n < 3:
        raise ValueError("wymagane: 1 ≤ dlugosc ≤ n, boot ≥ 1, n ≥ 3")
    bloki = -(-n // dlugosc)
    start = rng.integers(0, n, size=(boot, bloki, 1))
    idx = (start + np.arange(dlugosc)) % n
    return idx.reshape(boot, bloki * dlugosc)[:, :n]


def pwartosci_blokowe(r, q, es, p: float, idx_dni: np.ndarray, idx_bloki: dict[int, np.ndarray]):
    """p-wartości (A, B, C) dla każdej długości bloku: B z `idx_dni` (jak w zamrożonej regule K),
    A i C z `idx_bloki[L]`. Zwraca {L: (p_a, p_b, p_c)}; NaN = statystyka niezdefiniowana."""
    k = r.shape[1]
    s, d = wklady_dzienne(r, q, es, p)
    t_a, t_b, t_c = t_srednia(s, k * p), t_klaster(s, LAG_KLASTER), t_srednia(d, 0.0)
    ma, md = s.mean(), d.mean()
    p_b = p_boot(float(t_b), _t_boot(s, idx_dni, lambda x: t_klaster(x, LAG_KLASTER)), "rowne")
    wynik = {}
    for dl, idx in idx_bloki.items():
        p_a = p_boot(float(t_a), _t_boot(s, idx, lambda x: t_srednia(x, ma)), "rowne")
        p_c = p_boot(float(t_c), _t_boot(d, idx, lambda x: t_srednia(x, md)), "prawa")
        wynik[dl] = (p_a, p_b, p_c)
    return wynik


def odrzuca(pw, alfa: float = ALFA) -> tuple[bool, bool, bool, bool]:
    """(razem, A, B, C): Bonferroni na 3 składowych; NaN nie odrzuca."""
    a, b, c = (bool(x < alfa / 3) for x in pw)
    return (a or b or c, a, b, c)
