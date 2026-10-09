"""
likwidacja_zdarzenia.py — rzeczywiste dotknięcia progu likwidacji w dziennych świecach (karta 024), zero I/O.

Wpis na zamknięciu dnia i; pozycja izolowana o dźwigni L i stawce mmr; zdarzenie = w którymś z dni i+1…i+dni dzienny
low (long) <= close_i·(1 − (1/L − mmr)) albo dzienny high (short) >= close_i·(1 + (1/L − mmr)).
"""

from __future__ import annotations

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def dotkniecia(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    wpisy: np.ndarray,
    dzwignia: float,
    mmr: float,
    strona: str,
    dni: int,
) -> np.ndarray:
    """Tablica bool długości len(wpisy); wpis musi mieć pełne okno (wpisy + dni <= n − 1)."""
    close, high, low = (np.asarray(x, dtype=float) for x in (close, high, low))
    wpisy = np.asarray(wpisy, dtype=int)
    n = len(close)
    if not (len(high) == len(low) == n):
        raise ValueError("close, high, low: ta sama długość")
    if dni < 1 or (wpisy < 0).any() or (wpisy + dni > n - 1).any():
        raise ValueError("wpis bez pełnego okna dni+1…dni+h")
    margines = 1.0 / dzwignia - mmr
    if margines <= 0:
        raise ValueError("depozyt nie pokrywa mmr")
    if strona == "long":
        najgorszy = sliding_window_view(low, dni).min(axis=1)[wpisy + 1]
        return najgorszy <= close[wpisy] * (1.0 - margines)
    if strona == "short":
        najgorszy = sliding_window_view(high, dni).max(axis=1)[wpisy + 1]
        return najgorszy >= close[wpisy] * (1.0 + margines)
    raise ValueError("strona: long albo short")


def klastry(dni_wpisow: np.ndarray, odstep: int = 7) -> int:
    """Liczba klastrów: posortowane dni wpisu, kolejne odległe o <= `odstep` dni łączą się łańcuchowo."""
    d = np.unique(np.asarray(dni_wpisow, dtype=int))
    if len(d) == 0:
        return 0
    return int(1 + np.sum(np.diff(d) > odstep))
