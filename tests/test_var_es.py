"""Testy przyrządu VaR/ES (miara/var_es.py): ręczne przykłady, własności (hypothesis), lekkie R8."""

from __future__ import annotations

import math
from itertools import pairwise

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from scipy.integrate import quad
from scipy.stats import binom, chi2, chi2_contingency, ks_2samp, norm
from scipy.stats import t as student_t

from miara.var_es import (
    _lr,
    as_z2,
    as_z2_h0,
    as_z2_h0_polozenie_skala,
    as_z2_pwartosc,
    as_z2_pwartosc_ogolna,
    christoffersen_cc,
    christoffersen_ind,
    czy_polozenie_skala,
    kupiec_uc,
    losuj_innowacje,
    trafienia,
    var_es_normal,
    var_es_t,
)
from symulacje.garch_panel import generuj_panel
from symulacje.run_kv1 import ALFA, POZIOMY, TESTY, _kryteria

# --- trafienia i Kupiec --------------------------------------------------------------------------


def test_trafienia_nierownosc_ostra_i_pandas():
    h = trafienia([-3.0, -2.0, -1.0], [-2.0, -2.0, -2.0])
    assert h.dtype == bool and h.tolist() == [True, False, False]  # r = q nie jest trafieniem
    s = trafienia(pd.Series([-3.0, 1.0]), pd.Series([-2.0, -2.0]))
    assert s.tolist() == [True, False]
    # kontrakt pozycyjny: różne indeksy pandas są zestawiane po pozycji, nie po etykiecie
    inne = trafienia(pd.Series([-3.0, 1.0], index=[0, 1]), pd.Series([-2.0, -2.0], index=[5, 6]))
    assert inne.tolist() == [True, False]


def test_kupiec_reczny_wzor_i_binom():
    n, x, p = 250, 7, 0.01
    pi = x / n
    wzor = -2 * math.log((1 - p) ** (n - x) * p**x) + 2 * math.log((1 - pi) ** (n - x) * pi**x)
    h = np.zeros(n, dtype=bool)
    h[[3, 40, 41, 100, 150, 200, 249]] = True
    out = kupiec_uc(h, p)
    assert out["x"] == x and out["n"] == n and out["odsetek"] == pytest.approx(pi)
    assert out["LR"] == pytest.approx(wzor, rel=1e-10)
    assert out["LR"] == pytest.approx(2 * (binom.logpmf(x, n, pi) - binom.logpmf(x, n, p)))
    assert out["p_wartosc"] == pytest.approx(chi2.sf(wzor, 1), rel=1e-10)


def test_kupiec_brzegi_x0_xn_n1():
    h0 = np.zeros(100, dtype=bool)
    assert kupiec_uc(h0, 0.05)["LR"] == pytest.approx(-200 * math.log(0.95))  # 10,2587
    assert kupiec_uc(h0, 0.05)["LR"] == pytest.approx(10.2587, abs=1e-4)
    h1 = np.ones(10, dtype=bool)
    assert kupiec_uc(h1, 0.5)["LR"] == pytest.approx(-20 * math.log(0.5))  # 13,8629
    assert kupiec_uc([0], 0.05)["LR"] == pytest.approx(-2 * math.log(0.95))
    assert kupiec_uc([1], 0.05)["LR"] == pytest.approx(-2 * math.log(0.05))
    for h in (h0, h1, np.array([False]), np.array([True])):
        o = kupiec_uc(h, 0.3)
        assert np.isfinite(o["LR"]) and 0.0 <= o["p_wartosc"] <= 1.0


# --- Christoffersen ------------------------------------------------------------------------------

SEKWENCJA_A = [0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0]  # n00 4, n01 2, n10 2, n11 3
SEKWENCJA_NIEZALEZNA = [0, 0, 1, 0, 0, 1, 1, 0, 0, 0]  # π01 = π11 = 1/3 → LR_ind = 0


def test_christoffersen_ind_reczny_przyklad():
    o = christoffersen_ind(SEKWENCJA_A)
    assert (o["n00"], o["n01"], o["n10"], o["n11"]) == (4, 2, 2, 3)
    ln = math.log
    ll1 = 4 * ln(4 / 6) + 2 * ln(2 / 6) + 2 * ln(2 / 5) + 3 * ln(3 / 5)  # π01 = 1/3, π11 = 3/5
    ll0 = 6 * ln(6 / 11) + 5 * ln(5 / 11)  # π = 5/11
    assert o["niezdefiniowany"] is False
    assert o["LR"] == pytest.approx(2 * (ll1 - ll0), rel=1e-10)
    assert o["p_wartosc"] == pytest.approx(chi2.sf(o["LR"], 1), rel=1e-10)


def test_christoffersen_ind_niezalezny_ma_lr_zero():
    o = christoffersen_ind(SEKWENCJA_NIEZALEZNA)
    assert o["LR"] == pytest.approx(0.0, abs=1e-12) and o["p_wartosc"] == pytest.approx(1.0)


def test_christoffersen_ind_to_statystyka_g_tabeli_2x2():
    """Niezależna weryfikacja: LR_ind = statystyka G testu niezależności tabeli przejść."""
    rng = np.random.default_rng(5)
    for p in (0.1, 0.3):
        h = rng.random(400) < p
        o = christoffersen_ind(h)
        tab = [[o["n00"], o["n01"]], [o["n10"], o["n11"]]]
        g, pw, _, _ = chi2_contingency(tab, correction=False, lambda_="log-likelihood")
        assert o["LR"] == pytest.approx(g, rel=1e-9)
        assert o["p_wartosc"] == pytest.approx(pw, rel=1e-8)


@pytest.mark.parametrize(
    "h",
    [
        np.zeros(50, dtype=bool),  # brak trafień
        np.ones(50, dtype=bool),  # same trafienia
        np.r_[np.zeros(49, dtype=bool), True],  # jedyne trafienie na końcu
        np.r_[True, np.zeros(49, dtype=bool)],  # jedyne trafienie na początku
        np.array([True]),  # n = 1
        np.array([False, False]),
    ],
)
def test_christoffersen_ind_zdegenerowane_jawnie(h):
    o = christoffersen_ind(h)
    assert o["niezdefiniowany"] is True
    assert math.isnan(o["LR"]) and math.isnan(o["p_wartosc"])


def test_christoffersen_ind_n11_zero_nie_jest_zdegenerowany():
    """Pojedyncze, rozdzielone trafienia: n11 = 0, brzegi dodatnie — LR się liczy (0·ln 0 = 0)."""
    h = np.zeros(60, dtype=bool)
    h[[5, 20, 35, 50]] = True
    o = christoffersen_ind(h)
    assert o["n11"] == 0 and o["niezdefiniowany"] is False
    tab = [[o["n00"], o["n01"]], [o["n10"], o["n11"]]]
    g = chi2_contingency(tab, correction=False, lambda_="log-likelihood")[0]
    assert o["LR"] == pytest.approx(g, rel=1e-9) and o["LR"] > 0


