"""
NC1B — kontrola negatywna przyrządu `miara` na danych syntetycznych (pre-rejestracja:
`runs/2026-09-30_nc1b-kontrola-negatywna-miara/README.md`). Neutralny reporter (R14): drukuje
liczby i spełnienie kryteriów zapisanych z góry; werdykt podpisuje README rundy.

    python -m miara.run_nc1b > runs/2026-09-30_nc1b-kontrola-negatywna-miara/raw_output.txt
"""

from __future__ import annotations

import math
import time

import numpy as np

from miara.kontrola_negatywna import regula_przekrojowa, regula_trendu, synthetic_returns
from miara.neff import summarize_pnl

SEEDS = range(40)
N_DAYS, N_COINS = 2_000, 20
Z = 1.959964
REGULY = {"R-TS": regula_trendu, "R-XS": regula_przekrojowa}


def wilson(k: int, n: int, z: float = Z) -> tuple[float, float]:
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def main() -> None:
    t0 = time.time()
    wyniki = {f"{k}{s}": [] for k in REGULY for s in ("", " peek")}
    zwrot = {k: [] for k in wyniki}
    for seed in SEEDS:
        r = synthetic_returns(N_DAYS, N_COINS, seed=seed)
        for name, fn in REGULY.items():
            for peek in (False, True):
                s = summarize_pnl(fn(r, peek=peek), periods_per_year=365, capital_per_notional=1.0)
                key = f"{name}{' peek' if peek else ''}"
                wyniki[key].append(s["t_neff"])
                zwrot[key].append(s["annual_notional"])

    print("NC1B — t_neff dziennego zwrotu brutto, 40 losowań × 20 monet × 2 000 dni\n")
    print(f"{'reguła':<10} | śr. t | sd t | |t|>1,96 | min t | max t | śr. zwrot %/rok | kryterium")
    alarmy = 0
    for key, ts in wyniki.items():
        t = np.array(ts)
        k = int((np.abs(t) > Z).sum())
        if key.endswith("peek"):
            ok = bool((t > 5).all())
            kryt = f"t > 5 we wszystkich: {'TAK' if ok else 'NIE'} ({int((t > 5).sum())}/40)"
        else:
            alarmy += k
            ok = abs(t.mean()) < 0.5 and k <= 5
            kryt = f"|śr.| < 0,5 i alarmy ≤ 5: {'TAK' if ok else 'NIE'}"
        print(
            f"{key:<10} | {t.mean():+.2f} | {t.std(ddof=1):.2f} | {k:>2}/40    | {t.min():+.2f} | "
            f"{t.max():+.2f} | {100 * np.mean(zwrot[key]):+8.1f}        | {kryt}"
        )
    lo, hi = wilson(alarmy, 80)
    print(
        f"\nŁącznie fałszywe alarmy (bez peek): {alarmy}/80 = {100 * alarmy / 80:.1f} % "
        f"[Wilson 95 %: {100 * lo:.1f}; {100 * hi:.1f}] — alpha NC1: 4/120 = 3,3 % [1,3; 8,3]"
    )
    print("\nt_neff per losowanie (ziarno: R-TS, R-XS, R-TS peek, R-XS peek):")
    for i, seed in enumerate(SEEDS):
        print(f"  {seed:2d}: " + ", ".join(f"{wyniki[k][i]:+.2f}" for k in wyniki))
    print(f"\nczas: {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
