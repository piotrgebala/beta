"""K′ (bootstrap blokowy): indeksy, rozmiar na szumie niezależnym, poprawa rozmiaru przy zależności, moc."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from scipy.stats import norm

from miara.var_es import var_es_t
from symulacje.k_prim_blokowy import indeksy_blokowe, odrzuca, pwartosci_blokowe
from symulacje.moc_var_es import NU

P = 0.05


@settings(max_examples=60, deadline=None)
@given(
    n=st.integers(3, 300),
    dl=st.integers(1, 300),
    boot=st.integers(1, 20),
    ziarno=st.integers(0, 10**6),
)
def test_indeksy_ksztalt_zakres_i_ciaglosc_blokow(n, dl, boot, ziarno):
    if dl > n:
        with pytest.raises(ValueError):
            indeksy_blokowe(n, dl, boot, np.random.default_rng(ziarno))
        return
    idx = indeksy_blokowe(n, dl, boot, np.random.default_rng(ziarno))
    assert idx.shape == (boot, n)
    assert idx.min() >= 0 and idx.max() < n
    if dl > 1 and n > dl:
        krok = np.diff(idx[:, :dl], axis=1) % n
        assert (krok == 1).all()


def test_indeksy_bledne_wejscia():
    rng = np.random.default_rng(0)
    for args in ((2, 1, 5), (10, 0, 5), (10, 11, 5), (10, 3, 0)):
        with pytest.raises(ValueError):
            indeksy_blokowe(*args, rng)


def _panel(rng, n, k, sigma):
    eps = rng.standard_t(NU, size=(n, k)) * np.sqrt((NU - 2) / NU)
    return sigma[:, None] * eps


def _pw(r, boot, dlugosci, rng):
    q, es = var_es_t(np.ones(r.shape), P, NU)
    n = len(r)
    idx_dni = rng.integers(0, n, size=(boot, n))
    bloki = {dl: indeksy_blokowe(n, dl, boot, rng) for dl in dlugosci}
    return pwartosci_blokowe(r, q, es, P, idx_dni, bloki)


def test_rozmiar_na_szumie_niezaleznym_blisko_nominalnego():
    rng = np.random.default_rng(11)
    odrz = {1: [], 40: []}
    for _ in range(150):
        pw = _pw(_panel(rng, 600, 3, np.ones(600)), 199, (1, 40), rng)
        for dl, v in odrz.items():
            v.append(odrzuca(pw[dl])[0])
    for dl, v in odrz.items():
        assert np.mean(v) < 0.14, (dl, np.mean(v))


def test_blokowy_poprawia_rozmiar_przy_zaleznosci_poziomu():
    rng = np.random.default_rng(12)
    n, dl_fazy = 1500, 150
    odrz = {1: [], 150: []}
    for _ in range(120):
        sigma = np.repeat(rng.choice([0.8, 1.2], size=n // dl_fazy), dl_fazy)
        pw = _pw(_panel(rng, n, 3, sigma), 199, (1, 150), rng)
        for dl, v in odrz.items():
            v.append(odrzuca(pw[dl])[1])
    assert np.mean(odrz[1]) > np.mean(odrz[150]) + 0.10


def test_moc_przy_zanizonym_ryzyku_i_kontrola_negatywna_wyroczni():
    rng = np.random.default_rng(13)
    m_zan, m_wyr = [], []
    for _ in range(60):
        r = _panel(rng, 1200, 4, np.ones(1200))
        q, es = var_es_t(np.full(r.shape, 0.7), P, NU)
        n = len(r)
        idx_dni = rng.integers(0, n, size=(199, n))
        bl = {60: indeksy_blokowe(n, 60, 199, rng)}
        m_zan.append(odrzuca(pwartosci_blokowe(r, q, es, P, idx_dni, bl)[60])[0])
        m_wyr.append(odrzuca(_pw(r, 199, (60,), rng)[60])[0])
    assert np.mean(m_zan) > 0.95
    assert np.mean(m_wyr) < 0.15


def test_odrzuca_nan_nie_odrzuca():
    assert odrzuca((float("nan"), float("nan"), float("nan")))[0] is False
    assert odrzuca((0.001, 0.5, 0.5)) == (True, True, False, False)
    assert norm.isf(0.05 / 6) > 2.3
