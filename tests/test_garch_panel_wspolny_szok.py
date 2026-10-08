"""Generator LV2c (karta 019): parytet z LV2 przy wyłączonych elementach, brzegi kopuły, niezmienniki."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from scipy import stats

from symulacje.garch_panel import generuj_panel
from symulacje.garch_panel_wspolny_szok import generuj_panel_lv2c, mnoznik_skali


@pytest.mark.parametrize("seed,k", [(0, 1), (3, 4), (11, 15)])
def test_parytet_bit_w_bit_z_generatorem_lv2_przy_wylaczonych_elementach(seed, k):
    a = generuj_panel(300, k, seed=seed, rho=0.8)
    b = generuj_panel_lv2c(300, k, seed=seed, rho=0.8, rho_szok=0.0, persystencja=None)
    for nazwa in ("r", "sigma2", "rv"):
        assert a[nazwa].equals(b[nazwa]), nazwa


def test_persystencja_098_to_to_samo_co_lv2_z_dokladnoscia_zaokraglen():
    a = generuj_panel(400, 4, seed=5, rho=0.8)["r"].to_numpy()
    b = generuj_panel_lv2c(400, 4, seed=5, rho=0.8, persystencja=0.98)["r"].to_numpy()
    assert np.allclose(a, b, rtol=1e-9, atol=0)


def test_mnoznik_skali_ma_brzeg_t_nu_bo_w_normalne():
    nu = 5.0
    w = np.random.default_rng(1).standard_normal(200_000)
    q = (nu - 2.0) / mnoznik_skali(w, nu)  # powinno mieć rozkład χ²_ν
    assert stats.kstest(q, stats.chi2(nu).cdf).pvalue > 0.01
    assert abs(mnoznik_skali(w, nu).mean() - 1.0) < 0.03


def test_wspolny_szok_zwieksza_zaleznosc_mnoznikow_zgodnie_z_kopula():
    nu, n = 5.0, 150_000
    rng = np.random.default_rng(2)
    for rho_szok in (0.3, 0.8):
        fm, e = rng.standard_normal(n), rng.standard_normal((n, 2))
        w = np.sqrt(rho_szok) * fm[:, None] + np.sqrt(1.0 - rho_szok) * e
        m = mnoznik_skali(w, nu)
        spearman = stats.spearmanr(m[:, 0], m[:, 1]).statistic
        assert spearman == pytest.approx(6.0 / np.pi * np.arcsin(rho_szok / 2.0), abs=0.01)


def test_brzeg_pojedynczej_monety_nie_zalezy_od_rho_szok():
    # odsetek innowacji poniżej kwantyla 5 % rozkładu t_5 o wariancji 1 (−1,561) ma być ≈ 5 % przy obu wartościach
    q05 = stats.t.ppf(0.05, 5) * np.sqrt(3.0 / 5.0)
    for rho_szok in (0.0, 0.9):
        p = generuj_panel_lv2c(2600, 8, seed=9, rho_szok=rho_szok, persystencja=0.98)
        eps = (p["r"] / np.sqrt(p["sigma2"])).to_numpy()
        assert (eps < q05).mean() == pytest.approx(0.05, abs=0.008)
        assert np.allclose(eps.std(), 1.0, atol=0.08)


def test_wspolny_szok_zwieksza_wspolne_wielkie_dni():
    # w dniach, gdy jedna moneta ma |ε| powyżej kwantyla 99 %, druga częściej też ma duże |ε|
    def zbieznosc(rho_szok):
        p = generuj_panel_lv2c(4000, 2, seed=4, rho=0.0, rho_szok=rho_szok, persystencja=0.98)
        eps = np.abs((p["r"] / np.sqrt(p["sigma2"])).to_numpy())
        prog = np.quantile(eps, 0.95, axis=0)
        duze = eps > prog
        return (duze[:, 0] & duze[:, 1]).sum() / duze[:, 0].sum()

    assert zbieznosc(0.9) > 2.0 * zbieznosc(0.0)


def test_alpha_zmienia_proces_a_domyslna_wartosc_to_lv2():
    a = generuj_panel_lv2c(300, 3, seed=2, rho=0.8, alpha=0.08)
    b = generuj_panel_lv2c(300, 3, seed=2, rho=0.8, persystencja=0.9999, alpha=0.2)
    assert a["r"].equals(generuj_panel(300, 3, seed=2, rho=0.8)["r"])
    assert not a["sigma2"].equals(b["sigma2"])
    c = generuj_panel_lv2c(300, 3, seed=2, rho=0.8, alpha=0.2)  # persystencja LV2 0,98 przy α = 0,2
    omega = 0.04**2 * (1 - 0.98)
    sig, r = c["sigma2"].to_numpy(), c["r"].to_numpy()
    assert np.allclose(sig[1:], omega + 0.2 * r[:-1] ** 2 + 0.78 * sig[:-1])
    for zle in (0.0, 1.0, 0.99):
        with pytest.raises(ValueError, match="alpha"):
            generuj_panel_lv2c(50, 3, alpha=zle)


def test_persystencja_na_monety_i_walidacja():
    p = generuj_panel_lv2c(200, 3, seed=1, persystencja=[0.99, 0.9999, 0.95])
    assert p["r"].shape == (200, 3) and (p["sigma2"] > 0).all().all()
    for zle in (0.05, 1.0, 1.2):
        with pytest.raises(ValueError, match="persystencja"):
            generuj_panel_lv2c(50, 3, persystencja=zle)
    with pytest.raises(ValueError, match="rho_szok"):
        generuj_panel_lv2c(50, 3, rho_szok=1.5)
    with pytest.raises(ValueError, match="rho"):
        generuj_panel_lv2c(50, 3, rho=-0.1)
    with pytest.raises(ValueError, match="nu"):
        generuj_panel_lv2c(50, 3, nu=2.0)
    with pytest.raises(ValueError):
        generuj_panel_lv2c(50, 3, persystencja=[0.98, 0.98])  # zła długość wektora


@settings(max_examples=40, deadline=None)
@given(
    n=st.integers(5, 80),
    k=st.integers(1, 6),
    seed=st.integers(0, 2**31 - 1),
    rho=st.floats(0.0, 1.0),
    rho_szok=st.floats(0.0, 1.0),
    pers=st.floats(0.31, 0.9999),
    alpha=st.floats(0.01, 0.3),
)
def test_niezmienniki_generatora(n, k, seed, rho, rho_szok, pers, alpha):
    a = generuj_panel_lv2c(
        n, k, seed, rho=rho, rho_szok=rho_szok, persystencja=pers, alpha=alpha, burn=20
    )
    b = generuj_panel_lv2c(
        n, k, seed, rho=rho, rho_szok=rho_szok, persystencja=pers, alpha=alpha, burn=20
    )
    for nazwa in ("r", "sigma2", "rv"):
        assert a[nazwa].shape == (n, k)  # długości
        assert a[nazwa].equals(b[nazwa])  # R19: determinizm
        assert np.isfinite(a[nazwa].to_numpy()).all()
    assert (a["sigma2"] > 0).all().all()  # dodatniość σ²
    assert (a["rv"] >= 0).all().all()
    inne = generuj_panel_lv2c(
        n, k, seed + 1, rho=rho, rho_szok=rho_szok, persystencja=pers, alpha=alpha, burn=20
    )
    assert not a["r"].equals(inne["r"])  # kolejność ziaren: inne ziarno, inny panel
