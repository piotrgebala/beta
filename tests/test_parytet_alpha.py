"""
Parytet przyrządu (zasada 24): `miara/` daje te same liczby co kod alpha na wektorach testowych,
z tolerancją 1e-12. Wartości oczekiwane: `tests/fixtures/parytet_alpha.json` (hash commita alpha
w pliku), generator: `python -m tests.generuj_parytet_alpha`.
"""

from __future__ import annotations

import importlib
import inspect
import json
from pathlib import Path

import pytest

from tests.wektory_parytetu import FUNKCJE, przypadki, roznice, wykonaj

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "parytet_alpha.json"
TOL = 1e-12

# Funkcje publiczne `miara/`, których NIE ma w alpha (nowe w beta) — poza parytetem.
TYLKO_BETA = {
    "miara.metryki": {"build_summary"},
    "miara.kontrola_negatywna": {"regula_trendu", "regula_przekrojowa"},
    "miara.dsr": set(),
    "miara.neff": set(),
}


@pytest.fixture(scope="module")
def oczekiwane() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def beta() -> dict:
    return wykonaj(lambda name: getattr(importlib.import_module(FUNKCJE[name][1]), name))


def test_fixture_z_commita_alpha(oczekiwane):
    assert len(oczekiwane["alpha_commit"]) == 40
    assert oczekiwane["alpha_pliki_sha256"]


def test_te_same_przypadki(oczekiwane):
    assert sorted(oczekiwane["wyniki"]) == sorted(k for k, _, _ in przypadki())


@pytest.mark.parametrize("key", [k for k, _, _ in przypadki()])
def test_parytet(key, oczekiwane, beta):
    exp = oczekiwane["wyniki"][key]
    got = beta[key]
    assert got["fn"] == exp["fn"]
    diff = roznice(exp["out"], got["out"], TOL)
    assert not diff, f"{key} ({exp['fn']}): " + "; ".join(diff[:5])


def test_kazda_przeniesiona_funkcja_ma_wektor():
    """≥ 1 wektor na każdą publiczną funkcję `miara/` przeniesioną z alpha (kryterium zadania 001)."""
    pokryte = {fn for _, fn, _ in przypadki()}
    for modul, wyjatki in TYLKO_BETA.items():
        m = importlib.import_module(modul)
        publiczne = {
            n
            for n, f in inspect.getmembers(m, inspect.isfunction)
            if not n.startswith("_") and f.__module__ == modul
        }
        brak = publiczne - wyjatki - pokryte
        assert not brak, f"{modul}: funkcje bez wektora parytetu: {sorted(brak)}"
        for n in publiczne - wyjatki:
            assert FUNKCJE[n][1] == modul
