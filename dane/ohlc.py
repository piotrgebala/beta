"""
ohlc.py — dzienne high / low / close ze świec 5m (doba UTC) i liczba świec w dobie.

high = max(high 5m), low = min(low 5m), close = ostatnie zamknięcie doby. Bez poprawek danych:
dzień niepełny to `n_swiec` < 288, decyzję o jego ważności zostawiamy cechom (`cechy.techniczne`).
"""

from __future__ import annotations

import pandas as pd


def ohlc_dzienne(df5m: pd.DataFrame) -> pd.DataFrame:
    """Świece 5m (kolumny `timestamp` UTC, `high`, `low`, `close`) → indeks dnia: high, low, close, n_swiec."""
    for k in ("timestamp", "high", "low", "close"):
        if k not in df5m.columns:
            raise ValueError(f"wejście bez kolumny `{k}`")
    d = df5m[["timestamp", "high", "low", "close"]].sort_values("timestamp")
    if d["timestamp"].duplicated().any():
        raise ValueError("duplikaty znaczników 5m — najpierw raport jakości danych")
    dzien = d["timestamp"].dt.floor("D")
    out = d.groupby(dzien).agg(
        high=("high", "max"), low=("low", "min"), close=("close", "last"), n_swiec=("close", "size")
    )
    out.index.name = "day"
    return out
