"""Testy przyrządu DM (miara/dm.py) i laboratorium symulacji F1 (symulacje/)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from hypothesis import given, settings
from hypothesis import strategies as st

from miara.dm import diebold_mariano, dm_t, hac_variance, mse_log, newey_west_lag, qlike
from symulacje.garch_panel import generuj_panel, momenty, prognoza_ewma, prognoza_okno
from symulacje.moc_dm import (
    mde,
    moc_kryterium,
    moc_kryterium_braki,
    stationary_bootstrap_indices,
)


def test_qlike_zero_tylko_przy_trafieniu():
    assert qlike(2.0, 2.0) == 0.0
    assert qlike(2.0, 1.0) > 0 and qlike(1.0, 2.0) > 0
    assert mse_log(np.e, 1.0) == pytest.approx(1.0)


def test_newey_west_lag():
    assert newey_west_lag(100) == 4
    assert newey_west_lag(2100) == 7


def test_hac_zgodny_ze_statsmodels():
    rng = np.random.default_rng(1)
    e = rng.standard_normal(800)
    d = np.convolve(e, [1.0, 0.6, 0.3], mode="same") + 0.1
    L = 6
    res = sm.OLS(d, np.ones_like(d)).fit(
        cov_type="HAC", cov_kwds={"maxlags": L, "use_correction": False}
    )
    se_sm = float(res.bse[0])
    se = float(np.sqrt(hac_variance(d, L) / len(d)))
    assert se == pytest.approx(se_sm, rel=1e-10)


@settings(max_examples=100, deadline=None)
@given(
    st.lists(st.floats(-10, 10, allow_nan=False), min_size=20, max_size=200),
    st.floats(-5, 5, allow_nan=False),
)
def test_hac_niezalezny_od_przesuniecia(xs, c):
    """S liczone na odchyleniach — przesunięcie szeregu nie zmienia wariancji (fundament moc_dm)."""
    x = np.array(xs)
    assert hac_variance(x + c, 3) == pytest.approx(hac_variance(x, 3), rel=1e-9, abs=1e-9)


def test_dm_znak_i_macierz():
    rng = np.random.default_rng(2)
    a = rng.exponential(1.0, 1000) + 0.2
    b = rng.exponential(1.0, 1000)
    r = diebold_mariano(a, b)
    assert r["t"] > 1.96  # B ma mniejszą stratę → t dodatnie
    assert r["n_eff"] > 0
    t2 = dm_t(np.c_[a - b, b - a], r["lag"])
    assert t2[0] == pytest.approx(r["t"]) and t2[1] == pytest.approx(-r["t"])


def test_dm_pomija_nan_i_odrzuca_krotkie():
    r = diebold_mariano([np.nan, 1.0, 2.0, 3.0, 1.5], [0.5, np.nan, 1.0, 1.0, 1.0], lag=1)
    assert r["n"] == 3
    with pytest.raises(ValueError):
        diebold_mariano([1.0, 2.0], [1.0, 1.0])


def test_panel_determinizm_i_ksztalt():
    a = generuj_panel(300, 4, seed=3)
    b = generuj_panel(300, 4, seed=3)
    assert a["r"].shape == (300, 4)
    pd.testing.assert_frame_equal(a["rv"], b["rv"])
    assert (a["rv"] > 0).all().all() and (a["sigma2"] > 0).all().all()


def test_panel_bez_przecieku_sigma2():
    """σ²_t zależy tylko od zwrotów do t − 1: zmiana szoków od dnia k nie zmienia σ² do dnia k."""
    p = generuj_panel(400, 2, seed=5, burn=0)
    r = p["r"].to_numpy()
    a, b = 0.08, 0.90
    om = 0.04**2 * (1 - a - b)
    s = np.empty_like(r)
    v = np.full(2, 0.04**2)
    for t in range(len(r)):
        s[t] = v
        v = om + a * r[t] ** 2 + b * v
    assert np.allclose(s, p["sigma2"].to_numpy())


def test_panel_momenty_krypto_podobne():
    m = momenty(generuj_panel(20_000, 3, seed=4, rho=0.5)["r"])
    assert m["vol"] == pytest.approx(0.04, rel=0.2)
    assert m["excess_kurtosis"] > 2.0
    assert m["acf_r2_lag1"] > 0.05
    assert 0.3 < m["corr"] < 0.55


def test_panel_zle_parametry():
    with pytest.raises(ValueError):
        generuj_panel(10, 2, nu=2.0)
    with pytest.raises(ValueError):
        generuj_panel(10, 2, garch=(0.2, 0.85))
    with pytest.raises(ValueError):
        generuj_panel(10, 2, rho=1.5)


@pytest.mark.parametrize("fn", [prognoza_okno, prognoza_ewma])
def test_prognozy_bez_przecieku(fn):
    p = generuj_panel(200, 3, seed=6)
    base = fn(p["r"])
    r2 = p["r"].copy()
    r2.iloc[100:] *= 5.0
    alt = fn(r2)
    pd.testing.assert_frame_equal(base.iloc[:101], alt.iloc[:101])


def test_wyrocznia_lepsza_niz_stala():
    """Kontrola pozytywna przyrządu DM: wiedza o σ² bije stałą prognozę."""
    p = generuj_panel(2100, 1, seed=7)
    rv = p["rv"].iloc[:, 0]
    r = diebold_mariano(qlike(rv, 0.04**2), qlike(rv, p["sigma2"].iloc[:, 0]))
    assert r["t"] > 1.96


def test_bootstrap_indeksy():
    rng = np.random.default_rng(0)
    idx = stationary_bootstrap_indices(50, 10_000, 10.0, rng)
    assert idx.min() >= 0 and idx.max() < 50
    runs = (
        np.sum(np.diff(idx) != 1) + 1
    )  # przybliżona liczba bloków (zawijanie 49→0 liczy się jako ciąg)
    assert 10_000 / runs == pytest.approx(10.0, rel=0.2)
    with pytest.raises(ValueError):
        stationary_bootstrap_indices(0, 5, 2.0, rng)


def test_moc_rosnie_z_efektem_i_zero_przy_h0():
    rng = np.random.default_rng(8)
    D = rng.standard_normal((3000, 5))
    out = moc_kryterium(D, 500, np.array([0.0, 0.1, 0.3]), reps=200, mean_block=5, seed=1)
    assert out["moc_kryterium"][0] < 0.02
    assert out["moc_moneta"][0] == pytest.approx(0.025, abs=0.02)
    assert out["moc_kryterium"][2] > 0.95
    assert np.all(np.diff(out["moc_moneta"]) >= 0)


def test_mde_interpolacja():
    assert mde(np.array([0.0, 0.1, 0.2]), np.array([0.0, 0.6, 1.0])) == pytest.approx(0.15)
    assert np.isnan(mde(np.array([0.0, 0.1]), np.array([0.0, 0.5])))
    assert mde(np.array([0.1, 0.2]), np.array([0.9, 1.0])) == 0.1


def test_moc_braki_bez_brakow_rowna_sie_moc_kryterium():
    rng = np.random.default_rng(11)
    D = rng.standard_normal((400, 4)) + 0.3 * rng.standard_normal((400, 1))
    deltas = np.array([0.0, 0.1, 0.2, 0.4])
    a = moc_kryterium(D, len(D), deltas, reps=100, mean_block=5, seed=3)
    b = moc_kryterium_braki(D, deltas, reps=100, mean_block=5, seed=3)
    for k in ("moc_kryterium", "moc_moneta", "alarm_gorsza"):
        np.testing.assert_allclose(a[k], b[k], atol=1e-12)


@pytest.mark.filterwarnings("ignore::RuntimeWarning")  # kolumna z samych NaN (przypadek brzegowy)
def test_moc_braki_rozlaczne_okresy():
    """Dwie monety bez ani jednego wspólnego dnia (jak MATIC i WIF): moc liczona, nie pada."""
    rng = np.random.default_rng(12)
    D = rng.standard_normal((1200, 3))
    D[600:, 0] = np.nan  # moneta 0 żyje tylko w pierwszej połowie
    D[:700, 1] = np.nan  # moneta 1 tylko w drugiej
    out = moc_kryterium_braki(D, np.array([0.0, 0.3]), reps=200, mean_block=5, seed=1)
    assert out["moc_moneta"][0] == pytest.approx(0.025, abs=0.02)  # H0: ~2,5 % w prawo
    assert out["moc_kryterium"][1] > 0.9  # δ = 0,3 przy n ≈ 500–1200 → prawie zawsze
    tylko_nan = D.copy()
    tylko_nan[:, 2] = np.nan
    out2 = moc_kryterium_braki(tylko_nan, np.array([0.5]), reps=20, mean_block=5, seed=1)
    assert out2["moc_moneta"][0] <= 2 / 3 + 1e-12  # moneta bez danych nigdy nie przechodzi
