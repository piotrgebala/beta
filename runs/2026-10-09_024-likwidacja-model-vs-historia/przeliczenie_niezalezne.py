"""Przeliczenie niezależne wyniku 024: O (klastry) i E (niezależne) dla 3× odtworzone zwykłą pętlą po świecach
z plików parquet i σ̂/ν̂ z `data/lq024_prognozy.npz`, bez importu `likwidacja_zdarzenia`, `ryzyko_pozycji`, `run_lq024`.

    PYTHONPATH=. python runs/2026-10-09_024-likwidacja-model-vs-historia/przeliczenie_niezalezne.py
"""

from __future__ import annotations

import math
from itertools import pairwise

import numpy as np
import pandas as pd
from scipy.stats import poisson
from scipy.stats import t as student

KOSZYK = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT")
L, MMR, H, VR = 3.0, 0.01, 7, 2.264

z = np.load("data/lq024_prognozy.npz")
daty = pd.DatetimeIndex(z["daty"]).tz_localize("UTC")
wpisy, ok = z["wpisy"], z["ok"]
marg = 1 / L - MMR
swieca = {}
for m in KOSZYK:
    df = pd.read_parquet(f"data/binance_um/1d/{m}.parquet")
    df["d"] = pd.to_datetime(df["timestamp"], utc=True).dt.normalize()
    swieca[m] = df.set_index("d")[["close", "high", "low"]]

zdarzenia, e_blok = [], 0.0
for strona in ("long", "short"):
    for m in KOSZYK:
        s, nu = z[f"{m}_sigma"], z[f"{m}_nu"]
        for k, i in enumerate(wpisy):
            if not ok[k]:
                continue
            sw = swieca[m]
            c0 = sw.loc[daty[i], "close"]
            okno = [daty[i] + pd.Timedelta(days=j) for j in range(1, H + 1)]
            if strona == "long":
                hit = min(sw.loc[d, "low"] for d in okno) <= c0 * (1 - marg)
                prog = -math.log1p(-marg)
            else:
                hit = max(sw.loc[d, "high"] for d in okno) >= c0 * (1 + marg)
                prog = math.log1p(marg)
            if hit:
                zdarzenia.append(int(i))
            sh = s[k] * math.sqrt(H)
            zz = prog / sh * math.sqrt(nu[k] / (nu[k] - 2))
            p = min(1.0, 2 * student.sf(zz, nu[k]))
            ok_idx = int(ok[: k + 1].sum()) - 1  # numer wpisu wśród tych z pełnym oknem
            if ok_idx % H == 0:
                e_blok += p

zdarzenia = sorted(set(zdarzenia))
o = 1 + sum(1 for a, b in pairwise(zdarzenia) if b - a > H) if zdarzenia else 0
e = e_blok / VR
print(
    f"3× long+short: O = {o}, E niezal. = {e:.2f}, O/E = {o / e:.2f}, p = {poisson.sf(o - 1, e):.4f}"
)