def test_christoffersen_cc_rozklad_na_uc_i_ind_na_n_minus_1():
    p = 0.2
    o = christoffersen_cc(SEKWENCJA_A, p)
    ln = math.log
    ll1 = 4 * ln(4 / 6) + 2 * ln(2 / 6) + 2 * ln(2 / 5) + 3 * ln(3 / 5)
    ll_p = 6 * ln(1 - p) + 5 * ln(p)  # H0: π01 = π11 = p na przejściach (n − 1 = 11)
    assert o["n"] == 12 and o["n_uc"] == 11
    assert o["LR"] == pytest.approx(2 * (ll1 - ll_p), rel=1e-10)
    # LR_uc na próbie I_2..I_n (x = 5 z 11), nie na całych 12
    assert o["LR_uc"] == pytest.approx(kupiec_uc(SEKWENCJA_A[1:], p)["LR"], rel=1e-10)
    assert o["LR"] == pytest.approx(o["LR_uc"] + o["LR_ind"], rel=1e-10)
    assert o["LR_ind"] == pytest.approx(christoffersen_ind(SEKWENCJA_A)["LR"], rel=1e-10)
    assert o["p_wartosc"] == pytest.approx(chi2.sf(o["LR"], 2), rel=1e-10)


ASYM_POCZATEK = [1] + [0] * 9  # jedyne trafienie na początku: n00 8, n01 0, n10 1, n11 0
ASYM_KONIEC = [0] * 9 + [1]  # jedyne trafienie na końcu: n00 8, n01 1, n10 0, n11 0
ASYM_DWA = [0, 0, 0, 1, 0, 0, 0, 0, 0, 1]  # start 0, koniec 1: n00 6, n01 2, n10 1, n11 0


def _lr_uc_wzorem(x: int, n: int, p: float) -> float:
    """LR Kupca wprost ze wzoru, bez kodu przyrządu (0·ln 0 = 0)."""

    def ll(pr: float) -> float:
        return (x * math.log(pr) if x else 0.0) + ((n - x) * math.log(1 - pr) if n - x else 0.0)

    return 2 * (ll(x / n) - ll(p))


def test_christoffersen_asymetryczne_konce_serii_etykiety_i_konwencja_n_minus_1():
    """Seria zaczyna się albo kończy trafieniem (n01 ≠ n10): kierunek czasu i etykiety są ważne."""
    p = 0.05
    o = christoffersen_ind(ASYM_POCZATEK)
    assert (o["n00"], o["n01"], o["n10"], o["n11"]) == (8, 0, 1, 0)
    c = christoffersen_cc(ASYM_POCZATEK, p)
    assert c["n_uc"] == 9 and c["LR_uc"] == pytest.approx(_lr_uc_wzorem(0, 9, p), rel=1e-10)
    assert c["LR_uc"] == pytest.approx(0.92328, abs=1e-5)  # x = 0 z I_2..I_n, nie 1 z 9
    assert c["LR_uc"] == pytest.approx(kupiec_uc(ASYM_POCZATEK[1:], p)["LR"], rel=1e-10)

    o = christoffersen_ind(ASYM_KONIEC)
    assert (o["n00"], o["n01"], o["n10"], o["n11"]) == (8, 1, 0, 0)
    c = christoffersen_cc(ASYM_KONIEC, p)
    assert c["LR_uc"] == pytest.approx(_lr_uc_wzorem(1, 9, p), rel=1e-10)
    assert c["LR_uc"] == pytest.approx(0.53318, abs=1e-5)  # x = 1 z I_2..I_n, nie 0 z 9
    assert c["LR_uc"] == pytest.approx(kupiec_uc(ASYM_KONIEC[1:], p)["LR"], rel=1e-10)


def test_christoffersen_asymetryczny_przyklad_z_ind_liczony_recznie():
    p, ln = 0.2, math.log
    o = christoffersen_ind(ASYM_DWA)
    assert (o["n00"], o["n01"], o["n10"], o["n11"]) == (6, 2, 1, 0)  # n01 ≠ n10
    ll_markow = 6 * ln(6 / 8) + 2 * ln(2 / 8)  # π01 = 1/4, π11 = 0 (jedno przejście 1→0)
    ll_pi = 7 * ln(7 / 9) + 2 * ln(2 / 9)  # π = 2/9 na 9 przejściach
    ll_h0 = 7 * ln(1 - p) + 2 * ln(p)
    c = christoffersen_cc(ASYM_DWA, p)
    assert o["LR"] == pytest.approx(2 * (ll_markow - ll_pi), rel=1e-10)
    assert c["LR_uc"] == pytest.approx(2 * (ll_pi - ll_h0), rel=1e-10)  # = 0,0270
    assert c["LR"] == pytest.approx(2 * (ll_markow - ll_h0), rel=1e-10)  # = 0,5644
    # odwrócenie czasu zmienia próbę I_2..I_n (x = 2 → x = 1), więc LR_uc nie może się zgadzać
    assert christoffersen_cc(ASYM_DWA[::-1], p)["LR_uc"] != pytest.approx(c["LR_uc"], rel=1e-3)


def test_christoffersen_cc_zdegenerowany_ind_ale_cc_okreslony():
    o = christoffersen_cc(np.zeros(50, dtype=bool), 0.05)
    assert o["ind_niezdefiniowany"] is True and o["niezdefiniowany"] is False
    assert o["LR_ind"] == pytest.approx(0.0, abs=1e-12)
    assert o["LR"] == pytest.approx(-2 * 49 * math.log(0.95))  # samo pokrycie: 0 trafień w 49
    n1 = christoffersen_cc([1], 0.05)
    assert n1["niezdefiniowany"] is True and math.isnan(n1["LR"])


# --- walidacja wejść -----------------------------------------------------------------------------


def test_walidacja_nan_dlugosci_wymiary():
    r = np.array([-1.0, 0.5, -3.0])
    q = np.array([-2.0, -2.0, -2.0])
    es = np.array([-3.0, -3.0, -3.0])
    with pytest.raises(ValueError):
        trafienia([np.nan, 0.5, -3.0], q)
    with pytest.raises(ValueError):
        trafienia(r, [-2.0, -2.0])  # różne długości
    with pytest.raises(ValueError):
        trafienia([np.inf, 0.5, -3.0], q)
    with pytest.raises(ValueError):
        trafienia(np.zeros((3, 2)), q)  # nie 1-D
    with pytest.raises(ValueError):
        trafienia([], [])
    with pytest.raises(ValueError):
        as_z2(r, q, es[:2], 0.25)
    with pytest.raises(ValueError):
        as_z2(r, [np.nan, -2.0, -2.0], es, 0.25)
    for zle in ([0, 1, 2], [0.0, np.nan, 1.0], [], [[0, 1], [1, 0]], ["a", "b"], ["0", "1"]):
        with pytest.raises(ValueError):
            kupiec_uc(zle, 0.05)
        with pytest.raises(ValueError):
            christoffersen_ind(zle)
    for p in (0.0, 1.0, -0.1, 1.5):
        with pytest.raises(ValueError):
            kupiec_uc([0, 1], p)
        with pytest.raises(ValueError):
            christoffersen_cc([0, 1, 0], p)
    assert kupiec_uc(pd.Series([0, 1, 0, 0]), 0.25)["x"] == 1  # pandas, 0/1 jako int


