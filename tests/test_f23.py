"""F2-3 — HAR + wskaźniki techniczne vs HAR: wspólna próba, brak przecieku, kontrola pozytywna i negatywna."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from miara.dm import diebold_mariano
from modele import run_f21b as b
from modele import run_f22 as f22
from modele import run_f23 as c
from modele.zmiennosc import prognoza_har

T0 = pd.Timestamp("2021-03-24", tz="UTC")


def _idx(n: int) -> pd.DatetimeIndex:
    return pd.date_range(T0, periods=n, freq="D")


def _u(**kw) -> c.Ustawienia:
    return replace(c.Ustawienia(), min_trening=120, reps=50, **kw)


def _swiat(n: int, seed: int, sila: float):
    """
    Utajona log-wariancja h (AR(1)); RV = exp(h) · szum. Pięć cech: jedna niesie h z dnia d+1 plus szum
    (`sila` = 1: informacyjna, 0: czysty szum), cztery to szum niezwiązany z h.
    """
    rng = np.random.default_rng(seed)
    h = np.zeros(n + 3)
    for t in range(1, n + 3):
        h[t] = 0.95 * h[t - 1] + 0.25 * rng.standard_normal()
    rv = pd.Series(np.exp(-7.0 + h[:n] + 0.35 * rng.standard_normal(n)), index=_idx(n))
    sygnal = h[2 : n + 2] + 0.15 * rng.standard_normal(n)
    x = pd.DataFrame(rng.standard_normal((n, 5)), index=_idx(n), columns=list(c.CECHY))
    x["atr14"] = sila * sygnal + (1 - sila) * x["atr14"]
    return rv, x


# ------------------------------------------------- stałe i próg


def test_z_holm_to_alfa_005_na_trzy_pary():
    assert c.Z_HOLM == pytest.approx(norm.isf(0.05 / 6))
    assert 2.39 < c.Z_HOLM < 2.40
    assert c.Ustawienia().z == c.Z_HOLM  # bramka i kryterium używają tego samego progu


def test_cztery_monety_i_pelny_udzial_wymaga_wszystkich():
    assert len(c.MONETY) == 4 and set(c.MONETY) == {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"}
    assert f22.werdykt([3, 3, 3, 3], 0.8, c.Z_HOLM)["need"] == 4
    assert not f22.werdykt([3, 3, 3, 2.0], 0.8, c.Z_HOLM)["ok"]


def test_cechy_w_rejestrze_i_w_runnerze_te_same():
    from tests.test_cechy import REJESTR

    z_rejestru = {n for n, w in REJESTR.items() if w["runda_definicji"] == "F2-3"}
    assert z_rejestru == set(c.CECHY)


# ------------------------------------------------- wspólna próba i parytet z HAR


def test_baseline_liczony_na_tej_samej_probie_co_harx():
    rv, x = _swiat(500, 2, 1.0)
    x.iloc[:150, 2] = np.nan  # jedna cecha zaczyna się później niż RV
    p = c.prognozy(rv, x, _u())
    assert p["f_har"].notna().equals(p["f_harx"].notna())
    assert p["f_har"].first_valid_index() >= _idx(500)[150 + 120]
    assert prognoza_har(rv, 120, 30).first_valid_index() < p["f_har"].first_valid_index()


def test_czysty_har_nie_zalezy_od_wartosci_cech():
    rv, x = _swiat(500, 3, 1.0)
    p1 = c.prognozy(rv, x, _u())
    x2 = pd.DataFrame(
        np.random.default_rng(9).standard_normal(x.shape), index=x.index, columns=x.columns
    )
    p2 = c.prognozy(rv, x2, _u())
    pd.testing.assert_series_equal(p1["f_har"], p2["f_har"])
    assert not np.allclose(p1["f_harx"].dropna(), p2["f_harx"].dropna())


def test_prognoza_nie_zalezy_od_przyszlosci():
    rv, x = _swiat(600, 4, 1.0)
    pelna = c.prognozy(rv, x, _u())
    t = 400
    rv2, x2 = rv.copy(), x.copy()
    rv2.iloc[t + 1 :] *= 7.0
    x2.iloc[t + 1 :] += 3.0
    obcieta = c.prognozy(rv2, x2, _u())
    for kol in ("f_har", "f_harx"):
        assert np.allclose(obcieta[kol].iloc[: t + 2], pelna[kol].iloc[: t + 2], equal_nan=True)
        assert pelna[kol].iloc[: t + 2].notna().sum() > 50


# ------------------------------------------------- kontrola pozytywna i negatywna (R8)


def _t_qlike(sila: float, seed: int, n: int = 900) -> float:
    rv, x = _swiat(n, seed, sila)
    s = f22.straty(c.prognozy(rv, x, _u()))
    return diebold_mariano(s["q_har"], s["q_harx"])["t"]


def test_kontrola_pozytywna_informacyjna_cecha_bije_har():
    t = [_t_qlike(1.0, s) for s in range(4)]
    assert min(t) > c.Z_HOLM


def test_kontrola_negatywna_szum_nie_bije_har_czesciej_niz_przypadek():
    t = np.array([_t_qlike(0.0, 100 + s) for s in range(24)])
    assert (t > c.Z_HOLM).mean() <= 0.15
    assert t.mean() < 0.5  # pięć zbędnych regresorów kosztuje dokładność poza próbą


# ------------------------------------------------- od świec 5m do strat (mechanika, nie dowód o rynku)


def _swiece_ohlc(sigma2: np.ndarray, seed: int) -> pd.DataFrame:
    df = b.swiece_syntetyczne(sigma2, T0.strftime("%Y-%m-%d"), seed)
    rng = np.random.default_rng(seed + 1)
    cl = df["close"].to_numpy()
    otw = np.r_[cl[0], cl[:-1]]
    szer = np.abs(rng.normal(0.0, 0.0008, len(df)))
    df["open"] = otw
    df["high"] = np.maximum(otw, cl) * (1 + szer)
    df["low"] = np.minimum(otw, cl) * (1 - szer)
    return df


def _swiece_swiat(n: int, seed: int) -> pd.DataFrame:
    rv, _ = _swiat(n, seed, 0.0)
    return _swiece_ohlc(rv.to_numpy(), seed)


def test_cechy_techniczne_maja_pelny_kalendarz_i_piec_kolumn():
    sw = _swiece_swiat(120, 1)
    x = c.cechy_techniczne(sw)
    assert list(x.columns) == list(c.CECHY)
    assert len(x) == 120 and x.notna().all(axis=1).sum() > 80
    assert not np.isinf(x.to_numpy()).any()


def test_straty_monety_i_dni_oos_zgodne_na_syntetyku():
    n = 700
    sw = _swiece_swiat(n, 2)
    u = replace(_u(), okres_do=T0 + (n - 1) * b.DZIEN)
    st = c.straty_monety(sw, u)
    assert len(st) > 100
    assert st.index.equals(c.dni_oos(sw, u))


def test_przebieg_syntetyczny_zatrzymuje_sie_na_niezgodnych_dniach(capsys):
    n = 700
    sw = _swiece_swiat(n, 3)
    u = replace(_u(), okres_do=T0 + (n - 1) * b.DZIEN)
    oczek = {"monety": c.MONETY, "dni_oos": dict.fromkeys(c.MONETY, 1), "odcisk": "x"}
    out = c.przebieg(dict.fromkeys(c.MONETY, sw), u, False, oczekiwane=oczek)
    assert out["etap"] == "stop_dane"
    assert "STOP przed stratami" in capsys.readouterr().out


def test_przebieg_syntetyczny_dochodzi_do_bramki(capsys):
    n = 700
    sw = _swiece_swiat(n, 4)
    u = replace(_u(), okres_do=T0 + (n - 1) * b.DZIEN)
    out = c.przebieg(dict.fromkeys(c.MONETY, sw), u, False, oczekiwane=None)
    assert out["etap"] in {"niemierzalna", "test"}
    assert "bramka mierzalności" in capsys.readouterr().out


def test_tylko_dni_nie_liczy_strat(capsys):
    n = 700
    sw = _swiece_swiat(n, 5)
    u = replace(_u(), okres_do=T0 + (n - 1) * b.DZIEN)
    out = c.przebieg(dict.fromkeys(c.MONETY, sw), u, True, oczekiwane=None)
    assert out["etap"] == "dni" and "bramka" not in out
    assert "bez strat" in capsys.readouterr().out
