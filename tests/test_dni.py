"""Klasyfikacja dni 5m (zadanie 014): martwe ogony, dziury, parytet z Poprawką 1 F2-1, własności."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from dane import dni as dn
from dane.rv import rv_dzienna
from modele import run_f21

START = pd.Timestamp("2021-01-01", tz="UTC")
TRYBY = ("ruch", "stala", "bez_obrotu", "ruch_bez_obrotu")
KOLUMNY = ["n_swiec", "wolumen", "rv", "martwy", "po_dziurze", "niepelny", "wazny"]


def _swiece(spec: list[tuple[int, str]], seed: int = 0) -> pd.DataFrame:
    """
    Świece 5m na kolejne dni od 2021-01-01: `spec` = (liczba świec od 00:00, tryb) na dzień.
    Tryb: `ruch` (cena się rusza, obrót > 0), `stala` (stała cena, obrót > 0), `bez_obrotu`
    (stała cena, obrót 0 — martwy ogon), `ruch_bez_obrotu` (cena się rusza, obrót 0).
    Dzień z 0 świec = dziura archiwum. Cena jest ciągła między dniami.
    """
    rng = np.random.default_rng(seed)
    czesci, cena = [], 100.0
    for i, (n, tryb) in enumerate(spec):
        ts = START + pd.Timedelta(days=i) + pd.to_timedelta(np.arange(n) * 5, unit="min")
        rusza = tryb in ("ruch", "ruch_bez_obrotu")
        zmiany = rng.normal(0, 0.002, n) if rusza else np.zeros(n)
        close = cena * np.exp(np.cumsum(zmiany))
        cena = float(close[-1]) if n else cena
        vol = np.zeros(n) if "bez_obrotu" in tryb else rng.uniform(1.0, 2.0, n)
        czesci.append(pd.DataFrame({"timestamp": ts, "close": close, "volume": vol}))
    return pd.concat(czesci, ignore_index=True)


def _maska_poprawki1(df5m: pd.DataFrame) -> pd.Series:
    """Maska dnia ważnego z `modele.run_f21.straty_monety` (Poprawka 1), przepisana 1:1."""
    d = rv_dzienna(df5m)
    rv = d["rv"].where((d["n_swiec"] >= 274) & (d["rv"] > 0))
    return rv.notna()


def test_dzien_pelny():
    out = dn.dni_wazne(_swiece([(288, "ruch")] * 3))
    assert list(out.columns) == KOLUMNY and out.index.name == "day"
    assert str(out.index.tz) == "UTC" and len(out) == 3
    assert (out["n_swiec"] == 288).all() and (out["wolumen"] > 0).all()
    assert out["rv"].iloc[1:].gt(0).all()
    assert not out[["martwy", "po_dziurze", "niepelny"]].any().any()
    assert out["wazny"].tolist() == [False, True, True]  # pierwszy dzień: rv NaN


def test_dzien_niepelny_granica_274():
    out = dn.dni_wazne(_swiece([(288, "ruch"), (273, "ruch"), (274, "ruch"), (100, "ruch")]))
    assert out["niepelny"].tolist() == [False, True, False, True]
    assert out["wazny"].tolist() == [False, False, True, False]
    assert not out["po_dziurze"].any() and not out["martwy"].any()
    luzny = dn.dni_wazne(_swiece([(288, "ruch"), (273, "ruch")]), min_swiec=200)
    assert luzny["wazny"].tolist() == [False, True] and not luzny["niepelny"].any()


def test_martwy_ogon_stala_cena_bez_obrotu():
    out = dn.dni_wazne(_swiece([(288, "ruch")] * 2 + [(288, "bez_obrotu")] * 2))
    assert out["martwy"].tolist() == [False, False, True, True]
    assert (out["rv"].iloc[2:] == 0).all() and (out["wolumen"].iloc[2:] == 0).all()
    assert out["wazny"].tolist() == [False, True, False, False]
    assert not out["niepelny"].any()  # pełne 288 świec, a mimo to nie handel


def test_martwy_rv_zero_albo_wolumen_zero():
    """rv == 0 (stała cena z obrotem) i wolumen == 0 (ruch ceny bez obrotu) są martwe osobno."""
    spec = [(288, "ruch"), (288, "stala"), (288, "ruch_bez_obrotu"), (288, "ruch")]
    out = dn.dni_wazne(_swiece(spec))
    assert out["martwy"].tolist() == [False, True, True, False]
    assert out["rv"].iloc[1] == 0 and out["wolumen"].iloc[1] > 0
    assert out["rv"].iloc[2] > 0 and out["wolumen"].iloc[2] == 0
    # `wazny` = Poprawka 1 (patrzy tylko na rv): dzień z obrotem 0 i rv > 0 zostaje ważny
    assert out["wazny"].tolist() == [False, False, True, True]
    assert not (out["wazny"] & ~out["martwy"]).iloc[2]


def test_dziura_wielodniowa_dni_bez_swiec_sa_w_wyniku():
    df = _swiece([(288, "ruch")] * 2 + [(0, "ruch")] * 2 + [(288, "ruch")] * 2)
    out = dn.dni_wazne(df)
    assert len(out) == 6
    assert out.index.to_list() == list(pd.date_range(START, periods=6, freq="D"))
    assert out["n_swiec"].tolist() == [288, 288, 0, 0, 288, 288]
    assert out["rv"].iloc[2:4].isna().all() and (out["wolumen"].iloc[2:4] == 0).all()
    assert out["niepelny"].tolist() == [False, False, True, True, False, False]
    assert not out["martwy"].any()  # brak danych to nie martwy dzień
    assert out["wazny"].tolist() == [False, True, False, False, True, True]
    # rv dnia po dziurze zawiera zwrot od zamknięcia sprzed dziury
    d = rv_dzienna(df)  # rv_dzienna nie ma pustych dni: jej wiersz 2 to dzień 4
    assert out["rv"].iloc[4] == d["rv"].iloc[2]


def test_dzien_po_dziurze_flaga_i_wykluczenie():
    df = _swiece([(288, "ruch")] * 2 + [(0, "ruch")] * 3 + [(288, "ruch")] * 2)
    out = dn.dni_wazne(df)
    assert out["po_dziurze"].tolist() == [False, False, False, False, False, True, False]
    assert out["wazny"].iloc[5]  # domyślnie jak w F2-1: flaga nie wyklucza
    strict = dn.dni_wazne(df, wyklucz_po_dziurze=True)
    assert strict["wazny"].tolist() == [False, True, False, False, False, False, True]
    pd.testing.assert_frame_equal(out.drop(columns="wazny"), strict.drop(columns="wazny"))
    wazne_po_dziurze = dn.podsumowanie_dni(out)["wazne_po_dziurze"]
    assert wazne_po_dziurze == int(out["wazny"].sum() - strict["wazny"].sum()) == 1


def test_dziura_krotsza_niz_doba_nie_jest_po_dziurze():
    out = dn.dni_wazne(_swiece([(288, "ruch"), (100, "ruch"), (288, "ruch")]))
    assert not out["po_dziurze"].any()
    assert out["niepelny"].tolist() == [False, True, False]


def test_pierwszy_dzien_historii():
    out = dn.dni_wazne(_swiece([(288, "ruch"), (288, "ruch")]))
    assert np.isnan(out["rv"].iloc[0])
    assert not out["wazny"].iloc[0] and not out["po_dziurze"].iloc[0] and not out["martwy"].iloc[0]
    # historia zaczyna się od martwego ogona: rv NaN, więc o martwości rozstrzyga wolumen
    zero = dn.dni_wazne(_swiece([(288, "bez_obrotu"), (288, "ruch")]))
    assert zero["martwy"].tolist() == [True, False] and not zero["wazny"].iloc[0]


def test_dni_na_poczatku_bez_swiec_nie_wchodza_do_kalendarza():
    """Kalendarz idzie od pierwszego do ostatniego dnia ZE świecami (jak `rv_dzienna`)."""
    out = dn.dni_wazne(_swiece([(0, "ruch"), (288, "ruch"), (288, "ruch")]))
    assert out.index[0] == START + pd.Timedelta(days=1) and len(out) == 2


def test_blady_wejscia():
    df = _swiece([(288, "ruch")] * 2)
    with pytest.raises(ValueError, match="volume"):
        dn.dni_wazne(df.drop(columns="volume"))
    with pytest.raises(ValueError, match="close"):
        dn.dni_wazne(df.drop(columns="close"))
    with pytest.raises(ValueError, match="timestamp"):
        dn.dni_wazne(df.drop(columns="timestamp"))
    with pytest.raises(ValueError, match="pusty"):
        dn.dni_wazne(df.iloc[:0])
    with pytest.raises(ValueError, match="duplikaty"):
        dn.dni_wazne(pd.concat([df, df.iloc[:1]]))


@pytest.mark.parametrize("tz", ["Europe/Warsaw", "Etc/GMT-5", "America/New_York"])
def test_strefa_inna_niz_utc_jest_odrzucana(tz):
    """Doba to doba UTC: znacznik w czasie lokalnym podzieliłby dni po lokalnej północy."""
    df = _swiece([(288, "ruch")] * 3)
    with pytest.raises(ValueError, match="UTC"):
        dn.dni_wazne(df.assign(timestamp=df["timestamp"].dt.tz_convert(tz)))


def test_znacznik_naiwny_lub_nie_czas_jest_odrzucany():
    df = _swiece([(288, "ruch")] * 3)
    with pytest.raises(ValueError, match="UTC"):
        dn.dni_wazne(df.assign(timestamp=df["timestamp"].dt.tz_localize(None)))
    ms = df["timestamp"].astype("int64") // 10**6
    with pytest.raises(ValueError, match="UTC"):
        dn.dni_wazne(df.assign(timestamp=ms))
    z_nat = df.copy()
    z_nat.loc[5, "timestamp"] = pd.NaT
    with pytest.raises(ValueError, match="NaT"):
        dn.dni_wazne(z_nat)


def test_utc_w_roznych_zapisach_jest_przyjmowane():
    df = _swiece([(288, "ruch")] * 3)
    ref = dn.dni_wazne(df).reset_index(drop=True)
    for tz in ("UTC", "Etc/UTC"):
        out = dn.dni_wazne(df.assign(timestamp=df["timestamp"].dt.tz_convert(tz)))
        pd.testing.assert_frame_equal(ref, out.reset_index(drop=True))


@pytest.mark.parametrize(
    "kolumna, wartosc, komunikat",
    [
        ("close", np.nan, "close"),
        ("close", np.inf, "close"),
        ("close", 0.0, "close"),
        ("close", -1.0, "close"),
        ("volume", np.nan, "volume"),
        ("volume", np.inf, "volume"),
        ("volume", -1.0, "volume"),
    ],
)
def test_braki_i_nieskonczonosci_w_cenie_lub_wolumenie_sa_odrzucane(kolumna, wartosc, komunikat):
    """Bez cichych napraw: NaN w `close` byłby pominięty w RV, NaN w `volume` dałby „martwy”."""
    df = _swiece([(288, "ruch")] * 3)
    df.loc[400, kolumna] = wartosc
    with pytest.raises(ValueError, match=komunikat):
        dn.dni_wazne(df)
    dzien = df["timestamp"].dt.floor("D") == START + pd.Timedelta(days=1)
    df.loc[dzien, kolumna] = wartosc  # cały dzień naraz (np. dzień samych NaN)
    with pytest.raises(ValueError, match=komunikat):
        dn.dni_wazne(df)


@pytest.mark.parametrize("min_swiec", [-5, 0, 289, 273.5, True, "274"])
def test_min_swiec_poza_zakresem_jest_odrzucane(min_swiec):
    with pytest.raises(ValueError, match="min_swiec"):
        dn.dni_wazne(_swiece([(288, "ruch")] * 2), min_swiec=min_swiec)


def test_min_swiec_na_granicach_zakresu_dziala():
    df = _swiece([(288, "ruch"), (1, "ruch"), (288, "ruch")])
    assert not dn.dni_wazne(df, min_swiec=1)["niepelny"].any()
    assert dn.dni_wazne(df, min_swiec=np.int64(288))["niepelny"].tolist() == [False, True, False]


def test_nie_zmienia_wejscia_i_nie_zalezy_od_kolejnosci_wierszy():
    df = _swiece([(288, "ruch"), (0, "ruch"), (288, "bez_obrotu"), (120, "ruch")])
    a = dn.dni_wazne(df)
    nieposortowane = df.sample(frac=1.0, random_state=1)  # wejście celowo w złej kolejności
    kopia = nieposortowane.copy()
    b = dn.dni_wazne(nieposortowane)
    pd.testing.assert_frame_equal(nieposortowane, kopia)  # nie sortuje wejścia w miejscu
    pd.testing.assert_frame_equal(a, b)


def test_martwy_to_dokladne_zero_a_nie_tolerancja():
    """Mikroskopijny, ale dodatni wolumen i rv nie są martwe — bez progu tolerancji."""
    n = 288
    ts = START + pd.to_timedelta(np.arange(3 * n) * 5, unit="min")
    close = 100.0 * np.exp(np.cumsum(np.r_[0.0, np.full(3 * n - 1, 1e-8)]))
    df = pd.DataFrame({"timestamp": ts, "close": close, "volume": np.full(3 * n, 1e-9)})
    out = dn.dni_wazne(df)
    assert (out["wolumen"].iloc[1:] > 0).all() and (out["wolumen"].iloc[1:] < 1e-5).all()
    assert (out["rv"].iloc[1:] > 0).all() and (out["rv"].iloc[1:] < 1e-9).all()
    assert not out["martwy"].any() and out["wazny"].tolist() == [False, True, True]


def test_dzien_z_jedna_swieca_jest_dniem_a_nie_dziura():
    """1 świeca to już dzień ze świecami: bez flagi `po_dziurze`, martwy tylko przy zerach."""
    out = dn.dni_wazne(_swiece([(288, "ruch"), (1, "bez_obrotu"), (288, "ruch"), (1, "ruch")]))
    assert out["n_swiec"].tolist() == [288, 1, 288, 1]
    assert out["martwy"].tolist() == [False, True, False, False]
    assert out["po_dziurze"].tolist() == [False, False, False, False]  # po 1 świecy nie ma dziury
    assert out["niepelny"].tolist() == [False, True, False, True]
    assert out["wazny"].tolist() == [False, False, True, False]
    # dzień zaraz po dniu z 0 świec jest po dziurze, zaraz po dniu z 1 świecą — nie
    d = dn.dni_wazne(_swiece([(288, "ruch"), (0, "ruch"), (1, "ruch"), (288, "ruch")]))
    assert d["po_dziurze"].tolist() == [False, False, True, False]


def test_dziura_konczaca_sie_o_polnocy_nie_jest_flagowana():
    """Udokumentowane ograniczenie: flaga łapie tylko dziury całodobowe (patrz `dni_wazne`)."""
    out = dn.dni_wazne(_swiece([(288, "ruch"), (10, "ruch"), (288, "ruch")]))
    assert out["niepelny"].tolist() == [False, True, False]
    assert not out["po_dziurze"].any()
    assert out["wazny"].tolist() == [False, False, True]  # RV dnia 3 ma zwrot z kilku godzin


def test_dzien_po_martwym_segmencie_nie_jest_po_dziurze():
    """Martwy segment ZE świecami (jak PUMPUSDT 2025) nie jest dziurą — to zakres flagi `martwy`."""
    out = dn.dni_wazne(_swiece([(288, "ruch")] + [(288, "bez_obrotu")] * 3 + [(288, "ruch")]))
    assert out["martwy"].tolist() == [False, True, True, True, False]
    assert not out["po_dziurze"].any() and not out["niepelny"].any()
    assert out["wazny"].tolist() == [False, False, False, False, True]


def test_podsumowanie_dni():
    spec = [(288, "ruch")] * 2 + [(0, "ruch")] + [(288, "ruch"), (288, "bez_obrotu")]
    spec += [(50, "ruch"), (3, "ruch")]
    s = dn.podsumowanie_dni(dn.dni_wazne(_swiece(spec)))
    assert s == {
        "dni": 7,
        "wazne": 2,  # dni 1 i 3 (dzień 0: rv NaN; 2: dziura; 4: martwy; 5, 6: niepełne)
        "martwe": 1,
        "po_dziurze": 1,
        "niepelne": 3,  # dziura + dzień z 50 świecami + dzień z 3 świecami
        "bez_swiec": 1,  # dzień z 3 świecami to NIE brak świec
        "wazne_po_dziurze": 1,
    }


@pytest.mark.parametrize("seed", range(8))
def test_parytet_z_maska_poprawki1_na_syntetycznych(seed):
    """Domyślny `wazny` = lista dni ważnych z F2-1; dni bez świec (których tam nie ma) nieważne."""
    rng = np.random.default_rng(seed)
    n = rng.choice([0, 0, 1, 100, 273, 274, 288, 288, 288], size=40)
    tryby = rng.choice(TRYBY, size=40, p=[0.6, 0.15, 0.15, 0.1])
    df = _swiece(list(zip(n.tolist(), tryby.tolist())), seed=seed)
    out = dn.dni_wazne(df)
    maska = _maska_poprawki1(df)
    pd.testing.assert_series_equal(
        out["wazny"].reindex(maska.index), maska, check_names=False, check_freq=False
    )
    assert not out["wazny"].drop(maska.index).any()
    assert set(out.index[out["wazny"]]) == set(maska.index[maska])


def _spec_parytetu() -> list[tuple[int, str]]:
    """250 dni: dziura 2 dni, dni z 100/273/274 świecami, stała cena z obrotem, martwy segment."""
    spec = [(288, "ruch")] * 250
    for i, wpis in {
        60: (0, "ruch"),
        61: (0, "ruch"),
        80: (100, "ruch"),
        100: (273, "ruch"),
    }.items():
        spec[i] = wpis
    spec[101], spec[130] = (274, "ruch"), (288, "stala")
    for i in range(150, 156):
        spec[i] = (288, "bez_obrotu")
    spec[200] = (288, "ruch_bez_obrotu")
    return spec


def test_min_swiec_jak_w_run_f21():
    assert dn.MIN_SWIEC == run_f21.MIN_SWIEC == 274


def test_parytet_z_prawdziwym_straty_monety_z_run_f21(monkeypatch):
    """
    Dni ważne = dokładnie te RV, które `modele.run_f21.straty_monety` (Poprawka 1) podaje do HAR.
    Wywołujemy PRAWDZIWĄ funkcję z F2-1 (bez przepisanej maski), podmieniając tylko prognozę HAR
    na przechwyt wejścia — zmiana maski albo MIN_SWIEC w run_f21 zepsuje ten test.
    """
    przechwycone = []

    def przechwyt(rv, min_trening=365, co_ile=30):
        przechwycone.append(rv)
        return pd.Series(1.0, index=rv.index)

    monkeypatch.setattr(run_f21, "prognoza_har", przechwyt)
    df = _swiece(_spec_parytetu(), seed=3)
    run_f21.straty_monety(df, min_trening=30, co_ile=10)
    (rv_f21,) = przechwycone
    dni = dn.dni_wazne(df)
    wazne = dni.index[dni["wazny"]]
    assert 200 < len(wazne) < 250  # dane mają dni ważne i nieważne (test nie jest pusty)
    assert set(rv_f21.index[rv_f21.notna()]) == set(wazne)
    pd.testing.assert_series_equal(
        rv_f21.dropna(), dni.loc[wazne, "rv"], check_names=False, check_freq=False
    )
    assert dn._dni_z_poprawki1(df, dn.MIN_SWIEC) == set(wazne)


def test_straty_monety_z_prawdziwym_har_uzywa_tylko_dni_waznych():
    df = _swiece(_spec_parytetu(), seed=3)
    straty = run_f21.straty_monety(df, min_trening=30, co_ile=10)
    dni = dn.dni_wazne(df)
    assert len(straty) > 50
    assert set(straty.index) <= set(dni.index[dni["wazny"]])


# --- własności (hypothesis) -------------------------------------------------------------------

spec_st = st.lists(
    st.tuples(st.sampled_from([0, 1, 100, 273, 274, 288]), st.sampled_from(TRYBY)),
    min_size=2,
    max_size=12,
)


@settings(max_examples=60, deadline=None)
@given(spec=spec_st, min_swiec=st.integers(1, 288), seed=st.integers(0, 3))
def test_wazny_implikuje_pelny_i_dodatnie_rv(spec, min_swiec, seed):
    df = _swiece(spec, seed)
    assume(len(df) > 0)
    out = dn.dni_wazne(df, min_swiec=min_swiec)
    w = out[out["wazny"]]
    assert (w["n_swiec"] >= min_swiec).all() and (w["rv"] > 0).all()
    assert (out["wazny"] == (~out["niepelny"] & (out["rv"] > 0))).all()
    assert (out.loc[out["martwy"], "n_swiec"] > 0).all()
    assert (out.loc[out["po_dziurze"], "n_swiec"] > 0).all()
    # wyklucz_po_dziurze zawęża zbiór ważnych tylko o dni po dziurze
    strict = dn.dni_wazne(df, min_swiec=min_swiec, wyklucz_po_dziurze=True)
    roznica = out["wazny"] & ~strict["wazny"]
    assert not (strict["wazny"] & ~out["wazny"]).any() and out["po_dziurze"][roznica].all()


def _oczekiwane(spec: list[tuple[int, str]], min_swiec: int) -> pd.DataFrame:
    """Niezależny model odniesienia flag dnia: liczony z samej specyfikacji, bez `dni_wazne`."""
    ma = [i for i, (n, _) in enumerate(spec) if n > 0]
    wiersze = []
    for i in range(ma[0], ma[-1] + 1):
        n, tryb = spec[i]
        pierwszy = i == ma[0]  # pierwszy dzień historii nie ma rv
        rv_zero = n > 0 and not pierwszy and tryb in ("stala", "bez_obrotu")
        rv_dodatnie = n > 0 and not pierwszy and tryb in ("ruch", "ruch_bez_obrotu")
        wiersze.append(
            {
                "n_swiec": n,
                "martwy": rv_zero or (n > 0 and "bez_obrotu" in tryb),
                "po_dziurze": n > 0 and not pierwszy and spec[i - 1][0] == 0,
                "niepelny": n < min_swiec,
                "wazny": n >= min_swiec and rv_dodatnie,
            }
        )
    start = START + pd.Timedelta(days=ma[0])
    indeks = pd.date_range(start, periods=len(wiersze), freq="D", name="day")
    return pd.DataFrame(wiersze, index=indeks)


@settings(max_examples=80, deadline=None)
@given(spec=spec_st, min_swiec=st.integers(1, 288), seed=st.integers(0, 3))
def test_flagi_zgodne_z_modelem_odniesienia(spec, min_swiec, seed):
    """Wszystkie flagi (w tym `martwy` i `po_dziurze` dla dni z 1 świecą) vs niezależny model."""
    df = _swiece(spec, seed)
    assume(len(df) > 0)
    out = dn.dni_wazne(df, min_swiec=min_swiec)
    oczekiwane = _oczekiwane(spec, min_swiec)
    pd.testing.assert_frame_equal(
        out[list(oczekiwane.columns)], oczekiwane, check_dtype=False, check_freq=False
    )


@settings(max_examples=60, deadline=None)
@given(spec=spec_st, seed=st.integers(0, 3))
def test_kalendarz_ciagly_i_dni_bez_swiec_w_wyniku(spec, seed):
    df = _swiece(spec, seed)
    assume(len(df) > 0)
    out = dn.dni_wazne(df)
    ma = [i for i, (n, _) in enumerate(spec) if n > 0]
    oczekiwane = pd.date_range(START + pd.Timedelta(days=ma[0]), START + pd.Timedelta(days=ma[-1]))
    assert out.index.equals(oczekiwane)
    assert out["n_swiec"].tolist() == [spec[i][0] for i in range(ma[0], ma[-1] + 1)]
    pusty = out[out["n_swiec"] == 0]
    assert pusty["rv"].isna().all() and (pusty["wolumen"] == 0).all() and pusty["niepelny"].all()


@settings(max_examples=60, deadline=None)
@given(spec=spec_st, ciecie=st.integers(1, 11), seed=st.integers(0, 3))
def test_dopisanie_dni_nie_zmienia_wczesniejszych(spec, ciecie, seed):
    """Brak przecieku z przyszłości: klasyfikacja dnia nie zależy od dni po nim."""
    assume(ciecie < len(spec))
    df = _swiece(spec, seed)
    do_ciecia = df[df["timestamp"] < START + pd.Timedelta(days=ciecie)]
    assume(len(do_ciecia) > 0)
    czesc = dn.dni_wazne(do_ciecia)
    calosc = dn.dni_wazne(df)
    pd.testing.assert_frame_equal(czesc, calosc.loc[czesc.index], check_freq=False)


# --- raport na plikach (sprawdzenie na danych lokalnych) ----------------------------------------


def _dzien(i: int) -> pd.Timestamp:
    return START + pd.Timedelta(days=i)


def _zapisz_symbol(
    dir_dane,
    symbol: str,
    spec,
    bez_dnia_w_1d: int | None = None,
    dodaj_1d: dict[int, float] | None = None,
    wolumen_1d: dict[int, float] | None = None,
):
    """
    Zapisuje 5m i 1d jednego symbolu. Dni numerowane od 0 (START): `bez_dnia_w_1d` usuwa wiersz 1d,
    `dodaj_1d` dopisuje wiersz 1d (dzień → wolumen) dla dnia, `wolumen_1d` zmienia wolumen 1d dnia.
    """
    df = _swiece(spec)
    (dir_dane / "5m").mkdir(exist_ok=True)
    (dir_dane / "1d").mkdir(exist_ok=True)
    df.to_parquet(dir_dane / "5m" / f"{symbol}.parquet")
    dzien = df.groupby(df["timestamp"].dt.floor("D")).agg(volume=("volume", "sum")).reset_index()
    for i, v in (wolumen_1d or {}).items():
        dzien.loc[dzien["timestamp"] == _dzien(i), "volume"] = v
    if bez_dnia_w_1d is not None:
        dzien = dzien[dzien["timestamp"] != _dzien(bez_dnia_w_1d)]
    extra = [{"timestamp": _dzien(i), "volume": v} for i, v in (dodaj_1d or {}).items()]
    dzien = pd.concat([dzien, pd.DataFrame(extra)]).sort_values("timestamp")
    dzien.reset_index(drop=True).to_parquet(dir_dane / "1d" / f"{symbol}.parquet")


SPEC_FTM = [(288, "ruch")] * 3 + [(0, "ruch")] + [(288, "ruch"), (288, "bez_obrotu")]


def test_analiza_symbolu_zgodna_z_1d_i_poprawka1(tmp_path):
    spec = [(288, "ruch")] * 3 + [(0, "ruch")] + [(288, "ruch"), (288, "bez_obrotu")] * 2
    _zapisz_symbol(tmp_path, "AAAUSDT", spec)
    r = dn.analiza_symbolu("AAAUSDT", tmp_path / "5m", tmp_path / "1d")
    assert r["martwe"] == r["bez_obrotu_1d"] == r["wolumen0"] == r["rv0"] == r["oba"] == 2
    assert r["tylko_5m"] == r["tylko_1d"] == r["dni_tylko_w_1d"] == r["p1_roznice"] == 0
    assert r["wazne"] == r["p1_wazne"] == 4 and r["bez_swiec"] == 1 and r["po_dziurze"] == 1
    assert r["ostatni_dzien"] == "2021-01-08" and r["ostatni_n_swiec"] == 288
    assert r["wol_rozny"] == 0


def test_analiza_symbolu_pokazuje_roznice_z_1d(tmp_path):
    spec = [(288, "ruch")] * 2 + [(288, "bez_obrotu")] * 2
    _zapisz_symbol(tmp_path, "AAAUSDT", spec, bez_dnia_w_1d=3)  # w 1d brakuje jednego martwego dnia
    r = dn.analiza_symbolu("AAAUSDT", tmp_path / "5m", tmp_path / "1d")
    assert (r["martwe"], r["bez_obrotu_1d"], r["tylko_5m"], r["tylko_1d"]) == (2, 1, 1, 0)
    assert r["dni_tylko_w_1d"] == 0  # dzień jest w 5m, brakuje go w 1d — to inny kierunek


def test_analiza_symbolu_dzien_martwy_tylko_w_1d(tmp_path):
    """Wiersz 1d z obrotem 0 przy dniu z ruchem i obrotem w 5m to `tylko_1d` (nie `tylko_5m`)."""
    _zapisz_symbol(tmp_path, "AAAUSDT", [(288, "ruch")] * 4, wolumen_1d={2: 0.0})
    r = dn.analiza_symbolu("AAAUSDT", tmp_path / "5m", tmp_path / "1d")
    assert (r["martwe"], r["bez_obrotu_1d"], r["tylko_5m"], r["tylko_1d"]) == (0, 1, 0, 1)
    assert r["wol_rozny"] == 1 and r["dni_tylko_w_1d"] == 0


def test_analiza_symbolu_dni_tylko_w_1d(tmp_path):
    """Wiersz 1d dla dnia bez żadnej świecy 5m: `dni_tylko_w_1d`; z obrotem 0 także `tylko_1d`."""
    spec = [(288, "ruch")] * 2 + [(0, "ruch")] + [(288, "ruch")]
    _zapisz_symbol(tmp_path, "AAAUSDT", spec, dodaj_1d={2: 5.0})
    _zapisz_symbol(tmp_path, "BBBUSDT", spec, dodaj_1d={2: 0.0})
    a = dn.analiza_symbolu("AAAUSDT", tmp_path / "5m", tmp_path / "1d")
    b = dn.analiza_symbolu("BBBUSDT", tmp_path / "5m", tmp_path / "1d")
    assert (a["dni_tylko_w_1d"], a["bez_obrotu_1d"], a["tylko_1d"]) == (1, 0, 0)
    assert (b["dni_tylko_w_1d"], b["bez_obrotu_1d"], b["tylko_1d"]) == (1, 1, 1)
    assert a["martwe"] == b["martwe"] == 0 and a["wol_rozny"] == b["wol_rozny"] == 0


SPEC_ZERA = [(288, "ruch"), (288, "stala"), (288, "ruch_bez_obrotu"), (288, "bez_obrotu")]
SPEC_ZERA += [(288, "stala"), (0, "ruch"), (288, "ruch")]


def test_analiza_symbolu_rozroznia_wolumen0_rv0_i_oba(tmp_path):
    """Dzień z samym rv = 0, z samym wolumenem = 0 i z oboma; dzień bez świec nie liczy się."""
    _zapisz_symbol(tmp_path, "AAAUSDT", SPEC_ZERA)
    r = dn.analiza_symbolu("AAAUSDT", tmp_path / "5m", tmp_path / "1d")
    assert (r["wolumen0"], r["rv0"], r["oba"], r["martwe"]) == (2, 3, 1, 4)
    assert (r["bez_obrotu_1d"], r["tylko_5m"], r["tylko_1d"]) == (2, 2, 0)  # `stala` ma obrót > 0
    assert r["bez_swiec"] == 1


def test_raport_rozbija_dni_z_samym_wolumenem_lub_samym_rv(tmp_path):
    _zapisz_symbol(tmp_path, "AAAUSDT", SPEC_ZERA)
    tekst = "\n".join(dn.raport(tmp_path / "5m", tmp_path / "1d", ["AAAUSDT"]))
    assert "dni z samym wolumen = 0 (rv > 0): 1; z samym rv = 0 (wolumen > 0): 2;" in tekst


def test_analiza_symbolu_ostatni_dzien_niepelny(tmp_path):
    _zapisz_symbol(tmp_path, "AAAUSDT", [(288, "ruch")] * 3 + [(117, "ruch")])
    r = dn.analiza_symbolu("AAAUSDT", tmp_path / "5m", tmp_path / "1d")
    assert r["ostatni_dzien"] == "2021-01-04" and r["ostatni_n_swiec"] == 117
    assert r["niepelne"] == 1 and r["wazne"] == 2


def test_analiza_symbolu_przekazuje_min_swiec_do_obu_list(tmp_path):
    _zapisz_symbol(tmp_path, "AAAUSDT", [(288, "ruch"), (273, "ruch"), (288, "ruch")])
    domyslny = dn.analiza_symbolu("AAAUSDT", tmp_path / "5m", tmp_path / "1d")
    luzny = dn.analiza_symbolu("AAAUSDT", tmp_path / "5m", tmp_path / "1d", min_swiec=200)
    assert (domyslny["wazne"], domyslny["niepelne"]) == (1, 1)
    assert (luzny["wazne"], luzny["niepelne"]) == (2, 0)
    assert domyslny["p1_roznice"] == luzny["p1_roznice"] == 0 and luzny["p1_wazne"] == 2


def test_dni_z_poprawki1_granica_274_i_rv_dodatnie():
    df = _swiece([(288, "ruch"), (273, "ruch"), (274, "ruch"), (288, "stala")])
    assert dn._dni_z_poprawki1(df, 274) == {START + pd.Timedelta(days=2)}  # 273 za mało, rv = 0 nie
    assert dn._dni_z_poprawki1(df, 273) == {START + pd.Timedelta(days=i) for i in (1, 2)}


def _rozjedz_poprawke1(monkeypatch, kierunek: str, warunek=lambda df: True):
    """Podmienia listę Poprawki 1 tak, by różniła się o 1 dzień od `dni_wazne` (kontrola R8)."""
    oryginal = dn._dni_z_poprawki1

    def falszywa(df5m, min_swiec):
        dni = oryginal(df5m, min_swiec)
        if not warunek(df5m):
            return dni
        if kierunek == "dodaj":
            return dni | {pd.Timestamp("2030-01-01", tz="UTC")}  # dzień, którego `dni_wazne` nie ma
        return dni - {min(dni)}  # dzień, który `dni_wazne` uznaje za ważny

    monkeypatch.setattr(dn, "_dni_z_poprawki1", falszywa)


@pytest.mark.parametrize("kierunek", ["dodaj", "odejmij"])
def test_analiza_symbolu_wykrywa_rozbieznosc_z_poprawka1_w_obu_kierunkach(
    tmp_path, monkeypatch, kierunek
):
    _zapisz_symbol(tmp_path, "AAAUSDT", SPEC_FTM)
    ref = dn.analiza_symbolu("AAAUSDT", tmp_path / "5m", tmp_path / "1d")
    assert ref["p1_roznice"] == 0
    _rozjedz_poprawke1(monkeypatch, kierunek)
    r = dn.analiza_symbolu("AAAUSDT", tmp_path / "5m", tmp_path / "1d")
    assert r["p1_roznice"] == 1  # różnica symetryczna łapie dzień dodany i odjęty
    assert r["p1_wazne"] == ref["p1_wazne"] + (1 if kierunek == "dodaj" else -1)
    assert r["wazne"] == ref["wazne"]  # `dni_wazne` się nie zmienia


def test_raport_parytet_na_plikach(tmp_path):
    spec = [(288, "ruch")] * 3 + [(0, "ruch")] + [(288, "ruch"), (288, "bez_obrotu")]
    _zapisz_symbol(tmp_path, "FTMUSDT", spec)
    _zapisz_symbol(tmp_path, "BBBUSDT", [(288, "ruch")] * 4)
    tekst = "\n".join(dn.raport(tmp_path / "5m", tmp_path / "1d", ["FTMUSDT", "BBBUSDT"]))
    assert "Parytet: 2/2 symboli z identyczną listą dni, suma różnic 0" in tekst
    assert "FTMUSDT" in tekst and "RAZEM" in tekst
    assert "(symboli z różnicą: 0)" in tekst and "tylko w archiwum 1d: 0" in tekst


def test_raport_wiersz_razem_sumuje_symbole(tmp_path):
    _zapisz_symbol(tmp_path, "FTMUSDT", SPEC_FTM)
    _zapisz_symbol(tmp_path, "BBBUSDT", [(288, "ruch")] * 4)
    linie = dn.raport(tmp_path / "5m", tmp_path / "1d", ["FTMUSDT", "BBBUSDT"])
    razem = next(x for x in linie if x.startswith("RAZEM")).split()[1:]
    # kolejność: dni, wazne, martwe, po_dziurze, niepelne, bez_swiec, wazne_po_dziurze
    # FTM: 6/3/1/1/1/1/1, BBB: 4/3/0/0/0/0/0
    assert razem == ["10", "6", "1", "1", "1", "1", "1"]


def test_raport_pokazuje_rozbieznosc_parytetu(tmp_path, monkeypatch):
    """Kontrola negatywna linii „Parytet”: jedna moneta z rozjechaną listą → 1/2 i suma różnic 1."""
    _zapisz_symbol(tmp_path, "FTMUSDT", SPEC_FTM)
    _zapisz_symbol(tmp_path, "BBBUSDT", [(288, "ruch")] * 4)
    _rozjedz_poprawke1(monkeypatch, "odejmij", warunek=lambda df: len(df) > 4 * 288)  # tylko FTM
    tekst = "\n".join(dn.raport(tmp_path / "5m", tmp_path / "1d", ["FTMUSDT", "BBBUSDT"]))
    assert "Parytet: 1/2 symboli z identyczną listą dni, suma różnic 1" in tekst
    assert "Parytet: 2/2" not in tekst


def test_raport_liczy_symbole_z_roznica_wzgledem_1d(tmp_path):
    _zapisz_symbol(tmp_path, "FTMUSDT", SPEC_FTM, bez_dnia_w_1d=5)  # w 1d brak martwego dnia
    _zapisz_symbol(tmp_path, "BBBUSDT", [(288, "ruch")] * 4, dodaj_1d={4: 7.0})  # dzień tylko w 1d
    tekst = "\n".join(dn.raport(tmp_path / "5m", tmp_path / "1d", ["FTMUSDT", "BBBUSDT"]))
    assert "martwe 5m 1, dni_bez_obrotu 1d 0; dni tylko w 5m 1, tylko w 1d 0" in tekst
    assert "(symboli z różnicą: 1)" in tekst
    assert "dni obecne tylko w archiwum 1d: 1;" in tekst


def test_main_drukuje_raport_dla_wskazanych_katalogow(tmp_path, capsys):
    _zapisz_symbol(tmp_path, "FTMUSDT", SPEC_FTM)
    _zapisz_symbol(tmp_path, "BBBUSDT", [(288, "ruch")] * 4)
    sklad = tmp_path / "sklad.json"
    sklad.write_text(json.dumps({"2021-01": ["FTMUSDT", "BBBUSDT"]}), encoding="utf-8")
    dn.main(["--dane", str(tmp_path), "--sklad", str(sklad)])
    tekst = capsys.readouterr().out
    assert "Symboli w danych: 2; monet F2-1: 2" in tekst
    assert "Parytet: 2/2 symboli z identyczną listą dni, suma różnic 0" in tekst


def test_domyslne_sciezki_cli_wskazuja_istniejace_pliki_repo():
    assert dn.SKLAD_TOP20.is_file()
    assert (
        dn.SKLAD_TOP20.parent == dn.ROOT / "dane"
        and dn.KATALOG_DANYCH == dn.ROOT / "data" / "binance_um"
    )
    assert isinstance(json.loads(dn.SKLAD_TOP20.read_text(encoding="utf-8")), dict)


def test_analiza_symbolu_liczy_dni_z_roznym_wolumenem_5m_i_1d(tmp_path):
    _zapisz_symbol(tmp_path, "AAAUSDT", [(288, "ruch")] * 3)
    d1 = pd.read_parquet(tmp_path / "1d" / "AAAUSDT.parquet")
    d1.loc[1, "volume"] *= 1.05
    d1.to_parquet(tmp_path / "1d" / "AAAUSDT.parquet")
    r = dn.analiza_symbolu("AAAUSDT", tmp_path / "5m", tmp_path / "1d")
    assert r["wol_rozny"] == 1 and r["tylko_5m"] == r["tylko_1d"] == 0
