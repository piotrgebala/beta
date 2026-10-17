"""
F2-2 — HAR + log DVOL vs czysty HAR na stracie QLIKE, horyzont 1 dzień, BTC i ETH (jedyne monety z
ciągłym DVOL). Pre-rejestracja: `runs/2026-10-17_f22-har-dvol/README.md` (zapisana przed przebiegiem).
Neutralny reporter (R14).

Jedna zmienna względem HAR: dochodzi regresor log DVOL (zamknięcie dnia d−1 w wierszu d, rejestr cech
`dvol_opozn`, opóźnienie 1 dzień). Baseline (R17) = czysty HAR liczony na DOKŁADNIE tych samych wierszach
(`prognoza_har(..., uzyj_dodatkowych=False)`), więc różnica strat to wyłącznie wkład DVOL, nie dłuższy
trening. Dane, dni ważne, okres i walk-forward jak F2-1b (`run_f21b.szeregi_monety`).

Krok 1 (R3): bramka mierzalności na centrowanej różnicy strat (średnia różnicy nie wychodzi z funkcji),
próg |t| = Z_HOLM (korekta Bonferroniego na 2 pary modeli licznika „zmienność 2021+”; górna granica Holma).
Krok 2: DM per moneta; POZYTYWNY ⇔ t > Z_HOLM w obu monetach i żadna z t < −Z_HOLM.

    python -m modele.run_f22 --tylko-dni      # dni OOS bez strat (pre-rejestracja)
    python -m modele.run_f22 > runs/2026-10-17_f22-har-dvol/raw_output.txt
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from cechy.zmiennosc import compute_dvol_opozn
from miara.dm import diebold_mariano, mse_log, qlike
from modele import run_f21b as b
from modele.run_f21 import DELTA_ZAKLADANE, DELTAS
from modele.zmiennosc import prognoza_har
from symulacje.moc_dm import Z, mde, moc_kryterium_braki

ROOT = Path(__file__).resolve().parents[1]
PARY = (("BTCUSDT", "BTC"), ("ETHUSDT", "ETH"))  # (symbol Binance, waluta DVOL)
Z_HOLM = float(norm.isf(0.025 / 2.0))  # 2,2414: α = 0,05 podzielone na 2 pary modeli
UDZIAL = 0.8
ZIARNO_BRAMKI = 2201
ZIARNO_ZASTEPCZE = 2202

# Pre-rejestracja (README, „Wynik doboru dni”): policzone `--tylko-dni` przed zapisem, bez strat.
OCZEKIWANE: dict | None = {
    "monety": ("BTCUSDT", "ETHUSDT"),
    "dni_oos": {"BTCUSDT": 1650, "ETHUSDT": 1650},
    "odcisk": "f10ec282c39ae538",
}


@dataclass(frozen=True)
class Ustawienia:
    okres_do: pd.Timestamp = b.OKRES_DO
    min_trening: int = 365
    co_ile: int = 30
    reps: int = 1000
    blok: int = 30
    z: float = Z_HOLM
    udzial: float = UDZIAL

    def f21b(self) -> b.Ustawienia:
        return replace(b.Ustawienia(), okres_do=self.okres_do)


# ------------------------------------------------- szeregi, prognozy, straty


def log_dvol(dvol: pd.DataFrame) -> pd.Series:
    """log DVOL z opóźnieniem 1 dnia (rejestr `dvol_opozn`); close ≤ 0 → NaN, nigdy −∞."""
    s = compute_dvol_opozn(dvol)
    return np.log(s.where(s > 0)).rename("ldvol")


def prognozy(rv: pd.Series, ldv: pd.Series, u: Ustawienia) -> pd.DataFrame:
    """RV i prognozy dnia t+1 (w wierszu t+1): czysty HAR i HAR + log DVOL na wspólnej próbie."""
    dod = ldv.to_frame()
    return pd.DataFrame(
        {
            "rv": rv,
            "f_har": prognoza_har(rv, u.min_trening, u.co_ile, dod, uzyj_dodatkowych=False),
            "f_harx": prognoza_har(rv, u.min_trening, u.co_ile, dod, uzyj_dodatkowych=True),
        }
    )


def straty(p: pd.DataFrame) -> pd.DataFrame:
    out = p.dropna()
    out = out[(out["rv"] > 0) & (out["f_har"] > 0) & (out["f_harx"] > 0)].copy()
    out["q_har"] = qlike(out["rv"], out["f_har"])
    out["q_harx"] = qlike(out["rv"], out["f_harx"])
    out["m_har"] = mse_log(out["rv"], out["f_har"])
    out["m_harx"] = mse_log(out["rv"], out["f_harx"])
    return out


def straty_monety(df5m: pd.DataFrame, dvol: pd.DataFrame, u: Ustawienia) -> pd.DataFrame:
    uf = u.f21b()
    rv, _ = b.szeregi_monety(b.obetnij(df5m, uf), uf)
    return straty(prognozy(rv, log_dvol(dvol), u))


def dni_oos(df5m: pd.DataFrame, dvol: pd.DataFrame, u: Ustawienia) -> pd.DatetimeIndex:
    """
    Dni OOS bez prognoz na prawdziwych wartościach: ten sam przebieg na szeregach zastępczych
    (losowe dodatnie liczby tam, gdzie RV i DVOL są znane; NaN tam, gdzie nie). Prognoza istnieje
    dokładnie wtedy, gdy istnieje wzór braków — więc dni nie niosą informacji, który model jest lepszy.
    """
    uf = u.f21b()
    rv, _ = b.szeregi_monety(b.obetnij(df5m, uf), uf)
    ldv = log_dvol(dvol)
    rng = np.random.default_rng(ZIARNO_ZASTEPCZE)
    rv_z = pd.Series(np.exp(rng.normal(-7.0, 1.0, len(rv))), index=rv.index).where(rv.notna())
    l_z = pd.Series(rng.normal(4.0, 0.3, len(ldv)), index=ldv.index).where(ldv.notna())
    return straty(prognozy(rv_z, l_z, u)).index


# ------------------------------------------------- bramka i werdykt


def bramka(st: dict[str, pd.DataFrame], u: Ustawienia) -> dict:
    """MDE kryterium na centrowanej różnicy strat (baseline − HAR+DVOL); bez średniej różnicy."""
    D = pd.DataFrame({s: v["q_har"] - v["q_harx"] for s, v in st.items()}).sort_index()
    Dc = (D - D.mean()).to_numpy()
    moc = moc_kryterium_braki(Dc, DELTAS, u.reps, u.blok, seed=ZIARNO_BRAMKI, share=u.udzial, z=u.z)
    opis = moc_kryterium_braki(Dc, DELTAS, u.reps, u.blok, seed=ZIARNO_BRAMKI, share=u.udzial, z=Z)
    neff = []
    for c in D.columns:
        x = (D[c] - D[c].mean()).dropna().to_numpy()
        neff.append(diebold_mariano(x, np.zeros(len(x)))["n_eff"] / len(x))
    kor = D.corr(min_periods=100).to_numpy()[np.triu_indices(D.shape[1], 1)]
    return {
        "dni_kalendarza": len(D),
        "dni_wspolne": int(D.notna().all(axis=1).sum()),
        "n_mediana": int(np.median([len(v) for v in st.values()])),
        "neff_n": float(np.mean(neff)),
        "korel_D": float(np.nanmean(kor)),
        "mde_kryterium": mde(DELTAS, moc["moc_kryterium"]),
        "mde_moneta": mde(DELTAS, moc["moc_moneta"]),
        "mde_kryterium_196": mde(DELTAS, opis["moc_kryterium"]),
    }


def werdykt(t: list[float], udzial: float = UDZIAL, z: float = Z_HOLM) -> dict:
    """POZYTYWNY ⇔ t > z w ≥ ⌈udzial · K⌉ monet i żadna z t < −z (t > 0 = HAR+DVOL lepszy)."""
    k = len(t)
    need = math.ceil(udzial * k - 1e-12)
    good = sum(x > z for x in t)
    bad = sum(x < -z for x in t)
    return {"k": k, "need": need, "good": good, "bad": bad, "ok": good >= need and bad == 0}


def test_dm(st: dict[str, pd.DataFrame]) -> list[dict]:
    rows = []
    for s, v in st.items():
        q = diebold_mariano(v["q_har"], v["q_harx"])
        m = diebold_mariano(v["m_har"], v["m_harx"])
        rows.append(
            {
                "symbol": s,
                "n": q["n"],
                "od": str(v.index.min().date()),
                "t_qlike": q["t"],
                "delta": q["mean_d"] / float((v["q_har"] - v["q_harx"]).std()),
                "t_mse_log": m["t"],
            }
        )
    return rows


# ------------------------------------------------- przebieg


def przebieg(
    swiece: dict[str, pd.DataFrame],
    dvol: dict[str, pd.DataFrame],
    u: Ustawienia,
    tylko_dni: bool,
    oczekiwane: dict | None = None,
) -> dict:
    """Dni OOS → [zgodność z pre-rejestracją] → straty → kontrola dni → Krok 1 → Krok 2."""
    monety = [s for s, _ in PARY]
    wynik: dict = {"etap": "dni"}
    print(f"Z (kryterium, po korekcie na 2 pary) = {u.z:.4f}; bramka MDE ≤ {DELTA_ZAKLADANE}")
    oos = {s: dni_oos(swiece[s], dvol[w], u) for s, w in PARY}
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

    st = {s: straty_monety(swiece[s], dvol[w], u) for s, w in PARY}
    if not all(st[s].index.equals(oos[s]) for s in monety):
        print("  → STOP: dni strat ≠ dni OOS; licznik „zmienność 2021+” bez zmian.")
        wynik["etap"] = "stop_dni"
        return wynik

    g = bramka(st, u)
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
    print("  → MIERZALNA: krok 2 (odczyt licznika „zmienność 2021+”: 1 → 2).")

    rows = test_dm(st)
    w = werdykt([r["t_qlike"] for r in rows], u.udzial, u.z)
    print("\nKrok 2 — DM na QLIKE (t > 0: HAR+DVOL lepszy), per moneta:")
    print(" symbol     |    n | od         | t QLIKE |  δ     | t MSE log")
    for r in rows:
        print(
            f" {r['symbol']:<10} | {r['n']:4d} | {r['od']} | {r['t_qlike']:+7.2f} | "
            f"{r['delta']:+.3f} | {r['t_mse_log']:+9.2f}"
        )
    print(
        f"\nKryterium F2-2: t > {u.z:.2f} w {w['good']}/{w['k']} monet (wymagane ≥ {w['need']}), "
        f"t < −{u.z:.2f}: {w['bad']} → {'POZYTYWNY' if w['ok'] else 'NIEPOZYTYWNY'}"
    )
    wynik.update(etap="test", werdykt=w, wiersze=rows)
    return wynik


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="F2-2: HAR + log DVOL vs HAR (QLIKE, DM).")
    ap.add_argument("--dane", type=Path, default=ROOT / "data" / "binance_um" / "5m")
    ap.add_argument("--dvol", type=Path, default=ROOT / "data" / "deribit_dvol")
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--tylko-dni", action="store_true", help="dni OOS, bez strat")
    a = ap.parse_args(argv)
    from dane.ladowanie import wczytaj_swiece

    u = replace(Ustawienia(), reps=a.reps)
    swiece = {s: wczytaj_swiece(a.dane / f"{s}.parquet") for s, _ in PARY}
    dvol = {w: pd.read_parquet(a.dvol / f"{w}_1d.parquet") for _, w in PARY}
    print("F2-2 — HAR + log DVOL vs czysty HAR (QLIKE, 1 dzień), BTC i ETH")
    przebieg(swiece, dvol, u, a.tylko_dni, OCZEKIWANE)


if __name__ == "__main__":
    main()
