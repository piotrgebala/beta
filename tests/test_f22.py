"""F2-2 — HAR + log DVOL vs HAR: wspólna próba, brak przecieku, kontrola pozytywna i negatywna, werdykt."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from scipy.stats import norm

from miara.dm import diebold_mariano
from modele import run_f21b as b
from modele import run_f22 as c
from modele.zmiennosc import prognoza_har
from symulacje.moc_dm import moc_kryterium_braki

T0 = pd.Timestamp("2021-03-24", tz="UTC")


def _idx(n: int) -> pd.DatetimeIndex:
    return pd.date_range(T0, periods=n, freq="D")


def _swiat(n: int, seed: int, sila: float):
    """
    Utajona log-wariancja h (AR(1)); RV = exp(h) · szum. DVOL w wierszu d niesie h z dnia d+1 plus szum
    (`sila` = 1: informacyjny, 0: czysty szum bez związku z h). Zwraca (rv, ldv_w_wierszach_dni).
    """
    rng = np.random.default_rng(seed)
    h = np.zeros(n + 3)
    for t in range(1, n + 3):
        h[t] = 0.95 * h[t - 1] + 0.25 * rng.standard_normal()
    rv = np.exp(-7.0 + h[:n] + 0.35 * rng.standard_normal(n))
    sygnal = h[2 : n + 2] + 0.15 * rng.standard_normal(n)
    szum = rng.standard_normal(n)
    ldv_dzien = pd.Series(4.0 + 0.5 * (sila * sygnal + (1 - sila) * szum), index=_idx(n))
    return pd.Series(rv, index=_idx(n)), ldv_dzien


def _u(**kw) -> c.Ustawienia:
    return replace(c.Ustawienia(), min_trening=120, reps=50, **kw)


def _dvol_ramka(ldv_dzien: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"timestamp": ldv_dzien.index, "close": np.exp(ldv_dzien.to_numpy())})


# ------------------------------------------------- wspólna próba i parytet z HAR


def test_bez_dodatkowych_wynik_jak_dotad():
    rv, ldv = _swiat(500, 1, 1.0)
    a = prognoza_har(rv, 120, 30)
    b_ = prognoza_har(rv, 120, 30, dodatkowe=ldv.to_frame(), uzyj_dodatkowych=False)
    assert a.notna().sum() > 100
    pd.testing.assert_series_equal(a, b_)  # kompletne dodatkowe nie zmieniają czystego HAR


def test_baseline_liczony_na_tej_samej_probie_co_harx():
    rv, ldv = _swiat(500, 2, 1.0)
    ldv = ldv.copy()
    ldv.iloc[:150] = np.nan  # DVOL zaczyna się później niż RV
    p = c.prognozy(rv, ldv, _u())
    assert p["f_har"].notna().equals(p["f_harx"].notna())
    assert p["f_har"].first_valid_index() >= _idx(500)[150 + 120]
    # czysty HAR na pełnej próbie zaczynałby się wcześniej — to wspólna próba ma zniwelować
    assert prognoza_har(rv, 120, 30).first_valid_index() < p["f_har"].first_valid_index()


# ------------------------------------------------- brak przecieku (R7)


def test_prognoza_nie_zalezy_od_przyszlosci():
    rv, ldv = _swiat(600, 3, 1.0)
    pelna = c.prognozy(rv, ldv, _u())
    t = 400
    rv2, ldv2 = rv.copy(), ldv.copy()
    rv2.iloc[t + 1 :] *= 7.0  # wiersze po t zakłócone
    ldv2.iloc[t + 1 :] += 3.0
    obcieta = c.prognozy(rv2, ldv2, _u())
    # prognoza w wierszu t+1 (cechy z wiersza t, trening do t) nie może się zmienić
    for kol in ("f_har", "f_harx"):
        assert np.allclose(obcieta[kol].iloc[: t + 2], pelna[kol].iloc[: t + 2], equal_nan=True)
        assert pelna[kol].iloc[: t + 2].notna().sum() > 50  # test nie jest pusty


def test_log_dvol_ma_opoznienie_jednego_dnia():
    _, ldv = _swiat(50, 4, 1.0)
    out = c.log_dvol(_dvol_ramka(ldv))
    assert out.iloc[5] == pytest.approx(ldv.iloc[4])
    assert np.isnan(out.iloc[0])


def test_log_dvol_zero_to_nan_nie_minus_nieskonczonosc():
    df = pd.DataFrame({"timestamp": _idx(5), "close": [50.0, 0.0, 60.0, 55.0, 52.0]})
    out = c.log_dvol(df)
    assert not np.isinf(out).any()
    assert np.isnan(out.iloc[2])


# ------------------------------------------------- kontrola pozytywna i negatywna (R8)


def _t_qlike(sila: float, seed: int, n: int = 900) -> float:
    rv, ldv = _swiat(n, seed, sila)
    s = c.straty(c.prognozy(rv, ldv, _u()))
    return diebold_mariano(s["q_har"], s["q_harx"])["t"]


def test_kontrola_pozytywna_informacyjny_dvol_bije_har():
    t = [_t_qlike(1.0, s) for s in range(4)]
    assert min(t) > c.Z_HOLM


def test_kontrola_negatywna_szum_nie_bije_har_czesciej_niz_przypadek():
    t = np.array([_t_qlike(0.0, 100 + s) for s in range(24)])
    assert (t > c.Z_HOLM).mean() <= 0.15  # nominalnie ~1 %, margines na małą próbę
    # zbędny regresor kosztuje dokładność poza próbą (błąd estymacji), więc średnie t jest ujemne, nie dodatnie
    assert t.mean() < 0.5


# ------------------------------------------------- bramka, werdykt


def test_z_holm_to_alfa_005_na_dwie_pary():
    assert c.Z_HOLM == pytest.approx(norm.isf(0.0125))
    assert 2.24 < c.Z_HOLM < 2.25


def test_wyzszy_prog_nie_zwieksza_mocy_bramki():
    rng = np.random.default_rng(0)
    D = rng.standard_normal((600, 2))
    d = np.array([0.0, 0.1, 0.2])
    niski = moc_kryterium_braki(D, d, 200, 20, seed=1, z=1.96)["moc_kryterium"]
    wysoki = moc_kryterium_braki(D, d, 200, 20, seed=1, z=c.Z_HOLM)["moc_kryterium"]
    assert (wysoki <= niski + 1e-12).all()


def test_domyslny_prog_bramki_bez_zmian():
    rng = np.random.default_rng(0)
    D = rng.standard_normal((400, 2))
    d = np.array([0.0, 0.15])
    a = moc_kryterium_braki(D, d, 100, 20, seed=3)
    b_ = moc_kryterium_braki(D, d, 100, 20, seed=3, z=1.959964)
    assert (a["moc_kryterium"] == b_["moc_kryterium"]).all()


def test_werdykt_dwie_monety_obie_musza_przejsc():
    assert c.werdykt([3.0, 2.5])["ok"]
    assert not c.werdykt([3.0, 2.0])["ok"]  # 2,0 < Z_HOLM
    assert not c.werdykt([3.0, -2.5])["ok"]  # jedna istotnie gorsza
    assert c.werdykt([3.0, 2.5])["need"] == 2


@settings(max_examples=100, deadline=None)
@given(t=st.lists(st.floats(-6, 6), min_size=1, max_size=6), z=st.floats(1.5, 3.0))
def test_hyp_werdykt_spojny(t, z):
    w = c.werdykt(t, 0.8, z)
    assert w["good"] + w["bad"] <= w["k"]
    if w["ok"]:
        assert w["bad"] == 0 and w["good"] >= w["need"]
    w2 = c.werdykt([x + 10 for x in t], 0.8, z)  # sama poprawa nie psuje werdyktu
    assert w2["ok"] or w["k"] == 0


# ------------------------------------------------- przebieg end-to-end na danych syntetycznych


def test_przebieg_syntetyczny_zatrzymuje_sie_na_niezgodnych_dniach(capsys):
    n = 700
    rv, ldv = _swiat(n, 5, 1.0)
    sw = b.swiece_syntetyczne(rv.to_numpy(), "2021-03-24", seed=1)
    u = replace(_u(), okres_do=T0 + (n - 1) * b.DZIEN)
    dv = {"BTC": _dvol_ramka(ldv), "ETH": _dvol_ramka(ldv)}
    out = c.przebieg(
        {"BTCUSDT": sw, "ETHUSDT": sw},
        dv,
        u,
        False,
        oczekiwane={
            "monety": ("BTCUSDT", "ETHUSDT"),
            "dni_oos": {"BTCUSDT": 1, "ETHUSDT": 1},
            "odcisk": "x",
        },
    )
    assert out["etap"] == "stop_dane"
    assert "STOP przed stratami" in capsys.readouterr().out