def test_walidacja_znaku_es():
    r, q = np.array([-3.0, 1.0]), np.array([-2.0, -2.0])
    with pytest.raises(ValueError):
        as_z2(r, q, np.array([3.0, 3.0]), 0.25)  # es dodatnie (strata zamiast zwrotu)
    with pytest.raises(ValueError):
        as_z2(r, q, np.array([-1.0, -1.0]), 0.25)  # es > q (zamienione argumenty?)


ZLE_P = [0.0, 1.0, -0.1, 1.5, float("nan")]
R3, Q3, ES3 = np.array([-1.0, 0.5, -3.0]), np.full(3, -2.0), np.full(3, -3.0)


def _sampler_normalny(n):
    return lambda g, k: g.standard_normal((k, n))


def _sampler_sigma(sg):
    """Sampler σ_t ε_t z normalnym ε (rozkład predykcyjny prognozy normalnej)."""
    return lambda g, k: sg[None, :] * g.standard_normal((k, len(sg)))


@pytest.mark.parametrize("p", ZLE_P)
def test_walidacja_poziomu_p_w_rodzinie_z2(p):
    with pytest.raises(ValueError):
        as_z2(R3, Q3, ES3, p)
    with pytest.raises(ValueError):
        as_z2_h0(Q3, ES3, p, _sampler_normalny(3), 5, seed=1)
    with pytest.raises(ValueError):
        as_z2_h0_polozenie_skala(10, p, "normal", None, 5, seed=1)
    with pytest.raises(ValueError):
        as_z2_pwartosc_ogolna(R3, Q3, ES3, p, _sampler_normalny(3), 5, seed=1)


def test_walidacja_dlugosci_3_vs_1_nie_przechodzi_przez_broadcasting():
    q1, es1 = np.array([-2.0]), np.array([-3.0])
    for r, q, es in ((R3, q1, es1), (R3, Q3, es1), (R3, q1, ES3), (R3[:1], Q3, ES3)):
        with pytest.raises(ValueError):
            as_z2(r, q, es, 0.25)
    with pytest.raises(ValueError):
        as_z2_h0(Q3, es1, 0.25, _sampler_normalny(3), 5, seed=1)
    with pytest.raises(ValueError):
        trafienia(R3, q1)


def test_walidacja_es_w_as_z2_i_as_z2_h0():
    """es ≥ 0 albo > q to błąd także przy q ≥ 0 (dzielenie przez es) i w ścieżce ogólnej."""
    zle = [
        (Q3, np.zeros(3)),  # es = 0 przy q < 0 → es > q
        (
            np.full(3, 1.0),
            np.zeros(3),
        ),  # es = 0 przy q ≥ 0: bez własnego sprawdzenia dzielenie przez 0
        (Q3, np.full(3, 3.0)),  # es > 0
        (Q3, np.full(3, -1.0)),  # es > q
    ]
    for q, es in zle:
        with pytest.raises(ValueError):
            as_z2(R3, q, es, 0.25)
        with pytest.raises(ValueError):
            as_z2_h0(q, es, 0.25, _sampler_normalny(3), 5, seed=1)


def test_walidacja_samplera_ksztalt_i_wartosci():
    n = 4
    q, es = np.full(n, -2.0), np.full(n, -3.0)
    for zly_ksztalt in ((5, 1), (5, n + 1), (5, n - 1), (n, 5)):
        with pytest.raises(ValueError, match="kształt"):
            as_z2_h0(q, es, 0.25, lambda g, k, f=zly_ksztalt: np.zeros(f), 5, seed=1)
    for zla in (np.nan, np.inf, -np.inf):
        with pytest.raises(ValueError, match="NaN"):
            as_z2_h0(q, es, 0.25, lambda g, k, z=zla: np.full((k, n), z), 3, seed=1)


@pytest.mark.parametrize("reps", [0, -1, 2.7, True, None, "5"])
def test_reps_i_n_musza_byc_calkowite(reps):
    """Komunikat o liczbie całkowitej ≥ 1 — nie jakikolwiek błąd z dalszej części rachunku."""
    with pytest.raises(ValueError, match="całkowitą ≥ 1"):
        as_z2_h0(Q3, ES3, 0.25, _sampler_normalny(3), reps, seed=1)
    with pytest.raises(ValueError, match="całkowitą ≥ 1"):
        as_z2_h0_polozenie_skala(reps, 0.05, "normal", None, 5, seed=1)
    with pytest.raises(ValueError, match="całkowitą ≥ 1"):
        as_z2_h0_polozenie_skala(5, 0.05, "normal", None, reps, seed=1)


def test_losuj_innowacje_i_var_es_t_walidacja_rodziny_i_nu():
    g = np.random.default_rng(0)
    with pytest.raises(ValueError):
        losuj_innowacje(g, 3, "cauchy")
    for nu in (2.0, 1.5, 1.0, 0.5, np.nan, np.inf, None):
        with pytest.raises(ValueError):
            losuj_innowacje(g, 3, "t", nu)
        with pytest.raises(ValueError):
            var_es_t(1.0, 0.05, nu)
    assert losuj_innowacje(g, 3, "t", 2.01).shape == (3,)


def test_lr_ujemny_poza_zaokragleniami_to_blad_wzoru():
    """LR ≥ 0 z definicji: −1e-12 to szum zaokrągleń (→ 0), −1e-6 to błąd wzoru (→ wyjątek)."""
    assert _lr(3.5) == 3.5 and _lr(0.0) == 0.0
    assert _lr(-1e-12) == 0.0 and _lr(-1e-9) == 0.0
    for zle in (-1e-6, -1.0):
        with pytest.raises(ArithmeticError, match="ujemny"):
            _lr(zle)


# --- Z2 Acerbiego–Szekelya -----------------------------------------------------------------------


def test_z2_reczne_przyklady_i_znak():
    q, es, p = np.full(4, -2.0), np.full(4, -3.0), 0.25
    # trafienie dokładnie o tyle głębokie, ile prognozowane es → Z2 = 0
    assert as_z2([-3.0, 1.0, -1.0, 2.0], q, es, p) == pytest.approx(0.0)
    # głębsze niż es → niedoszacowanie → Z2 < 0: 1 − (−6)/(4 · 0,25 · (−3)) = −1
    assert as_z2([-6.0, 1.0, -1.0, 2.0], q, es, p) == pytest.approx(-1.0)
    # płytsze niż es → ogon przeszacowany → Z2 > 0: 1 − (−2,4)/(−3) = 0,2
    assert as_z2([-2.4, 1.0, -1.0, 2.0], q, es, p) == pytest.approx(0.2)
    assert as_z2([-1.0, 1.0, -1.0, 2.0], q, es, p) == pytest.approx(1.0)  # brak trafień
    # r = q NIE jest trafieniem (jak w `trafienia`): wkład 0, Z2 = 1 (a przy r <= q byłoby 1/3)
    assert as_z2([-2.0, 1.0, -1.0, 2.0], q, es, p) == pytest.approx(1.0)
    assert not trafienia([-2.0, 1.0, -1.0, 2.0], q).any()
    # es zmienne w czasie: dwa trafienia równe es_t → Z2 = 0
    r2 = np.array([-4.0, -5.0, 1.0, 1.0])
    q2, es2 = np.array([-2.0, -3.0, -2.0, -2.0]), np.array([-4.0, -5.0, -4.0, -4.0])
    assert as_z2(r2, q2, es2, 0.5) == pytest.approx(0.0)


