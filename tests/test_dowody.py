"""Testy reportera F3: e-procesy, Bayes, zgodność stałych z alpha."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import integrate
from scipy.stats import norm

from dowody import raport
from dowody.bayes import posterior
from dowody.eproces import log_e_mieszanka, obalenie, potwierdzenie, tau_dla
from dowody.nogi import NOGI

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("strona", [-1, 1])
@pytest.mark.parametrize("S", [-3.0, -0.5, 0.0, 1.2, 4.0])
def test_wzor_zgodny_z_calka(S, strona):
    """Postać zamknięta = całka numeryczna mieszanki po połowie N(0, τ²)."""
    V, tau = 2.5, 0.8

    def f(lam):
        return np.exp(lam * S - lam**2 * V / 2) * 2 * norm.pdf(lam, scale=tau)

    lo, hi = (-np.inf, 0) if strona == -1 else (0, np.inf)
    num, _ = integrate.quad(f, lo, hi)
    assert np.exp(log_e_mieszanka(S, V, tau, strona)) == pytest.approx(num, rel=1e-8)


def test_e_startuje_od_1_i_jest_wartoscia_oczekiwana_1():
    """E przy V → 0 dąży do 1; średnia E_t pod H0 ≈ 1 (martyngał)."""
    assert np.exp(log_e_mieszanka(0.0, 1e-12, 1.0, -1)) == pytest.approx(1.0, rel=1e-6)
    rng = np.random.default_rng(0)
    sd = 0.01
    x = rng.normal(0.0003, sd, size=(200_000, 30))
    S = (x - 0.0003).sum(axis=1)
    e = np.exp(log_e_mieszanka(S, 30 * sd**2, tau_dla(0.0003, sd), -1))
    assert e.mean() == pytest.approx(1.0, abs=0.02)


def test_kierunki():
    sd = 0.01
    zle = np.full(300, -0.003)  # dużo gorzej niż zakładane +0,05 %/dzień
    dobre = np.full(300, 0.003)
    assert obalenie(zle, 0.0005, sd)[-1] > 40
    assert obalenie(dobre, 0.0005, sd)[-1] < 1
    assert potwierdzenie(dobre, 0.0005, sd)[-1] > 40
    assert potwierdzenie(zle, 0.0005, sd)[-1] < 1


def test_nan_pomijane_i_bledy():
    e = obalenie([0.01, np.nan, -0.01], 0.0005, 0.01)
    assert len(e) == 2
    with pytest.raises(ValueError):
        log_e_mieszanka(0.0, 1.0, 1.0, 0)
    with pytest.raises(ValueError):
        log_e_mieszanka(0.0, 1.0, -1.0, 1)


def test_posterior():
    pr = posterior([], 0.2, 0.0, 0.1)
    assert pr["mean"] == 0.0 and pr["sd"] == 0.1 and pr["p_dodatnia"] == pytest.approx(0.5)
    rng = np.random.default_rng(1)
    x = rng.normal(0.30 / 365, 0.2 / 365**0.5, 365 * 2000)
    p = posterior(x, 0.2, 0.0, 0.1)
    assert p["mean"] == pytest.approx(0.30, abs=0.02)  # dużo danych → prior się nie liczy
    assert p["p_dodatnia"] > 0.99


def test_stale_zgodne_z_alpha():
    src = (ROOT / "../alpha/backtest/odczyt_dziennika.py").resolve()
    if not src.is_file():
        pytest.skip("brak repo alpha obok beta")
    txt = src.read_text(encoding="utf-8")
    for n in NOGI:
        pat = rf'Leg\(\s*"{n.name}",(?:(?!Leg\().)*?"{n.plik}",\s*"{n.kolumna}",\s*([\d.]+),\s*([\d.]+)'
        m = re.search(pat, txt, re.DOTALL)
        assert m, n.name
        assert (float(m.group(1)), float(m.group(2))) == (n.mu, n.sigma)


def test_raport_na_atrapie(tmp_path, capsys):
    rng = np.random.default_rng(2)
    days = pd.date_range("2026-09-24", periods=20).strftime("%Y-%m-%d")
    pd.DataFrame(
        {
            "date": days,
            "r_trend": rng.normal(0, 0.01, 20),
            "r_coinbase": rng.normal(0, 0.02, 20),
            "r_port": rng.normal(0, 0.01, 20),
        }
    ).to_csv(tmp_path / "wyniki.csv", index=False)
    raport.main(["--dziennik", str(tmp_path)])
    out = capsys.readouterr().out
    assert "NIE WIĄŻE" in out and "TS1" in out and "brak pliku x1_wyniki.csv" in out
