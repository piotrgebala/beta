"""Cechy techniczne F2-3: definicje na ręcznie policzonych przykładach, maska ważności, dziury, własności."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cechy import techniczne as t
from dane.ohlc import ohlc_dzienne

T0 = pd.Timestamp("2021-01-01", tz="UTC")


def _ramka(close, high=None, low=None, n_swiec=288) -> pd.DataFrame:
    close = np.asarray(close, dtype=float)
    high = close * 1.01 if high is None else np.asarray(high, dtype=float)
    low = close * 0.99 if low is None else np.asarray(low, dtype=float)
    idx = pd.date_range(T0, periods=len(close), freq="D")
    return pd.DataFrame({"high": high, "low": low, "close": close, "n_swiec": n_swiec}, index=idx)


def test_zakres_dzien_wartosc_reczna():
    df = _ramka([100.0, 100.0], high=[110.0, 105.0], low=[100.0, 100.0])
    # ln(110/100) i ln(105/100); wyjście to logarytm tych zakresów
    assert t.compute_zakres_dzien(df).iloc[0] == pytest.approx(np.log(np.log(1.10)))
    assert t.compute_zakres_dzien(df).iloc[1] == pytest.approx(np.log(np.log(1.05)))


def test_atr14_wartosc_reczna_z_true_range():
    close = np.full(20, 100.0)
    high = np.full(20, 102.0)
    low = np.full(20, 99.0)
    high[5] = 106.0  # TR dnia 5 = 106−99 = 7
    out = t.compute_atr14(_ramka(close, high, low))
    # dni 3..16 → okno 14 dni zawiera dzień 5: TR = 3 poza dniem 5, 7 w dniu 5
    oczek = np.log(((13 * 3.0 + 7.0) / 14.0) / 100.0)
    assert out.iloc[16] == pytest.approx(oczek)
    assert np.isnan(out.iloc[:14]).all()  # pierwszy TR (dzień 0) bez poprzedniego zamknięcia


def test_atr14_uzywa_luki_do_poprzedniego_zamkniecia():
    close = np.full(20, 100.0)
    high = np.full(20, 101.0)
    low = np.full(20, 100.0)
    low[10], high[10], close[10] = 109.0, 110.0, 110.0  # luka w górę: TR = |110 − 100| = 10
    out = t.compute_atr14(_ramka(close, high, low))
    wartosc = out.iloc[11]  # okno dni −2..11 → dni 0..11 za krótkie? sprawdzamy dzień 15
    assert np.isnan(wartosc)
    assert np.isfinite(out.iloc[15])
    assert out.iloc[15] > np.log(
        1.0 / 100.0
    )  # TR luki podnosi średnią ponad 1/100 z samego zakresu


def test_ema20_odl_stala_cena_to_zero_a_skok_to_dodatnia_odleglosc():
    out = t.compute_ema20_odl(_ramka(np.full(40, 100.0)))
    assert np.isnan(out.iloc[:19]).all()
    assert out.iloc[19:].abs().max() < 1e-12
    close = np.r_[np.full(30, 100.0), 120.0, np.full(9, 120.0)]
    o2 = t.compute_ema20_odl(_ramka(close))
    assert o2.iloc[30] > 0.05 and o2.iloc[39] < o2.iloc[30]  # EMA dogania cenę


def test_bb20_szer_wartosc_reczna():
    close = np.arange(100.0, 130.0)
    out = t.compute_bb20_szer(_ramka(close))
    okno = close[10:30]
    assert out.iloc[29] == pytest.approx(np.log(4 * okno.std(ddof=1) / okno.mean()))


def test_rsi14_skrajnosci_i_zakres():
    rosnie = t.compute_rsi14(_ramka(np.arange(100.0, 130.0)))
    assert rosnie.iloc[20] == pytest.approx(1.0)
    spada = t.compute_rsi14(_ramka(np.arange(130.0, 100.0, -1.0)))
    assert spada.iloc[20] == pytest.approx(-1.0)
    stala = t.compute_rsi14(_ramka(np.full(30, 100.0)))
    assert stala.isna().all()  # brak ruchu = NaN, nie 0/0


def test_maska_waznosci_273_vs_274_i_zepsute_swiece():
    n = np.full(40, 288)
    n[25], n[26] = 274, 273
    df = _ramka(100 * np.exp(np.cumsum(np.full(40, 0.001))), n_swiec=n)
    z = t.compute_zakres_dzien(df)
    assert np.isfinite(z.iloc[25]) and np.isnan(z.iloc[26])
    # high == low (doba martwa) → NaN, nigdy −∞
    df2 = _ramka(np.full(30, 100.0), high=np.full(30, 100.0), low=np.full(30, 100.0))
    for f in (t.compute_zakres_dzien, t.compute_atr14, t.compute_ema20_odl, t.compute_bb20_szer):
        assert not np.isinf(f(df2)).any()
    assert t.compute_zakres_dzien(df2).isna().all()


def test_dziura_w_oknie_daje_nan_bez_wypelniania():
    close = 100 + np.sin(np.arange(60))
    df = _ramka(close).drop(index=pd.Timestamp("2021-01-25", tz="UTC"))  # brak doby 24 (0-indeks)
    for f, okno in ((t.compute_atr14, 15), (t.compute_bb20_szer, 20), (t.compute_rsi14, 15)):
        out = f(df)
        assert len(out) == 60  # pełny kalendarz
        assert out.iloc[24 : 24 + okno - 1].isna().all(), f.__name__
        assert np.isfinite(out.iloc[24 + okno + 1])


def test_walidacje_wejscia():
    df = _ramka(np.full(30, 100.0))
    with pytest.raises(ValueError):
        t.compute_atr14(df.drop(columns="high"))
    with pytest.raises(ValueError):
        t.compute_atr14(df.iloc[0:0])
    dup = pd.concat([df, df.iloc[:1]])
    with pytest.raises(ValueError):
        t.compute_atr14(dup)


def test_ohlc_dzienne_agreguje_max_min_ostatnie():
    ts = pd.date_range(T0, periods=288 * 2, freq="5min")
    rng = np.random.default_rng(0)
    cl = 100 + np.cumsum(rng.normal(size=len(ts)))
    df = pd.DataFrame({"timestamp": ts, "high": cl + 1, "low": cl - 1, "close": cl})
    d = ohlc_dzienne(df)
    assert list(d["n_swiec"]) == [288, 288]
    assert d["high"].iloc[0] == pytest.approx((cl[:288] + 1).max())
    assert d["low"].iloc[1] == pytest.approx((cl[288:] - 1).min())
    assert d["close"].iloc[1] == pytest.approx(cl[-1])
    with pytest.raises(ValueError):
        ohlc_dzienne(df.drop(columns="low"))
    with pytest.raises(ValueError):
        ohlc_dzienne(pd.concat([df, df.iloc[:1]]))


@settings(max_examples=60, deadline=None)
@given(
    ruchy=st.lists(st.floats(-0.05, 0.05), min_size=40, max_size=80),
    szer=st.floats(0.0005, 0.03),
)
def test_hyp_cechy_skonczone_i_rsi_w_zakresie(ruchy, szer):
    close = 100.0 * np.exp(np.cumsum(ruchy))
    df = _ramka(close, high=close * (1 + szer), low=close * (1 - szer))
    for nazwa in ("zakres_dzien", "atr14", "ema20_odl", "bb20_szer", "rsi14"):
        out = getattr(t, f"compute_{nazwa}")(df)
        assert not np.isinf(out.to_numpy(dtype=float)).any(), nazwa
    rsi = t.compute_rsi14(df).dropna()
    assert ((rsi >= -1 - 1e-12) & (rsi <= 1 + 1e-12)).all()
