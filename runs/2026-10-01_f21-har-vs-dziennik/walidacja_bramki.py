"""
Walidacja bramki F2-1 (skill data:validate-data) — OPIS, nie zmienia werdyktu (ten wynika z ziarna 2101).
Wszystko na CENTROWANYCH różnicach strat (bez informacji o kierunku efektu):
1. błąd Monte Carlo MDE: to samo na ziarnach 1–5;
2. rozkład: MDE pojedynczej monety przy jej własnym n (ile „luzu” zjadają krótkie monety);
3. kontrola liczby dni OOS względem kalendarza (dziury archiwum 2022-02/04).

    python runs/2026-10-01_f21-har-vs-dziennik/walidacja_bramki.py > runs/2026-10-01_f21-har-vs-dziennik/walidacja_output.txt
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dane.ladowanie import wczytaj_swiece
from modele.run_f21 import DELTAS, straty_monety, wybierz_monety
from symulacje.moc_dm import mde, moc_kryterium, moc_kryterium_braki


def main() -> None:
    sklad = json.loads((ROOT / "dane" / "sklad_top20.json").read_text(encoding="utf-8"))
    straty = {
        s: straty_monety(wczytaj_swiece(ROOT / "data" / "binance_um" / "5m" / f"{s}.parquet"))
        for s in wybierz_monety(sklad)
    }
    D = pd.DataFrame({s: v["q_dz"] - v["q_har"] for s, v in straty.items()}).sort_index()
    Dc = D - D.mean()

    print("1. Błąd Monte Carlo MDE kryterium (1 000 losowań, różne ziarna; werdykt = ziarno 2101):")
    for seed in (2101, 1, 2, 3, 4, 5):
        out = moc_kryterium_braki(Dc.to_numpy(), DELTAS, 1000, 30, seed=seed)
        print(f"   ziarno {seed:4d}: MDE kryterium {mde(DELTAS, out['moc_kryterium']):.3f}")

    print("\n2. MDE pojedynczej monety przy jej własnym n (500 losowań, ziarno 7):")
    for s in Dc.columns:
        x = Dc[[s]].dropna().to_numpy()
        out = moc_kryterium(x, len(x), DELTAS, 500, 30, seed=7, share=1.0)
        print(f"   {s:13s} n {len(x):5d}  MDE {mde(DELTAS, out['moc_moneta']):.3f}")

    print("\n3. Dni OOS vs kalendarz:")
    for s, v in straty.items():
        cal = pd.date_range(v.index.min(), v.index.max(), freq="D")
        brak = cal.difference(v.index)
        print(
            f"   {s:13s} {v.index.min().date()} → {v.index.max().date()}  dni {len(v):5d} "
            f"kalendarz {len(cal):5d}  brak {len(brak):3d} {[str(d.date()) for d in brak[:6]]}"
        )
    fin = all(np.isfinite(v[["q_dz", "q_har"]].to_numpy()).all() for v in straty.values())
    print(f"\n   wszystkie straty skończone: {fin}")


if __name__ == "__main__":
    main()
