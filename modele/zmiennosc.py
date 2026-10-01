"""
zmiennosc.py — prognozy wariancji dziennej na dzień t+1 (filar F2, drabina R17: najpierw najprostszy).

1. `prognoza_dziennik` — DOKŁADNIE to, czego dziś używa dziennik alpha (`ts_momentum.ewma_vol`):
   EWMA kwadratów prostych zwrotów dziennych, środek masy 60, min. 30 obserwacji, bez centrowania;
   wartość w dniu t (zwroty ≤ t) jest prognozą wariancji dnia t+1.
2. `prognoza_har` — HAR-RV (Corsi 2009) na logarytmach, okna 1 / 7 / 30 dni (tydzień krypto = 7 dni),
   walk-forward: refit co `co_ile` dni na rosnącym oknie, min. `min_trening` dni, para (cechy_t, cel_t+1)
   wchodzi do treningu tylko gdy t+1 ≤ dzień refitu (purging dla horyzontu 1 dnia). Prognoza wariancji =
   exp(ŷ + s²/2) (korekta log-normalna, s² — wariancja reszt treningu).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def prognoza_dziennik(r: pd.Series, com: int = 60, min_periods: int = 30) -> pd.Series:
    """Prognoza wariancji dnia t+1 umieszczona w wierszu t+1 (przesunięta o 1)."""
    return (r**2).ewm(com=com, min_periods=min_periods).mean().shift(1)


def cechy_har(rv: pd.Series) -> pd.DataFrame:
    lv = np.log(rv)
    return pd.DataFrame(
        {"c": 1.0, "d": lv, "w": lv.rolling(7).mean(), "m": lv.rolling(30).mean()}, index=rv.index
    )


def prognoza_har(rv: pd.Series, min_trening: int = 365, co_ile: int = 30) -> pd.Series:
    """Prognoza wariancji dnia t+1 umieszczona w wierszu t+1; NaN przed pierwszym refitem."""
    X = cechy_har(rv)
    y_next = np.log(rv).shift(-1)  # cel dla wiersza t = log RV_{t+1}
    ok = X.notna().all(axis=1).to_numpy() & y_next.notna().to_numpy()
    Xv, yv = X.to_numpy(), y_next.to_numpy()
    n = len(rv)
    out = np.full(n, np.nan)
    first = np.nonzero(ok)[0]
    if len(first) == 0:
        return pd.Series(out, index=rv.index)
    start = first[0] + min_trening
    beta, s2 = None, None
    for t in range(start, n - 1):
        if beta is None or (t - start) % co_ile == 0:
            tr = ok.copy()
            tr[t:] = False  # wiersz s ma cel s+1 ≤ t  ⇔  s ≤ t − 1
            if tr.sum() < min_trening // 2:
                continue
            beta, *_ = np.linalg.lstsq(Xv[tr], yv[tr], rcond=None)
            res = yv[tr] - Xv[tr] @ beta
            s2 = float(res.var(ddof=Xv.shape[1]))
        if np.isfinite(Xv[t]).all():
            out[t + 1] = np.exp(Xv[t] @ beta + s2 / 2.0)
    return pd.Series(out, index=rv.index)
