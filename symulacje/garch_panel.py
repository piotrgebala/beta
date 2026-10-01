"""
garch_panel.py — generator panelu dziennych zwrotów z ZNANĄ zmiennością warunkową i zmiennością
zrealizowaną (RV) do kalibracji przyrządów filaru F2 (laboratorium F1, `docs/PRD.md` §7).

Model (monety i, dni t):
    r_it = σ_it · √m_it · (√ρ f_t + √(1 − ρ) e_it),          f_t, e_it ~ N(0, 1)
    m_it = (ν − 2) / χ²_ν                                     (E m = 1: daily shock ~ t_ν, grube ogony)
    σ²_{i,t+1} = ω + α r²_it + β σ²_it,   ω = σ̄² (1 − α − β)  (GARCH(1,1), σ̄ = `daily_vol`)
    RV_it = σ²_it · m_it · χ²_M / M                            (suma M kwadratów zwrotów 5m, M = 288)
σ²_it jest znane w chwili t − 1 → prognoza „z prawdziwego procesu” (wyrocznia). m_it to
nieprzewidywalna część wariancji dnia, χ²_M / M — szum pomiaru RV. Średni zwrot = 0 (nigdy nie
kalibrujemy do średniej — PRD F1). ρ steruje korelacją monet (czynnik rynkowy).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def generuj_panel(
    n_days: int,
    n_coins: int,
    seed: int = 0,
    nu: float = 5.0,
    rho: float = 0.5,
    daily_vol: float = 0.04,
    garch: tuple[float, float] = (0.08, 0.90),
    m_intraday: int = 288,
    burn: int = 500,
    start: str = "2021-01-01",
) -> dict[str, pd.DataFrame]:
    """Panele `r` (zwrot), `sigma2` (wariancja warunkowa znana w t − 1), `rv` (zmienność zrealizowana)."""
    if nu <= 2:
        raise ValueError("nu musi być > 2 (skończona wariancja)")
    alpha, beta = garch
    if alpha < 0 or beta < 0 or alpha + beta >= 1:
        raise ValueError("GARCH wymaga alpha, beta ≥ 0 i alpha + beta < 1")
    if not 0.0 <= rho <= 1.0:
        raise ValueError("rho w [0, 1]")
    rng = np.random.default_rng(seed)
    total = n_days + burn
    f = rng.standard_normal(total)
    e = rng.standard_normal((total, n_coins))
    z = np.sqrt(rho) * f[:, None] + np.sqrt(1.0 - rho) * e
    m = (nu - 2.0) / rng.chisquare(nu, size=(total, n_coins))
    g = rng.chisquare(m_intraday, size=(total, n_coins)) / m_intraday
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


def prognoza_okno(r: pd.DataFrame, window: int = 30) -> pd.DataFrame:
    """Baseline: wariancja z okna wstecz = średnia r² z dni t − window … t − 1 (średnia zwrotu = 0)."""
    return (r**2).rolling(window).mean().shift(1)


def prognoza_ewma(r: pd.DataFrame, lam: float = 0.94) -> pd.DataFrame:
    """EWMA (RiskMetrics): σ̂²_t = λ σ̂²_{t−1} + (1 − λ) r²_{t−1}; start od średniej z pierwszych 30 dni."""
    x = (r**2).to_numpy()
    out = np.full_like(x, np.nan)
    if len(x) <= 30:
        return pd.DataFrame(out, index=r.index, columns=r.columns)
    v = x[:30].mean(axis=0)
    out[30] = v
    for t in range(31, len(x)):
        v = lam * v + (1.0 - lam) * x[t - 1]
        out[t] = v
    return pd.DataFrame(out, index=r.index, columns=r.columns)


def momenty(r: pd.DataFrame) -> dict:
    """Momenty kalibracyjne (średnio po monetach): zmienność dzienna, nadwyżka kurtozy, acf(r²) lag 1,
    korelacja między monetami."""
    x = r.to_numpy()
    c = x - x.mean(axis=0)
    kurt = (c**4).mean(axis=0) / (c**2).mean(axis=0) ** 2 - 3.0
    sq = c**2 - (c**2).mean(axis=0)
    acf1 = (sq[1:] * sq[:-1]).sum(axis=0) / (sq * sq).sum(axis=0)
    corr = np.corrcoef(x.T)
    k = corr.shape[0]
    off = corr[np.triu_indices(k, 1)] if k > 1 else np.array([np.nan])
    return {
        "vol": float(x.std(axis=0).mean()),
        "excess_kurtosis": float(np.median(kurt)),
        "acf_r2_lag1": float(acf1.mean()),
        "corr": float(off.mean()),
    }
