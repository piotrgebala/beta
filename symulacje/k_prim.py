"""
k_prim.py — karta 022: górna granica mocy testu zbiorczego z PRAWDZIWYM błędem standardowym (rozrzut po panelach).

Test z błędem szacowanym (bootstrap blokowy, HAC) nie ma większej mocy niż ten sam test z błędem prawdziwym, więc odsetek
odrzuceń liczony tu jest górną granicą dla reguły K′. Zero I/O.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm

ALFA = 0.05


def odrzucenia_idealne(
    hit: np.ndarray, u: np.ndarray, zb_b: np.ndarray | None, p: float, alfa: float = ALFA
) -> dict:
    """
    Odsetki odrzuceń po panelach: A dwustronnie α/3 na odsetku trafień, C prawostronnie α/3 na średnim wskaźniku ES,
    B z zapisanego wskaźnika odrzucenia (albo pominięte, gdy `zb_b` is None); razem = którakolwiek.
    """
    hit, u = np.asarray(hit, dtype=float), np.asarray(u, dtype=float)
    if hit.shape != u.shape or hit.ndim != 1 or len(hit) < 3:
        raise ValueError("hit i u: wektory 1-D tej samej długości ≥ 3")
    kryt_a = norm.isf(alfa / 6)
    kryt_c = norm.isf(alfa / 3)
    z_a = (hit - p) / hit.std(ddof=1)
    z_c = (u - 1.0) / u.std(ddof=1)
    a = np.abs(z_a) > kryt_a
    c = z_c > kryt_c
    b = np.zeros_like(a) if zb_b is None else np.asarray(zb_b) > 0.5
    return {
        "A": float(a.mean()),
        "B": float(b.mean()),
        "C": float(c.mean()),
        "razem": float((a | b | c).mean()),
        "z_a_sr": float(z_a.mean()),
        "z_c_sr": float(z_c.mean()),
    }
