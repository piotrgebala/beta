"""
eproces.py — e-procesy „zawsze ważne” dla średniego dziennego zwrotu nogi (filar F3, `docs/PRD.md` §7).

Klasyczny próg sprawdzany co dzień zawyża fałszywe alarmy. e-proces E_t to nieujemny (nad)martyngał
przy H0, więc P(sup_t E_t ≥ 1/α) ≤ α (nierówność Ville'a) — wolno patrzeć codziennie.

Konstrukcja: mieszanka jednostronna (połówka rozkładu normalnego N(0, τ²) po λ) wykładniczych
martyngałów exp(λ S_t − λ² V_t / 2), S_t = Σ (x_i − m0), V_t = t σ_d² ze ZAKŁADANĄ σ (jak SE w ADR-09):

    E_t = 2 / (τ √a) · exp(S² / (2a)) · Φ(± S / √a),     a = V_t + 1/τ²

znak „−” — obalenie (H0: μ = μ_zakładane, alternatywa: niżej), „+” — potwierdzenie (H0: μ ≤ 0).
Martyngał dokładny przy dziennych zwrotach N(m0, σ_d²); przy grubych ogonach i innej σ — przybliżenie,
które sprawdza laboratorium (`symulacje/run_ld1.py`).

F3 jest REPORTEREM obok kryterium ADR-09 (z = 2,31 na 92/182/365 dniach) — nie zastępuje go (D3).
"""

from __future__ import annotations

import numpy as np
from scipy.special import log_ndtr


def log_e_mieszanka(S, V, tau: float, strona: int) -> np.ndarray:
    """log E dla sumy odchyleń S i wariancji V (tablice o tym samym kształcie); strona −1 albo +1."""
    if strona not in (-1, 1):
        raise ValueError("strona = −1 (obalenie) albo +1 (potwierdzenie)")
    if tau <= 0:
        raise ValueError("tau > 0")
    S = np.asarray(S, dtype=float)
    V = np.asarray(V, dtype=float)
    a = V + 1.0 / tau**2
    return (
        np.log(2.0)
        - np.log(tau)
        - 0.5 * np.log(a)
        + S**2 / (2.0 * a)
        + log_ndtr(strona * S / np.sqrt(a))
    )


def tau_dla(efekt_d: float, sigma_d: float) -> float:
    """τ dostrojone do efektu dziennego δ: optymalne λ* = δ / σ²."""
    return abs(efekt_d) / sigma_d**2


def sciezka(x, m0: float, sigma_d: float, tau: float, strona: int) -> np.ndarray:
    """Ścieżka E_t (t = 1..n) dla dziennych zwrotów `x` (NaN pomijane — dzień bez wyniku)."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    S = np.cumsum(x - m0)
    V = np.arange(1, len(x) + 1) * sigma_d**2
    return np.exp(log_e_mieszanka(S, V, tau, strona))


def obalenie(x, mu_d: float, sigma_d: float, tau: float | None = None) -> np.ndarray:
    """e-proces przeciw H0 „noga ma zakładane μ” (alternatywa: zero przewagi, τ = μ_d / σ_d²)."""
    return sciezka(x, mu_d, sigma_d, tau or tau_dla(mu_d, sigma_d), -1)


def potwierdzenie(x, mu_d: float, sigma_d: float, tau: float | None = None) -> np.ndarray:
    """e-proces przeciw H0 „μ ≤ 0” (alternatywa: zakładane μ)."""
    return sciezka(x, 0.0, sigma_d, tau or tau_dla(mu_d, sigma_d), +1)
