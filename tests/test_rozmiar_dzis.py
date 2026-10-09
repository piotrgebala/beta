"""Tabela „na dziś” na panelu syntetycznym (bez danych rynkowych)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from modele.rozmiar_dzis import prognoza_sigma_nu, tabela_dzis
from symulacje.garch_panel import generuj_panel


def _panel(n: int = 1200, seed: int = 3) -> pd.DataFrame:
    r = generuj_panel(n, 2, seed=seed)["r"].to_numpy()
    return pd.DataFrame(r, columns=["A", "B"])


def test_prognoza_sigma_rzedu_sd_serii():
    r = _panel()["A"].to_numpy()
    sigma, nu, trwalosc, _ = prognoza_sigma_nu(r)
    assert 0.3 * r.std() < sigma < 3 * r.std()
    assert nu > 2 and 0 < trwalosc < 1.0001


def test_tabela_ksztalt_i_monotonicznosc_po_zapasie():
    tab = tabela_dzis(_panel(), cele=(0.2,), zapasy=(1.0, 1.5))
    assert len(tab) == 4 and set(tab["moneta"]) == {"A", "B"}
    for _, g in tab.groupby("moneta"):
        a, b = g.sort_values("zapas").iloc[0], g.sort_values("zapas").iloc[1]
        assert b["sigma_dzien_%"] == pytest.approx(1.5 * a["sigma_dzien_%"])
        assert b["dzwignia_cel_20%"] <= a["dzwignia_cel_20%"] + 1e-12
        assert b["dystans_3x_sigm"] < a["dystans_3x_sigm"]
        assert b["P_likw_3x_7d_%"] >= a["P_likw_3x_7d_%"]
    assert (tab["dzwignia_cel_20%"] <= 3.0 + 1e-12).all()
    assert (tab["dystans_2x_sigm"] > tab["dystans_3x_sigm"]).all()
    assert np.isfinite(tab.select_dtypes("number").to_numpy()).all()
