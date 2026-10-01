"""
bayes.py — rozkład a posteriori średniego rocznego zwrotu nogi (filar F3, reporter).

Model normalny-normalny ze ZNANĄ σ (zakładaną, jak w ADR-09): średnia z n dni ~ N(μ, σ² / (n/365)).
Prior sceptyczny (PRD F3: „ślad z historii ściągnięty mocno do zera — DSR 0,52 to słaby prior”):
N(0, μ_hist²) — wynik historii leży 1 σ priora od zera.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm

from dowody.nogi import DNI_W_ROKU


def posterior(x, sigma: float, prior_mean: float, prior_sd: float) -> dict:
    """x — dzienne zwroty; σ, prior — roczne. Zwraca średnią, sd, 95 % przedział i P(μ > 0)."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n == 0:
        m, s = prior_mean, prior_sd
    else:
        xbar = float(x.mean()) * DNI_W_ROKU
        se2 = sigma**2 / (n / DNI_W_ROKU)
        prec = 1.0 / prior_sd**2 + 1.0 / se2
        m = (prior_mean / prior_sd**2 + xbar / se2) / prec
        s = math.sqrt(1.0 / prec)
    return {
        "n": n,
        "mean": m,
        "sd": s,
        "ci_low": m - 1.959964 * s,
        "ci_high": m + 1.959964 * s,
        "p_dodatnia": float(norm.sf(0.0, loc=m, scale=s)),
    }