def _z2_pod_h0(rodzina: str, n: int, p: float, reps: int, seed: int) -> np.ndarray:
    """Z2 liczone NIEZALEŻNIE od as_z2_h0: pętla po ścieżkach, σ_t zmienne, wzory zamknięte."""
    rng = np.random.default_rng(seed)
    sg = np.exp(rng.normal(0.0, 0.7, n))
    if rodzina == "normal":
        q, es = var_es_normal(sg, p)
    else:
        q, es = var_es_t(sg, p, 5.0)
    out = np.empty(reps)
    for i in range(reps):
        e = losuj_innowacje(rng, n, rodzina, 5.0)
        out[i] = as_z2(sg * e, q, es, p)
    return out


@pytest.mark.parametrize("rodzina", ["normal", "t"])
def test_z2_wartosc_oczekiwana_zero_pod_h0(rodzina):
    z = _z2_pod_h0(rodzina, n=500, p=0.05, reps=4000, seed=11)
    se = z.std(ddof=1) / math.sqrt(len(z))
    assert abs(z.mean()) < 4 * se  # E[Z2] = 0 (4 błędy standardowe; ziarno stałe)
    assert z.std(ddof=1) > 0.05  # nie jest zdegenerowane


def test_z2_niedoszacowanie_daje_ujemne_z2():
    """Prawda t5, prognoza normalna przy p = 1 %: ogon za cienki → E[Z2] = −0,754 (całka quad)."""
    rng = np.random.default_rng(3)
    n, p = 4000, 0.01
    sg = np.full(n, 0.03)
    q, es = var_es_normal(sg, p)
    z = np.array([as_z2(sg * losuj_innowacje(rng, n, "t", 5.0), q, es, p) for _ in range(200)])
    se = z.std(ddof=1) / math.sqrt(len(z))
    assert abs(z.mean() - (-0.754)) < 4 * se  # wartość analityczna z całki (quad), 4 SE
    assert z.mean() < -0.5  # i na pewno wyraźnie ujemne


@settings(max_examples=100, deadline=None)
@given(
    st.lists(st.floats(-5, 5, allow_nan=False), min_size=1, max_size=40),
    st.data(),
    st.sampled_from([0.25, 0.5, 2.0, 4.0, 8.0]),  # potęgi 2: skalowanie bez błędu zaokrągleń
    st.floats(0.01, 0.99),
)
def test_z2_niezmienniczy_na_skale(r, data, c, p):
    n = len(r)
    q = np.array(data.draw(st.lists(st.floats(-3, -0.5), min_size=n, max_size=n)))
    d = np.array(data.draw(st.lists(st.floats(0.0, 3.0), min_size=n, max_size=n)))
    es = q - d
    r = np.array(r)
    z = as_z2(r, q, es, p)
    assert as_z2(c * r, c * q, c * es, p) == pytest.approx(z, rel=1e-9, abs=1e-9)


@settings(max_examples=100, deadline=None)
@given(
    st.lists(st.integers(-4, 4), min_size=1, max_size=30),
    st.integers(-4, -1),
    st.floats(0.01, 0.99),
)
def test_z2_uzywa_tej_samej_definicji_trafienia_co_trafienia(r, q0, p):
    """Liczby całkowite → częste remisy r = q; Z2 z `trafienia()` liczonego osobno."""
    n = len(r)
    r, q = np.array(r, dtype=float), np.full(n, float(q0))
    es = q - 1.0
    h = trafienia(r, q)
    oczekiwane = 1.0 - float(np.sum(r[h] / es[h])) / (n * p)
    assert as_z2(r, q, es, p) == pytest.approx(oczekiwane, abs=1e-12)


def test_z2_niezmienniczy_na_dowolne_c():
    rng = np.random.default_rng(8)
    r = rng.standard_normal(500) * 0.03
    q, es = var_es_t(0.03, 0.05, 5.0)
    q, es = np.full(500, q), np.full(500, es)
    for c in (0.37, 3.7, 1234.5):
        assert as_z2(c * r, c * q, c * es, 0.05) == pytest.approx(as_z2(r, q, es, 0.05), abs=1e-9)


# --- p-wartość Z2 z symulacji pod H0 -------------------------------------------------------------


def test_as_z2_pwartosc_formula_i_brzegi():
    z0 = [-3.0, -2.0, -1.0, 0.0, 1.0]
    assert as_z2_pwartosc(-1.5, z0) == pytest.approx(3 / 6)  # (1 + 2) / (1 + 5)
    assert as_z2_pwartosc(-9.0, z0) == pytest.approx(1 / 6)  # nigdy 0
    assert as_z2_pwartosc(9.0, z0) == pytest.approx(1.0)
    assert as_z2_pwartosc(-1.0, z0) == pytest.approx(4 / 6)  # remis wlicza się do ogona
    with pytest.raises(ValueError):
        as_z2_pwartosc(0.0, [0.0, np.nan])
    for zle in (np.nan, np.inf, -np.inf):  # NaN nie może dać „najmniejszej możliwej p-wartości”
        with pytest.raises(ValueError):
            as_z2_pwartosc(zle, z0)


SEED_ZLE = [None, True, False, 1.5, "1", np.random.default_rng(1)]


@pytest.mark.parametrize("seed", SEED_ZLE)
def test_ziarno_musi_byc_int_albo_seedsequence(seed):
    """R19: None (entropia systemu), bool i Generator nie przechodzą jako „jawne” ziarno."""
    q, es = var_es_normal(np.full(20, 1.0), 0.05)
    with pytest.raises(TypeError):
        as_z2_h0(q, es, 0.05, _sampler_normalny(20), 5, seed=seed)
    with pytest.raises(TypeError):
        as_z2_pwartosc_ogolna(np.zeros(20), q, es, 0.05, _sampler_normalny(20), 5, seed=seed)
    with pytest.raises(TypeError):
        as_z2_h0_polozenie_skala(20, 0.05, "normal", None, 5, seed=seed)


def test_ziarno_brak_argumentu_numpy_int_i_ujemne():
    q, es = var_es_normal(np.full(20, 1.0), 0.05)
    with pytest.raises(TypeError):
        as_z2_h0(q, es, 0.05, _sampler_normalny(20), 5)
    with pytest.raises(TypeError):
        as_z2_pwartosc_ogolna(np.zeros(20), q, es, 0.05, _sampler_normalny(20), 5)
    a = as_z2_h0(q, es, 0.05, _sampler_normalny(20), 5, seed=3)
    b = as_z2_h0(q, es, 0.05, _sampler_normalny(20), 5, seed=np.int64(3))
    np.testing.assert_array_equal(a, b)
    with pytest.raises(ValueError):
        as_z2_h0(q, es, 0.05, _sampler_normalny(20), 5, seed=-1)


