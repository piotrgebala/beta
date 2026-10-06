"""
F2-1 — HAR-RV vs prognoza zmienności dziennika alpha (EWMA r², środek masy 60) na stracie QLIKE, horyzont
1 dzień, 20 monet. Pre-rejestracja: `runs/2026-10-01_f21-har-vs-dziennik/README.md` (zapisana przed danymi).
Neutralny reporter (R14). Uruchamiać na maszynie z danymi z zadania 002.

Krok 1 (R3) — bramka mierzalności na CENTROWANEJ różnicy strat (średnia nie jest drukowana): MDE kryterium
bootstrapem jak w LM1. MDE > 0,10 → NIEMIERZALNA, skrypt kończy BEZ testu DM (licznik się nie zmienia).
Krok 2 — test DM per moneta i kryterium F2 (PRD §10.4); to jest odczyt licznika „zmienność 2021+”.

    python -m modele.run_f21 > runs/2026-10-01_f21-har-vs-dziennik/raw_output.txt
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from dane.ladowanie import wczytaj_swiece
from dane.rv import SWIEC_NA_DZIEN, rv_dzienna
from miara.dm import diebold_mariano, mse_log, qlike
from modele.zmiennosc import prognoza_dziennik, prognoza_har
from symulacje.moc_dm import mde, moc_kryterium_braki

ROOT = Path(__file__).resolve().parents[1]
K_MONET = 20
MIN_SWIEC = math.ceil(0.95 * SWIEC_NA_DZIEN)  # dzień ważny: ≥ 274 z 288 świec 5m
DELTA_ZAKLADANE = 0.10
Z = 1.959964
DELTAS = np.round(np.arange(0.0, 0.3001, 0.005), 3)


def wybierz_monety(sklad: dict[str, list[str]], k: int = K_MONET) -> list[str]:
    """k symboli z największą liczbą miesięcy w składzie top-20 (remis → alfabetycznie)."""
    cnt: dict[str, int] = {}
    for syms in sklad.values():
        for s in syms:
            cnt[s] = cnt.get(s, 0) + 1
    return sorted(sorted(cnt), key=lambda s: -cnt[s])[:k]


def straty_monety(df5m: pd.DataFrame, min_trening: int = 365, co_ile: int = 30) -> pd.DataFrame:
    """Dzienne RV, prognozy i straty OOS jednej monety (wiersze: dni z obiema prognozami i ważnym RV)."""
    d = rv_dzienna(df5m)
    # Poprawka 1 (P1): RV = 0 (doba bez jednej zmiany ceny — martwe świece archiwum po wycofaniu kontraktu)
    # to brak handlu, więc dzień nieważny jak doba z < 274 świecami; inaczej log RV = −∞ psuje HAR.
    rv = d["rv"].where((d["n_swiec"] >= MIN_SWIEC) & (d["rv"] > 0))
    f_dz = prognoza_dziennik(d["r"])
    f_har = prognoza_har(rv, min_trening=min_trening, co_ile=co_ile)
    out = pd.DataFrame({"rv": rv, "f_dz": f_dz, "f_har": f_har}).dropna()
    out = out[(out["rv"] > 0) & (out["f_dz"] > 0)]
    out["q_dz"] = qlike(out["rv"], out["f_dz"])
    out["q_har"] = qlike(out["rv"], out["f_har"])
    out["m_dz"] = mse_log(out["rv"], out["f_dz"])
    out["m_har"] = mse_log(out["rv"], out["f_har"])
    return out


def bramka_mde(straty: dict[str, pd.DataFrame], reps: int = 1000, blok: int = 30) -> dict:
    """
    MDE kryterium na centrowanej różnicy strat (średnia różnicy nie wychodzi z funkcji). Poprawka 1 (P2):
    część wspólna OOS 20 monet jest pusta, więc bootstrap idzie po kalendarzu sumy dni OOS z brakami
    (`moc_kryterium_braki`) — każda moneta liczy t ze swoich dni.
    """
    D = pd.DataFrame({s: v["q_dz"] - v["q_har"] for s, v in straty.items()}).sort_index()
    n = int(np.median([len(v) for v in straty.values()]))
    Dc = D - D.mean()
    out = moc_kryterium_braki(Dc.to_numpy(), DELTAS, reps, blok, seed=2101)
    neff = []
    for c in Dc.columns:
        x = Dc[c].dropna().to_numpy()
        neff.append(diebold_mariano(x, np.zeros(len(x)))["n_eff"] / len(x))
    kor = Dc.corr(min_periods=100).to_numpy()[np.triu_indices(Dc.shape[1], 1)]
    return {
        "dni_kalendarza": len(D),
        "dni_wspolne": int(D.notna().all(axis=1).sum()),
        "n_mediana": n,
        "neff_n": float(np.mean(neff)),
        "korel_D": float(np.nanmean(kor)),
        "mde_kryterium": mde(DELTAS, out["moc_kryterium"]),
        "mde_moneta": mde(DELTAS, out["moc_moneta"]),
    }


def test_dm(straty: dict[str, pd.DataFrame]) -> list[dict]:
    rows = []
    for s, v in straty.items():
        q = diebold_mariano(v["q_dz"], v["q_har"])
        m = diebold_mariano(v["m_dz"], v["m_har"])
        rows.append(
            {
                "symbol": s,
                "n": q["n"],
                "od": str(v.index.min().date()),
                "t_qlike": q["t"],
                "delta": q["mean_d"] / float((v["q_dz"] - v["q_har"]).std()),
                "t_mse_log": m["t"],
                "skala_rv_do_r2": float(v["rv"].mean() / v["f_dz"].mean()),
            }
        )
    return rows


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="F2-1: HAR-RV vs zmienność dziennika (QLIKE, DM).")
    ap.add_argument("--dane", type=Path, default=ROOT / "data" / "binance_um" / "5m")
    ap.add_argument("--sklad", type=Path, default=ROOT / "dane" / "sklad_top20.json")
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--min-trening", type=int, default=365)
    a = ap.parse_args(argv)
    sklad = json.loads(a.sklad.read_text(encoding="utf-8"))
    monety = wybierz_monety(sklad)
    print(f"F2-1 — monety ({len(monety)}): {', '.join(monety)}")
    straty = {}
    for s in monety:
        path = a.dane / f"{s}.parquet"
        if not path.is_file():
            print(f"  {s}: brak pliku — pominięta")
            continue
        straty[s] = straty_monety(wczytaj_swiece(path), min_trening=a.min_trening)
        print(f"  {s}: {len(straty[s])} dni OOS od {straty[s].index.min().date()}")

    g = bramka_mde(straty, reps=a.reps)
    print(
        f"\nKrok 1 — bramka mierzalności (R3): dni kalendarza {g['dni_kalendarza']} (wspólne wszystkim "
        f"monetom {g['dni_wspolne']}), n (mediana) {g['n_mediana']}, "
        f"N_eff/n {g['neff_n']:.2f}, korel. różnic strat {g['korel_D']:.2f}"
    )
    print(
        f"  MDE kryterium {g['mde_kryterium']:.3f} (1 moneta {g['mde_moneta']:.3f}); próg {DELTA_ZAKLADANE}"
    )
    if not g["mde_kryterium"] <= DELTA_ZAKLADANE:
        print(
            "  → NIEMIERZALNA: test DM NIE jest uruchamiany (licznik „zmienność 2021+” bez zmian)."
        )
        return
    print("  → MIERZALNA: krok 2 (odczyt licznika „zmienność 2021+”: +1).")

    rows = test_dm(straty)
    k = len(rows)
    need = math.ceil(0.8 * k - 1e-12)
    good = sum(r["t_qlike"] > Z for r in rows)
    bad = sum(r["t_qlike"] < -Z for r in rows)
    print("\nKrok 2 — DM na QLIKE (t > 0: HAR lepszy), per moneta:")
    print(
        " symbol        |    n | od         | t QLIKE |  δ     | t MSE log | RV / prognoza dziennika"
    )
    for r in rows:
        print(
            f" {r['symbol']:<13} | {r['n']:4d} | {r['od']} | {r['t_qlike']:+7.2f} | {r['delta']:+.3f} | "
            f"{r['t_mse_log']:+9.2f} | {r['skala_rv_do_r2']:.2f}"
        )
    ok = good >= need and bad == 0
    print(
        f"\nKryterium F2: t > 1,96 w {good}/{k} monet (wymagane ≥ {need}), istotnie gorszych: {bad} → "
        f"{'POZYTYWNE' if ok else 'NIE SPEŁNIONE'}"
    )


if __name__ == "__main__":
    main()
