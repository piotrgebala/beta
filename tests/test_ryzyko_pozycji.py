"""Wielkość pozycji, dystans do likwidacji i limit ES — wartości ręczne, symulacja i własności (hypothesis)."""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from modele.ryzyko_pozycji import (
    dystans_w_sigmach,
    dzwignia_celu,
    dzwignia_konc,
    es_straty,
    p_likwidacji,
    ruch_do_likwidacji,
    skala_limitu_es,
)

SIGMA = st.floats(min_value=1e-3, max_value=0.3)
DZW = st.floats(min_value=0.5, max_value=20.0)
NU = st.floats(min_value=2.5, max_value=30.0)


def test_dzwignia_celu_wartosc_reczna_i_sufit():
    sigma_roczna = 0.02 * math.sqrt(365)
    assert dzwignia_celu(0.02, 0.20, 3.0) == pytest.approx(0.20 / sigma_roczna)
    assert dzwignia_celu(0.001, 0.20, 3.0) == 3.0  # sufit wygrywa z celem


def test_dzwignia_konc_bierze_najmniejsza_z_trzech():
    assert dzwignia_konc(0.02, 0.20, 3.0) == pytest.approx(dzwignia_celu(0.02, 0.20, 3.0))
    assert dzwignia_konc(0.02, 0.20, 0.3) == 0.3
    assert dzwignia_konc(0.02, 0.20, 3.0, es_dzienny=0.05, limit_es=0.01) == pytest.approx(0.2)
    with pytest.raises(ValueError, match="razem"):
        dzwignia_konc(0.02, 0.20, 3.0, es_dzienny=0.05)


def test_ruch_do_likwidacji_3x_wartosc_reczna():
    margines = 1 / 3 - 0.005
    assert ruch_do_likwidacji(3.0, 0.005, "long") == pytest.approx(math.log(1 - margines))
    assert ruch_do_likwidacji(3.0, 0.005, "short") == pytest.approx(math.log(1 + margines))
    assert ruch_do_likwidacji(3.0, 0.005, "long") < 0 < ruch_do_likwidacji(3.0, 0.005, "short")
    # w cenach: long likwidowany po spadku o ok. 32,8 %
    assert 1 - math.exp(ruch_do_likwidacji(3.0, 0.005)) == pytest.approx(0.32833, abs=1e-4)


def test_long_bez_dzwigni_i_mmr_nie_ma_ceny_likwidacji():
    assert ruch_do_likwidacji(1.0, 0.0, "long") == -math.inf
    assert dystans_w_sigmach(1.0, 0.0, 0.02) == math.inf
    assert p_likwidacji(1.0, 0.0, 0.02, nu=5.0) == 0.0


@pytest.mark.parametrize(
    "wywolanie",
    [
        lambda: ruch_do_likwidacji(0.0, 0.005),
        lambda: ruch_do_likwidacji(3.0, -0.1),
        lambda: ruch_do_likwidacji(200.0, 0.01),  # 1/L ≤ mmr
        lambda: ruch_do_likwidacji(3.0, 0.005, "bok"),
        lambda: dzwignia_celu(0.0, 0.2, 3.0),
        lambda: dzwignia_celu(float("nan"), 0.2, 3.0),
        lambda: p_likwidacji(3.0, 0.005, 0.02, nu=2.0),
        lambda: dystans_w_sigmach(3.0, 0.005, 0.02, dni=0),
        lambda: skala_limitu_es([1.0, 2.0], [0.1], 0.1),
        lambda: skala_limitu_es([1.0], [-0.1], 0.1),
        lambda: skala_limitu_es([float("inf")], [0.1], 0.1),
    ],
)
def test_wejscia_bledne_to_wyjatek(wywolanie):
    with pytest.raises(ValueError):
        wywolanie()


def test_dystans_w_sigmach_rosnie_z_horyzontem_malejaco():
    d1 = dystans_w_sigmach(3.0, 0.005, 0.02, dni=1)
    d4 = dystans_w_sigmach(3.0, 0.005, 0.02, dni=4)
    assert d4 == pytest.approx(d1 / 2)


def test_p_likwidacji_zgodne_z_symulacja_dla_prawie_normalnego():
    # zwrot h-dniowy ~ N(0, σ²h): P(koniec poza progiem) z wzoru vs symulacja; dotknięcie ≥ koniec okresu
    rng = np.random.default_rng(7)
    sigma, h, dzw, mmr = 0.04, 10, 6.0, 0.005
    prog = ruch_do_likwidacji(dzw, mmr, "long")
    sciezki = np.cumsum(rng.normal(0.0, sigma, (200_000, h)), axis=1)
    koniec = float(np.mean(sciezki[:, -1] < prog))
    dotkn_dyskretne = float(np.mean(sciezki.min(axis=1) < prog))
    wzor_koniec = p_likwidacji(dzw, mmr, sigma, nu=1e6, dni=h, dotkniecie=False)
    wzor_dotkn = p_likwidacji(dzw, mmr, sigma, nu=1e6, dni=h, dotkniecie=True)
    assert wzor_koniec == pytest.approx(koniec, abs=0.004)
    assert dotkn_dyskretne <= wzor_dotkn + 0.004  # górne przybliżenie, nie równość
    assert wzor_dotkn == pytest.approx(2 * wzor_koniec)


