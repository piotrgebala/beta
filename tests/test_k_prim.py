"""Górna granica mocy K′: rozmiar na wycentrowanym szumie, moc przy przesunięciu, błędne wejścia."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import norm

from symulacje.k_prim import odrzucenia_idealne


def test_rozmiar_bonferroni_na_szumie_wycentrowanym():
    rng = np.random.default_rng(1)
    n = 200_000
    hit = 0.05 + 0.004 * rng.standard_normal(n)
    u = 1.0 + 0.08 * rng.standard_normal(n)
    w = odrzucenia_idealne(hit, u, None, 0.05)
    assert w["A"] == pytest.approx(0.05 / 3, abs=0.002)
    assert w["C"] == pytest.approx(0.05 / 3, abs=0.002)
    assert w["razem"] == pytest.approx(1 - (1 - 0.05 / 3) ** 2, abs=0.003)


def test_moc_przy_przesunieciu_zgodna_ze_wzorem():
    rng = np.random.default_rng(2)
    n = 200_000
    delta = 3.0  # przesunięcie w jednostkach SE
    hit = 0.05 + 0.004 * (delta + rng.standard_normal(n))
    u = 1.0 + 0.08 * rng.standard_normal(n)
    w = odrzucenia_idealne(hit, u, None, 0.05)
    kryt = norm.isf(0.05 / 6)
    assert w["A"] == pytest.approx(norm.sf(kryt - delta) + norm.cdf(-kryt - delta), abs=0.004)
    zb_b = np.ones(n)
    assert odrzucenia_idealne(hit, u, zb_b, 0.05)["razem"] == 1.0


def test_bledne_wejscia():
    with pytest.raises(ValueError):
        odrzucenia_idealne(np.ones(5), np.ones(4), None, 0.05)
    with pytest.raises(ValueError):
        odrzucenia_idealne(np.ones(2), np.ones(2), None, 0.05)
