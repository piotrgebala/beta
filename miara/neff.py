"""
neff.py — efektywna liczba niezależnych obserwacji (N_eff) i statystyki średniego P&L z korektą
na autokorelację (zasada R10: N_eff ≤ n zawsze).

Port 1:1 z alpha (parytet: `tests/test_parytet_alpha.py`, zasada 24):
- `effective_sample_size` ← `alpha/agents/labeling.py` (z poprawką AU3: mianownik ≤ 0 → N_eff = n);
- `summarize_pnl`         ← `alpha/backtest/carry_hedged.py` (N_eff w [1, n], audyt AU1).

Wzór: N_eff = n / (1 + 2 Σ_{k=1..max_lag} ρ_k). Korekta ma tylko ODEJMOWAĆ pewność (alpha,
wniosek 50) — stąd przycięcie do n w miejscach, które jej używają.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

Z_TWO_SIDED_95 = 1.959964

# Domyślne stałe `summarize_pnl` jak w alpha C1 (rozliczenia co 8 h, kapitał 2× nominał).
# Wywołujący z danymi dziennymi podaje periods_per_year=365 i capital_per_notional=1.0.
PERIODS_PER_YEAR = 3 * 365
CAPITAL_PER_NOTIONAL = 2.0


def effective_sample_size(returns: pd.Series, max_lag: int = 50) -> dict:
    """
    N_eff = n / (1 + 2 Σ ρ_k) po autokorelacjach rzędów 1..max_lag (NaN pomijane).

    Suma autokorelacji < −0,5 daje mianownik ≤ 0 — wzór nie ma wtedy sensu, więc N_eff = n
    (korekta może tylko odejmować pewność).

    Returns:
        {"n": liczba obserwacji po dropna, "n_eff": efektywna liczba próbek, "max_lag": max_lag}.
    """
    clean = returns.dropna()
    n = len(clean)
    autocorrs = [clean.autocorr(lag=k) for k in range(1, max_lag + 1)]
    autocorrs = [a for a in autocorrs if not np.isnan(a)]
    denominator = 1 + 2 * sum(autocorrs)
    n_eff = n / denominator if denominator > 0 else float(n)
    return {"n": n, "n_eff": n_eff, "max_lag": max_lag}


def summarize_pnl(
    pnl: pd.Series,
    z: float = Z_TWO_SIDED_95,
    periods_per_year: int = PERIODS_PER_YEAR,
    capital_per_notional: float = CAPITAL_PER_NOTIONAL,
) -> dict:
    """
    Średni P&L per okres z CI (se z N_eff ∈ [1, n]), t, t_neff, annualizacja na nominale i kapitale.

    Przy n < 2 zwraca tylko {"n": n}.
    """
    x = pnl.dropna().astype(float)
    n = len(x)
    if n < 2:
        return {"n": n}
    mean = float(x.mean())
    sd = float(x.std(ddof=1))
    se = sd / np.sqrt(n)
    n_eff = max(1.0, min(float(effective_sample_size(x)["n_eff"]), float(n)))
    se_neff = sd / np.sqrt(n_eff)
    t = mean / se if se > 0 else float("nan")
    t_neff = mean / se_neff if se_neff > 0 else float("nan")
    lo, hi = mean - z * se_neff, mean + z * se_neff
    return {
        "n": n,
        "mean": mean,
        "median": float(x.median()),
        "sd": sd,
        "se": se,
        "n_eff": n_eff,
        "se_neff": se_neff,
        "t": t,
        "t_neff": t_neff,
        "ci_low": lo,
        "ci_high": hi,
        "annual_notional": mean * periods_per_year,
        "annual_notional_ci": (lo * periods_per_year, hi * periods_per_year),
        "annual_capital": mean * periods_per_year / capital_per_notional,
        "annual_capital_ci": (
            lo * periods_per_year / capital_per_notional,
            hi * periods_per_year / capital_per_notional,
        ),
        "total": float(x.sum()),
    }
