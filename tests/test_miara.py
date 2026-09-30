"""Testy jednostkowe i własności (`hypothesis`) przyrządu `miara/` — ponad parytet z alpha."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from miara import dsr, metryki
from miara import kontrola_negatywna as nc
from miara.neff import effective_sample_size, summarize_pnl

szeregi = st.lists(
    st.floats(min_value=-0.5, max_value=0.5, allow_nan=False), min_size=2, max_size=300
).map(pd.Series)


@settings(max_examples=200, deadline=None)
@given(szeregi)
def test_neff_nigdy_ponad_n_w_summarize_pnl(x):
    """R10: N_eff ∈ [1, n], więc |t_neff| ≤ |t|."""
    s = summarize_pnl(x)
    assert 1.0 <= s["n_eff"] <= s["n"]
    if np.isfinite(s["t"]) and np.isfinite(s["t_neff"]):
        assert abs(s["t_neff"]) <= abs(s["t"]) + 1e-9


@settings(max_examples=200, deadline=None)
@given(szeregi)
def test_ess_dodatnie(x):
    assert effective_sample_size(x)["n_eff"] > 0


@given(st.integers(min_value=1, max_value=10**6))
def test_pasmo_walda_maleje_z_n(n):
    assert metryki.wald_half_width(n + 1) < metryki.wald_half_width(n)


@given(
    st.floats(min_value=0.01, max_value=0.99),
    st.floats(min_value=0.01, max_value=0.99),
    st.integers(min_value=1, max_value=100_000),
)
def test_mierzalnosc_zgodna_z_progiem(p, be, n):
    r = metryki.measurability_report(p, be, n)
    assert r["measurable"] == (p > metryki.min_detectable_hit_rate(be, n))
    assert r["verdict"] in {"MIERZALNA", "NIEMIERZALNA"}


def test_mierzalnosc_przyklad_alpha_h21():
    """98 transakcji, próg 52,25 %: pasmo ≈ 9,9 pp, więc trafność 58 % jest NIEMIERZALNA."""
    r = metryki.measurability_report(0.58, 0.5225, 98)
    assert r["verdict"] == "NIEMIERZALNA"
    assert r["band_width_pp"] == pytest.approx(9.899, abs=1e-3)


def test_required_trades_symetria_i_granice():
    assert metryki.required_trades(0.5, 0.5) == float("inf")
    assert np.isnan(metryki.required_trades(1.0, 0.5))
    assert metryki.required_trades(0.55, 0.5) == pytest.approx(783.0, abs=1.0)


def test_dsr_prog_rosnie_z_n():
    ts = [dsr.required_t(n) for n in (1, 10, 41, 100)]
    assert ts == sorted(ts)
    assert dsr.required_t(41) == pytest.approx(3.84, abs=0.005)


def test_dsr_rejestr_alpha_spojny():
    """Wspólny rejestr (zasada 22) czytany z alpha — tylko gdy alpha jest obok (lokalnie, nie w CI)."""
    if not dsr.REJESTR.is_file():
        pytest.skip("brak repo alpha obok beta")
    rows = dsr.load_registry()
    assert dsr.registry_errors(rows) == []
    assert dsr.n_warianty(rows) >= 40


def test_summarize_trade_returns_wymaga_jednego_rezimu():
    rng = np.random.default_rng(0)
    n = 40
    t = pd.DataFrame(
        {
            "regime": ["a", "b"] * (n // 2),
            "kill_switch_active": False,
            "entry_price": 100.0,
            "exit_price": 100.0 + rng.standard_normal(n),
            "position_size": 1.0,
            "gross_pnl": rng.standard_normal(n),
            "cost": 0.09,
            "equity_before": 10_000.0,
        }
    )
    t["net_pnl"] = t["gross_pnl"] - t["cost"]
    with pytest.raises(ValueError):
        metryki.summarize_trade_returns(metryki.build_summary(t))
    s = metryki.summarize_trade_returns(metryki.build_summary(t.assign(regime="all")))
    assert s["n"] == n and s["n_eff"] <= n


# --- generator kontroli negatywnej (testy przeniesione z alpha tests/test_negative_control.py) ---


def test_generator_deterministyczny():
    a = nc.synthetic_returns(300, 5, seed=1)
    b = nc.synthetic_returns(300, 5, seed=1)
    c = nc.synthetic_returns(300, 5, seed=2)
    assert a.shape == (300, 5)
    assert isinstance(a.index, pd.DatetimeIndex) and a.index.tz is not None
    pd.testing.assert_frame_equal(a, b)
    assert not a.equals(c)


def test_generator_bez_pamieci_kierunku_z_grubymi_ogonami():
    r = nc.synthetic_returns(20_000, 2, seed=3)["C00USDT"].to_numpy()
    band = 4.0 / np.sqrt(len(r))
    s = np.sign(r)
    for lag in (1, 7, 28):
        assert abs(nc.autocorr(s, lag)) < band
        assert abs(nc.autocorr(r, lag)) < 2 * band
    assert nc.autocorr(r**2, 1) > 0.05
    assert nc.excess_kurtosis(r) > 1.0
    assert r.std() == pytest.approx(0.04, rel=0.25)


def test_generator_czynnik_wspolny():
    r = nc.synthetic_returns(20_000, 3, seed=4, rho=0.5)
    c = r.corr().to_numpy()[np.triu_indices(3, 1)]
    assert c == pytest.approx([0.5] * 3, abs=0.07)


def test_generator_zle_parametry():
    with pytest.raises(ValueError):
        nc.synthetic_returns(10, 2, df=2.0)
    with pytest.raises(ValueError):
        nc.synthetic_returns(10, 2, garch=(0.5, 0.6))


def test_ohlc_spojne():
    r = nc.synthetic_returns(500, 4, seed=5)
    o = nc.synthetic_ohlc(r, seed=5)
    hi, lo, op, cl = o["high"], o["low"], o["open"], o["close"]
    assert (hi >= np.maximum(op, cl) - 1e-12).all().all()
    assert (lo <= np.minimum(op, cl) + 1e-12).all().all()
    assert (lo > 0).all().all()


# --- reguły referencyjne (nowe w beta) ---


@pytest.mark.parametrize("regula", [nc.regula_trendu, nc.regula_przekrojowa])
def test_regula_nie_zaglada_w_przyszlosc(regula):
    """Leakage (R7): zmiana zwrotów od dnia k nie zmienia P&L przed dniem k."""
    r = nc.synthetic_returns(200, 10, seed=11)
    base = regula(r)
    k = 120
    r2 = r.copy()
    r2.iloc[k:] = -r2.iloc[k:] * 3.0
    alt = regula(r2)
    pd.testing.assert_series_equal(base.loc[: r.index[k - 1]], alt.loc[: r.index[k - 1]])


@pytest.mark.parametrize("regula", [nc.regula_trendu, nc.regula_przekrojowa])
def test_regula_z_zagladaniem_widzi_przyszlosc(regula):
    """Kontrola czułości: celowe zajrzenie w przyszły tydzień daje ogromne t."""
    r = nc.synthetic_returns(1_200, 10, seed=0)
    s = summarize_pnl(regula(r, peek=True), periods_per_year=365, capital_per_notional=1.0)
    assert s["t_neff"] > 5.0


def test_regula_przekrojowa_neutralna_rynkowo():
    """Równy zwrot wszystkich monet → long-short (po 0,5 kapitału na nogę) zarabia zero."""
    idx = pd.date_range("2021-01-01", periods=60, freq="D", tz="UTC")
    r = pd.DataFrame(0.01, index=idx, columns=[f"C{i}" for i in range(20)])
    pnl = nc.regula_przekrojowa(r)
    assert len(pnl) > 0
    assert np.allclose(pnl.to_numpy(), 0.0)
