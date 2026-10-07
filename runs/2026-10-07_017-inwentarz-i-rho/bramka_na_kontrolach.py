"""
Diagnostyka dodatkowa karty 017 (PO przeglądzie kodu; poza pre-rejestracją i poza bramką).

Pytanie: czy bramka ρ̂ + 2 SE ≤ 0,282 w ogóle może przejść na panelach, których zależność JEST taka jak w
laboratorium (kontrola dodatnia R8: ρ = 0,8, 15 monet × 2 100 dni)? Dane syntetyczne, bez prawdziwych cen.

    python runs/2026-10-07_017-inwentarz-i-rho/bramka_na_kontrolach.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from modele import pomiar_rho_h as m
from symulacje.garch_panel import generuj_panel


def main() -> None:
    print(
        f"Bramka {m.PROG_RHO} na panelach syntetycznych ρ = 0,8 (15 × {m.N_KONTROLI}), L = {m.BLOK}"
    )
    print(f"{'ziarno':>6} | {'ρ̂':>7} | {'SE':>7} | {'ρ̂+2SE':>7} | bramka")
    wyn = []
    for z in m.ZIARNA_DODATNIEJ:
        r = generuj_panel(m.N_KONTROLI, m.K_KONTROLI, seed=int(z), rho=0.8)["r"].to_numpy()
        pom = m.pomiar(r)
        wyn.append((pom.rho, pom.se[m.BLOK]))
        print(
            f"{z:>6} | {pom.rho:7.4f} | {pom.se[m.BLOK]:7.4f} | {pom.gorna:7.4f} | "
            f"{'PRZECHODZI' if pom.bramka else 'NIE PRZECHODZI'}"
        )
    rho, se = np.array(wyn).T
    print(f"średnie: ρ̂ {rho.mean():.4f}, SE {se.mean():.4f}, ρ̂+2SE {(rho + 2 * se).mean():.4f}")
    print(f"rozrzut ρ̂ między panelami (SD, ddof=1): {rho.std(ddof=1):.4f}")
    print(f"paneli z bramką PRZECHODZI: {int(((rho + 2 * se) <= m.PROG_RHO).sum())} z {len(rho)}")


if __name__ == "__main__":
    main()
