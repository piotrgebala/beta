"""
Druga droga do liczb z karty 017 (walidacja po przebiegu; nie jest częścią rejestrowego przebiegu).

Niezależne od `modele/pomiar_rho_h.py` i `dane/zwroty_dzienne.py`:
  - panel zwrotów: własny kod (pandas, bez `panel_wspolny`), ten sam zakres dat;
  - prognoza: zamrożone `symulacje.prognozy_lv2.zbuduj_zrodla` + `prognoza` (z atrapami sigma2 / rv,
    których GARCH-t nie używa);
  - S_t: zamrożone `symulacje.moc_var_es.wklady_dzienne`; VR wzorem z `symulacje/run_lv2.py`;
  - SE: bootstrap blokowy zapisany inaczej (pętla, `np.take(..., mode="wrap")`), INNE ziarno niż rejestrowe.

    python runs/2026-10-07_017-inwentarz-i-rho/druga_droga.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dane.zwroty_dzienne import MONETY_F21B
from symulacje.moc_var_es import wklady_dzienne
from symulacje.prognozy_lv2 import START, prognoza, zbuduj_zrodla

DO = pd.Timestamp("2026-09-30", tz="UTC")
P, BLOK, B = 0.05, 20, 2000
ZIARNO_DRUGIE = 4242


def panel_zwrotow() -> pd.DataFrame:
    kolumny = {}
    for m in MONETY_F21B:
        d = pd.read_parquet(ROOT / "data" / "binance_um" / "1d" / f"{m}.parquet")
        d = d[d["timestamp"] >= pd.Timestamp("2021-01-01", tz="UTC")]
        dzien = d["timestamp"].dt.normalize()
        c = pd.Series(d["close"].to_numpy(float), index=dzien)
        c = c[c.index <= DO]
        kal = pd.date_range(c.index.min(), DO, freq="D")
        kolumny[m] = np.log(c.reindex(kal)).diff()
    return pd.concat(kolumny, axis=1).dropna()


def se_bootstrap(s: np.ndarray, k: int, blok: int, ziarno: int) -> float:
    n = len(s)
    rng = np.random.default_rng(ziarno)
    wyn = np.empty(B)
    for i in range(B):
        kawalki = []
        while sum(len(x) for x in kawalki) < n:
            a = int(rng.integers(0, n))
            kawalki.append(np.take(s, np.arange(a, a + blok), mode="wrap"))
        x = np.concatenate(kawalki)[:n]
        wyn[i] = (x.var(ddof=1) / (k * P * (1 - P)) - 1) / (k - 1)
    return float(wyn.std(ddof=1))


def main() -> None:
    r = panel_zwrotow()
    n, k = r.shape
    print(f"panel: {n} wierszy × {k} monet, {r.index[0].date()} … {r.index[-1].date()}")
    rv = (r**2).rolling(5, min_periods=1).mean() + 1e-6  # atrapa; GARCH-t jej nie używa
    zr = zbuduj_zrodla({"r": r, "sigma2": r * 0 + 1.0, "rv": rv})
    q, es = prognoza(zr, "garch_tnu", P)
    s, _ = wklady_dzienne(zr.r, q, es, P)
    vr = float(s.var(ddof=1) / (k * P * (1 - P)))
    rho = (vr - 1) / (k - 1)
    se = se_bootstrap(s, k, BLOK, ZIARNO_DRUGIE)
    print(f"dni oceny: {len(s)} (START = {START})")
    print(
        f"GARCH: dopasowań {zr.diag['dopasowania']}, niezbieżnych {zr.diag['nie_zbiezne']}, "
        f"przy granicy {zr.diag['brzeg']}, persystencja {zr.diag['persystencja']:.4f}, "
        f"ν̂ {zr.diag['nu']:.2f}"
    )
    print(f"VR = {vr:.3f}")
    print(f"ρ̂ = {rho:.4f}")
    print(f"SE (druga implementacja, L = {BLOK}, B = {B}, ziarno {ZIARNO_DRUGIE}) = {se:.4f}")
    print(f"ρ̂ + 2 SE = {rho + 2 * se:.4f}")


if __name__ == "__main__":
    main()
