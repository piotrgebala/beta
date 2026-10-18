"""
F2-3 — HAR + pięć wskaźników technicznych vs czysty HAR na stracie QLIKE, horyzont 1 dzień, BTC, ETH,
SOL, BNB (prognoza ZMIENNOŚCI, nie kierunku). Pre-rejestracja: `runs/2026-10-18_f23-har-techniczne/README.md`
(zapisana przed przebiegiem). Neutralny reporter (R14).

Jedna zmienna względem HAR: dochodzi pięć regresorów z `cechy.techniczne` (opóźnienie 0, wiersz d =
informacja po dobie d). Model: zwykła regresja najmniejszych kwadratów (R17, bez regularyzacji i bez
strojenia, R18). Baseline = czysty HAR na DOKŁADNIE tych samych wierszach (`uzyj_dodatkowych=False`).
Bramka, test DM i werdykt są z `modele.run_f22` (kolumny strat `q_har`, `q_harx` — tu `q_harx` to HAR + cechy
techniczne). Dane, dni ważne, okres i walk-forward jak F2-1b (`run_f21b.szeregi_monety`).

Krok 1 (R3): bramka mierzalności, próg |t| = Z_HOLM (Bonferroni na 3 pary modeli licznika „zmienność
2021+”). Krok 2: DM per moneta; POZYTYWNY ⇔ t > Z_HOLM w ≥ ⌈0,8 · 4⌉ = 4 monetach i żadna z t < −Z_HOLM.

    python -m modele.run_f23 --tylko-dni      # dni OOS bez strat (pre-rejestracja)
    python -m modele.run_f23 > runs/2026-10-18_f23-har-techniczne/raw_output.txt
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from cechy import techniczne
from dane.ohlc import ohlc_dzienne
from modele import run_f21b as b
from modele import run_f22 as f22
from modele.run_f21 import DELTA_ZAKLADANE
from modele.zmiennosc import prognoza_har

ROOT = Path(__file__).resolve().parents[1]
MONETY = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT")
Z_HOLM = float(norm.isf(0.025 / 3.0))  # 2,3940: α = 0,05 podzielone na 3 pary modeli
ZIARNO_ZASTEPCZE = 2302
CECHY = ("zakres_dzien", "atr14", "ema20_odl", "bb20_szer", "rsi14")

# Pre-rejestracja (README, „Wynik doboru dni”): policzone `--tylko-dni` przed zapisem, bez strat.
OCZEKIWANE: dict | None = {
    "monety": MONETY,
    "dni_oos": {"BTCUSDT": 1703, "ETHUSDT": 1703, "SOLUSDT": 1636, "BNBUSDT": 1703},
    "odcisk": "8c22047ed61fb1b6",
}


@dataclass(frozen=True)
class Ustawienia(f22.Ustawienia):
    z: float = Z_HOLM


def cechy_techniczne(df5m: pd.DataFrame) -> pd.DataFrame:
    """Pięć cech z `cechy.techniczne` (kolumny w kolejności CECHY) na kalendarzu dziennym."""
    d = ohlc_dzienne(df5m)
    return pd.concat([getattr(techniczne, f"compute_{n}")(d) for n in CECHY], axis=1)


def prognozy(rv: pd.Series, x: pd.DataFrame, u: Ustawienia) -> pd.DataFrame:
    """RV i prognozy dnia t+1 (w wierszu t+1): czysty HAR i HAR + cechy techniczne, wspólna próba."""
    return pd.DataFrame(
        {
            "rv": rv,
            "f_har": prognoza_har(rv, u.min_trening, u.co_ile, x, uzyj_dodatkowych=False),
            "f_harx": prognoza_har(rv, u.min_trening, u.co_ile, x, uzyj_dodatkowych=True),
        }
    )


def straty_monety(df5m: pd.DataFrame, u: Ustawienia) -> pd.DataFrame:
    uf = u.f21b()
    ob = b.obetnij(df5m, uf)
    rv, _ = b.szeregi_monety(ob, uf)
    return f22.straty(prognozy(rv, cechy_techniczne(ob), u))


def dni_oos(df5m: pd.DataFrame, u: Ustawienia) -> pd.DatetimeIndex:
    """
    Dni OOS bez prognoz na prawdziwych wartościach: ten sam przebieg na szeregach zastępczych (losowe
    liczby tam, gdzie RV i cecha są znane; NaN tam, gdzie nie). Dni nie niosą informacji, który model
    jest lepszy.
    """
    uf = u.f21b()
    ob = b.obetnij(df5m, uf)
    rv, _ = b.szeregi_monety(ob, uf)
    x = cechy_techniczne(ob).reindex(rv.index)
    rng = np.random.default_rng(ZIARNO_ZASTEPCZE)
    rv_z = pd.Series(np.exp(rng.normal(-7.0, 1.0, len(rv))), index=rv.index).where(rv.notna())
    x_z = pd.DataFrame(rng.normal(0.0, 1.0, x.shape), index=x.index, columns=x.columns).where(
        x.notna()
    )
    return f22.straty(prognozy(rv_z, x_z, u)).index


def przebieg(
    swiece: dict[str, pd.DataFrame],
    u: Ustawienia,
    tylko_dni: bool,
    oczekiwane: dict | None = None,
) -> dict:
    """Dni OOS → [zgodność z pre-rejestracją] → straty → kontrola dni → Krok 1 → Krok 2."""
    monety = list(MONETY)
    wynik: dict = {"etap": "dni"}
    print(f"Z (kryterium, po korekcie na 3 pary) = {u.z:.4f}; bramka MDE ≤ {DELTA_ZAKLADANE}")
    oos = {s: dni_oos(swiece[s], u) for s in monety}
    for s in monety:
        print(f"  {s:<10} {len(oos[s]):5d} dni OOS: {b._d(oos[s].min())} … {b._d(oos[s].max())}")
    print(f"  odcisk dni OOS {b.odcisk_oos(oos)}")
    roznice = b.zgodnosc_z_rejestracja(monety, oos, oczekiwane)
    if oczekiwane is not None:
        print(
            "  zgodność z pre-rejestracją (dni OOS, odcisk): " + ("tak" if not roznice else "NIE")
        )
        for r in roznice:
            print(f"    - {r}")
    if tylko_dni:
        print("\n--tylko-dni: koniec (bez strat, bez bramki, bez testu).")
        return wynik
    if roznice:
        print("  → STOP przed stratami: dane różnią się od pre-rejestracji; licznik bez zmian.")
        wynik["etap"] = "stop_dane"
        return wynik

    st = {s: straty_monety(swiece[s], u) for s in monety}
    if not all(st[s].index.equals(oos[s]) for s in monety):
        print("  → STOP: dni strat ≠ dni OOS; licznik „zmienność 2021+” bez zmian.")
        wynik["etap"] = "stop_dni"
        return wynik

    g = f22.bramka(st, u)
    wynik["bramka"] = g
    print(
        f"\nKrok 1 — bramka mierzalności (R3): dni kalendarza {g['dni_kalendarza']} "
        f"(wspólne {g['dni_wspolne']}), n (mediana) {g['n_mediana']}, "
        f"N_eff/n {g['neff_n']:.2f}, korel. różnic strat {g['korel_D']:.2f}"
    )
    print(
        f"  MDE kryterium {g['mde_kryterium']:.3f} (1 moneta {g['mde_moneta']:.3f}); "
        f"próg {DELTA_ZAKLADANE}; opis przy Z = 1,96: {g['mde_kryterium_196']:.3f}"
    )
    if not g["mde_kryterium"] <= DELTA_ZAKLADANE:
        print(
            "  → NIEMIERZALNA: test DM NIE jest uruchamiany (licznik „zmienność 2021+” bez zmian)."
        )
        wynik["etap"] = "niemierzalna"
        return wynik
    print("  → MIERZALNA: krok 2 (odczyt licznika „zmienność 2021+”: 2 → 3).")

    rows = f22.test_dm(st)
    w = f22.werdykt([r["t_qlike"] for r in rows], u.udzial, u.z)
    print("\nKrok 2 — DM na QLIKE (t > 0: HAR + cechy techniczne lepszy), per moneta:")
    print(" symbol     |    n | od         | t QLIKE |  δ     | t MSE log")
    for r in rows:
        print(
            f" {r['symbol']:<10} | {r['n']:4d} | {r['od']} | {r['t_qlike']:+7.2f} | "
            f"{r['delta']:+.3f} | {r['t_mse_log']:+9.2f}"
        )
    print(
        f"\nKryterium F2-3: t > {u.z:.2f} w {w['good']}/{w['k']} monet (wymagane ≥ {w['need']}), "
        f"t < −{u.z:.2f}: {w['bad']} → {'POZYTYWNY' if w['ok'] else 'NIEPOZYTYWNY'}"
    )
    wynik.update(etap="test", werdykt=w, wiersze=rows)
    return wynik


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="F2-3: HAR + wskaźniki techniczne vs HAR (QLIKE, DM).")
    ap.add_argument("--dane", type=Path, default=ROOT / "data" / "binance_um" / "5m")
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--tylko-dni", action="store_true", help="dni OOS, bez strat")
    a = ap.parse_args(argv)
    from dane.ladowanie import wczytaj_swiece

    u = replace(Ustawienia(), reps=a.reps)
    swiece = {s: wczytaj_swiece(a.dane / f"{s}.parquet") for s in MONETY}
    print("F2-3 — HAR + wskaźniki techniczne vs czysty HAR (QLIKE, 1 dzień), BTC, ETH, SOL, BNB")
    przebieg(swiece, u, a.tylko_dni, OCZEKIWANE)


if __name__ == "__main__":
    main()
