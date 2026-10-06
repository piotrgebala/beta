"""
F2-1b — HAR-RV vs prognoza zmienności dziennika alpha (EWMA r², środek masy 60) na stracie QLIKE,
horyzont 1 dzień, monety dobrane po DŁUGOŚCI danych. Pre-rejestracja:
`runs/2026-10-06_f21b-har-vs-dziennik-dlugie/README.md` (zapisana przed przebiegiem).
Neutralny reporter (R14).

Ten sam wariant hipotezy co F2-1 (R2: zbiór informacyjny, formuła, target, horyzont, baseline,
walk-forward — funkcje importowane z `modele.zmiennosc` i `modele.run_f21`). Jedyna kopia: blok
strat `straty()` (z `run_f21.straty_monety`, którego maski nie da się wydzielić — runda zamknięta);
parytet pilnuje `test_parytet_z_f21_bez_flagi`.
Zmienia się tylko populacja monet i obsługa dni ważnych (`dane.dni.dni_wazne`, zadanie 014):
- dobór: ≥ 12 miesięcy w składzie top-20 point-in-time od 2021-01 ORAZ dni ważne od ≤ 2021-01-31
  do ≥ 2026-09-30 i ≥ 95 % dni ważnych w okresie 2021-01-01…2026-09-30; K = min(20, liczba) wg
  liczby miesięcy w top-20 (remis → alfabetycznie); K < 12 → NIEMIERZALNA z definicji;
- dzień ważny = `wazny & ~martwy` z `dni_wazne(..., wyklucz_po_dziurze=True)`;
- dane obcięte na 2026-09-30 włącznie (dopisywanie danych przez automat nie zmienia wyniku).

Krok 1 (R3) — bramka mierzalności jak F2-1 (`run_f21.bramka_mde`: centrowana różnica strat,
ziarno 2101). Krok 2 — test DM per moneta i kryterium: t > 1,96 w ≥ ⌈0,8 K⌉ monet i żadna
z t < −1,96 (`werdykt`). Stop bez bramki i testu (licznik bez zmian), gdy monety / dni OOS
różnią się od pre-rejestracji (`OCZEKIWANE`) albo dni strat ≠ dni OOS.

    python -m modele.run_f21b > runs/2026-10-06_f21b-har-vs-dziennik-dlugie/raw_output.txt
    python -m modele.run_f21b --tylko-monety   # dobór i dni OOS, BEZ strat (pre-rejestracja)
    python -m modele.run_f21b --smoke          # cały przebieg na syntetycznych danych GARCH
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

from dane.dni import dni_wazne
from dane.ladowanie import wczytaj_swiece
from dane.rv import rv_dzienna
from miara.dm import mse_log, qlike
from modele.run_f21 import DELTA_ZAKLADANE, Z, bramka_mde, test_dm
from modele.zmiennosc import prognoza_dziennik, prognoza_har
from symulacje.moc_dm import moc_kryterium_braki

ROOT = Path(__file__).resolve().parents[1]
DZIEN = pd.Timedelta(days=1)
ZIARNO_ZASTEPCZE = 2102  # szereg zastępczy do liczenia dni OOS bez prognoz na prawdziwym RV
OKRES_OD = pd.Timestamp("2021-01-01", tz="UTC")
OKRES_DO = pd.Timestamp("2026-09-30", tz="UTC")  # ostatni dzień danych (włącznie)
NAJPOZNIEJ_START = pd.Timestamp("2021-01-31", tz="UTC")
# Bramka (`run_f21.bramka_mde` → `moc_kryterium_braki`) liczy moc dla udziału z domyślnego `share`;
# kryterium kroku 2 musi używać tego samego udziału (przegląd, przed przebiegiem).
UDZIAL_BRAMKI = inspect.signature(moc_kryterium_braki).parameters["share"].default

# Pre-rejestracja (README, „Wynik doboru”): monety i dni OOS policzone `--tylko-monety` przed
# zapisem (tylko dostępność danych). Przebieg na prawdziwych danych porównuje z tym PRZED stratami;
# jakakolwiek różnica (np. dane pobrane ponownie) → stop bez strat, licznik bez zmian, Poprawka.
OCZEKIWANE_MONETY = (
    "BNBUSDT", "BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT",
    "AVAXUSDT", "LTCUSDT", "BCHUSDT", "DOTUSDT", "FILUSDT", "ETCUSDT", "NEARUSDT",
)  # fmt: skip
OCZEKIWANE_DNI_OOS = {s: 1703 for s in OCZEKIWANE_MONETY} | {
    s: 1636 for s in ("XRPUSDT", "SOLUSDT", "LTCUSDT", "FILUSDT", "NEARUSDT")
}
OCZEKIWANY_ODCISK = "80001c5c1ca5686c"
OCZEKIWANE = {
    "monety": OCZEKIWANE_MONETY,
    "dni_oos": OCZEKIWANE_DNI_OOS,
    "odcisk": OCZEKIWANY_ODCISK,
}


@dataclass(frozen=True)
class Ustawienia:
    """Parametry z pre-rejestracji (smoke zmienia tylko długość okresu, K_min, trening, reps)."""

    okres_od: pd.Timestamp = OKRES_OD
    okres_do: pd.Timestamp = OKRES_DO
    najpozniej_start: pd.Timestamp = NAJPOZNIEJ_START
    min_miesiecy: int = 12
    min_udzial: float = 0.95
    k_max: int = 20
    k_min: int = 12
    udzial_kryterium: float = UDZIAL_BRAMKI  # = 0,8; ten sam udział co w bramce
    wyklucz_po_dziurze: bool = True
    min_trening: int = 365
    co_ile: int = 30
    reps: int = 1000


# ------------------------------------------------- dobór monet (tylko skład + dni ważne)


def miesiace_top20(sklad: dict[str, list[str]], od: str = "2021-01") -> dict[str, int]:
    """Liczba miesięcy w składzie top-20 point-in-time od miesiąca `od` (klucze RRRR-MM-DD)."""
    cnt: dict[str, int] = {}
    for miesiac, syms in sklad.items():
        if miesiac[:7] < od:
            continue
        for s in syms:
            cnt[s] = cnt.get(s, 0) + 1
    return cnt


def maska_dni(dni: pd.DataFrame) -> pd.Series:
    """Dzień ważny F2-1b: `wazny & ~martwy` z wyniku `dni_wazne` (pre-rejestracja, punkt 4)."""
    return dni["wazny"] & ~dni["martwy"]


def dostepnosc(dni: pd.DataFrame, u: Ustawienia) -> dict:
    """Pierwszy / ostatni dzień ważny i udział dni ważnych w okresie [okres_od, okres_do]."""
    m = maska_dni(dni)
    kal = pd.date_range(u.okres_od, u.okres_do, freq="D")
    w_okresie = m.reindex(kal, fill_value=False).astype(bool)
    wazne = m.index[m.to_numpy(dtype=bool)]
    return {
        "pierwszy": wazne.min() if len(wazne) else pd.NaT,
        "ostatni": wazne.max() if len(wazne) else pd.NaT,
        "dni_okresu": len(kal),
        "wazne_w_okresie": int(w_okresie.sum()),
        "udzial": float(w_okresie.mean()),
    }


def kwalifikuje(d: dict | None, u: Ustawienia) -> bool:
    if d is None or pd.isna(d["pierwszy"]):
        return False
    return bool(
        d["pierwszy"] <= u.najpozniej_start
        and d["ostatni"] >= u.okres_do
        and d["udzial"] >= u.min_udzial
    )


def dobierz_monety(
    miesiace: dict[str, int], dostep: dict[str, dict | None], u: Ustawienia
) -> list[str]:
    """
    Kandydat: ≥ `min_miesiecy` w top-20; kwalifikuje się przy dostępności z `kwalifikuje`.
    Z kwalifikujących K = min(k_max, liczba) wg liczby miesięcy w top-20 (remis → alfabetycznie).
    Wejście: tylko skład (miesiące) i dostępność dni ważnych — żadnych cen, zwrotów, RV ani strat.
    """
    ok = [s for s, n in miesiace.items() if n >= u.min_miesiecy and kwalifikuje(dostep.get(s), u)]
    return sorted(sorted(ok), key=lambda s: -miesiace[s])[: u.k_max]


# ------------------------------------------------- szeregi, prognozy, straty


def obetnij(df5m: pd.DataFrame, u: Ustawienia) -> pd.DataFrame:
    """Świece do końca dnia `okres_do` włącznie (dane dopisane później nie wchodzą)."""
    return df5m.loc[df5m["timestamp"] < u.okres_do + DZIEN].reset_index(drop=True)


def szeregi_monety(df5m: pd.DataFrame, u: Ustawienia) -> tuple[pd.Series, pd.Series]:
    """
    (rv, r) na wierszach dni ze świecami — tak jak F2-1 (`rv_dzienna`): rv = NaN w dniach nieważnych
    (maska `dni_wazne`), r = zwrot close-to-close dla baseline'u dziennika bez zmian.
    """
    d = rv_dzienna(df5m)
    dni = dni_wazne(df5m, wyklucz_po_dziurze=u.wyklucz_po_dziurze)
    m = maska_dni(dni).reindex(d.index, fill_value=False).astype(bool)
    return d["rv"].where(m), d["r"]


def prognozy(rv: pd.Series, r: pd.Series, u: Ustawienia) -> pd.DataFrame:
    """RV i prognozy dnia t+1 (w wierszu t+1): dziennik (EWMA 60) i HAR walk-forward (F2-1)."""
    return pd.DataFrame(
        {
            "rv": rv,
            "f_dz": prognoza_dziennik(r),
            "f_har": prognoza_har(rv, min_trening=u.min_trening, co_ile=u.co_ile),
        }
    )


def straty(p: pd.DataFrame) -> pd.DataFrame:
    """Wiersze z obiema prognozami i ważnym RV; straty QLIKE i MSE log (jak F2-1)."""
    out = p.dropna()
    out = out[(out["rv"] > 0) & (out["f_dz"] > 0)].copy()
    out["q_dz"] = qlike(out["rv"], out["f_dz"])
    out["q_har"] = qlike(out["rv"], out["f_har"])
    out["m_dz"] = mse_log(out["rv"], out["f_dz"])
    out["m_har"] = mse_log(out["rv"], out["f_har"])
    return out


def straty_monety_b(df5m: pd.DataFrame, u: Ustawienia) -> pd.DataFrame:
    return straty(prognozy(*szeregi_monety(obetnij(df5m, u), u), u))


def dni_oos(df5m: pd.DataFrame, u: Ustawienia) -> pd.DatetimeIndex:
    """
    Dni OOS BEZ prognoz na prawdziwym RV: ten sam przebieg na szeregu zastępczym (losowe dodatnie
    liczby z jawnym ziarnem tam, gdzie rv / r są znane; NaN tam, gdzie nie). Prognoza istnieje
    dokładnie wtedy, gdy istnieje wzór braków — więc daje te same dni, co `straty_monety_b`, bez
    żadnej informacji o tym, który model jest lepszy (test `test_dni_oos_zgodne_ze_stratami`).
    """
    rv, r = szeregi_monety(obetnij(df5m, u), u)
    rng = np.random.default_rng(ZIARNO_ZASTEPCZE)
    rv_z = pd.Series(np.exp(rng.normal(-7.0, 1.0, len(rv))), index=rv.index).where(rv.notna())
    r_z = pd.Series(rng.normal(0.0, 0.03, len(r)), index=r.index).where(r.notna())
    return straty(prognozy(rv_z, r_z, u)).index


def odcisk_oos(oos: dict[str, pd.DatetimeIndex]) -> str:
    """Odcisk (SHA-256, 16 znaków) listy monet i ich dni OOS — do porównania z pre-rejestracją."""
    tekst = "\n".join(f"{s}:" + ",".join(d.strftime("%Y-%m-%d") for d in v) for s, v in oos.items())
    return hashlib.sha256(tekst.encode()).hexdigest()[:16]


def zgodnosc_z_rejestracja(
    monety: list[str], oos: dict[str, pd.DatetimeIndex], oczekiwane: dict | None
) -> list[str]:
    """Różnice względem pre-rejestracji (pusta lista = zgodne; `oczekiwane` None = smoke/testy)."""
    if oczekiwane is None:
        return []
    roznice = []
    if tuple(monety) != tuple(oczekiwane["monety"]):
        roznice.append(f"monety {monety} ≠ {list(oczekiwane['monety'])}")
    for s in monety:
        n = oczekiwane["dni_oos"].get(s)
        if len(oos[s]) != n:
            roznice.append(f"{s}: {len(oos[s])} dni OOS ≠ {n}")
    if odcisk_oos(oos) != oczekiwane["odcisk"]:
        roznice.append(f"odcisk dni OOS {odcisk_oos(oos)} ≠ {oczekiwane['odcisk']}")
    return roznice


def werdykt(t: list[float], udzial: float) -> dict:
    """
    Reguła kroku 2 (pre-rejestracja): POZYTYWNY ⇔ t > 1,96 w ≥ ⌈udzial · K⌉ monet i żadna moneta
    z t < −1,96 (t > 0 = HAR lepszy). t równe dokładnie ±Z nie liczy się ani jako dobre, ani złe.
    """
    k = len(t)
    need = math.ceil(udzial * k - 1e-12)
    good = sum(x > Z for x in t)
    bad = sum(x < -Z for x in t)
    return {"k": k, "need": need, "good": good, "bad": bad, "ok": good >= need and bad == 0}


# ------------------------------------------------- przebieg


def _wczytaj(dane: Path, s: str, u: Ustawienia) -> pd.DataFrame | None:
    path = dane / f"{s}.parquet"
    return obetnij(wczytaj_swiece(path), u) if path.is_file() else None


def _d(x) -> str:
    return "—" if pd.isna(x) else str(x.date())


def wydruk_doboru(
    sklad: dict[str, list[str]], dane: Path, u: Ustawienia
) -> tuple[list[str], dict[str, pd.DataFrame]]:
    """Krok 0: kandydaci, dostępność, dobór, dni OOS (bez strat). Zwraca monety i ich świece."""
    mies = miesiace_top20(sklad)
    kand = sorted(sorted(s for s, n in mies.items() if n >= u.min_miesiecy), key=lambda s: -mies[s])
    print(
        f"Krok 0 — dobór monet: miesięcy w składzie top-20 {len(sklad)} "
        f"({min(sklad)[:7]}…{max(sklad)[:7]}); kandydaci z ≥ {u.min_miesiecy} mies.: {len(kand)}"
    )
    print(
        f"  warunek: dni ważne (wazny & ~martwy, wyklucz_po_dziurze={u.wyklucz_po_dziurze}) od ≤ "
        f"{_d(u.najpozniej_start)} do ≥ {_d(u.okres_do)}, udział ≥ {u.min_udzial:.0%} w "
        f"{_d(u.okres_od)}…{_d(u.okres_do)}"
    )
    print(
        " symbol          | mies. | pierwszy   | ostatni    | ważne / dni okresu | udział | kwal."
    )
    dostep: dict[str, dict | None] = {}
    swiece: dict[str, pd.DataFrame] = {}
    for s in kand:
        df = _wczytaj(dane, s, u)
        if df is None or df.empty:
            dostep[s] = None
            print(f" {s:<15} | {mies[s]:5d} | brak danych")
            continue
        dostep[s] = dostepnosc(dni_wazne(df, wyklucz_po_dziurze=u.wyklucz_po_dziurze), u)
        swiece[s] = df
        d = dostep[s]
        print(
            f" {s:<15} | {mies[s]:5d} | {_d(d['pierwszy'])} | {_d(d['ostatni'])} | "
            f"{d['wazne_w_okresie']:7d} / {d['dni_okresu']:<8d} | {d['udzial']:6.1%} | "
            f"{'tak' if kwalifikuje(d, u) else 'nie'}"
        )
    monety = dobierz_monety(mies, dostep, u)
    n_kwal = sum(kwalifikuje(dostep.get(s), u) for s in kand)
    print(f"\n  kwalifikuje się {n_kwal}; K = min({u.k_max}, {n_kwal}) = {len(monety)}")
    print(f"  monety ({len(monety)}): {', '.join(monety)}")
    return monety, {s: swiece[s] for s in monety}


def przebieg(
    sklad: dict[str, list[str]],
    dane: Path,
    u: Ustawienia,
    tylko_monety: bool,
    oczekiwane: dict | None = None,
) -> None:
    """
    Krok 0 (dobór, dni OOS) → [porównanie z pre-rejestracją] → straty → kontrola dni → Krok 1 →
    Krok 2. Każda niezgodność przed Krokiem 1 kończy przebieg BEZ bramki i testu (licznik bez
    zmian).
    """
    assert u.udzial_kryterium == UDZIAL_BRAMKI, "kryterium i bramka muszą mieć ten sam udział"
    monety, swiece = wydruk_doboru(sklad, dane, u)
    k = len(monety)
    if k < u.k_min:
        print(
            f"  → K = {k} < {u.k_min}: runda NIEMIERZALNA z definicji (pre-rejestracja). "
            "Bez strat i bez testu; licznik „zmienność 2021+” bez zmian."
        )
        return
    need = werdykt([0.0] * k, u.udzial_kryterium)["need"]
    print(
        f"  kryterium kroku 2: t > 1,96 w ≥ ⌈{u.udzial_kryterium} · {k}⌉ = {need} monet, "
        "0 z t < −1,96"
    )

    print("\nDni OOS (z wzoru braków, bez prognoz na prawdziwym RV):")
    oos = {s: dni_oos(swiece[s], u) for s in monety}
    for s in monety:
        print(f"  {s:<15} {len(oos[s]):5d} dni OOS: {_d(oos[s].min())} … {_d(oos[s].max())}")
    dl = [len(v) for v in oos.values()]
    kal = oos[monety[0]]
    for v in oos.values():
        kal = kal.union(v)
    print(
        f"  n (mediana) {int(np.median(dl))}, min {min(dl)}, maks {max(dl)}; dni kalendarza "
        f"(suma) {len(kal)}; odcisk dni OOS {odcisk_oos(oos)}"
    )
    roznice = zgodnosc_z_rejestracja(monety, oos, oczekiwane)
    if oczekiwane is not None:
        print(
            "  zgodność z pre-rejestracją (monety, dni OOS, odcisk): "
            + ("tak" if not roznice else "NIE")
        )
        for r in roznice:
            print(f"    - {r}")
    if tylko_monety:
        print("\n--tylko-monety: koniec (bez strat, bez bramki, bez testu).")
        return
    if roznice:
        print(
            "  → STOP przed stratami: dane różnią się od pre-rejestracji. Bez bramki i bez testu; "
            "licznik „zmienność 2021+” bez zmian; potrzebna Poprawka."
        )
        return

    st = {s: straty_monety_b(swiece[s], u) for s in monety}
    zgodne = all(st[s].index.equals(oos[s]) for s in monety)
    print(
        "  kontrola: dni strat = dni OOS z wzoru braków u wszystkich monet: "
        + ("tak" if zgodne else "NIE")
    )
    if not zgodne:
        print(
            "  → STOP przed Krokiem 1: dni strat ≠ dni OOS. Bez bramki i bez testu; "
            "licznik „zmienność 2021+” bez zmian; potrzebna Poprawka."
        )
        return

    g = bramka_mde(st, reps=u.reps)
    print(
        f"\nKrok 1 — bramka mierzalności (R3): dni kalendarza {g['dni_kalendarza']} "
        f"(wspólne wszystkim monetom {g['dni_wspolne']}), n (mediana) {g['n_mediana']}, "
        f"N_eff/n {g['neff_n']:.2f}, korel. różnic strat {g['korel_D']:.2f}"
    )
    print(
        f"  MDE kryterium {g['mde_kryterium']:.3f} (1 moneta {g['mde_moneta']:.3f}); "
        f"próg {DELTA_ZAKLADANE}"
    )
    if not g["mde_kryterium"] <= DELTA_ZAKLADANE:
        print(
            "  → NIEMIERZALNA: test DM NIE jest uruchamiany (licznik „zmienność 2021+” bez zmian)."
        )
        return
    print("  → MIERZALNA: krok 2 (odczyt licznika „zmienność 2021+”: 0 → 1).")

    rows = test_dm(st)
    w = werdykt([r["t_qlike"] for r in rows], u.udzial_kryterium)
    print("\nKrok 2 — DM na QLIKE (t > 0: HAR lepszy), per moneta:")
    print(
        " symbol          |    n | od         | t QLIKE |  δ     | t MSE log "
        "| RV / prognoza dziennika"
    )
    for r in rows:
        print(
            f" {r['symbol']:<15} | {r['n']:4d} | {r['od']} | {r['t_qlike']:+7.2f} | "
            f"{r['delta']:+.3f} | {r['t_mse_log']:+9.2f} | {r['skala_rv_do_r2']:.2f}"
        )
    print(
        f"\nKryterium F2-1b: t > 1,96 w {w['good']}/{w['k']} monet (wymagane ≥ {w['need']}), "
        f"t < −1,96: {w['bad']} → {'POZYTYWNY' if w['ok'] else 'NIEPOZYTYWNY'}"
    )


# ------------------------------------------------- dane syntetyczne (smoke, testy)


def swiece_syntetyczne(sigma2: np.ndarray, start: str, seed: int) -> pd.DataFrame:
    """Świece 5m z dzienną wariancją `sigma2` (zwroty 5m normalne, wariancja σ²/288), wolumen 1."""
    rng = np.random.default_rng(seed)
    var = np.repeat(np.asarray(sigma2, dtype=float), 288) / 288
    lr = rng.standard_normal(len(var)) * np.sqrt(var)
    ts = pd.date_range(start, periods=len(var), freq="5min", tz="UTC")
    return pd.DataFrame(
        {"timestamp": ts, "close": 100 * np.exp(np.cumsum(lr)), "volume": np.ones(len(var))}
    )


def smoke(n_dni: int = 2100, n_monet: int = 5, reps: int = 200) -> None:
    """Cały przebieg na panelu GARCH (kontrola pozytywna: oczekiwane MIERZALNA i POZYTYWNY)."""
    from symulacje.garch_panel import generuj_panel

    p = generuj_panel(n_dni, n_monet, seed=2103, rho=0.5)
    start = "2021-01-01"
    u = replace(
        Ustawienia(),
        okres_do=pd.Timestamp(start, tz="UTC") + (n_dni - 1) * DZIEN,
        k_min=3,
        min_trening=365,
        reps=reps,
    )
    with tempfile.TemporaryDirectory() as tmp:
        dane = Path(tmp)
        syms = list(p["sigma2"].columns)
        for j, s in enumerate(syms):
            df = swiece_syntetyczne(p["rv"].iloc[:, j].to_numpy(), start, seed=j)
            df.to_parquet(dane / f"{s}.parquet")
        sklad = {f"2021-{m:02d}-01": syms for m in range(1, 13)}
        print(f"SMOKE — dane syntetyczne GARCH: {n_monet} monet × {n_dni} dni, K_min = 3\n")
        przebieg(sklad, dane, u, tylko_monety=False)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description="F2-1b: HAR-RV vs zmienność dziennika, monety po długości."
    )
    ap.add_argument("--dane", type=Path, default=ROOT / "data" / "binance_um" / "5m")
    ap.add_argument("--sklad", type=Path, default=ROOT / "dane" / "sklad_top20.json")
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--tylko-monety", action="store_true", help="dobór i dni OOS, bez strat")
    ap.add_argument("--smoke", action="store_true", help="przebieg na danych syntetycznych")
    a = ap.parse_args(argv)
    if a.smoke:
        smoke()
        return
    u = replace(Ustawienia(), reps=a.reps)
    sklad = json.loads(a.sklad.read_text(encoding="utf-8"))
    print(
        "F2-1b — HAR-RV vs prognoza dziennika (QLIKE, 1 dzień), monety dobrane po długości danych"
    )
    przebieg(sklad, a.dane, u, tylko_monety=a.tylko_monety, oczekiwane=OCZEKIWANE)


if __name__ == "__main__":
    main()