def test_es_straty_zgodne_z_symulacja_t():
    nu, sigma, p = 5.0, 0.03, 0.05
    var, es = es_straty(sigma, p, nu)
    rng = np.random.default_rng(11)
    r = sigma * rng.standard_t(nu, 2_000_000) * math.sqrt((nu - 2) / nu)
    strata = -r
    prog = np.quantile(strata, 1 - p)
    assert var == pytest.approx(prog, rel=0.02)
    assert es == pytest.approx(strata[strata >= prog].mean(), rel=0.03)
    assert es > var > 0


def test_skala_limitu_es_wartosc_reczna():
    w, skala = skala_limitu_es([1.0, -2.0], [0.05, 0.04], limit=0.065)
    # ryzyko = 1·0,05 + 2·0,04 = 0,13 → skala 0,5
    assert skala == pytest.approx(0.5)
    assert w == pytest.approx([0.5, -1.0])
    w2, skala2 = skala_limitu_es([1.0, -2.0], [0.05, 0.04], limit=1.0)
    assert skala2 == 1.0 and w2 == pytest.approx([1.0, -2.0])


@settings(max_examples=200, deadline=None)
@given(s1=SIGMA, s2=SIGMA, cel=st.floats(0.01, 2.0), sufit=st.floats(0.1, 10.0))
def test_hyp_dzwignia_w_zakresie_i_nierosnaca_ze_zmiennoscia(s1, s2, cel, sufit):
    a, b = dzwignia_celu(s1, cel, sufit), dzwignia_celu(s2, cel, sufit)
    assert 0 < a <= sufit and 0 < b <= sufit
    if s1 <= s2:
        assert a >= b - 1e-12


@settings(max_examples=200, deadline=None)
@given(s=SIGMA, cel=st.floats(0.01, 2.0), sufit=st.floats(0.1, 10.0), es=SIGMA, lim=SIGMA)
def test_hyp_dzwignia_konc_nie_przekracza_zadnego_limitu(s, cel, sufit, es, lim):
    d = dzwignia_konc(s, cel, sufit, es, lim)
    assert 0 < d <= sufit * (1 + 1e-12)
    assert d <= dzwignia_celu(s, cel, sufit) * (1 + 1e-12)
    assert d * es <= lim * (1 + 1e-9)


@settings(max_examples=200, deadline=None)
@given(l1=st.floats(1.0, 30.0), l2=st.floats(1.0, 30.0), mmr=st.floats(0.0, 0.03))
def test_hyp_wieksza_dzwignia_to_blizsza_likwidacja(l1, l2, mmr):
    if 1 / l1 <= mmr or 1 / l2 <= mmr:
        return
    d1, d2 = dystans_w_sigmach(l1, mmr, 0.02), dystans_w_sigmach(l2, mmr, 0.02)
    if l1 < l2:
        assert d1 >= d2 - 1e-12


@settings(max_examples=200, deadline=None)
@given(
    dzw=st.floats(1.0, 15.0),
    s1=SIGMA,
    s2=SIGMA,
    nu=NU,
    dni=st.integers(1, 30),
    strona=st.sampled_from(["long", "short"]),
)
def test_hyp_p_likwidacji_w_przedziale_i_rosnie_ze_zmiennoscia(dzw, s1, s2, nu, dni, strona):
    mmr = 0.005
    if 1 / dzw <= mmr:
        return
    p1 = p_likwidacji(dzw, mmr, s1, nu, strona, dni)
    p2 = p_likwidacji(dzw, mmr, s2, nu, strona, dni)
    assert 0.0 <= p1 <= 1.0 and 0.0 <= p2 <= 1.0
    if s1 <= s2:
        assert p1 <= p2 + 1e-12
    assert p_likwidacji(dzw, mmr, s1, nu, strona, dni, dotkniecie=False) <= p1 + 1e-12


@settings(max_examples=200, deadline=None)
@given(
    wagi=st.lists(st.floats(-5, 5), min_size=1, max_size=8),
    limit=st.floats(0.001, 1.0),
    seed=st.integers(0, 10_000),
)
def test_hyp_skala_limitu_es(wagi, limit, seed):
    es = np.random.default_rng(seed).uniform(0.0, 0.2, len(wagi))
    nowe, skala = skala_limitu_es(wagi, es, limit)
    assert 0 < skala <= 1.0
    assert float(np.sum(np.abs(nowe) * es)) <= limit * (1 + 1e-9)
    assert (np.abs(nowe) <= np.abs(wagi) + 1e-12).all()
    assert (nowe * np.asarray(wagi) >= 0).all()  # żadna waga nie zmienia znaku
    ponownie, skala2 = skala_limitu_es(nowe, es, limit)
    assert skala2 == pytest.approx(1.0, abs=1e-9) and ponownie == pytest.approx(nowe)