def test_h0_wymaga_jawnego_ziarna_i_jest_deterministyczne():
    n, p = 100, 0.05
    with pytest.raises(TypeError):
        as_z2_h0_polozenie_skala(n, p, "normal", None, 50)  # brak seed (R19)
    a = as_z2_h0_polozenie_skala(n, p, "t", 5.0, 200, seed=1)
    b = as_z2_h0_polozenie_skala(n, p, "t", 5.0, 200, seed=1)
    c = as_z2_h0_polozenie_skala(n, p, "t", 5.0, 200, seed=2)
    d = as_z2_h0_polozenie_skala(n, p, "t", 5.0, 200, seed=np.random.SeedSequence(1))
    np.testing.assert_array_equal(a, b)
    np.testing.assert_array_equal(a, d)  # int i SeedSequence(int) to to samo ziarno
    assert not np.array_equal(a, c)
    with pytest.raises(ValueError):
        as_z2_h0_polozenie_skala(n, p, "cauchy", None, 10, seed=1)
    with pytest.raises(ValueError):
        as_z2_h0_polozenie_skala(n, p, "t", None, 10, seed=1)


@pytest.mark.parametrize("rodzina,nu", [("normal", None), ("t", 5.0)])
def test_h0_polozenie_skala_rowna_sie_wersji_ogolnej_dla_dowolnego_sigma(rodzina, nu):
    """σ_t się skraca: ogólna wersja z σ_t ε_t daje TE SAME Z2 co skrót (ścieżka po ścieżce)."""
    n, p, reps = 300, 0.05, 1500
    rng = np.random.default_rng(3)
    sg = np.exp(rng.normal(0.0, 1.0, n))  # silnie zmienne σ_t
    q, es = var_es_normal(sg, p) if rodzina == "normal" else var_es_t(sg, p, nu)

    def los(rng_, k):
        return sg[None, :] * losuj_innowacje(rng_, (k, n), rodzina, nu)

    ogolna = as_z2_h0(q, es, p, los, reps, seed=10)
    skrot = as_z2_h0_polozenie_skala(n, p, rodzina, nu, reps, seed=10)
    np.testing.assert_allclose(ogolna, skrot, atol=1e-9)
    # i statystycznie, na niezależnych ziarnach (dwupróbkowy KS)
    inne = as_z2_h0_polozenie_skala(n, p, rodzina, nu, reps, seed=11)
    assert ks_2samp(ogolna, inne).pvalue > 0.01


def test_h0_ogolna_wersja_partie_i_kontrola_ksztaltu():
    q, es = var_es_normal(np.full(1500, 1.0), 0.05)
    # n = 1500 → partia ≤ 1333 ścieżek: wymusza więcej niż jedną partię
    z = as_z2_h0(q, es, 0.05, lambda g, k: g.standard_normal((k, 1500)), 2000, seed=4)
    assert z.shape == (2000,) and abs(z.mean()) < 0.01
    with pytest.raises(ValueError):
        as_z2_h0(q, es, 0.05, lambda g, k: g.standard_normal((k, 10)), 5, seed=4)


def test_pwartosc_pod_h0_ma_rozmiar_blisko_nominalnego():
    p, n = 0.05, 500
    z_h0 = as_z2_h0_polozenie_skala(n, p, "t", 5.0, 4000, seed=21)
    z = _z2_pod_h0("t", n, p, 2000, seed=22)
    pw = np.array([as_z2_pwartosc(x, z_h0) for x in z])
    assert 0.035 < (pw < 0.05).mean() < 0.065
    assert 0.47 < pw.mean() < 0.53


def test_as_z2_pwartosc_ogolna_rowna_sklejce_as_z2_i_h0_przy_tym_samym_ziarnie():
    n, p = 400, 0.05
    sg = np.full(n, 0.02)
    q, es = var_es_normal(sg, p)
    r = sg * losuj_innowacje(np.random.default_rng(5), n, "normal")
    los = _sampler_sigma(sg)

    o = as_z2_pwartosc_ogolna(r, q, es, p, los, 500, seed=6)
    z0 = as_z2_h0(q, es, p, los, 500, seed=6)
    assert o["z2"] == pytest.approx(as_z2(r, q, es, p)) and o["reps"] == 500
    assert o["p_wartosc"] == as_z2_pwartosc(as_z2(r, q, es, p), z0)  # dokładnie ta sama liczba
    assert 1 / 501 <= o["p_wartosc"] <= 1.0


def test_as_z2_pwartosc_ogolna_kierunek_zla_prognoza_mala_p_dobra_srednio_polowa():
    """Lewy ogon: za cienki ogon → p ≈ 1/(B+1); prawdziwy model → p ~ U(0, 1), średnia ≈ 0,5."""
    n, p, B = 300, 0.05, 400
    sg = np.full(n, 0.02)
    q, es = var_es_normal(sg, p)
    los = _sampler_sigma(sg)
    zla = 1.6 * sg * losuj_innowacje(np.random.default_rng(1), n, "normal")  # σ za małe 1,6×
    assert as_z2_pwartosc_ogolna(zla, q, es, p, los, B, seed=2)["p_wartosc"] < 0.01
    dobre = [sg * losuj_innowacje(np.random.default_rng(100 + i), n, "normal") for i in range(40)]
    pw = [
        as_z2_pwartosc_ogolna(r, q, es, p, los, B, seed=200 + i)["p_wartosc"]
        for i, r in enumerate(dobre)
    ]
    assert 0.35 < np.mean(pw) < 0.65 and min(pw) < 0.5 < max(pw)


def test_czy_polozenie_skala_i_niespojne_es_przesuwa_ogolny_rozklad_zerowy():
    """Dwa API są równoważne tylko dla prognozy σ_t (a, b); przy es spoza rodziny skrót ≠ ogólna."""
    n, p, reps = 2000, 0.05, 1000
    sg = np.exp(np.random.default_rng(0).normal(0.0, 0.5, n))
    q, es = var_es_t(sg, p, 5.0)
    assert czy_polozenie_skala(q, es, p, "t", 5.0)
    assert not czy_polozenie_skala(q, es, p, "normal")  # zła rodzina
    assert not czy_polozenie_skala(-q, -es, p, "t", 5.0)  # σ_t < 0
    assert not czy_polozenie_skala(q, es * (1 + 1e-6), p, "t", 5.0)  # es nie z rodziny
    with pytest.raises(ValueError):
        czy_polozenie_skala(q, es[:-1], p, "t", 5.0)
    qn, en = var_es_normal(1.0, p)
    qs, _ = var_es_t(1.0, p, 5.0)
    q_s, es_zly = np.full(n, qs), np.full(n, qs * en / qn)  # q prawdziwe, es o ok. 13 % za niskie
    assert not czy_polozenie_skala(q_s, es_zly, p, "t", 5.0)
    ogolna = as_z2_h0(
        q_s, es_zly, p, lambda g, k: losuj_innowacje(g, (k, n), "t", 5.0), reps, seed=1
    )
    skrot = as_z2_h0_polozenie_skala(n, p, "t", 5.0, reps, seed=1)
    assert -0.18 < ogolna.mean() < -0.11  # ogólna: rozkład zerowy przesunięty o błąd es (−0,144)
    assert abs(skrot.mean()) < 0.015  # skrót: rozkład zerowy modelu rodziny, E[Z2] = 0


# --- zamknięte wzory VaR/ES ----------------------------------------------------------------------


@pytest.mark.parametrize("p", [0.01, 0.05, 0.10])
@pytest.mark.parametrize("sigma", [1.0, 0.03])
def test_var_es_normal_zgodne_z_calka(p, sigma):
    q, es = var_es_normal(sigma, p)
    assert norm.cdf(q, scale=sigma) == pytest.approx(p, rel=1e-12)
    calka = quad(lambda x: x * norm.pdf(x, scale=sigma), -np.inf, q, epsabs=0, epsrel=1e-12)[0] / p
    assert es == pytest.approx(calka, rel=1e-8)
    assert es < q < 0


