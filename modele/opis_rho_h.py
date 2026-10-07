"""
opis_rho_h.py — karta 020: opis zależności trafień VaR 5 % dla koszyka 4 monet, BEZ bramki i BEZ oceny prognozy.

Pre-rejestracja: `runs/2026-10-07_020-opis-4-monety/README.md`. Ta sama miara co 017 (`modele.pomiar_rho_h`, bez zmian);
tu tylko inny wydruk: bez progu 0,282, bez okna C2, bez odsetka trafień, kontrole R8 dla K = 4.

    python -m modele.opis_rho_h > runs/2026-10-07_020-opis-4-monety/raw_output.txt
"""

from __future__ import annotations

import argparse

import numpy as np

from dane.zwroty_dzienne import KATALOG_1D, ostatnie_wiersze, panel_wspolny
from modele import pomiar_rho_h as m

MONETY_020 = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT")
K_020 = len(MONETY_020)
ZIARNA_DODATNIEJ = range(1, 41)  # rozłączne od ziaren pilotażu (5001…5020, 5101…5120)
ZIARNA_UJEMNEJ = range(101, 141)
ROZNICA_DODATNIEJ = (
    0.03  # |średnia − 0,282|; pilotaż: sd panelu 0,054, więc SE średniej z 40 paneli ≈ 0,009
)
PROG_UJEMNEJ = 0.02  # |średnia|; pilotaż: sd panelu 0,027, SE średniej ≈ 0,004
OCZEKIWANE_ROZLOGI = (
    228,
    117,
)  # dopasowań i dopasowań przy granicy: te same dopasowania co w 017 (diagnostyka_brzegu)


def tekst_opisu(pom: m.Pomiar) -> str:
    d, se = pom.diag, pom.se
    return "\n".join(
        [
            f"Pomiar zależności dziennej liczby przekroczeń VaR {100 * m.P:.0f} % (GARCH-t, refit co {m.KROK} dni, K = {pom.k})",
            f"  dni oceny: {pom.n_oos}",
            (
                f"  dopasowań GARCH: {d['dopasowania']}, niezbieżnych: {d['nie_zbiezne']}, "
                f"przy granicy: {d['brzeg']}, średnia persystencja α+β {d['persystencja']:.4f}, "
                f"średnie ν̂ {d['nu']:.2f}"
            ),
            f"  VR = Var(S_t) / (K p (1 − p)) = {pom.vr:.3f}",
            f"  ρ̂ = (VR − 1) / (K − 1) = {pom.rho:.4f}",
            f"  SE (bootstrap blokowy, L = {m.BLOK}, B = {m.B_BOOT}, ziarno {m.ZIARNO}) = {se[m.BLOK]:.4f}",
            "  wrażliwość SE (opis): "
            + ", ".join(f"L = {blok}: {se[blok]:.4f}" for blok in m.BLOKI_OPIS),
            f"  ρ̂ ± 2 SE = [{pom.rho - 2 * se[m.BLOK]:.4f}; {pom.rho + 2 * se[m.BLOK]:.4f}]",
            (
                f"  VR odpowiadające ρ̂ ± 2 SE = [{1 + (pom.k - 1) * (pom.rho - 2 * se[m.BLOK]):.3f}; "
                f"{1 + (pom.k - 1) * (pom.rho + 2 * se[m.BLOK]):.3f}]"
            ),
            (
                f"Spójność z 017: dopasowań {d['dopasowania']} (oczekiwane {OCZEKIWANE_ROZLOGI[0]}), "
                f"przy granicy {d['brzeg']} (oczekiwane {OCZEKIWANE_ROZLOGI[1]}) → "
                + (
                    "ZGODNA"
                    if (d["dopasowania"], d["brzeg"]) == OCZEKIWANE_ROZLOGI
                    else "NIEZGODNA — przebieg do wyjaśnienia, wyniku nie interpretować"
                )
            ),
        ]
    )


def tekst_kontroli(dodatnia: list[float], ujemna: list[float]) -> str:
    sd, su = float(np.mean(dodatnia)), float(np.mean(ujemna))
    ok_d = abs(sd - m.PROG_RHO) <= ROZNICA_DODATNIEJ
    ok_u = abs(su) <= PROG_UJEMNEJ
    return "\n".join(
        [
            f"Kontrole R8 ({len(dodatnia)} paneli syntetycznych po {K_020} monet, ta sama funkcja pomiarowa)",
            (
                f"  dodatnia (ρ = 0.8, oczekiwane ≈ {m.PROG_RHO}): średnia ρ̂ {sd:.4f}, "
                f"sd panelu {np.std(dodatnia, ddof=1):.4f}, kryterium |średnia − {m.PROG_RHO}| ≤ "
                f"{ROZNICA_DODATNIEJ} → {'ZALICZONA' if ok_d else 'NIEZALICZONA'}"
            ),
            (
                f"  ujemna (ρ = 0, oczekiwane ≈ 0): średnia ρ̂ {su:.4f}, "
                f"sd panelu {np.std(ujemna, ddof=1):.4f}, kryterium |średnia| ≤ "
                f"{PROG_UJEMNEJ} → {'ZALICZONA' if ok_u else 'NIEZALICZONA'}"
            ),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--katalog", default=str(KATALOG_1D))
    ap.add_argument("--do", default="2026-09-30", help="ostatni dzień danych (włącznie)")
    ap.add_argument("--ostatnie", type=int, default=0, help="ostatnie N wierszy panelu (0 = cały)")
    ap.add_argument("--monety", default=",".join(MONETY_020))
    ap.add_argument("--bez-kontroli", action="store_true")
    a = ap.parse_args(argv)
    monety = [x for x in a.monety.split(",") if x]
    if not a.bez_kontroli and len(monety) != K_020:
        raise ValueError(f"kryteria kontroli skalibrowano dla K = {K_020}")

    panel, inw, wyciete = panel_wspolny(monety, a.katalog, a.do)
    print(m.tekst_inwentarza(inw, panel, wyciete, a.do))
    panel = ostatnie_wiersze(panel, a.ostatnie)
    print()
    print(tekst_opisu(m.pomiar(panel.to_numpy())))
    if not a.bez_kontroli:
        n = len(panel)
        print()
        print(
            tekst_kontroli(
                m.kontrola(0.8, ZIARNA_DODATNIEJ, k=K_020, n=n),
                m.kontrola(0.0, ZIARNA_UJEMNEJ, k=K_020, n=n),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
