"""
Karta 024, część z wynikami: ile razy rzeczywisty dzienny low/high dotknął progu likwidacji w ciągu 7 dni od wpisu
wobec liczby, której oczekuje model (σ̂/ν̂ walk-forward). Procedura i kryteria — w README rundy (pre-rejestracja
zacommitowana wcześniej). Skrypt tylko raportuje; werdykt podpisuje Claude w README (R14).

    PYTHONPATH=. python -m modele.run_lq024
"""

from __future__ import annotations

from itertools import pairwise
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import poisson

from dane.ladowanie import wczytaj_swiece
from dane.zwroty_dzienne import KATALOG_1D, panel_wspolny
from modele.likwidacja_model import START, p_model, sigma_nu_walk_forward
from modele.likwidacja_zdarzenia import dotkniecia, klastry
from modele.run_lq024_mierzalnosc import DNI, DZWIGNIE, KOSZYK, MMR, STRONY, VR

P_PROG, RATIO_PROG, ODSTEP = 0.05, 1.5, 7
VR_WRAZLIWOSC = (1.0, VR, 4.0)
POZIOM_GLOWNY = 3.0


def swiece_na_panelu(moneta: str, indeks: pd.DatetimeIndex) -> pd.DataFrame:
    sw = wczytaj_swiece(Path(KATALOG_1D) / f"{moneta}.parquet")
    dzien = pd.DatetimeIndex(pd.to_datetime(sw["timestamp"], utc=True)).normalize()
    ramka = pd.DataFrame(
        {k: sw[k].to_numpy(dtype=float) for k in ("close", "high", "low")}, index=dzien
    )
    if ramka.index.has_duplicates:
        raise ValueError(f"{moneta}: duplikaty dni")
    return ramka.reindex(indeks)


def main() -> None:
    panel, _, _ = panel_wspolny(KOSZYK, do="2026-09-30")
    daty = panel.index
    n = len(panel)
    wpisy = np.arange(START - 1, n - 1)
    ok = np.array([i + DNI < n and (daty[i + DNI] - daty[i]).days == DNI for i in wpisy])
    print(f"Panel: {n} dni; wpisów {len(wpisy)}, z pełnym oknem {int(ok.sum())} ({ok.mean():.1%})")
    if ok.mean() < 0.95:
        raise SystemExit("STOP (R4.6): pełne okno w mniej niż 95 % wpisów")
    wpisy_ok = wpisy[ok]
    ramki, prognozy = {}, {}
    for m in KOSZYK:
        ramki[m] = swiece_na_panelu(m, daty)
        r = ramki[m]
        if r.isna().any().any() or not ((r.low <= r.close) & (r.close <= r.high)).all():
            raise SystemExit(f"STOP (R4.6): {m} ma dziury albo low/close/high niespójne")
        prognozy[m] = sigma_nu_walk_forward(panel[m].to_numpy())
    print("Dane high/low kompletne i spójne (low <= close <= high) dla wszystkich dni panelu.\n")

    wyniki = {}
    for L in DZWIGNIE:
        for strona in STRONY:
            e_okna = e_blok = 0.0
            trafien_okien = 0
            dni_wpisu, per_moneta = [], {}
            for m in KOSZYK:
                s, nu, _ = prognozy[m]
                p = p_model(s[ok], nu[ok], L, MMR, strona, DNI)
                e_okna += float(p.sum())
                e_blok += float(p[::DNI].sum())
                z = dotkniecia(
                    ramki[m].close.to_numpy(),
                    ramki[m].high.to_numpy(),
                    ramki[m].low.to_numpy(),
                    wpisy_ok,
                    L,
                    MMR,
                    strona,
                    DNI,
                )
                per_moneta[m] = int(z.sum())
                trafien_okien += int(z.sum())
                dni_wpisu.append(wpisy_ok[z])
            wyniki[(L, strona)] = {
                "e_okna": e_okna,
                "e_blok": e_blok,
                "trafien_okien": trafien_okien,
                "dni": np.concatenate(dni_wpisu),
                "per_moneta": per_moneta,
            }

    print("Opis (nakładające się okna, 4 monety razem; bez klastrów):")
    print(f"{'L':>3} {'strona':>6} {'trafień okien':>14} {'E okien':>9} {'iloraz':>7}  per moneta")
    for (L, strona), w in wyniki.items():
        print(
            f"{L:>3g} {strona:>6} {w['trafien_okien']:>14d} {w['e_okna']:>9.1f} "
            f"{w['trafien_okien'] / w['e_okna']:>7.2f}  {w['per_moneta']}"
        )

    print(f"\nWYNIK (klastry: trafienia o dniach wpisu <= {ODSTEP} dni od siebie = jeden klaster):")
    print(
        f"{'poziom':>14} {'O':>4} {'E niezal.':>10} {'O/E':>6} {'p (Poisson)':>12}   O/E przy VR 1 / 4"
    )
    glowny = None
    for L in DZWIGNIE:
        grupy = [("long+short", [(L, "long"), (L, "short")])] + [(s, [(L, s)]) for s in STRONY]
        for nazwa, klucze in grupy:
            o = klastry(np.concatenate([wyniki[k]["dni"] for k in klucze]), ODSTEP)
            blok = sum(wyniki[k]["e_blok"] for k in klucze)
            e = blok / VR
            p = float(poisson.sf(o - 1, e)) if o > 0 else 1.0
            wr = [o / (blok / v) for v in (VR_WRAZLIWOSC[0], VR_WRAZLIWOSC[2])]
            znacznik = (
                "  <- POZIOM GŁÓWNY" if (L == POZIOM_GLOWNY and nazwa == "long+short") else ""
            )
            print(
                f"{f'{L:g}× {nazwa}':>14} {o:>4d} {e:>10.2f} {o / e:>6.2f} {p:>12.4f}   "
                f"{wr[0]:.2f} / {wr[1]:.2f}{znacznik}"
            )
            if znacznik:
                glowny = (o, e, p)
    o, e, p = glowny
    print(
        f"\nPoziom główny: O = {o}, E = {e:.2f}, O/E = {o / e:.2f}, p = {p:.4f}; progi: "
        f"p < {P_PROG} ORAZ O/E >= {RATIO_PROG}  ->  "
        + ("MODEL ZANIŻA" if (p < P_PROG and o / e >= RATIO_PROG) else "NIE WYKAZANO ZANIŻENIA")
    )
    dni_gl = np.concatenate([wyniki[(POZIOM_GLOWNY, s)]["dni"] for s in STRONY])
    zdarzenia = np.unique(dni_gl)
    print("\nDni wpisu klastrów poziomu głównego (pierwszy dzień każdego klastra):")
    pierwsze = [int(zdarzenia[0])] if len(zdarzenia) else []
    pierwsze += [int(b) for a, b in pairwise(zdarzenia) if b - a > ODSTEP]
    print(", ".join(str(daty[i].date()) for i in pierwsze))


if __name__ == "__main__":
    main()