@pytest.mark.parametrize("nu", [3.0, 5.0, 8.0])
@pytest.mark.parametrize("p", [0.01, 0.05, 0.10])
@pytest.mark.parametrize("sigma", [1.0, 0.03])
def test_var_es_t_znormalizowane_zgodne_z_calka(nu, p, sigma):
    q, es = var_es_t(sigma, p, nu)
    skala = sigma * math.sqrt((nu - 2.0) / nu)  # wariancja σ², jak w generuj_panel
    assert student_t.cdf(q, nu, scale=skala) == pytest.approx(p, rel=1e-10)
    calka = (
        quad(
            lambda x: x * student_t.pdf(x, nu, scale=skala),
            -np.inf,
            q,
            epsabs=0,
            epsrel=1e-12,
            limit=500,
        )[0]
        / p
    )
    assert es == pytest.approx(calka, rel=1e-8)
    assert es < q < 0


def test_var_es_t_ma_wariancje_sigma2_i_tablice():
    nu = 5.0
    wariancja = quad(
        lambda x: x * x * student_t.pdf(x, nu, scale=math.sqrt(3 / 5)), -np.inf, np.inf
    )
    assert wariancja[0] == pytest.approx(1.0, rel=1e-8)
    sg = np.array([0.01, 0.02, 0.04])
    q, es = var_es_t(sg, 0.05, nu)
    q1, es1 = var_es_t(1.0, 0.05, nu)
    np.testing.assert_allclose(q, sg * q1)
    np.testing.assert_allclose(es, sg * es1)
    assert q.shape == (3,) and es.shape == (3,)


def test_var_es_walidacja():
    with pytest.raises(ValueError):
        var_es_t(1.0, 0.05, 2.0)
    with pytest.raises(ValueError):
        var_es_t(1.0, 0.05, 1.5)
    for p in (0.0, 1.0, 2.0):
        with pytest.raises(ValueError):
            var_es_normal(1.0, p)
        with pytest.raises(ValueError):
            var_es_t(1.0, p, 5.0)
    for s in (0.0, -1.0, np.nan):
        with pytest.raises(ValueError):
            var_es_normal(s, 0.05)
    with pytest.raises(ValueError):
        losuj_innowacje(np.random.default_rng(0), 5, "t")  # brak nu


@pytest.mark.parametrize("rodzina,nu", [("normal", None), ("t", 5.0)])
def test_wzory_zgodne_z_losowaniem(rodzina, nu):
    """Niezależna weryfikacja wzorów: częstość i średnia ogona w próbie 2 mln innowacji."""
    p = 0.05
    e = losuj_innowacje(np.random.default_rng(1), 2_000_000, rodzina, nu)
    q, es = var_es_normal(1.0, p) if rodzina == "normal" else var_es_t(1.0, p, nu)
    ogon = e[e < q]
    assert len(ogon) / len(e) == pytest.approx(p, abs=4 * math.sqrt(p * (1 - p) / len(e)))
    assert ogon.mean() == pytest.approx(es, abs=4 * ogon.std() / math.sqrt(len(ogon)))


# --- własności (hypothesis) ----------------------------------------------------------------------

HITY = st.lists(st.booleans(), min_size=1, max_size=300)


@settings(max_examples=200, deadline=None)
@given(HITY, st.floats(0.001, 0.999))
def test_kupiec_lr_nieujemne_p_w_zakresie(h, p):
    o = kupiec_uc(h, p)
    assert o["LR"] >= 0.0 and 0.0 <= o["p_wartosc"] <= 1.0
    assert o["x"] == sum(h) and o["n"] == len(h)


@settings(max_examples=200, deadline=None)
@given(HITY.flatmap(lambda h: st.tuples(st.just(h), st.permutations(h))), st.floats(0.001, 0.999))
def test_kupiec_zalezy_tylko_od_liczby_trafien(para, p):
    h, perm = para
    assert kupiec_uc(h, p)["LR"] == kupiec_uc(list(perm), p)["LR"]


@settings(max_examples=100, deadline=None)
@given(st.integers(1, 9), st.integers(1, 40), st.integers(2, 10))
def test_kupiec_lr_zero_gdy_odsetek_rowny_p(a, m, b):
    a = 1 + (a - 1) % (b - 1)  # 1 ≤ a < b, więc p = a/b ∈ (0, 1)
    p = a / b
    h = np.zeros(b * m, dtype=bool)
    h[: a * m] = True
    o = kupiec_uc(h, p)
    assert o["odsetek"] == pytest.approx(p)
    assert o["LR"] == pytest.approx(0.0, abs=1e-9)


HITY2 = st.lists(st.booleans(), min_size=2, max_size=80)


def _ll_lancuch_petla(h, pi01: float, pi11: float) -> float:
    """Log-wiarygodność łańcucha 1. rzędu (warunkowa na h[0]) liczona pętlą po sekwencji."""
    ll = 0.0
    for wczoraj, dzis in pairwise(h):
        pi = pi11 if wczoraj else pi01
        ll += math.log(pi if dzis else 1.0 - pi)
    return ll


def _lr_petla(h, p: float) -> tuple[float, float, float]:
    """(LR_uc, LR_ind, LR_cc) z pętli po sekwencji — oracle niezależny od _przejscia i tabeli 2×2."""
    h = [bool(x) for x in h]
    n = {(a, b): 0 for a in (False, True) for b in (False, True)}
    for a, b in pairwise(h):
        n[a, b] += 1
    w0, w1 = n[False, False] + n[False, True], n[True, False] + n[True, True]
    pi01 = n[False, True] / w0 if w0 else 0.0
    pi11 = n[True, True] / w1 if w1 else 0.0
    pi = (n[False, True] + n[True, True]) / (w0 + w1)
    ll_mle = _ll_lancuch_petla(h, pi01, pi11)
    ll_pi = _ll_lancuch_petla(h, pi, pi)
    ll_h0 = _ll_lancuch_petla(h, p, p)
    return 2 * (ll_pi - ll_h0), 2 * (ll_mle - ll_pi), 2 * (ll_mle - ll_h0)


@settings(max_examples=300, deadline=None)
@given(HITY2, st.floats(0.01, 0.99))
def test_christoffersen_cc_zgodne_z_wiarygodnoscia_lancucha_liczona_petla(h, p):
    lr_uc, lr_ind, lr_cc = _lr_petla(h, p)
    c = christoffersen_cc(h, p)
    assert c["LR_uc"] == pytest.approx(lr_uc, abs=1e-9)
    assert c["LR_ind"] == pytest.approx(lr_ind, abs=1e-9)
    assert c["LR"] == pytest.approx(lr_cc, abs=1e-9)
    assert c["LR_uc"] == pytest.approx(kupiec_uc(h[1:], p)["LR"], abs=1e-9)  # próba I_2..I_n
    assert c["n_uc"] == len(h) - 1 and c["p_wartosc"] == pytest.approx(chi2.sf(c["LR"], 2))


