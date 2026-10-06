"""
rv.py — zmienność zrealizowana dnia (RV) ze świec 5m: RV_d = Σ (log C_i − log C_{i−1})² po świecach dnia
UTC d (pierwszy zwrot dnia liczony od ostatniego zamknięcia dnia poprzedniego, więc doba jest pełna).
Obok: dzienny zwrot prosty close-to-close (zamknięcie ostatniej świecy dnia), liczba świec w dniu.
Bez poprawek danych — dzień niepełny oznacza `n_swiec` < 288 i decyzję zostawia wywołującemu.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SWIEC_NA_DZIEN = 288


def rv_dzienna(df5m: pd.DataFrame) -> pd.DataFrame:
    """Świece 5m (kolumny `timestamp` UTC, `close`) → DataFrame z indeksem dnia: rv, r, n_swiec."""
    d = df5m[["timestamp", "close"]].sort_values("timestamp")
    if d["timestamp"].duplicated().any():
        raise ValueError("duplikaty znaczników 5m — najpierw raport jakości danych")
    lr = np.log(d["close"]).diff()
    day = d["timestamp"].dt.floor("D")
    g = pd.DataFrame({"day": day, "lr2": lr**2, "close": d["close"]})
    out = g.groupby("day").agg(rv=("lr2", "sum"), n_swiec=("lr2", "size"), close=("close", "last"))
    out["r"] = out["close"].pct_change(fill_method=None)
    out.loc[out.index[0], "rv"] = np.nan  # pierwszy dzień bez zwrotu otwarcia
    out.index.name = "day"
    return out[["rv", "r", "n_swiec"]]
