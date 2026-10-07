"""
Diagnostyka dodatkowa karty 017 (PO obejrzeniu wyniku bramki; poza pre-rejestracją i poza bramką).

Pytanie: który parametr GARCH-t leży przy granicy w dopasowaniach z przebiegu 017 (227 z 855)?
Dotyczy wyłącznie parametrów estymatora; nie dotyka trafień ani prognoz VaR.

    python runs/2026-10-07_017-inwentarz-i-rho/diagnostyka_brzegu.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dane.zwroty_dzienne import MONETY_F21B, panel_wspolny
from symulacje.garch_t import dopasuj_garch_t
from symulacje.prognozy_lv2 import KROK, START

PROG_PERSYSTENCJI = 0.9997  # granica w kodzie: P_MAX = 0,9999


def etykiety(f) -> list[str]:
    pers, udzial = f.alpha + f.beta, f.alpha / (f.alpha + f.beta)
    wyn = []
    if pers > PROG_PERSYSTENCJI:
        wyn.append("persystencja ≈ 0,9999")
    if udzial < 4e-4:
        wyn.append("alfa ≈ 0")
    if udzial > 1 - 4e-4:
        wyn.append("beta ≈ 0")
    if f.nu > 99:
        wyn.append("nu ≈ 100")
    if f.nu < 2.51:
        wyn.append("nu ≈ 2,5")
    if f.omega / f.backcast < 1e-8:
        wyn.append("omega ≈ 0")
    return wyn


def main() -> None:
    panel, _, _ = panel_wspolny(MONETY_F21B)
    r = panel.to_numpy()
    n, k = r.shape
    poprzednie = [None] * k
    rodzaje, wg_monet = Counter(), {m: [0, 0] for m in MONETY_F21B}
    razem = 0
    for b in range(START, n, KROK):
        for j, moneta in enumerate(MONETY_F21B):
            f = dopasuj_garch_t(r[:b, j], start=poprzednie[j])
            poprzednie[j] = f
            razem += 1
            if f.brzeg:
                rodzaje[tuple(etykiety(f)) or ("inne",)] += 1
                wg_monet[moneta][b > 1200] += 1
    print(f"dopasowań: {razem}; przy granicy: {sum(rodzaje.values())}")
    for rodzaj, ile in rodzaje.most_common():
        print(f"  {ile:4d}  {', '.join(rodzaj)}")
    print("przy granicy wg monet (refit z oknem historii ≤ 1200 dni / dłuższym):")
    for moneta, (wczesne, pozne) in wg_monet.items():
        print(f"  {moneta:9s} {wczesne:3d} {pozne:3d}")


if __name__ == "__main__":
    main()
