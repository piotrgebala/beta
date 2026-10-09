"""Detekcja dotknięć progu likwidacji i klastry — wartości ręczne, własności (hypothesis), kontrole symulacyjne."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from modele.likwidacja_model import p_model
from modele.likwidacja_zdarzenia import dotkniecia, klastry


def _seria(n=12):
    close = np.full(n, 100.0)
    return close, close.copy(), close.copy()


def test_long_3x_prog_to_okolo_67_przy_mmr_1pct():
    # margines = 1/3 − 0,01 → cena likwidacji 100·(1 − 0,32333) = 67,667
    close, high, low = _seria()
    low[4] = 67.60
    z = dotkniecia(close, high, low, np.array([2]), 3.0, 0.01, "long", 7)
    assert z.tolist() == [True]
    low[4] = 67.70
    z = dotkniecia(close, high, low, np.array([2]), 3.0, 0.01, "long", 7)
    assert z.tolist() == [False]


def test_short_uzywa_high_i_okno_zaczyna_sie_dzien_po_wpisie():
    close, high, low = _seria()
    high[2] = 500.0  # w dniu wpisu — nie liczy się
    high[10] = 500.0  # poza oknem wpisu 2 (dni 3…9)
    z = dotkniecia(close, high, low, np.array([2]), 3.0, 0.01, "short", 7)
    assert z.tolist() == [False]
    high[9] = 133.4  # 100·(1 + 0,32333) = 132,33
    z = dotkniecia(close, high, low, np.array([2]), 3.0, 0.01, "short", 7)
    assert z.tolist() == [True]


def test_wpis_bez_pelnego_okna_to_wyjatek():
    close, high, low = _seria(10)
    with pytest.raises(ValueError):
        dotkniecia(close, high, low, np.array([3]), 3.0, 0.01, "long", 7)
    with pytest.raises(ValueError):
        dotkniecia(close, high, low, np.array([1]), 3.0, 0.01, "bok", 7)
    with pytest.raises(ValueError):
        dotkniecia(close, high, low[:-1], np.array([1]), 3.0, 0.01, "long", 7)


def test_klastry_wartosci_reczne():
    assert klastry(np.array([])) == 0
    assert klastry(np.array([5])) == 1
    assert klastry(np.array([5, 9, 15])) == 1  # łańcuch: 4 i 6 dni
    assert klastry(np.array([5, 9, 17])) == 2  # przerwa 8 > 7
    assert klastry(np.array([17, 5, 9, 9])) == 2  # kolejność i duplikaty nie mają znaczenia


@settings(max_examples=200, deadline=None)
@given(
    dni=st.lists(st.integers(0, 400), max_size=60),
    o1=st.integers(0, 20),
    o2=st.integers(0, 20),
)
def test_hyp_klastry(dni, o1, o2):
    a = np.array(dni, dtype=int)
    k1, k2 = klastry(a, o1), klastry(a, o2)
    assert 0 <= k1 <= len(np.unique(a))
    assert (k1 == 0) == (len(a) == 0)
    if o1 <= o2:
        assert k1 >= k2  # szerszy odstęp łączy więcej


@settings(max_examples=100, deadline=None)
@given(
    seed=st.integers(0, 10_000),
    l1=st.floats(2.0, 12.0),
    l2=st.floats(2.0, 12.0),
    strona=st.sampled_from(["long", "short"]),
)
def test_hyp_wieksza_dzwignia_wiecej_dotkniec(seed, l1, l2, strona):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, 80)))
    high, low = close * 1.02, close * 0.98
    wpisy = np.arange(0, 72)
    a = dotkniecia(close, high, low, wpisy, l1, 0.01, strona, 7)
    b = dotkniecia(close, high, low, wpisy, l2, 0.01, strona, 7)
    if l1 <= l2:
        assert (a <= b).all()  # każde dotknięcie przy mniejszej dźwigni jest też przy większej


def _dzienne_hlc(sigma, n_dni, kroki, seed):
    rng = np.random.default_rng(seed)
    drobne = rng.normal(0.0, sigma / np.sqrt(kroki), n_dni * kroki)
    log_cena = np.concatenate([[0.0], np.cumsum(drobne)])
    close = np.exp(log_cena[kroki::kroki])
    high = np.empty(n_dni)
    low = np.empty(n_dni)
    for d in range(n_dni):
        seg = log_cena[d * kroki : (d + 1) * kroki + 1]
        high[d], low[d] = np.exp(seg.max()), np.exp(seg.min())
    return (
        np.concatenate([[1.0], close]),
        np.concatenate([[1.0], high]),
        np.concatenate([[1.0], low]),
    )


@pytest.mark.parametrize("mnoznik, oczekiwany", [(1.0, (0.82, 1.0)), (2.0, (2.0, 3.0))])
def test_kontrola_negatywna_i_pozytywna_na_symulacji(mnoznik, oczekiwany):
    # σ prawdziwa = mnoznik·σ modelu; model zgodny (mnoznik 1) → O/E ≈ 1 (nieco poniżej: 2·ogon to górne przybliżenie
    # dla ścieżki ciągłej, a siatka 48 kroków dziennych ją tnie); model zaniżony 2× → O/E wyraźnie > 1
    sigma_modelu, dni, n = 0.05, 7, 20_000
    close, high, low = _dzienne_hlc(sigma_modelu * mnoznik, n, 48, seed=5)
    wpisy = np.arange(0, n - dni)
    z = dotkniecia(close, high, low, wpisy, 6.0, 0.01, "long", dni)
    e = p_model(
        np.full(len(wpisy), sigma_modelu), np.full(len(wpisy), 1e6), 6.0, 0.01, "long", dni
    ).sum()
    stosunek = z.sum() / e
    assert oczekiwany[0] < stosunek < oczekiwany[1], stosunek
