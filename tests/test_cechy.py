"""
Rejestr cech i bramka przecieku (010, FR-10..13, R7/R8/R19/R25): dane syntetyczne, bez sieci.

1. Jeden test po CAŁYM rejestrze: każda cecha przechodzi `sprawdz_przeciek` na danych swojego
   zbioru informacyjnego, z dziurami i bez (fabryka per zbiór, ziarno jawne). Cechy RV liczone
   są przez cały łańcuch od świec 5m (agregacja 5m → doba też podlega bramce).
2. Integralność rejestru: pola, daty ISO, brak duplikatów wariantów (R2, bez spacji i wielkości
   liter) i kluczy YAML, funkcje `compute_*` bez wpisu (także w podpakietach i jako obce wywołania),
   zakaz progów percentylowych zgodny z masą punktową surowych danych (FR-12).
3. Semantyka cech (definicje, maska ważności RV, okna kalendarzowe, opóźnienia, dziury).
4. Kontrola pozytywna (R8): cechy z celowym przeciekiem żyją tylko tutaj i muszą zostać złapane;
   osobno przecieki przez dziury, długość próby, warunki rzadkie, kolumny nieliczbowe.
5. Kontrola negatywna: poprawne cechy (także z opóźnieniem i z dziurami) nie dają fałszywego alarmu.
6. Przypięte zachowanie harnessu (domyślne zakłócenia, tolerancja, NaN, czystość, argumenty).
7. Masa punktowa (FR-12) i własności `hypothesis`.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import re
import sys
import types
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from functools import cache, partial
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

import cechy
from cechy import zmiennosc
from cechy.przeciek import (
    OBCIECIE,
    PROG_MASY,
    ZAKLOCENIA,
    MasaPunktowaBlad,
    Naruszenie,
    _zaklocona_kolumna,
    ciecia,
    masa_punktowa,
    sprawdz_przeciek,
    walidacja_progu_percentylowego,
)
from dane.rv import rv_dzienna
from modele.run_f21 import MIN_SWIEC
from modele.zmiennosc import cechy_har

ROOT = Path(__file__).resolve().parents[1]
REJESTR_YAML = ROOT / "cechy" / "rejestr.yaml"
INDEX_RUND = ROOT / "runs" / "INDEX.md"
POLA = {
    "funkcja",
    "zbior_informacyjny",
    "formula",
    "opoznienie_dni",
    "dodano",
    "runda_definicji",
    "runda",
    "progi",
    "wariant",
}
PROGI = {"absolutne", "percentylowe_dozwolone"}
DZIEN = pd.Timedelta(days=1)
START = pd.Timestamp("2021-01-01", tz="UTC")  # piątek


class _LoaderBezDuplikatow(yaml.SafeLoader):
    """SafeLoader odrzucający powtórzony klucz mapy (zwykły YAML po cichu bierze ostatni)."""


def _mapa_bez_duplikatow(loader, node, deep=False):
    klucze = [loader.construct_object(k, deep=True) for k, _ in node.value]
    powtorzone = sorted({str(k) for k in klucze if klucze.count(k) > 1})
    if powtorzone:
        raise ValueError(f"powtórzony klucz w YAML: {powtorzone}")
    return loader.construct_mapping(node, deep)


_LoaderBezDuplikatow.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapa_bez_duplikatow
)


def wczytaj_rejestr_z_tekstu(tekst: str) -> dict:
    return yaml.load(tekst, Loader=_LoaderBezDuplikatow)["cechy"]


def wczytaj_rejestr(path: Path = REJESTR_YAML) -> dict:
    return wczytaj_rejestr_z_tekstu(path.read_text(encoding="utf-8"))


REJESTR = wczytaj_rejestr()


# ---------- fabryki danych syntetycznych per zbiór informacyjny ----------

SLOTY_5M = 288
KROK_5M = pd.Timedelta(minutes=5)
KROK_8H = pd.Timedelta(hours=8)
BAZA = 1e-4  # stawka bazowa funding (masa punktowa)
# doby szczególne w świecach 5m z dziurami
DZIEN_BRAK, DZIEN_NIEPELNY, DZIEN_MARTWY, DZIEN_274, DZIEN_273 = 12, 20, 28, 35, 36


def _swiece_5m(dziury: bool = False, dni: int = 110, seed: int = 0) -> pd.DataFrame:
    """
    Świece 5m z dzienną zmianą zmienności. Z dziurami: doba 12 bez świec, doba 20 z 258 świecami,
    doba 28 martwa (stała cena = RV 0 przy 288 świecach), doba 35 z 274 (ważna) i 36 z 273 (nie).
    """
    rng = np.random.default_rng(seed)
    sd = np.repeat(0.002 * np.exp(0.4 * rng.normal(size=dni)), SLOTY_5M)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sd)))
    dzien = np.repeat(np.arange(dni), SLOTY_5M)
    slot = np.tile(np.arange(SLOTY_5M), dni)
    ts = pd.date_range(START, periods=dni * SLOTY_5M, freq="5min")
    if dziury:
        close[dzien == DZIEN_MARTWY] = close[dzien == DZIEN_MARTWY - 1][-1]
    df = pd.DataFrame({"timestamp": ts, "close": close})
    if not dziury:
        return df
    usun = (
        (dzien == DZIEN_BRAK)
        | ((dzien == DZIEN_NIEPELNY) & (slot >= 100) & (slot < 130))
        | ((dzien == DZIEN_274) & (slot < SLOTY_5M - 274))
        | ((dzien == DZIEN_273) & (slot < SLOTY_5M - 273))
    )
    return df[~usun].reset_index(drop=True)


def _dvol_1d(dziury: bool = False, dni: int = 200, seed: int = 0) -> pd.DataFrame:
    """Świece dzienne DVOL jak parquet z `dane.deribit_dvol`; z dziurami: brak 4 dni, 2 NaN."""
    rng = np.random.default_rng(seed)
    close = 60.0 * np.exp(np.cumsum(rng.normal(0.0, 0.03, dni)))
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range(START, periods=dni, freq="D"),
            "open": close * 1.01,
            "high": close * 1.05,
            "low": close * 0.95,
            "close": close,
        }
    )
    if dziury:
        df.loc[[70, 71], "close"] = np.nan
        df = df.drop(index=[50, 51, 120, 180]).reset_index(drop=True)
    return df


def _funding(dziury: bool = False, dni: int = 200, seed: int = 0) -> pd.DataFrame:
    """
    Stawki co 8h (00/08/16 UTC) jak w danych alpha, z masą punktową jak w prawdziwych: 15 % dób
    ma wszystkie 3 stawki = baza, w pozostałych jedna z 3 = baza (masa surowa ≈ 43 %, masa średnich
    dziennych ≈ 15 %). Z dziurami: brak 2 dób i 2 pojedynczych stawek, doba i stawka z NaN.
    """
    rng = np.random.default_rng(seed)
    stawki = rng.normal(BAZA, 5e-5, (dni, 3))
    cale = rng.permutation(dni)[: int(0.15 * dni)]
    reszta = np.setdiff1d(np.arange(dni), cale)
    stawki[cale, :] = BAZA
    stawki[reszta, rng.integers(0, 3, len(reszta))] = BAZA
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range(START, periods=dni * 3, freq="8h"),
            "funding_rate": stawki.ravel(),
        }
    )
    if dziury:
        df.loc[[420, 421, 422, 500], "funding_rate"] = np.nan
        df = df.drop(index=[90, 91, 92, 93, 94, 95, 151, 271]).reset_index(drop=True)
    return df


def _koniec_doby(dzien: int, krok: pd.Timedelta) -> pd.Timestamp:
    """Ostatni slot doby nr `dzien` (od początku próby) — cięcie „koniec dnia d”."""
    return START + (dzien + 1) * DZIEN - krok


def _punkty_5m(df: pd.DataFrame):
    wokol = [
        _koniec_doby(d, KROK_5M) for d in (11, 12, 13, 19, 20, 21, 28, 29, 35, 36, 37, 70, 100)
    ]
    return sorted({*ciecia(df, ile=6, ziarno=0, koniec_doby=True), *wokol}), None


def _punkty_dvol(df: pd.DataFrame):
    wokol = list(df["timestamp"].iloc[[49, 50, 69, 70, 71, 72, 100]])
    return sorted({*ciecia(df, ile=60, ziarno=0), *wokol}), None


def _punkty_funding(df: pd.DataFrame):
    """Zakłócanie na końcach dób; obcinanie także w środku doby (wolno przy opóźnieniu ≥ 1)."""
    dni = (29, 30, 31, 32, 50, 51, 90, 91, 139, 140, 141, 150)
    wokol = [_koniec_doby(d, KROK_8H) for d in dni]
    zaklocenia = sorted({*ciecia(df, ile=14, ziarno=0, koniec_doby=True), *wokol})
    return zaklocenia, ciecia(df, ile=40, ziarno=1)


@dataclass(frozen=True)
class Zbior:
    """Jak testować zbiór informacyjny: dane, łańcuch od surowych danych, punkty cięcia."""

    dane: Callable[[bool], pd.DataFrame]
    punkty: Callable[[pd.DataFrame], tuple[list, list | None]]
    lancuch: Callable[[Callable], Callable] = lambda compute: compute


def _lancuch_5m(compute: Callable) -> Callable:
    """Surowe świece 5m → doba (`dane.rv.rv_dzienna`) → cecha: cała droga pod bramką."""

    def przez_rv_dzienna(df5m: pd.DataFrame) -> pd.Series:
        return compute(rv_dzienna(df5m))

    return przez_rv_dzienna


ZBIORY = {
    "swiece_5m": Zbior(_swiece_5m, _punkty_5m, _lancuch_5m),
    "dvol_1d": Zbior(_dvol_1d, _punkty_dvol),
    "funding": Zbior(_funding, _punkty_funding),
}


@cache
def _dane_cache(zbior: str, dziury: bool) -> pd.DataFrame:
    return ZBIORY[zbior].dane(dziury)


def dane_dla(zbior: str, dziury: bool = False) -> pd.DataFrame:
    return _dane_cache(zbior, dziury).copy()


def _funkcja(sciezka: str):
    modul, nazwa = sciezka.rsplit(".", 1)
    return getattr(importlib.import_module(modul), nazwa)


# ---------- 1. jeden test po całym rejestrze ----------


@pytest.mark.parametrize("dziury", [False, True], ids=["czyste", "dziury"])
@pytest.mark.parametrize("nazwa", sorted(REJESTR))
def test_cecha_z_rejestru_bez_przecieku(nazwa, dziury):
    wpis = REJESTR[nazwa]
    assert wpis["zbior_informacyjny"] in ZBIORY, "brak fabryki danych dla zbioru informacyjnego"
    zbior = ZBIORY[wpis["zbior_informacyjny"]]
    df = dane_dla(wpis["zbior_informacyjny"], dziury)
    compute = zbior.lancuch(_funkcja(wpis["funkcja"]))
    assert np.isfinite(compute(df.copy()).to_numpy(dtype=float)).sum() > 30  # test nie jest pusty
    punkty, obciecia = zbior.punkty(df)
    n = sprawdz_przeciek(
        compute, df, punkty, opoznienie=wpis["opoznienie_dni"], punkty_obciecia=obciecia
    )
    assert n is None, str(n)


# ---------- 2. integralność rejestru ----------


def _moduly_cech() -> list[types.ModuleType]:
    """Wszystkie moduły pod `cechy`, także w podpakietach (rekurencyjnie)."""
    nazwy = [m.name for m in pkgutil.walk_packages(cechy.__path__, "cechy.")]
    return [importlib.import_module(n) for n in nazwy]


def _niezarejestrowane(rejestr: dict, moduly) -> set[str]:
    """
    Każde wywoływalne `compute_*` widoczne w modułach cech (funkcja, partial, import z innego
    modułu, obiekt z __call__) musi być tym samym obiektem co funkcja z rejestru; alias do
    zarejestrowanej funkcji jest dozwolony, bo to ten sam obiekt.
    """
    zarejestrowane = [_funkcja(w["funkcja"]) for w in rejestr.values()]
    return {
        f"{m.__name__}.{nazwa}"
        for m in moduly
        for nazwa, obiekt in vars(m).items()
        if nazwa.startswith("compute_")
        and callable(obiekt)
        and not any(obiekt is f for f in zarejestrowane)
    }


def _klucz_kanoniczny(wariant: str) -> str:
    return re.sub(r"\s+", "", wariant).lower()


def _powtorzone_warianty(rejestr: dict) -> dict[str, list[str]]:
    """Warianty identyczne po usunięciu spacji i wielkości liter (R2: ten sam wariant)."""
    po_wariancie: dict[str, list[str]] = {}
    for nazwa, w in rejestr.items():
        po_wariancie.setdefault(_klucz_kanoniczny(w["wariant"]), []).append(nazwa)
    return {k: v for k, v in po_wariancie.items() if len(v) > 1}


def test_rejestr_pola_i_formaty():
    assert REJESTR, "pusty rejestr"
    for nazwa, w in REJESTR.items():
        assert set(w) == POLA, f"{nazwa}: pola {sorted(set(w) ^ POLA)}"
        assert isinstance(w["dodano"], str), f"{nazwa}: data w cudzysłowie (tekst ISO)"
        date.fromisoformat(w["dodano"])
        assert w["zbior_informacyjny"] in ZBIORY, nazwa
        assert isinstance(w["opoznienie_dni"], int) and w["opoznienie_dni"] >= 0, nazwa
        for pole in ("runda_definicji", "runda"):
            assert w[pole] is None or (isinstance(w[pole], str) and w[pole]), f"{nazwa}: {pole}"
        assert w["progi"] in PROGI, f"{nazwa}: progi ∈ {sorted(PROGI)}"
        assert isinstance(w["formula"], str) and w["formula"], nazwa
        assert w["funkcja"].endswith(f".compute_{nazwa}"), f"{nazwa}: nazwa ≠ funkcja"
        klucz = f"{w['zbior_informacyjny']}|{w['formula']}|opoznienie={w['opoznienie_dni']}"
        assert w["wariant"] == klucz, f"{nazwa}: wariant powinien być {klucz!r}"


def test_rejestr_rundy_istnieja_w_indeksie_rund():
    indeks = INDEX_RUND.read_text(encoding="utf-8")
    for nazwa, w in REJESTR.items():
        for pole in ("runda_definicji", "runda"):
            if w[pole] is not None:
                assert f"| {w[pole]} |" in indeks, f"{nazwa}: {pole}={w[pole]} spoza runs/INDEX.md"


def test_rv_zdefiniowane_w_f21_a_niezmierzone():
    """F2-1 jest NIEMIERZALNA (test DM nieuruchomiony), więc `runda` (pomiar) zostaje pusta."""
    rv = {n: w for n, w in REJESTR.items() if n.startswith("rv_")}
    assert set(rv) == {"rv_dzien", "rv_tydzien", "rv_miesiac"}
    assert all(w["runda_definicji"] == "F2-1" and w["runda"] is None for w in rv.values())


def test_rejestr_bez_duplikatow_wariantow():
    assert _powtorzone_warianty(REJESTR) == {}


def test_wykrywa_duplikat_wariantu_takze_po_spacjach_i_wielkosci_liter():
    """R2: ten sam zbiór informacyjny + formuła = ten sam wariant pod inną nazwą."""
    w = REJESTR["rv_dzien"]
    kopia = dict(w)
    przerobiona = dict(w, wariant=w["wariant"].upper().replace(" ", ""))
    rejestr = {**REJESTR, "rv_dzien_bis": kopia, "rv_dzien_ter": przerobiona}
    assert _powtorzone_warianty(rejestr) == {
        _klucz_kanoniczny(w["wariant"]): ["rv_dzien", "rv_dzien_bis", "rv_dzien_ter"]
    }


def test_yaml_z_powtorzonym_kluczem_jest_odrzucany():
    tekst = "cechy:\n  a:\n    wariant: x\n  a:\n    wariant: y\n"
    with pytest.raises(ValueError, match="powtórzony klucz"):
        wczytaj_rejestr_z_tekstu(tekst)
    with pytest.raises(ValueError, match="powtórzony klucz"):
        wczytaj_rejestr_z_tekstu("cechy:\n  a:\n    wariant: x\n    wariant: y\n")
    assert wczytaj_rejestr_z_tekstu("cechy:\n  a:\n    wariant: x\n") == {"a": {"wariant": "x"}}


def test_funkcje_istnieja_z_podpisem_df():
    for nazwa, w in REJESTR.items():
        fn = _funkcja(w["funkcja"])
        assert fn.__name__ == f"compute_{nazwa}"
        par = list(inspect.signature(fn).parameters.values())
        assert par and par[0].name == "df", f"{nazwa}: podpis powinien zaczynać się od (df)"
        assert all(p.default is not p.empty for p in par[1:]), f"{nazwa}: dodatkowe bez wartości"


def test_kazda_funkcja_compute_ma_wpis_w_rejestrze():
    assert _niezarejestrowane(REJESTR, _moduly_cech()) == set()


def _obcy_modul(**obiekty) -> types.ModuleType:
    modul = types.ModuleType("cechy.obca")
    for nazwa, obiekt in obiekty.items():
        setattr(modul, nazwa, obiekt)
    return modul


def test_wykrywa_funkcje_compute_bez_wpisu():
    """Cecha bez wpisu NIE PRZECHODZI: wykrywacz widzi `compute_*` obecną w kodzie, a nie w YAML."""
    obca = _obcy_modul(compute_nowa=lambda df: df["x"], pomocnicza=lambda df: df)
    assert _niezarejestrowane(REJESTR, [*_moduly_cech(), obca]) == {"cechy.obca.compute_nowa"}


def test_wykrywa_obejscia_partial_import_i_obiekt_wywolywalny():
    """Obejścia rejestru: `partial` zarejestrowanej, funkcja importowana z obcego modułu, klasa."""

    class Wywolywalna:
        def __call__(self, df):
            return df["x"]

    zarejestrowana = _funkcja(REJESTR["funding"]["funkcja"])
    obca = _obcy_modul(
        compute_partial=partial(zarejestrowana),
        compute_import=pd.Series.sum,
        compute_obiekt=Wywolywalna(),
        compute_alias=zarejestrowana,  # ten sam obiekt co w rejestrze: dozwolony
        compute_liczba=3,  # nie jest wywoływalne
    )
    assert _niezarejestrowane(REJESTR, [obca]) == {
        "cechy.obca.compute_partial",
        "cechy.obca.compute_import",
        "cechy.obca.compute_obiekt",
    }


def test_wykrywa_funkcje_compute_w_podpakiecie(tmp_path, monkeypatch):
    pod = tmp_path / "pod"
    pod.mkdir()
    (pod / "__init__.py").write_text("", encoding="utf-8")
    (pod / "gleboki.py").write_text("def compute_ukryta(df):\n    return df['x']\n", "utf-8")
    monkeypatch.setattr(cechy, "__path__", [*cechy.__path__, str(tmp_path)])
    importlib.invalidate_caches()
    try:
        assert _niezarejestrowane(REJESTR, _moduly_cech()) == {"cechy.pod.gleboki.compute_ukryta"}
    finally:
        for nazwa in [k for k in sys.modules if k == "cechy.pod" or k.startswith("cechy.pod.")]:
            del sys.modules[nazwa]


def test_opoznienie_w_rejestrze_zgodne_z_kodem():
    assert REJESTR["dvol_opozn"]["opoznienie_dni"] == zmiennosc.OPOZNIENIE_DVOL_DNI
    assert REJESTR["funding"]["opoznienie_dni"] == zmiennosc.OPOZNIENIE_FUNDING_DNI
    assert all(REJESTR[n]["opoznienie_dni"] == 0 for n in REJESTR if n.startswith("rv_"))


def test_prog_ma_wartosc_z_f21():
    assert zmiennosc.MIN_SWIEC_DNIA == MIN_SWIEC == 274
    assert str(MIN_SWIEC) in REJESTR["rv_dzien"]["formula"]  # maska ważności należy do definicji


def _kolumny_liczbowe(df: pd.DataFrame) -> list[str]:
    return [k for k in df.columns if k != "timestamp" and pd.api.types.is_numeric_dtype(df[k])]


def test_progi_percentylowe_tylko_bez_masy_punktowej():
    """FR-12: surowa kolumna z masą > 20 % wymaga `progi: absolutne`; reszta musi to wytrzymać."""
    for nazwa, w in REJESTR.items():
        zbior = ZBIORY[w["zbior_informacyjny"]]
        df = dane_dla(w["zbior_informacyjny"])
        surowa = max(masa_punktowa(df[k]) for k in _kolumny_liczbowe(df))
        if surowa > PROG_MASY:
            assert w["progi"] == "absolutne", f"{nazwa}: masa surowych danych {surowa:.0%}"
        if w["progi"] == "percentylowe_dozwolone":
            wynik = zbior.lancuch(_funkcja(w["funkcja"]))(df)
            assert walidacja_progu_percentylowego(wynik.dropna()) <= PROG_MASY, nazwa


def test_funding_ma_zakaz_progow_percentylowych_choc_srednia_dzienna_przechodzi_walidacje():
    """Średnia dzienna rozcieńcza atom (≈ 15 % < 20 %), więc zakaz musi siedzieć w rejestrze."""
    assert REJESTR["funding"]["progi"] == "absolutne"
    df = dane_dla("funding")
    assert masa_punktowa(df["funding_rate"]) > PROG_MASY
    with pytest.raises(MasaPunktowaBlad):
        walidacja_progu_percentylowego(df["funding_rate"])
    srednia = zmiennosc.compute_funding(df).dropna()
    assert walidacja_progu_percentylowego(srednia) < PROG_MASY  # strażnik wyjścia NIE zatrzymuje


def test_masa_surowa_i_srednia_dzienna_jak_w_prawdziwych_danych():
    """198 z 999 dób samych stawek bazowych: średnia dzienna 19,8 % (przechodzi), surowe > 20 %."""
    dni = 999
    rng = np.random.default_rng(5)
    stawki = rng.normal(BAZA, 5e-5, (dni, 3))
    cale = rng.permutation(dni)[:198]
    reszta = np.setdiff1d(np.arange(dni), cale)
    stawki[cale, :] = BAZA
    stawki[reszta, rng.integers(0, 3, len(reszta))] = BAZA
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range(START, periods=dni * 3, freq="8h"),
            "funding_rate": stawki.ravel(),
        }
    )
    srednia = zmiennosc.compute_funding(df).dropna()
    assert len(srednia) == dni - 1
    assert masa_punktowa(srednia) == pytest.approx(198 / (dni - 1), abs=2e-3)
    assert walidacja_progu_percentylowego(srednia) < PROG_MASY  # strażnik wyjścia przepuszcza
    assert masa_punktowa(df["funding_rate"]) > 0.4
    with pytest.raises(MasaPunktowaBlad):
        walidacja_progu_percentylowego(df["funding_rate"])


# ---------- 3. semantyka cech (definicje, maska RV, okna kalendarzowe, opóźnienie, dziury) -------


def _ramka_dzienna(rv, n_swiec=None) -> pd.DataFrame:
    """Ramka dzienna w układzie `dane.rv.rv_dzienna`: indeks doby UTC, kolumny rv i n_swiec."""
    rv = np.asarray(rv, dtype=float)
    idx = pd.date_range(START, periods=len(rv), freq="D", name="day")
    n = np.full(len(rv), SLOTY_5M) if n_swiec is None else np.asarray(n_swiec)
    return pd.DataFrame({"rv": rv, "n_swiec": n}, index=idx)


RV_KOLUMNY = (("rv_dzien", "d"), ("rv_tydzien", "w"), ("rv_miesiac", "m"))


def _dzien(k: int) -> pd.Timestamp:
    return START + k * DZIEN


def test_rv_maska_waznosci_273_274_i_rv_dodatnie():
    """Poprawka 1 F2-1: dzień ważny, gdy n_swiec ≥ 274 ORAZ rv > 0; nieważny = NaN."""
    rv = [0.01, 0.02, 0.03, 0.0, 0.04, np.nan, 0.05]
    n = [288, 274, 273, 288, 100, 288, 288]
    w = zmiennosc.compute_rv_dzien(_ramka_dzienna(rv, n))
    oczekiwane = [np.log(0.01), np.log(0.02), np.nan, np.nan, np.nan, np.nan, np.log(0.05)]
    np.testing.assert_allclose(w.to_numpy(), oczekiwane)
    assert w.name == "rv_dzien"


@pytest.mark.parametrize("nazwa", [n for n, _ in RV_KOLUMNY])
def test_rv_nigdy_minus_inf(nazwa):
    rv = np.concatenate([np.exp(np.random.default_rng(0).normal(size=45)), np.zeros(5)])
    wynik = _funkcja(REJESTR[nazwa]["funkcja"])(_ramka_dzienna(rv))
    assert not np.isinf(wynik.to_numpy()).any()
    assert wynik.iloc[-1:].isna().all()  # doba z RV = 0 nie daje liczby


def test_rv_zgodne_z_cechy_har_i_maska_f21_bez_dziur():
    """R2: te same definicje co `modele.zmiennosc.cechy_har` na RV po masie F2-1 (bez dziur)."""
    df = rv_dzienna(dane_dla("swiece_5m"))
    har = cechy_har(df["rv"].where((df["n_swiec"] >= MIN_SWIEC) & (df["rv"] > 0)))
    for nazwa, kolumna in RV_KOLUMNY:
        wynik = _funkcja(REJESTR[nazwa]["funkcja"])(df)
        pd.testing.assert_series_equal(wynik, har[kolumna], check_names=False, check_freq=False)
        assert wynik.name == nazwa
        assert np.isfinite(wynik.to_numpy(dtype=float)).sum() > 50


def test_rv_lancuch_5m_z_dziurami_zgodny_z_cechy_har_na_kalendarzu():
    d = rv_dzienna(dane_dla("swiece_5m", dziury=True))
    assert len(d) < d.index.nunique() + 1 and d.index[-1] - d.index[0] > (len(d) - 1) * DZIEN
    kalendarz = pd.date_range(d.index.min(), d.index.max(), freq="D")
    rv = d["rv"].where((d["n_swiec"] >= MIN_SWIEC) & (d["rv"] > 0)).reindex(kalendarz)
    har = cechy_har(rv)
    for nazwa, kolumna in RV_KOLUMNY:
        wynik = _funkcja(REJESTR[nazwa]["funkcja"])(d)
        pd.testing.assert_series_equal(wynik, har[kolumna], check_names=False, check_freq=False)


def test_rv_dziury_w_lancuchu_5m_dni_waznosci_i_okna():
    d = rv_dzienna(dane_dla("swiece_5m", dziury=True))
    assert d.loc[_dzien(DZIEN_274), "n_swiec"] == 274 and d.loc[_dzien(DZIEN_273), "n_swiec"] == 273
    assert d.loc[_dzien(DZIEN_MARTWY), "rv"] == 0 and d.loc[_dzien(DZIEN_MARTWY), "n_swiec"] == 288
    w = zmiennosc.compute_rv_dzien(d)
    assert np.isfinite(w[_dzien(DZIEN_274)])  # dokładnie 274 świece = dzień ważny
    for nieważny in (DZIEN_BRAK, DZIEN_NIEPELNY, DZIEN_MARTWY, DZIEN_273):
        assert np.isnan(w[_dzien(nieważny)]), nieważny
    assert not np.isinf(w.to_numpy(dtype=float)).any()
    miesiac = zmiennosc.compute_rv_miesiac(d)
    assert miesiac[: _dzien(DZIEN_273 + 29)].isna().all()  # okno 30 dób obejmuje nieważną dobę 36
    assert np.isfinite(miesiac[_dzien(DZIEN_273 + 30)])
    tydzien = zmiennosc.compute_rv_tydzien(d)
    assert np.isnan(tydzien[_dzien(DZIEN_273 + 6)]) and np.isfinite(tydzien[_dzien(DZIEN_273 + 7)])


def test_rv_okna_sa_kalendarzowe_a_nie_pozycyjne():
    """Brakująca doba daje NaN w oknach, które ją obejmują; `cechy_har` liczyłoby okno wierszy."""
    df = _ramka_dzienna(np.exp(np.random.default_rng(1).normal(size=40)))
    z_dziura = df.drop(index=df.index[10])
    w = zmiennosc.compute_rv_tydzien(z_dziura)
    assert len(w) == 40 and w.index.equals(df.index)  # kalendarz pełny, z etykietą dla doby 10
    assert w.iloc[10:17].isna().all() and np.isfinite(w.iloc[17])
    pozycyjne = cechy_har(z_dziura["rv"])["w"]  # 7 wierszy = 8 dób: świadomie inny wariant
    assert np.isfinite(pozycyjne.iloc[10]) and np.isnan(w.iloc[11])
    pd.testing.assert_series_equal(  # bez dziur — to samo co do bitu
        zmiennosc.compute_rv_tydzien(df), cechy_har(df["rv"])["w"], check_names=False
    )


def test_rv_walidacje_wejscia():
    ok = _ramka_dzienna([0.01] * 40)
    with pytest.raises(ValueError, match="n_swiec"):
        zmiennosc.compute_rv_dzien(ok.drop(columns="n_swiec"))
    with pytest.raises(ValueError, match="`rv`"):
        zmiennosc.compute_rv_dzien(ok.drop(columns="rv"))
    with pytest.raises(ValueError, match="dzienny"):
        zmiennosc.compute_rv_dzien(ok.set_axis(pd.date_range(START, periods=40, freq="12h")))
    with pytest.raises(ValueError, match="dzienny"):
        zmiennosc.compute_rv_dzien(pd.concat([ok, ok.iloc[:1]]))
    with pytest.raises(ValueError, match="indeks"):
        zmiennosc.compute_rv_dzien(ok.reset_index(drop=True))
    with pytest.raises(ValueError, match="indeks"):
        zmiennosc.compute_rv_dzien(ok.iloc[:0])


def test_dvol_opozn_wartosc_dnia_d_dopiero_w_d_plus_1():
    df = dane_dla("dvol_1d")
    wynik = zmiennosc.compute_dvol_opozn(df)
    assert np.isnan(wynik.iloc[0])
    np.testing.assert_array_equal(wynik.iloc[1:].to_numpy(), df["close"].iloc[:-1].to_numpy())
    assert wynik.index.equals(pd.DatetimeIndex(df["timestamp"]))
    assert wynik.name == "dvol_opozn"


def test_dvol_opozn_dziura_nie_jest_zasypywana_przesunieciem_wierszy():
    df = dane_dla("dvol_1d").iloc[:10]
    z_dziura = df.drop(index=5).reset_index(drop=True)  # brak dnia 5
    wynik = zmiennosc.compute_dvol_opozn(z_dziura).set_axis(z_dziura["timestamp"])
    assert np.isnan(wynik[_dzien(6)])  # wiersz-po-wierszu dałby tu close dnia 4
    assert wynik[_dzien(4)] == df["close"].iloc[3]


def test_dvol_opozn_na_danych_z_dziurami_i_nan():
    df = dane_dla("dvol_1d", dziury=True)
    wynik = zmiennosc.compute_dvol_opozn(df)
    close = pd.Series(df["close"].to_numpy(), index=pd.DatetimeIndex(df["timestamp"]))
    np.testing.assert_array_equal(wynik.to_numpy(), close.reindex(wynik.index - DZIEN).to_numpy())
    assert len(wynik) == len(df)
    assert wynik.isna().sum() >= 6  # start, 4 brakujące doby po dziurach i 2 NaN w close


def test_dvol_duplikaty_i_brak_kolumny_to_blad():
    df = dane_dla("dvol_1d")
    with pytest.raises(ValueError, match="duplikaty"):
        zmiennosc.compute_dvol_opozn(pd.concat([df, df.iloc[:1]]))
    with pytest.raises(ValueError, match="close"):
        zmiennosc.compute_dvol_opozn(df.drop(columns="close"))
    with pytest.raises(ValueError, match="rv"):
        zmiennosc.compute_rv_dzien(df)


def _funding_reczny(stawki_po_dobach: dict[str, list[float]]) -> pd.DataFrame:
    ts, stawki = [], []
    for doba, lista in stawki_po_dobach.items():
        for i, s in enumerate(lista):
            ts.append(pd.Timestamp(doba, tz="UTC") + i * KROK_8H)
            stawki.append(s)
    return pd.DataFrame({"timestamp": ts, "funding_rate": stawki})


def test_funding_srednia_dzienna_z_opoznieniem_i_dziury():
    df = _funding_reczny(
        {"2021-01-01": [1.0, 2.0, 6.0], "2021-01-02": [4.0, 5.0, 12.0], "2021-01-04": [9.0]}
    )
    w = zmiennosc.compute_funding(df)
    assert list(w.index.strftime("%Y-%m-%d")) == [
        "2021-01-01",
        "2021-01-02",
        "2021-01-03",
        "2021-01-04",
    ]
    assert np.isnan(w.iloc[0])
    assert w.iloc[1] == 3.0  # ŚREDNIA doby 01-01 ([1,2,6]; mediana byłaby 2) w wierszu 01-02
    assert w.iloc[2] == 7.0  # średnia doby 01-02 ([4,5,12]; mediana 5)
    assert np.isnan(w.iloc[3])  # doby 01-03 nie było — brak wartości, nie ciche przeniesienie
    assert w.name == "funding"


def test_funding_nan_w_stawce_nie_psuje_sredniej_dnia():
    df = _funding_reczny({"2021-01-01": [1.0, np.nan, 5.0], "2021-01-02": [2.0, 2.0, 2.0]})
    assert zmiennosc.compute_funding(df).iloc[1] == 3.0


def test_funding_na_danych_z_dziurami_dzienna_srednia_dnia_d_minus_1():
    df = dane_dla("funding", dziury=True)
    w = zmiennosc.compute_funding(df)
    dzienna = df.set_index("timestamp")["funding_rate"].groupby(lambda t: t.floor("D")).mean()
    oczekiwane = dzienna.reindex(w.index - DZIEN).to_numpy()
    np.testing.assert_array_equal(w.to_numpy(), oczekiwane)
    assert np.isnan(w[_dzien(31)]) and np.isnan(w[_dzien(32)])  # doby 30 i 31 bez stawek


def test_funding_bledy_wejscia():
    df = dane_dla("funding").iloc[:30]
    with pytest.raises(ValueError, match="duplikaty"):
        zmiennosc.compute_funding(pd.concat([df, df.iloc[:1]]))
    with pytest.raises(ValueError, match="pusta"):
        zmiennosc.compute_funding(df.iloc[:0])
    with pytest.raises(ValueError, match="NaT"):
        zmiennosc.compute_funding(df.assign(timestamp=[pd.NaT] + list(df["timestamp"].iloc[1:])))
    with pytest.raises(ValueError, match="funding_rate"):
        zmiennosc.compute_funding(df.drop(columns="funding_rate"))


# ---------- 4. kontrola pozytywna (R8): celowe przecieki są łapane ----------


def _ramka_x(n: int = 260, seed: int = 0) -> pd.DataFrame:
    x = np.exp(np.random.default_rng(seed).normal(0.0, 0.5, n))
    return pd.DataFrame({"x": x}, index=pd.date_range(START, periods=n, freq="D"))


PUNKTY_X = [60, 110, 160, 220]

PRZECIEKI = {
    "okno_centrowane": lambda df: df["x"].rolling(5, center=True).mean(),
    "przesuniecie_w_przod": lambda df: df["x"].shift(-1),
    "normalizacja_po_calej_probie": lambda df: (df["x"] - df["x"].mean()) / df["x"].std(),
    "lead_cumsum": lambda df: df["x"][::-1].cumsum()[::-1],
    "ranga_po_calej_probie": lambda df: df["x"].rank(pct=True),
    "przyszla_srednia_ruchoma": lambda df: df["x"].rolling(5).mean().shift(-4),
    "dzielenie_przez_max_proby": lambda df: df["x"] / df["x"].max(),
}


@pytest.mark.parametrize("obciecie", [True, False], ids=["z_obcieciem", "samo_zaklocanie"])
@pytest.mark.parametrize("nazwa", sorted(PRZECIEKI))
def test_celowy_przeciek_jest_zlapany(nazwa, obciecie):
    assert nazwa not in REJESTR  # przecieki żyją tylko w testach
    n = sprawdz_przeciek(PRZECIEKI[nazwa], _ramka_x(), PUNKTY_X, obciecie=obciecie)
    assert n is not None


def test_przeciek_raportuje_pierwszy_indeks_naruszenia():
    df = _ramka_x()
    n = sprawdz_przeciek(PRZECIEKI["przesuniecie_w_przod"], df, PUNKTY_X)
    assert isinstance(n, Naruszenie)
    assert n.punkt_ciecia == PUNKTY_X[0]
    assert n.indeks == n.czas_ciecia == df.index[PUNKTY_X[0]]  # wiersz t patrzy w t+1
    assert (
        n.wartosc_czysta == df["x"].iloc[PUNKTY_X[0] + 1]
    )  # to, co cecha podejrzała z przyszłości
    assert not np.isnan(n.wartosc_zaklocona) and n.wartosc_zaklocona != n.wartosc_czysta
    assert "PRZECIEK" in str(n) and "zakłócenie" in str(n)


def test_jeden_rodzaj_zaklocenia_nie_wystarcza():
    """Odwrócenie przyszłości nie zmienia jej maksimum — dlatego jest kilka rodzajów zakłóceń."""
    df, f = _ramka_x(), PRZECIEKI["dzielenie_przez_max_proby"]
    assert sprawdz_przeciek(f, df, PUNKTY_X, zaklocenia=("odwrocone",), obciecie=False) is None
    assert sprawdz_przeciek(f, df, PUNKTY_X, zaklocenia=ZAKLOCENIA, obciecie=False) is not None


@pytest.mark.parametrize("rodzaj", ZAKLOCENIA)
def test_kazdy_rodzaj_zaklocenia_z_osobna_lapie_przesuniecie_w_przod(rodzaj):
    n = sprawdz_przeciek(
        PRZECIEKI["przesuniecie_w_przod"],
        _ramka_x(),
        PUNKTY_X,
        zaklocenia=(rodzaj,),
        obciecie=False,
    )
    assert n is not None and n.zaklocenie == rodzaj


def test_deklarowane_opoznienie_za_male_jest_lapane():
    """DVOL z tego samego dnia przy deklaracji „opóźnienie 1 dzień” — przeciek względem rejestru."""
    df = dane_dla("dvol_1d")
    punkty, _ = _punkty_dvol(df)

    def dvol_bez_opoznienia(d):
        return pd.Series(d["close"].to_numpy(), index=pd.DatetimeIndex(d["timestamp"]))

    assert sprawdz_przeciek(dvol_bez_opoznienia, df, punkty, opoznienie=0) is None
    assert sprawdz_przeciek(dvol_bez_opoznienia, df, punkty, opoznienie=1) is not None
    assert sprawdz_przeciek(zmiennosc.compute_dvol_opozn, df, punkty, opoznienie=1) is None


def test_funding_srednia_bez_opoznienia_lub_z_wyprzedzeniem_jest_lapana():
    df = dane_dla("funding")
    punkty, _ = _punkty_funding(df)  # końce dób: średnia dnia d jest znana dopiero po dniu d

    def srednia_dnia_d_w_dniu_d(d):
        s = pd.Series(d["funding_rate"].to_numpy(), index=pd.DatetimeIndex(d["timestamp"]))
        return s.groupby(s.index.floor("D")).mean()

    def srednia_jutra(d):
        return srednia_dnia_d_w_dniu_d(d).shift(-1)

    assert sprawdz_przeciek(srednia_dnia_d_w_dniu_d, df, punkty, opoznienie=0) is None
    assert sprawdz_przeciek(srednia_dnia_d_w_dniu_d, df, punkty, opoznienie=1) is not None
    assert sprawdz_przeciek(srednia_jutra, df, punkty, opoznienie=0) is not None


# --- przecieki przez dziury, długość próby, warunki rzadkie, kolumny nieliczbowe ---


def _ramka_ts(n: int = 80, seed: int = 0, usun=(), nan_w=()) -> pd.DataFrame:
    """Ramka dzienna z kolumną `timestamp` i `x`; `usun` = brakujące wiersze, `nan_w` = x = NaN."""
    x = np.exp(np.random.default_rng(seed).normal(0.0, 0.5, n))
    df = pd.DataFrame({"timestamp": pd.date_range(START, periods=n, freq="D"), "x": x})
    df.loc[list(nan_w), "x"] = np.nan
    return df.drop(index=list(usun)).reset_index(drop=True)


def _szereg(df: pd.DataFrame, kolumna: str = "x") -> pd.Series:
    return pd.Series(df[kolumna].to_numpy(dtype=float), index=pd.DatetimeIndex(df["timestamp"]))


def _na_kalendarz(s: pd.Series) -> pd.Series:
    return s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="D"))


LUKI = {
    "bfill_kalendarza": lambda df: _na_kalendarz(_szereg(df)).bfill(),
    "interpolacja": lambda df: _na_kalendarz(_szereg(df)).interpolate(),
    "reindex_method_bfill": lambda df: _szereg(df).reindex(
        pd.date_range(df["timestamp"].min(), df["timestamp"].max(), freq="D"), method="bfill"
    ),
    "bfill_wierszy_z_nan": lambda df: _szereg(df).bfill(),
}


@pytest.mark.parametrize("nazwa", sorted(LUKI))
def test_wypelnianie_dziur_do_przodu_jest_lapane_przez_ciecia_w_dziurach(nazwa):
    df = _ramka_ts(usun=(20, 21, 50), nan_w=(35, 36, 65))
    assert sprawdz_przeciek(LUKI[nazwa], df, ciecia(df)) is not None
    assert sprawdz_przeciek(LUKI[nazwa], df, ciecia(df), obciecie=False) is not None


def test_rzadkie_ciecia_nie_widza_wypelniania_dziur_dlatego_jest_ciecia():
    """Przeciek siedzi w slocie dziury; punkty w innych miejscach go nie dotykają."""
    df = _ramka_ts(usun=(20, 21, 50), nan_w=(35, 36, 65))
    assert sprawdz_przeciek(LUKI["bfill_kalendarza"], df, [60, 70]) is None
    assert sprawdz_przeciek(LUKI["bfill_kalendarza"], df, ciecia(df)) is not None


def test_wypelnianie_dziur_do_tylu_to_kontrola_negatywna():
    """ffill używa tylko przeszłości: żadnego alarmu, także w slotach dziur."""
    df = _ramka_ts(usun=(20, 21, 50), nan_w=(35, 36, 65))
    assert sprawdz_przeciek(lambda d: _na_kalendarz(_szereg(d)).ffill(), df, ciecia(df)) is None


def test_ciecie_w_dziurze_jest_chwila_a_nie_pozycja():
    df = _ramka_ts(usun=(20,))
    dziura = START + 20 * DZIEN  # brakujący wiersz; w ramce jest już dzień 21 na pozycji 20
    assert dziura not in set(df["timestamp"]) and dziura in ciecia(df)
    n = sprawdz_przeciek(LUKI["bfill_kalendarza"], df, [dziura])
    assert n is not None and n.punkt_ciecia == dziura and n.indeks == dziura


DLUGOSC_I_OS = {
    "razy_dlugosc_probie": lambda df: _szereg(df) * len(df),
    "plus_rozpietosc_osi": lambda df: _szereg(df)
    + (df["timestamp"].max() - df["timestamp"].min()).days,
}


@pytest.mark.parametrize("nazwa", sorted(DLUGOSC_I_OS))
def test_przeciek_przez_dlugosc_probie_lapie_tylko_obciecie(nazwa):
    df = _ramka_ts(100)
    punkty = [30, 60, 90]
    assert sprawdz_przeciek(DLUGOSC_I_OS[nazwa], df, punkty, obciecie=False) is None
    n = sprawdz_przeciek(DLUGOSC_I_OS[nazwa], df, punkty)
    assert n is not None and n.zaklocenie == OBCIECIE and "obcięcie" in str(n)


def _sobotni(df):
    s = _szereg(df)
    return s.shift(-1).where(s.index.dayofweek == 5, s)


def _pierwszego_dnia_miesiaca(df):
    s = _szereg(df)
    return s.shift(-1).where(s.index.day == 1, s)


@pytest.mark.parametrize("przeciek", [_sobotni, _pierwszego_dnia_miesiaca])
def test_przeciek_warunkowy_umyka_rzadkim_ciecom_a_ciecia_go_lapie(przeciek):
    df = _ramka_ts(260)
    assert sprawdz_przeciek(przeciek, df, PUNKTY_X) is None  # żadne z 4 cięć nie trafia w sobotę
    assert sprawdz_przeciek(przeciek, df, ciecia(df)) is not None


def _ramka_typy(n: int = 60, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "timestamp": pd.date_range(START, periods=n, freq="D"),
            "x": np.exp(rng.normal(0.0, 0.5, n)),
            "flaga": rng.random(n) < 0.5,
            "nazwa": [f"s{i}" for i in range(n)],
            "data": pd.date_range("2022-01-01", periods=n, freq="D"),
        }
    )


def _liczba(s: pd.Series, df: pd.DataFrame) -> pd.Series:
    return pd.Series(
        s.to_numpy(dtype=float, na_value=np.nan), index=pd.DatetimeIndex(df["timestamp"])
    )


KOLUMNY_NIELICZBOWE = {
    "bool": lambda df, k: _liczba(df["flaga"].shift(k), df),
    "tekst": lambda df, k: _liczba(df["nazwa"].shift(k).str.len(), df),
    "data": lambda df, k: _liczba((df["data"].shift(k) - df["data"]).dt.days, df),
}


@pytest.mark.parametrize("kolumna", sorted(KOLUMNY_NIELICZBOWE))
def test_przeciek_w_kolumnie_nieliczbowej_jest_lapany(kolumna):
    df = _ramka_typy()
    przeciek = lambda d: KOLUMNY_NIELICZBOWE[kolumna](d, -1)
    poprawna = lambda d: KOLUMNY_NIELICZBOWE[kolumna](d, 1)
    assert sprawdz_przeciek(przeciek, df, [20, 30, 40], obciecie=False) is not None
    assert sprawdz_przeciek(poprawna, df, [20, 30, 40]) is None


def test_kolumny_bez_zaklocenia_to_blad_a_nie_ciche_pominiecie():
    df = _ramka_typy().assign(okres=pd.period_range("2021-01", periods=60, freq="M"))
    with pytest.raises(TypeError, match="brak zakłócenia"):
        sprawdz_przeciek(lambda d: _szereg(d), df, [20, 30])


@pytest.mark.parametrize("kolumna", ["a", "b", "c"])
def test_przeciek_w_kazdej_kolumnie_wielokolumnowej_ramki(kolumna):
    rng = np.random.default_rng(3)
    df = _ramka_ts(80).drop(columns="x")
    for k in "abc":
        df[k] = np.exp(rng.normal(0.0, 0.5, len(df)))
    n = sprawdz_przeciek(lambda d: _szereg(d, kolumna).shift(-1), df, [20, 40, 60])
    assert n is not None
    assert sprawdz_przeciek(lambda d: _szereg(d, kolumna).shift(1), df, [20, 40, 60]) is None


MUTANTY_PRAWDZIWYCH_CECH = {
    "funding": {
        "bfill": lambda df: zmiennosc.compute_funding(df).bfill(),
        "razy_dlugosc": lambda df: zmiennosc.compute_funding(df) * len(df),
    },
    "dvol_1d": {
        "interpolacja": lambda df: _na_kalendarz(zmiennosc.compute_dvol_opozn(df)).interpolate(),
        "razy_dlugosc": lambda df: zmiennosc.compute_dvol_opozn(df) * len(df),
    },
}


@pytest.mark.parametrize(
    ("zbior", "mutant"),
    [(z, m) for z, ms in MUTANTY_PRAWDZIWYCH_CECH.items() for m in ms],
)
def test_zmutowana_prawdziwa_cecha_jest_lapana_na_danych_z_dziurami(zbior, mutant):
    wpis = next(w for w in REJESTR.values() if w["zbior_informacyjny"] == zbior)
    df = dane_dla(zbior, dziury=True)
    punkty, obciecia = ZBIORY[zbior].punkty(df)
    n = sprawdz_przeciek(
        MUTANTY_PRAWDZIWYCH_CECH[zbior][mutant],
        df,
        punkty,
        opoznienie=wpis["opoznienie_dni"],
        punkty_obciecia=obciecia,
    )
    assert n is not None


def _rv_z_jutra(df5m: pd.DataFrame) -> pd.Series:
    d = rv_dzienna(df5m)
    d["rv"] = d["rv"].shift(-1)  # RV następnej doby w wierszu doby d
    return zmiennosc.compute_rv_dzien(d)


def _rv_ze_scentrowanego_close(df5m: pd.DataFrame) -> pd.Series:
    wygladzone = df5m["close"].rolling(25, center=True, min_periods=1).mean()
    return zmiennosc.compute_rv_dzien(rv_dzienna(df5m.assign(close=wygladzone)))


@pytest.mark.parametrize("przeciek", [_rv_z_jutra, _rv_ze_scentrowanego_close])
def test_przeciek_w_agregacji_5m_do_doby_jest_lapany_przez_lancuch(przeciek):
    df = dane_dla("swiece_5m")
    punkty, _ = _punkty_5m(df)
    assert sprawdz_przeciek(przeciek, df, punkty) is not None


def test_ciecie_w_srodku_doby_dla_cechy_dziennej_bez_opoznienia_to_zly_kontrakt():
    """Doba d jest znana dopiero o północy: cięcie w jej środku zakłóca jeszcze trwającą dobę."""
    df = dane_dla("swiece_5m")
    srodek = START + 40 * DZIEN + pd.Timedelta(hours=12)
    compute = _lancuch_5m(zmiennosc.compute_rv_dzien)
    assert sprawdz_przeciek(compute, df, [srodek], obciecie=False) is not None
    assert sprawdz_przeciek(compute, df, [_koniec_doby(40, KROK_5M)]) is None


# ---------- 5. kontrola negatywna: poprawne cechy bez fałszywego alarmu ----------

POPRAWNE = {
    "srednia_ruchoma": lambda x, k: x.rolling(k).mean(),
    "odchylenie_ruchome": lambda x, k: x.rolling(k).std(),
    "min_ruchome": lambda x, k: x.rolling(k).min(),
    "ranga_wsteczna": lambda x, k: x.rolling(k).rank(pct=True),
    "ewm": lambda x, k: x.ewm(span=k).mean(),
    "expanding_odchylenie": lambda x, k: x.expanding().std(),
    "log_zwrot": lambda x, k: np.log(x).diff(),
    "cumsum": lambda x, k: x.cumsum(),
    "z_wsteczny": lambda x, k: (x - x.rolling(k).mean()) / x.rolling(k).std(),
}


@pytest.mark.parametrize("lag", [0, 2])
@pytest.mark.parametrize("nazwa", sorted(POPRAWNE))
def test_poprawna_cecha_bez_falszywego_alarmu(nazwa, lag):
    def compute(df):
        return POPRAWNE[nazwa](df["x"], 7).shift(lag)

    n = sprawdz_przeciek(compute, _ramka_x(), PUNKTY_X, opoznienie=lag)
    assert n is None, str(n)


@pytest.mark.parametrize("nazwa", sorted(POPRAWNE))
def test_poprawna_cecha_z_dziurami_i_nan_bez_falszywego_alarmu(nazwa):
    df = _ramka_ts(120, usun=(30, 31, 70), nan_w=(50, 90))
    n = sprawdz_przeciek(lambda d: POPRAWNE[nazwa](_szereg(d), 7), df, ciecia(df))
    assert n is None, str(n)


# ---------- 6. przypięte zachowanie harnessu ----------


def test_domyslne_argumenty_harnessu():
    """Domyślne ustawienia są bramką: wszystkie 4 zakłócenia, obcięcie, tolerancja zero."""
    par = inspect.signature(sprawdz_przeciek).parameters
    assert ZAKLOCENIA == ("losowe", "odwrocone", "skalowane", "nan")
    assert par["zaklocenia"].default == ZAKLOCENIA
    assert par["rtol"].default == 0.0 and par["obciecie"].default is True
    assert par["opoznienie"].default == 0 and par["ziarno"].default == 0


def test_tolerancja_zero_lapie_wyciek_1e13_a_rtol_go_wybacza():
    def maly_wyciek(df):
        return df["x"] + 1e-13 * df["x"].shift(-1)

    df, rodzaje = _ramka_x(), ("losowe", "odwrocone", "skalowane")
    ustawienia = {"zaklocenia": rodzaje, "obciecie": False}
    assert sprawdz_przeciek(maly_wyciek, df, PUNKTY_X, **ustawienia) is not None
    assert sprawdz_przeciek(maly_wyciek, df, PUNKTY_X, rtol=1e-9, **ustawienia) is None


def _warunkowy_nan(df):
    return df["x"].where(df["x"].shift(-1) >= 1.0)


def test_czysty_nan_a_po_zakloceniu_liczba_to_roznica():
    df = _ramka_x()
    n = sprawdz_przeciek(_warunkowy_nan, df, ciecia(df), zaklocenia=("skalowane",), obciecie=False)
    assert n is not None and np.isnan(n.wartosc_czysta) and not np.isnan(n.wartosc_zaklocona)


def test_czysta_liczba_a_po_zakloceniu_nan_to_roznica():
    df = _ramka_x()
    n = sprawdz_przeciek(_warunkowy_nan, df, ciecia(df), zaklocenia=("nan",), obciecie=False)
    assert n is not None and not np.isnan(n.wartosc_czysta) and np.isnan(n.wartosc_zaklocona)


def test_przeciek_w_starszej_etykiecie_niz_cieciowa_jest_lapany():
    df = _ramka_x()

    def f(d):
        s = d["x"].copy()
        s.iloc[5] = d["x"].iloc[-1]  # etykieta 5 podgląda ostatni wiersz próby
        return s

    n = sprawdz_przeciek(f, df, [60], obciecie=False)
    assert n is not None and n.indeks == df.index[5] and n.punkt_ciecia == 60


def test_przeciek_widoczny_dopiero_przy_trzecim_ciecu_nie_umyka():
    df = _ramka_x()

    def f(d):
        s = d["x"].copy()
        s.iloc[150] = d["x"].iloc[151]
        return s

    n = sprawdz_przeciek(f, df, [60, 110, 150, 220], obciecie=False)
    assert n is not None and n.punkt_ciecia == 150


def test_ziarno_jest_jawne_wynik_powtarzalny():
    df = _ramka_x()
    kopia = df.copy()
    a = sprawdz_przeciek(PRZECIEKI["lead_cumsum"], df, PUNKTY_X, ziarno=3)
    b = sprawdz_przeciek(PRZECIEKI["lead_cumsum"], df, PUNKTY_X, ziarno=3)
    pd.testing.assert_frame_equal(df, kopia)  # harness nie rusza wejścia
    assert a == b


def test_cecha_zmieniajaca_wejscie_jest_odrzucona():
    def psuje(d):
        d["x"] = d["x"] * 2
        return d["x"]

    with pytest.raises(ValueError, match="zmienia swoje wejście"):
        sprawdz_przeciek(psuje, _ramka_x(), PUNKTY_X)


def test_cecha_niedeterministyczna_jest_odrzucona():
    licznik = iter(range(10**6))
    with pytest.raises(ValueError, match="deterministyczna"):
        sprawdz_przeciek(lambda d: d["x"] + next(licznik), _ramka_x(), PUNKTY_X)


def test_wynik_o_zlym_ksztalcie_to_blad():
    df = _ramka_x()
    with pytest.raises(TypeError, match="oś czasu wyniku"):
        sprawdz_przeciek(lambda d: d["x"].reset_index(drop=True), df, PUNKTY_X)
    with pytest.raises(TypeError, match="oś czasu wyniku"):
        sprawdz_przeciek(lambda d: d["x"].tz_localize(None), df, PUNKTY_X)
    with pytest.raises(ValueError, match="zduplikowane"):
        sprawdz_przeciek(lambda d: pd.concat([d["x"], d["x"].iloc[:1]]), df, PUNKTY_X)
    with pytest.raises(TypeError, match="pd.Series"):
        sprawdz_przeciek(lambda d: d[["x"]], df, PUNKTY_X)
    with pytest.raises(TypeError, match="liczbowe"):
        sprawdz_przeciek(lambda d: d["x"].astype(str), df, PUNKTY_X)


@pytest.mark.parametrize(
    ("argumenty", "wyjatek", "wzorzec"),
    [
        ({"zaklocenia": ()}, ValueError, "puste"),
        ({"opoznienie": -1}, ValueError, "ujemne"),
        ({"zaklocenia": "nan"}, TypeError, "krotka"),
        ({"zaklocenia": ("nieznane",)}, ValueError, "rodzaj"),
        ({"rtol": -1e-9}, ValueError, "rtol"),
    ],
)
def test_argumenty_oslabiajace_test_sa_odrzucane(argumenty, wyjatek, wzorzec):
    with pytest.raises(wyjatek, match=wzorzec):
        sprawdz_przeciek(PRZECIEKI["przesuniecie_w_przod"], _ramka_x(), PUNKTY_X, **argumenty)


def test_pusty_test_to_blad_a_nie_zielone_swiatlo():
    df = _ramka_x(60)
    with pytest.raises(ValueError, match="pusty"):  # okno 100 > dane: same NaN
        sprawdz_przeciek(lambda d: d["x"].rolling(100).mean(), df, [30])
    with pytest.raises(ValueError, match="nic po t"):  # cięcie na ostatnim wierszu
        sprawdz_przeciek(lambda d: d["x"], df, [59])
    with pytest.raises(ValueError, match="spoza"):
        sprawdz_przeciek(lambda d: d["x"], df, [60])
    with pytest.raises(ValueError, match="brak punktów"):
        sprawdz_przeciek(lambda d: d["x"], df, [])
    with pytest.raises(ValueError, match="przed pierwszym"):
        sprawdz_przeciek(lambda d: d["x"], df, [START - DZIEN])


def test_wejscie_z_zepsuta_osia_lub_kolumnami_to_blad():
    df = _ramka_ts(30)
    f = lambda d: _szereg(d)
    with pytest.raises(ValueError, match="rosnąć"):
        sprawdz_przeciek(f, df.iloc[::-1], [5])
    with pytest.raises(ValueError, match="rosnąć"):
        sprawdz_przeciek(f, pd.concat([df, df.iloc[:1]]), [5])
    with pytest.raises(ValueError, match="braki"):
        sprawdz_przeciek(f, df.assign(timestamp=[pd.NaT] + list(df["timestamp"].iloc[1:])), [5])
    with pytest.raises(ValueError, match="unikalne"):
        sprawdz_przeciek(f, pd.concat([df, df[["x"]]], axis=1), [5])
    naiwna = _ramka_x(30).tz_localize(None)  # oś w indeksie, bez strefy
    with pytest.raises(ValueError, match="strefę"):
        sprawdz_przeciek(lambda d: d["x"], naiwna, [START])


def test_cieciem_moze_byc_chwila_a_naiwna_chwila_jest_utc():
    df = _ramka_ts(60)
    n = sprawdz_przeciek(lambda d: _szereg(d).shift(-1), df, [pd.Timestamp("2021-02-01")])
    assert n is not None and n.czas_ciecia == pd.Timestamp("2021-02-01", tz="UTC")


def test_os_liczbowa_pozycje_i_opoznienie_w_wierszach():
    df = pd.DataFrame({"x": np.random.default_rng(0).normal(size=60)})
    assert sprawdz_przeciek(lambda d: d["x"].shift(-1), df, ciecia(df)) is not None
    assert sprawdz_przeciek(lambda d: d["x"].shift(1), df, ciecia(df), opoznienie=1) is None
    assert sprawdz_przeciek(lambda d: d["x"], df, ciecia(df), opoznienie=1) is not None
    with pytest.raises(TypeError, match="pozycję"):
        sprawdz_przeciek(lambda d: d["x"], df, ["a"])


@pytest.mark.parametrize("rodzaj", ZAKLOCENIA)
@pytest.mark.parametrize("typ", ["float", "int", "bool", "boolean", "tekst", "obiekt", "kategoria"])
def test_zaklocenie_kolumny_zostawia_przeszlosc_i_zmienia_przyszlosc(typ, rodzaj):
    n, t = 40, 20
    seria = {
        "float": lambda: pd.Series(np.linspace(1.0, 9.0, n)),
        "int": lambda: pd.Series(np.arange(1, n + 1)),
        "bool": lambda: pd.Series(np.arange(n) % 2 == 0),
        "boolean": lambda: pd.Series(np.arange(n) % 2 == 0, dtype="boolean"),
        "tekst": lambda: pd.Series([f"s{i}" for i in range(n)]),
        "obiekt": lambda: pd.Series([f"s{i}" for i in range(n)], dtype=object),
        "kategoria": lambda: pd.Series([f"s{i}" for i in range(n)], dtype="category"),
    }[typ]()
    kopia = seria.copy()
    maska = np.arange(n) >= t
    wynik = _zaklocona_kolumna(seria, maska, rodzaj, np.random.default_rng(0))
    assert list(seria) == list(kopia)  # wejście nietknięte
    assert list(wynik.iloc[:t]) == list(kopia.iloc[:t])
    stara_przyszlosc, nowa_przyszlosc = list(kopia.iloc[t:]), list(wynik.iloc[t:])
    assert str(stara_przyszlosc) != str(nowa_przyszlosc)
    if rodzaj == "nan":
        assert wynik.iloc[t:].isna().all()


def test_zaklocenie_losowe_liczb_ma_losowa_skale():
    """Stała kolumna zakłócona samym losowaniem z siebie nic by nie zmieniła — skala to chroni."""
    seria = pd.Series(np.full(40, 2.0))
    maska = np.arange(40) >= 20
    a = _zaklocona_kolumna(seria, maska, "losowe", np.random.default_rng(0))
    assert (a.iloc[20:] != 2.0).all() and a.iloc[20:].between(0.2, 20.0).all()
    assert a.iloc[20:].nunique() > 1  # losowa skala, nie jedna stała


def test_ziarno_sprawdz_przeciek_steruje_zakloceniem_i_jest_powtarzalne():
    def widziane(ziarno: int) -> list[np.ndarray]:
        wywolania: list[np.ndarray] = []

        def compute(d: pd.DataFrame) -> pd.Series:
            wywolania.append(d["x"].to_numpy(copy=True))
            return d["x"]

        punkt = [START + 10 * DZIEN]
        sprawdz_przeciek(
            compute, _ramka_x(30), punkt, zaklocenia=("losowe",), ziarno=ziarno, obciecie=False
        )
        return wywolania

    a, b, c = widziane(0), widziane(0), widziane(1)
    assert len(a) == len(b) == len(c) and all(np.array_equal(x, y) for x, y in zip(a, b))
    assert any(not np.array_equal(x, y) for x, y in zip(a, c))  # inne ziarno = inne śmieci


@pytest.mark.parametrize("rodzaj", ZAKLOCENIA)
@pytest.mark.parametrize("typ", ["data", "przedzial"])
def test_zaklocenie_kolumn_czasowych(typ, rodzaj):
    n, t = 40, 20
    if typ == "data":
        seria = pd.Series(pd.date_range("2022-01-01", periods=n, freq="D", tz="UTC"))
    else:
        seria = pd.Series(pd.to_timedelta(np.arange(1, n + 1), unit="h"))
    wynik = _zaklocona_kolumna(seria, np.arange(n) >= t, rodzaj, np.random.default_rng(0))
    assert list(wynik.iloc[:t]) == list(seria.iloc[:t])
    assert str(list(wynik.iloc[t:])) != str(list(seria.iloc[t:]))


def test_ciecia_bez_dziur_to_wszystkie_wiersze_oprocz_ostatniego():
    df = _ramka_ts(30)
    assert ciecia(df) == list(df["timestamp"].iloc[:-1])


def test_ciecia_dodaja_sloty_dziur():
    df = _ramka_ts(30, usun=(10, 11, 20))
    c = ciecia(df)
    assert {START + 10 * DZIEN, START + 11 * DZIEN, START + 20 * DZIEN} <= set(c)
    assert c == sorted(c) and len(c) == 29 - 3 + 3


def test_ciecia_os_liczbowa_to_pozycje():
    assert ciecia(pd.DataFrame({"x": np.arange(10.0)})) == list(range(9))


def test_ciecia_probka_jest_deterministyczna_i_zachowuje_dziury():
    df = _ramka_ts(200, usun=(50, 51, 120))
    a, b, c = (ciecia(df, ile=20, ziarno=s) for s in (7, 7, 8))
    assert a == b and a != c
    assert {START + 50 * DZIEN, START + 51 * DZIEN, START + 120 * DZIEN} <= set(a)
    assert len(a) == 20 + 3


def test_ciecia_koniec_doby_na_siatce_8h_z_brakujaca_doba():
    df = dane_dla("funding", dziury=True)  # doby 30 i 31 bez żadnej stawki
    c = ciecia(df, koniec_doby=True)
    assert c == sorted(c) and len(c) == 199
    assert all(t.hour == 16 for t in c)
    assert {_koniec_doby(30, KROK_8H), _koniec_doby(31, KROK_8H)} <= set(c)
    assert len(ciecia(df, ile=10, koniec_doby=True)) == 10 + 2  # doby bez wierszy zawsze zostają


def test_ciecia_koniec_doby_na_siatce_5m():
    c = ciecia(dane_dla("swiece_5m"), koniec_doby=True)
    assert len(c) == 109 and all(t.hour == 23 and t.minute == 55 for t in c)


def test_ciecia_bledy():
    rzadka = pd.DataFrame(
        {"timestamp": pd.date_range(START, periods=10, freq="7D"), "x": np.arange(10.0)}
    )
    with pytest.raises(ValueError, match="nie rzadszej"):
        ciecia(rzadka, koniec_doby=True)
    with pytest.raises(ValueError, match="za mało"):
        ciecia(_ramka_ts(30).iloc[:1])


# ---------- 7. masa punktowa (FR-12) ----------


def _funding_podobny(n: int = 2000, masa: float = 0.36, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = rng.normal(1e-4, 5e-5, n)
    x[rng.permutation(n)[: int(masa * n)]] = 1e-4
    return x


def test_masa_punktowa_funding_blokuje_progi_percentylowe():
    x = pd.Series(_funding_podobny(masa=0.36))
    assert masa_punktowa(x) == pytest.approx(0.36, abs=1e-3)
    with pytest.raises(MasaPunktowaBlad, match="percentylowe"):
        walidacja_progu_percentylowego(x)


def test_masa_punktowa_szereg_ciagly_przechodzi():
    x = np.random.default_rng(1).normal(size=2000)
    assert masa_punktowa(x) == pytest.approx(1 / 2000)
    assert walidacja_progu_percentylowego(x) == pytest.approx(1 / 2000)


def test_prog_masy_punktowej_to_20_procent_z_fr12():
    assert PROG_MASY == 0.20
    wyzej = _funding_podobny(
        n=1000, masa=0.25
    )  # 25 % > 20 %: musi być zatrzymane domyślnym progiem
    with pytest.raises(MasaPunktowaBlad, match="percentylowe"):
        walidacja_progu_percentylowego(wyzej)


def test_masa_punktowa_granica_nan_i_zaokraglenie():
    x = _funding_podobny(n=1000, masa=0.20)
    assert walidacja_progu_percentylowego(x) == pytest.approx(0.20)  # dokładnie 20 % jest dozwolone
    with pytest.raises(MasaPunktowaBlad):
        walidacja_progu_percentylowego(x, prog_masy=0.19)
    z_nan = np.concatenate([x, np.full(500, np.nan)])
    assert masa_punktowa(z_nan) == pytest.approx(0.20)  # NaN nie liczą się do mianownika
    szum = pd.Series(1e-4 + np.random.default_rng(2).normal(0, 1e-16, 1000))  # jedna wartość ± szum
    assert masa_punktowa(szum) < 0.01
    assert masa_punktowa(szum, miejsca=12) == 1.0
    with pytest.raises(ValueError, match="pusty"):
        masa_punktowa([np.nan, np.nan])


def test_masa_punktowa_surowego_funding_z_fabryki():
    stawki = dane_dla("funding")["funding_rate"]
    assert masa_punktowa(stawki) == pytest.approx(
        260 / 600
    )  # 30 dób x 3 + 170 dób x 1 stawek bazowych
    with pytest.raises(MasaPunktowaBlad):
        walidacja_progu_percentylowego(stawki)


# ---------- własności (hypothesis) ----------

ULAMKI = st.lists(st.floats(0.0, 1.0), min_size=1, max_size=3)


def _punkty(ulamki, lo: int, hi: int) -> list[int]:
    return [lo + int(u * (hi - lo)) for u in ulamki]


@settings(max_examples=40, deadline=None)
@given(
    n=st.integers(80, 300),
    seed=st.integers(0, 10_000),
    okno=st.integers(2, 15),
    lag=st.integers(0, 3),
    nazwa=st.sampled_from(sorted(POPRAWNE)),
    ulamki=ULAMKI,
)
def test_hypothesis_poprawne_cechy_bez_falszywych_alarmow(n, seed, okno, lag, nazwa, ulamki):
    def compute(df):
        return POPRAWNE[nazwa](df["x"], okno).shift(lag)

    punkty = _punkty(ulamki, okno + lag + 3, n - 2)
    wynik = sprawdz_przeciek(compute, _ramka_x(n, seed), punkty, opoznienie=lag, ziarno=seed)
    assert wynik is None, str(wynik)


@settings(max_examples=30, deadline=None)
@given(
    n=st.integers(60, 200),
    seed=st.integers(0, 10_000),
    okno=st.integers(2, 12),
    lag=st.integers(0, 3),
    nazwa=st.sampled_from(sorted(POPRAWNE)),
    usun=st.sets(st.integers(1, 55), max_size=6),
)
def test_hypothesis_poprawne_cechy_z_dziurami_bez_falszywych_alarmow(
    n, seed, okno, lag, nazwa, usun
):
    df = _ramka_ts(n, seed, usun=usun)

    def compute(d):
        return POPRAWNE[nazwa](_szereg(d), okno).shift(lag)

    punkty = sorted({*ciecia(df, ile=8, ziarno=seed), df["timestamp"].iloc[-3]})
    wynik = sprawdz_przeciek(compute, df, punkty, opoznienie=lag, ziarno=seed)
    assert wynik is None, str(wynik)


@settings(max_examples=40, deadline=None)
@given(
    n=st.integers(80, 300),
    seed=st.integers(0, 10_000),
    k=st.integers(1, 6),
    ulamki=ULAMKI,
    rodzaj=st.sampled_from(["okno_centrowane", "przesuniecie"]),
)
def test_hypothesis_przeciek_w_przod_jest_wykrywany(n, seed, k, ulamki, rodzaj):
    if rodzaj == "okno_centrowane":

        def compute(df):
            return df["x"].rolling(2 * k + 1, center=True).mean()

    else:

        def compute(df):
            return df["x"].shift(-k)

    punkty = _punkty(ulamki, 2 * k + 3, n - 2 - k)
    assert sprawdz_przeciek(compute, _ramka_x(n, seed), punkty, ziarno=seed) is not None


@settings(max_examples=30, deadline=None)
@given(
    n=st.integers(40, 150),
    seed=st.integers(0, 10_000),
    usun=st.sets(st.integers(1, 35), min_size=1, max_size=5),
)
def test_hypothesis_bfill_przez_dziure_jest_zawsze_wykrywany(n, seed, usun):
    df = _ramka_ts(n, seed, usun=usun)
    assert sprawdz_przeciek(LUKI["bfill_kalendarza"], df, ciecia(df), ziarno=seed) is not None


@settings(max_examples=30, deadline=None)
@given(
    n=st.integers(40, 150),
    usun=st.sets(st.integers(1, 35), max_size=6),
)
def test_hypothesis_ciecia_pokrywaja_kazda_dziure(n, usun):
    df = _ramka_ts(n, usun=usun)
    c = ciecia(df)
    assert c == sorted(c) and len(set(c)) == len(c) and max(c) < df["timestamp"].iloc[-1]
    assert {START + i * DZIEN for i in usun} <= set(c)


@settings(max_examples=40, deadline=None)
@given(
    n=st.integers(50, 1500),
    masa=st.floats(0.0, 0.9),
    seed=st.integers(0, 10_000),
)
def test_hypothesis_masa_punktowa_w_granicach_i_zgodna_z_blokada(n, masa, seed):
    x = _funding_podobny(n, masa, seed)
    m = masa_punktowa(x)
    assert 1 / n <= m <= 1.0
    if m > PROG_MASY:
        with pytest.raises(MasaPunktowaBlad):
            walidacja_progu_percentylowego(x)
    else:
        assert walidacja_progu_percentylowego(x) == m
