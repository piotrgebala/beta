"""
likwidacja_model.py — prognozy σ i P(likwidacja) walk-forward dla karty 024 (bez żadnego wyniku z cen high/low).

Procedura zamrożona jak w laboratorium (karty 019–021): pierwsze dopasowanie GARCH-t na `start` = 400 zwrotach,
ponowne dopasowanie co `krok` = 30 dni (ciepły start), parametry stałe w bloku. Wpis na zamknięciu dnia na
pozycji i (0-based w panelu) używa σ̂ na dzień i + 1 — filtr widzi zwroty do pozycji i włącznie, parametry
pochodzą z dopasowania na zwrotach sprzed bloku, który zawiera dzień i + 1.
"""

from __future__ import annotations

import numpy as np

from modele.ryzyko_pozycji import p_likwidacji
from symulacje.garch_t import dopasuj_garch_t, filtr_sigma2

START, KROK = 400, 30


def sigma_nu_walk_forward(
    r, start: int = START, krok: int = KROK
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    (σ̂, ν̂, brzeg) dla pozycji wpisu i = start − 1 … n − 2 (długość n − start). σ̂[j] to prognoza na dzień
    start + j, znana po zamknięciu dnia start + j − 1; `brzeg` = dopasowanie bloku przy granicy/niezbieżne.
    """
    r = np.asarray(r, dtype=float)
    n = len(r)
    if r.ndim != 1 or n <= start or not np.isfinite(r).all():
        raise ValueError("r: skończony wektor dłuższy niż `start`")
    sigma, nu, brzeg = np.empty(n - start), np.empty(n - start), np.zeros(n - start, dtype=bool)
    f = None
    for b in range(start, n, krok):
        e = min(b + krok, n)
        f = dopasuj_garch_t(r[:b], start=f)
        s2 = filtr_sigma2(r[: e - 1] ** 2, f.omega, f.alpha, f.beta, f.backcast)
        sigma[b - start : e - start] = np.sqrt(s2[b:e])
        nu[b - start : e - start] = f.nu
        brzeg[b - start : e - start] = (not f.zbiezny) or bool(f.brzeg)
    return sigma, nu, brzeg


def p_model(sigma, nu, dzwignia: float, mmr: float, strona: str, dni: int) -> np.ndarray:
    """P(dotknięcia progu likwidacji w ciągu `dni` dni) dla każdej pozycji wpisu (σ stała w oknie)."""
    return np.array(
        [p_likwidacji(dzwignia, mmr, s, v, strona, dni, dotkniecie=True) for s, v in zip(sigma, nu)]
    )
