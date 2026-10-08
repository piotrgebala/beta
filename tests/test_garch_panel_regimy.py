"""Generator LV2d (karta 021): parytet z LV2c przy amplitudzie 0, własności poziomu wariancji, niezmienniki."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from symulacje.garch_panel_regimy import DLUGOSC, generuj_panel_lv2d, poziom_wariancji
from symulacje.garch_panel_wspolny_szok import generuj_panel_lv2c

PARAMETRY = {"rho": 0.8, "rho_szok": 0.5, "persystencja": 0.9999, "alpha": 0.16}


@pytest.mark.parametrize("seed,k", [(0, 1), (3, 4), (11, 15)])
def test_amplituda_zero_daje_panel_lv2c_bit_w_bit(seed, k):
    a = generuj_panel_lv2c(300, k, seed=seed, **PARAMETRY)
    b = generuj_panel_lv2d(300, k, seed=seed, amplituda=0.0, **PARAMETRY)
    for nazwa in ("r", "sigma2", "rv"):
        assert a[nazwa].equals(b[nazwa]), nazwa


def test_poziom_przy_amplitudzie_zero_to_same_jedynki():
    assert np.array_equal(poziom_wariancji(50, 0.0, DLUGOSC, 1), np.ones(50))


def test_poziom_jest_staly_w_rezimie_i_zmienia_sie_miedzy_rezimami():
    poziom = poziom_wariancji(5000, 0.6, 100.0, 7)
    skoki = np.flatnonzero(np.diff(poziom) != 0.0) + 1
    assert 20 < len(skoki) < 90  # ~ 5000/100 = 50 reżimów
    kawalki = np.split(poziom, skoki)
    assert all(np.all(k == k[0]) for k in kawalki)
    assert len({k[0] for k in kawalki}) == len(kawalki)


def test_poziom_ma_srednia_jeden_i_odchylenie_logarytmu_rowne_amplitudzie():
    s = 0.5
    # wiele niezależnych ścieżek: średnia po reżimach, nie po dniach jednej ścieżki
    reżimy = np.concatenate(
        [np.unique(poziom_wariancji(3000, s, 100.0, seed)) for seed in range(300)]
    )
    assert abs(reżimy.mean() - 1.0) < 0.03
    assert abs(np.log(reżimy).std() - s) < 0.03
    assert abs(np.log(reżimy).mean() + 0.5 * s**2) < 0.03


def test_pierwszy_dzien_zaczyna_rezim_nawet_przy_bardzo_dlugim_rezimie():
    poziom = poziom_wariancji(10, 0.5, 1e12, 3)
    assert np.all(poziom == poziom[0]) and poziom[0] != 1.0


def test_poziom_zalezy_tylko_od_ziarna_amplitudy_i_dlugosci():
    a = poziom_wariancji(400, 0.5, 150.0, 9)
    assert np.array_equal(a, poziom_wariancji(400, 0.5, 150.0, 9))
    assert not np.array_equal(a, poziom_wariancji(400, 0.5, 150.0, 10))


def test_losowania_poziomu_nie_zmieniaja_losowan_lv2c():
    # r / sqrt(L) odtwarza surowy panel LV2c (do zaokrągleń): poziom nie wchodzi do rekurencji GARCH
    n, k, seed, s = 600, 4, 5, 0.5
    surowy = generuj_panel_lv2c(n, k, seed=seed, **PARAMETRY)
    z_poziomem = generuj_panel_lv2d(n, k, seed=seed, amplituda=s, **PARAMETRY)
    poziom = poziom_wariancji(n, s, DLUGOSC, seed)
    assert np.allclose(
        z_poziomem["r"].to_numpy() / np.sqrt(poziom)[:, None], surowy["r"].to_numpy()
    )
    assert np.allclose(
        z_poziomem["sigma2"].to_numpy() / poziom[:, None], surowy["sigma2"].to_numpy()
    )
    assert np.allclose(z_poziomem["rv"].to_numpy() / poziom[:, None], surowy["rv"].to_numpy())


def test_standaryzowana_innowacja_nie_zalezy_od_poziomu():
    n, k, seed = 800, 3, 12
    a = generuj_panel_lv2d(n, k, seed=seed, amplituda=0.0, **PARAMETRY)
    b = generuj_panel_lv2d(n, k, seed=seed, amplituda=0.7, **PARAMETRY)
    za = a["r"].to_numpy() / np.sqrt(a["sigma2"].to_numpy())
    zb = b["r"].to_numpy() / np.sqrt(b["sigma2"].to_numpy())
    assert np.allclose(za, zb)


def test_poziom_jest_wspolny_dla_monet():
    n, seed = 500, 4
    a = generuj_panel_lv2d(n, 5, seed=seed, amplituda=0.0, **PARAMETRY)
    b = generuj_panel_lv2d(n, 5, seed=seed, amplituda=0.6, **PARAMETRY)
    iloraz = b["sigma2"].to_numpy() / a["sigma2"].to_numpy()
    assert np.allclose(iloraz, iloraz[:, [0]])


@pytest.mark.parametrize("rho_szok", [0.0, 0.5, 1.0])
def test_rozklad_pojedynczej_monety_nie_zalezy_od_rho_szok_ani_rho(rho_szok):
    # moneta 0 (nie jej sąsiedzi) ma ten sam szereg bez względu na zależność między monetami —
    # tylko w sensie rozkładu; sprawdzamy, że kwantyle |r| są zgodne w dużej próbie
    n = 20_000
    bazowy = generuj_panel_lv2d(n, 1, seed=1, amplituda=0.5, rho=0.0, rho_szok=0.0)["r"]
    inny = generuj_panel_lv2d(n, 1, seed=2, amplituda=0.5, rho=0.8, rho_szok=rho_szok)["r"]
    qa = np.quantile(np.abs(bazowy.to_numpy()[:, 0]), [0.25, 0.5, 0.75])
    qb = np.quantile(np.abs(inny.to_numpy()[:, 0]), [0.25, 0.5, 0.75])
    assert np.allclose(qa, qb, rtol=0.35)


def test_rejestr_wariancji_podnosi_kurtoze_zwrotow_wspolna_miara():
    n = 20_000
    a = generuj_panel_lv2d(n, 1, seed=3, amplituda=0.0, **PARAMETRY)["r"].to_numpy()[:, 0]
    b = generuj_panel_lv2d(n, 1, seed=3, amplituda=0.8, **PARAMETRY)["r"].to_numpy()[:, 0]

    def kurtoza(x):
        x = x - x.mean()
        return float((x**4).mean() / (x**2).mean() ** 2)

    assert kurtoza(b) > kurtoza(a)


@pytest.mark.parametrize(
    "kw, wyjatek",
    [
        ({"amplituda": -0.1}, "amplituda"),
        ({"amplituda": 0.5, "dlugosc": 0.5}, "dlugosc"),
        ({"amplituda": 0.0, "dlugosc": 0.0}, "dlugosc"),
    ],
)
def test_niepoprawne_argumenty_dostaja_blad(kw, wyjatek):
    with pytest.raises(ValueError, match=wyjatek):
        generuj_panel_lv2d(50, 2, seed=1, **PARAMETRY, **kw)


@settings(max_examples=40, deadline=None)
@given(
    n=st.integers(1, 400),
    s=st.floats(0.0, 1.5),
    d=st.floats(1.0, 1000.0),
    seed=st.integers(0, 2**31 - 1),
)
def test_poziom_wlasnosci_dla_dowolnych_argumentow(n, s, d, seed):
    poziom = poziom_wariancji(n, s, d, seed)
    assert poziom.shape == (n,)
    assert np.all(np.isfinite(poziom)) and np.all(poziom > 0.0)
    if s == 0.0:
        assert np.all(poziom == 1.0)
