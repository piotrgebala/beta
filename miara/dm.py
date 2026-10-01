"""
dm.py — porównanie prognoz zmienności: straty QLIKE i MSE log RV oraz test Diebolda–Mariano z HAC
(Newey–West). Przyrząd filaru F2 (`docs/PRD.md` §10.4): nowy model przechodzi, gdy DM t > 1,96 na jego
korzyść w ≥ 80 % monet i żadna moneta nie jest istotnie gorsza.

Konwencja znaku: d_t = L_A,t − L_B,t. Dodatnie t = prognoza B ma MNIEJSZĄ stratę (B lepsza od A).
W F2 A = baseline (okno wstecz), B = model kandydujący.

Wariancja długookresowa (Newey–West 1987, jądro Bartletta):
    S = γ0 + 2 Σ_{k=1..L} (1 − k/(L + 1)) γ_k,   γ_k = (1/n) Σ (d_t − d̄)(d_{t−k} − d̄)
    t = d̄ / √(S / n);   L domyślnie ⌊4 (n/100)^{2/9}⌋.
S nie zależy od d̄ (liczone na odchyleniach) — z tego korzysta rachunek mocy w `symulacje/moc_dm.py`.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm


def qlike(rv, forecast):
    """Strata QLIKE (Patton 2011): RV/F − log(RV/F) − 1 ≥ 0, zero tylko gdy F = RV."""
    ratio = np.asarray(rv, dtype=float) / np.asarray(forecast, dtype=float)
    return ratio - np.log(ratio) - 1.0


def mse_log(rv, forecast):
    """Błąd kwadratowy na logarytmach: (log RV − log F)²."""
    return (np.log(np.asarray(rv, dtype=float)) - np.log(np.asarray(forecast, dtype=float))) ** 2


def newey_west_lag(n: int) -> int:
    """Reguła Neweya–Westa: ⌊4 (n/100)^{2/9}⌋ (n = 2 100 → 7)."""
    return math.floor(4.0 * (n / 100.0) ** (2.0 / 9.0))


def hac_variance(d, lag: int | None = None) -> np.ndarray:
    """
    Wariancja długookresowa S kolumn `d` (n × k albo wektor n), jądro Bartletta. Zwraca tablicę k
    (albo skalar-tablicę dla wektora). NaN niedozwolone — obetnij je przed wywołaniem.
    """
    x = np.asarray(d, dtype=float)
    if np.isnan(x).any():
        raise ValueError("hac_variance: NaN w danych")
    n = x.shape[0]
    L = newey_west_lag(n) if lag is None else int(lag)
    if L < 0 or L >= n:
        raise ValueError(f"lag {L} spoza [0, n − 1]")
    e = x - x.mean(axis=0)
    s = (e * e).sum(axis=0) / n
    for k in range(1, L + 1):
        gk = (e[k:] * e[:-k]).sum(axis=0) / n
        s = s + 2.0 * (1.0 - k / (L + 1.0)) * gk
    return s


def dm_t(d, lag: int | None = None) -> np.ndarray:
    """t Diebolda–Mariano dla każdej kolumny `d` (różnic strat); NaN przy S ≤ 0."""
    x = np.asarray(d, dtype=float)
    n = x.shape[0]
    s = hac_variance(x, lag)
    se = np.sqrt(np.where(s > 0, s, np.nan) / n)
    return x.mean(axis=0) / se


def diebold_mariano(loss_a, loss_b, lag: int | None = None) -> dict:
    """
    Test DM dla jednej pary szeregów strat (pary z NaN w którymkolwiek pomijane).

    Returns:
        {n, lag, mean_d, se, t, p (dwustronne, normalne), n_eff = n · var(d) / S}.
        t > 0: prognoza B lepsza (mniejsza strata).
    """
    a = np.asarray(loss_a, dtype=float)
    b = np.asarray(loss_b, dtype=float)
    ok = ~(np.isnan(a) | np.isnan(b))
    d = a[ok] - b[ok]
    n = len(d)
    if n < 3:
        raise ValueError(f"za mało obserwacji: {n}")
    L = newey_west_lag(n) if lag is None else int(lag)
    s = float(hac_variance(d, L))
    var0 = float(((d - d.mean()) ** 2).mean())
    se = math.sqrt(s / n) if s > 0 else float("nan")
    t = float(d.mean() / se) if s > 0 else float("nan")
    return {
        "n": n,
        "lag": L,
        "mean_d": float(d.mean()),
        "se": se,
        "t": t,
        "p": float(2.0 * norm.sf(abs(t))) if not math.isnan(t) else float("nan"),
        "n_eff": float(n * var0 / s) if s > 0 else float("nan"),
    }