@settings(max_examples=200, deadline=None)
@given(HITY2)
def test_christoffersen_ind_etykiety_przejsc_i_zgodnosc_z_g_tabeli(h):
    o = christoffersen_ind(h)
    assert o["n01"] + o["n11"] == sum(h[1:])  # trafienia „dziś” (próba I_2..I_n)
    assert o["n10"] + o["n11"] == sum(h[:-1])  # trafienia „wczoraj”
    assert o["n01"] - o["n10"] == h[-1] - h[0]
    assert o["n00"] + o["n01"] + o["n10"] + o["n11"] == len(h) - 1
    c = christoffersen_cc(h, 0.1)
    assert c["ind_niezdefiniowany"] == o["niezdefiniowany"]
    if not o["niezdefiniowany"]:
        tab = [[o["n00"], o["n01"]], [o["n10"], o["n11"]]]
        g = chi2_contingency(tab, correction=False, lambda_="log-likelihood")[0]
        assert o["LR"] == pytest.approx(g, abs=1e-9) and 0.0 <= o["p_wartosc"] <= 1.0
    else:
        assert math.isnan(o["LR"]) and math.isnan(o["p_wartosc"])


@settings(max_examples=200, deadline=None)
@given(HITY, st.floats(0.001, 0.999))
def test_christoffersen_cc_okreslony_dla_n_co_najmniej_2(h, p):
    c = christoffersen_cc(h, p)
    assert c["niezdefiniowany"] == (len(h) < 2)
    if len(h) >= 2:
        assert c["LR"] >= 0.0 and 0.0 <= c["p_wartosc"] <= 1.0


@settings(max_examples=150, deadline=None)
@given(HITY)
def test_christoffersen_ind_symetria_wzgledem_odwrocenia_czasu(h):
    """Odwrócenie czasu transponuje tabelę przejść, a G tabeli 2×2 jest symetryczne."""
    a, b = christoffersen_ind(h), christoffersen_ind(h[::-1])
    assert a["niezdefiniowany"] == b["niezdefiniowany"]
    if not a["niezdefiniowany"]:
        assert a["LR"] == pytest.approx(b["LR"], abs=1e-9)


# --- lekkie kontrole R8 (pełne: symulacje/run_kv1.py) --------------------------------------------

N_R8, K_R8 = 10_000, 300


@pytest.fixture(scope="module")
def panel_r8():
    p = generuj_panel(N_R8, K_R8, seed=2026, nu=5.0, rho=0.0)  # ρ = 0: serie niezależne
    return p["r"].to_numpy(), np.sqrt(p["sigma2"].to_numpy())


@pytest.fixture(scope="module")
def h0_r8():
    return {
        (p, fam): as_z2_h0_polozenie_skala(N_R8, p, fam, 5.0 if fam == "t" else None, 2000, seed=s)
        for s, (p, fam) in enumerate([(0.01, "t"), (0.01, "normal"), (0.05, "t")], start=1)
    }


def _odsetki(r, s, p, prognoza, h0):
    """Odsetek odrzuceń na 5 % dla każdego testu po K_R8 seriach (NaN = brak odrzucenia)."""
    kup, ind, cc, z2, hit = [], [], [], [], []
    for j in range(r.shape[1]):
        q, es = prognoza(s[:, j])
        h = r[:, j] < q
        kup.append(kupiec_uc(h, p)["p_wartosc"])
        ind.append(christoffersen_ind(h)["p_wartosc"])
        cc.append(christoffersen_cc(h, p)["p_wartosc"])
        z2.append(as_z2_pwartosc(as_z2(r[:, j], q, es, p), h0))
        hit.append(h.mean())
    odrz = {
        k: float((np.array(v) < 0.05).mean())
        for k, v in zip(("kupiec", "ind", "cc", "z2"), (kup, ind, cc, z2), strict=True)
    }
    return odrz, float(np.mean(hit))


def test_r8_negatywna_prawdziwe_var_es_nie_sa_odrzucane(panel_r8, h0_r8):
    """Prawdziwe q/es z σ² generatora (t5): odsetek odrzuceń ≈ 5 % (300 serii, SE ≈ 1,3 pp)."""
    r, s = panel_r8
    odrz5, hit5 = _odsetki(r, s, 0.05, lambda sg: var_es_t(sg, 0.05, 5.0), h0_r8[(0.05, "t")])
    for nazwa, v in odrz5.items():
        assert 0.015 <= v <= 0.10, (nazwa, v)
    assert hit5 == pytest.approx(0.05, abs=0.001)
    odrz1, hit1 = _odsetki(r, s, 0.01, lambda sg: var_es_t(sg, 0.01, 5.0), h0_r8[(0.01, "t")])
    for nazwa in ("kupiec", "z2"):  # przy p = 1 % i n = 10 000 test ind nie ma jeszcze rozmiaru
        assert 0.01 <= odrz1[nazwa] <= 0.10, (nazwa, odrz1[nazwa])
    assert hit1 == pytest.approx(0.01, abs=0.0004)


def test_r8_pozytywna_normalne_var_es_przy_prawdzie_t5_sa_odrzucane(panel_r8, h0_r8):
    r, s = panel_r8
    odrz, hit = _odsetki(r, s, 0.01, lambda sg: var_es_normal(sg, 0.01), h0_r8[(0.01, "normal")])
    assert odrz["kupiec"] >= 0.8 and odrz["z2"] >= 0.8, odrz
    assert odrz["cc"] >= 0.8, odrz  # R8: cc ma składnik pokrycia (sam ind miałby tu ok. 5 %)
    assert hit > 0.013  # trafienia częstsze niż 1 % (analitycznie 1,50 %)


def test_r8_pozytywna_stale_sigma_przy_garch_lamie_niezaleznosc(panel_r8):
    r, _ = panel_r8
    q = var_es_t(0.04, 0.05, 5.0)[0]
    pw = np.array([christoffersen_ind(r[:, j] < q)["p_wartosc"] for j in range(r.shape[1])])
    assert (pw < 0.05).mean() >= 0.8


def test_r8_pozytywna_za_niskie_es_przy_dobrym_var_wykrywa_z2(panel_r8, h0_r8):
    """q prawdziwe, es ok. 13 % za nisko (E[Z2] = −0,15): Z2 odrzuca, a Kupiec nie ma powodu."""
    r, s = panel_r8
    qn, en = var_es_normal(1.0, 0.05)

    def prognoza(sg):
        q, _ = var_es_t(sg, 0.05, 5.0)
        return q, q * (en / qn)

    odrz, _ = _odsetki(r, s, 0.05, prognoza, h0_r8[(0.05, "t")])
    assert odrz["z2"] >= 0.8 and odrz["kupiec"] <= 0.10, odrz


def test_r8_sciezka_ogolna_z2_prawdziwy_model_nie_odrzucany_zla_prognoza_odrzucana(panel_r8):
    """Ścieżka `as_z2_pwartosc_ogolna` (dla prognoz nie typu położenie–skala), p = 1 %, n = 5 000."""
    r, s = panel_r8
    p, n, k = 0.01, 5000, 30
    odrz_zla, odrz_prawdziwa = [], []
    for j in range(k):
        sg, rj = s[:n, j], r[:n, j]
        qn, en = var_es_normal(sg, p)  # prognoza normalna z samplerem normalnym, prawda t5
        zla = as_z2_pwartosc_ogolna(rj, qn, en, p, _sampler_sigma(sg), 300, seed=j)
        odrz_zla.append(zla["p_wartosc"] < 0.05)
        qt, et = var_es_t(sg, p, 5.0)  # prawdziwy model (sampler t5)

        def los_t(g, m, sg=sg):
            return sg[None, :] * losuj_innowacje(g, (m, len(sg)), "t", 5.0)

        prawdziwa = as_z2_pwartosc_ogolna(rj, qt, et, p, los_t, 300, seed=1000 + j)
        odrz_prawdziwa.append(prawdziwa["p_wartosc"] < 0.05)
    assert np.mean(odrz_zla) >= 0.8, np.mean(odrz_zla)
    assert np.mean(odrz_prawdziwa) <= 0.20, np.mean(odrz_prawdziwa)  # 30 serii, SE ≈ 4 pp


# --- logika decyzyjna KV1 (symulacje/run_kv1.py::_kryteria) ---------------------------------------

N_SERII = 5000
PROGNOZY_KV1 = ("prawdziwa", "normalna", "stala", "es_za_niski")
# komórka (poziom, prognoza, test) → numer kryterium z README (1-based); inne komórki to tylko opis
NUMERY_KRYTERIOW = {
    **{(0.01, "prawdziwa", t): i for i, t in enumerate(TESTY, start=1)},
    **{(0.05, "prawdziwa", t): i for i, t in enumerate(TESTY, start=5)},
    (0.01, "normalna", "kupiec"): 11,
    (0.05, "normalna", "kupiec"): 12,
    (0.01, "normalna", "z2"): 13,
    (0.01, "stala", "ind"): 14,
    (0.05, "stala", "ind"): 15,
    (0.01, "es_za_niski", "z2"): 16,
    (0.05, "es_za_niski", "z2"): 17,
    (0.01, "normalna", "cc"): 18,
    (0.05, "normalna", "cc"): 19,
}


def _seria_p(odrzucenia: int, nan: int = 0) -> np.ndarray:
    """N_SERII p-wartości: dokładnie `odrzucenia` poniżej 5 %, `nan` niezdefiniowanych, reszta 0,5."""
    return np.r_[
        np.full(odrzucenia, 0.01), np.full(nan, np.nan), np.full(N_SERII - odrzucenia - nan, 0.5)
    ]


def _wyniki_idealne() -> dict:
    """Prawdziwa prognoza ≈ 5 % odrzuceń (i bez NaN), każda błędna 100 % odrzuceń."""
    return {
        p: {
            f: {t: _seria_p(250 if f == "prawdziwa" else N_SERII) for t in TESTY}
            for f in PROGNOZY_KV1
        }
        for p in POZIOMY
    }


def _nie_ok(kr) -> list[int]:
    return [i for i, c in enumerate(kr, start=1) if not c["ok"]]


def test_kv1_kryteria_19_w_grupach_i_idealne_wyniki_je_spelniaja():
    kr = _kryteria(_wyniki_idealne())
    assert len(kr) == 19 and _nie_ok(kr) == []
    grupy = [c["grupa"] for c in kr]
    assert [grupy.count(g) for g in ("NEGATYWNA", "POZYTYWNA 1", "POZYTYWNA 2", "POZYTYWNA 3")] == [
        10,
        3,
        2,
        2,
    ]
    assert grupy.count("POZYTYWNA 4") == 2
    assert all(c["n"] == N_SERII for c in kr)


@pytest.mark.parametrize(
    "komorka", [(p, f, t) for p in POZIOMY for f in PROGNOZY_KV1 for t in TESTY]
)
def test_kv1_kazda_komorka_psuje_dokladnie_swoje_kryterium_albo_zadne(komorka):
    """Okablowanie prognoza/test → numer kryterium z README; komórki opisowe nie wpływają na werdykt."""
    p, f, t = komorka
    wyn = _wyniki_idealne()
    wyn[p][f][t] = _seria_p(
        0 if f != "prawdziwa" else 1000
    )  # błędna: 0 % odrzuceń; prawdziwa: 20 %
    oczekiwane = [NUMERY_KRYTERIOW[komorka]] if komorka in NUMERY_KRYTERIOW else []
    assert _nie_ok(_kryteria(wyn)) == oczekiwane


@pytest.mark.parametrize(
    "odrzucenia,ok",
    [(124, False), (125, True), (375, True), (376, False)],  # pasmo [2,5 %; 7,5 %] z 5 000 serii
)
def test_kv1_granice_kontroli_negatywnej(odrzucenia, ok):
    wyn = _wyniki_idealne()
    wyn[0.05]["prawdziwa"]["kupiec"] = _seria_p(odrzucenia)
    assert (5 not in _nie_ok(_kryteria(wyn))) is ok


@pytest.mark.parametrize("odrzucenia,ok", [(3999, False), (4000, True)])  # próg 80 % z 5 000 serii
def test_kv1_granica_mocy_i_nan_to_brak_odrzucenia(odrzucenia, ok):
    wyn = _wyniki_idealne()
    wyn[0.01]["stala"]["ind"] = _seria_p(odrzucenia, nan=N_SERII - odrzucenia)
    assert (14 not in _nie_ok(_kryteria(wyn))) is ok  # NaN nie liczy się jako odrzucenie


@pytest.mark.parametrize("nan,ok", [(50, True), (51, False)])  # udział niezdefiniowanych ≤ 1 %
@pytest.mark.parametrize("p,nr_nan,nr_ind", [(0.01, 9, 2), (0.05, 10, 6)])
def test_kv1_granica_udzialu_niezdefiniowanych_ind_osobno_dla_kazdego_p(p, nr_nan, nr_ind, nan, ok):
    """Kryterium #9 patrzy tylko na p = 1 %, #10 tylko na p = 5 % (nie mylą się nawzajem)."""
    wyn = _wyniki_idealne()
    wyn[p]["prawdziwa"]["ind"] = _seria_p(250, nan=nan)  # odsetek odrzuceń ind bez zmian
    nie_ok = _nie_ok(_kryteria(wyn))
    assert nie_ok == ([] if ok else [nr_nan]) and nr_ind not in nie_ok


def test_kv1_p_wartosc_rowna_alfa_nie_jest_odrzuceniem():
    """Odrzucenie to ostra nierówność p < ALFA; p-wartość równa ALFA nie jest odrzuceniem."""
    wyn = _wyniki_idealne()
    # 124 odrzuceń + 1 p-wartość dokładnie ALFA: z ostrą nierównością 2,48 % (poza pasmem), z ≤ 2,50 %
    wyn[0.05]["prawdziwa"]["kupiec"] = np.r_[np.full(124, 0.01), np.full(N_SERII - 124, ALFA)]
    assert _nie_ok(_kryteria(wyn)) == [5]
    # moc: 3999 odrzuceń + 1 p-wartość dokładnie ALFA daje 79,98 %, a nie 80 %
    wyn = _wyniki_idealne()
    wyn[0.01]["stala"]["ind"] = np.r_[np.full(3999, 0.01), np.full(1, ALFA), np.full(1000, 0.5)]
    assert _nie_ok(_kryteria(wyn)) == [14]
