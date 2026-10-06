"""Testy laboratorium LV2 (symulacje/garch_t.py, prognozy_lv2.py, porownanie_lv2.py, run_lv2.py):
ręczne wzory strat, wartości oczekiwane (wzory zamknięte kontra kwadratura), własny estymator GARCH-t
kontra pakiet `arch`, brak wglądu w przyszłość w prognozach (R7), własności (`hypothesis`), mikro-kontrole
R8, determinizm względem liczby procesów, okablowanie reguł i zamrożenie konfiguracji z pre-rejestracji.
"""

from __future__ import annotations

import math
import warnings

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from scipy.integrate import quad
from scipy.stats import t as student_t

import symulacje.garch_t as gt
import symulacje.moc_var_es as mv
import symulacje.porownanie_lv2 as pl
import symulacje.prognozy_lv2 as pz
import symulacje.run_lv2 as lv2
from miara.dm import newey_west_lag
from miara.var_es import var_es_t
from symulacje.garch_panel import generuj_panel

P = 0.05

# --- straty: wzory ręczne ---------------------------------------------------------------------------


def test_fz0_wartosc_reczna_gdy_jest_trafienie():
    v, e, r = -0.02, -0.03, -0.04  # r ≤ v: składnik z trafieniem (v − r)/(p·|e|) = 13,3333
    oczekiwana = (v - r) / (P * -e) + v / e + math.log(-e) - 1.0
    assert pl.fz0(v, e, r, P) == pytest.approx(oczekiwana, abs=1e-12)
    assert pl.fz0(v, e, r, P) == pytest.approx(9.4934421, abs=1e-6)


def test_fz0_wartosc_reczna_bez_trafienia_i_na_granicy():
    v, e = -0.02, -0.03
    bez = v / e + math.log(-e) - 1.0  # 0,666667 − 3,506558 − 1
    assert pl.fz0(v, e, -0.01, P) == pytest.approx(-3.8398912, abs=1e-6)
    assert pl.fz0(v, e, 0.07, P) == pytest.approx(bez, abs=1e-12)
    assert pl.fz0(v, e, v, P) == pytest.approx(bez, abs=1e-12)  # r = v: strata ciągła


def test_fz0_odrzuca_dodatnie_var_i_es():
    with pytest.raises(ValueError, match="ujemne"):
        pl.fz0(0.01, -0.03, -0.02, P)
    with pytest.raises(ValueError, match="ujemne"):
        pl.fz0(-0.02, 0.0, -0.02, P)


def test_pinball_wartosci_reczne_i_strzalka_trafienia():
    v = -0.02
    assert pl.pinball(v, -0.03, P) == pytest.approx((P - 1.0) * (-0.01), abs=1e-15)  # 0,0095
    assert pl.pinball(v, 0.01, P) == pytest.approx(P * 0.03, abs=1e-15)  # 0,0015
    assert pl.pinball(v, v, P) == 0.0  # trafienie jest ostre (r < v), a strata i tak 0
    assert pl.pinball(v, -0.03, P) == pytest.approx(0.0095, abs=1e-15)


def test_roznica_fz0_nie_zalezy_od_wspolnej_skali():
    """Człon log(−e) skraca się w różnicy dwóch prognoz: wspólna skala zwrotu i prognoz nie ma wpływu."""
    rng = np.random.default_rng(3)
    r = rng.standard_normal(200) * 0.02
    v1, e1 = np.full(200, -0.030), np.full(200, -0.040)
    v2, e2 = np.full(200, -0.022), np.full(200, -0.031)
    d = pl.fz0(v1, e1, r, P) - pl.fz0(v2, e2, r, P)
    for k in (0.001, 7.0, 1e4):
        dk = pl.fz0(k * v1, k * e1, k * r, P) - pl.fz0(k * v2, k * e2, k * r, P)
        np.testing.assert_allclose(dk, d, atol=1e-9)


def test_straty_dzienne_srednia_po_monetach_i_waga_pinball():
    rng = np.random.default_rng(4)
    r = rng.standard_normal((6, 3)) * 0.02
    q, es = var_es_t(np.full((6, 3), 0.02), P, 5.0)
    waga = 0.01 + 0.02 * rng.random((6, 3))
    s = pl.straty_dzienne(r, q, es, P, waga)
    assert s.keys() == {"fz0", "pinb"}
    for t in range(6):
        fz = [pl.fz0(q[t, j], es[t, j], r[t, j], P) for j in range(3)]
        pb = [pl.pinball(q[t, j], r[t, j], P) / waga[t, j] for j in range(3)]
        assert s["fz0"][t] == pytest.approx(np.mean(fz), abs=1e-12)
        assert s["pinb"][t] == pytest.approx(np.mean(pb), abs=1e-12)
    with pytest.raises(ValueError, match="dodatnia"):
        pl.straty_dzienne(r, q, es, P, np.zeros((6, 3)))


# --- wartości oczekiwane pod prawdziwym t_ν: wzór zamknięty kontra kwadratura ----------------------


def _strata_calkowana(c: float, p: float, nu: float, strata: str) -> float:
    """E[strata] prognozy c·(VaR*, ES*) przy innowacjach t_ν o wariancji 1 — całkowanie numeryczne."""
    s = math.sqrt((nu - 2.0) / nu)
    v0, e0 = (float(x) for x in var_es_t(1.0, p, nu))
    v, e = c * v0, c * e0

    def gestosc(x: float) -> float:
        return float(student_t.pdf(x / s, nu)) / s

    if strata == "fz0":

        def f(x: float) -> float:
            return float(pl.fz0(v, e, x, p)) * gestosc(x)

    else:

        def f(x: float) -> float:
            return float(pl.pinball(v, x, p)) * gestosc(x)

    opcje = {"epsabs": 1e-13, "epsrel": 1e-11, "limit": 400}
    return quad(f, -np.inf, v, **opcje)[0] + quad(f, v, np.inf, **opcje)[0]


@pytest.mark.parametrize("strata", pl.STRATY)
@pytest.mark.parametrize("p", [0.01, 0.05])
@pytest.mark.parametrize("c", [0.7, 1.0, 1.3])
def test_oczekiwana_strata_zgodna_z_kwadratura(strata, p, c):
    assert pl.oczekiwana_strata(c, p, 5.0, strata) == pytest.approx(
        _strata_calkowana(c, p, 5.0, strata), abs=1e-7
    )


@pytest.mark.parametrize("strata", pl.STRATY)
@pytest.mark.parametrize("p", [0.01, 0.05])
def test_prawdziwa_prognoza_ma_najmniejsza_oczekiwana_strate(strata, p):
    """Obie straty są prawidłowe: minimum wartości oczekiwanej na c = 1 (mnożnik prawdziwej prognozy)."""
    e1 = pl.oczekiwana_strata(1.0, p, 5.0, strata)
    for c in (0.5, 0.8, 0.9, 0.99, 1.01, 1.1, 1.3, 2.0):
        assert pl.oczekiwana_strata(c, p, 5.0, strata) > e1


def test_oczekiwana_strata_odrzuca_zle_argumenty():
    with pytest.raises(ValueError, match="c > 0"):
        pl.oczekiwana_strata(0.0, P, 5.0, "fz0")
    with pytest.raises(ValueError, match="strata"):
        pl.oczekiwana_strata(1.0, P, 5.0, "mse")


@pytest.mark.parametrize("strata", pl.STRATY)
@pytest.mark.parametrize("p", [0.01, 0.05])
@pytest.mark.parametrize("c_a", lv2.C_ZERO)
def test_para_dokladnie_zerowa_ma_rowne_oczekiwane_straty(strata, p, c_a):
    c_b = pl.mnoznik_zerowy(c_a, p, 5.0, strata)
    assert c_a < 1.0 < c_b < 5.0  # druga gałąź paraboli straty
    assert pl.oczekiwana_strata(c_b, p, 5.0, strata) == pytest.approx(
        pl.oczekiwana_strata(c_a, p, 5.0, strata), abs=1e-10
    )
    assert _strata_calkowana(c_b, p, 5.0, strata) == pytest.approx(
        _strata_calkowana(c_a, p, 5.0, strata), abs=1e-7
    )


# --- test Diebolda–Mariano na dziennych różnicach strat -----------------------------------------


def _dm_reczny(d: np.ndarray) -> tuple[float, float]:
    """(t, se) z Newey–West napisanego od nowa: jądro Bartletta, opóźnienie ⌊4 (n/100)^{2/9}⌋."""
    n = len(d)
    lag = math.floor(4.0 * (n / 100.0) ** (2.0 / 9.0))
    dc = d - d.mean()
    gam = [float(np.dot(dc[k:], dc[: n - k])) / n for k in range(lag + 1)]
    s = gam[0] + 2.0 * sum((1.0 - k / (lag + 1.0)) * gam[k] for k in range(1, lag + 1))
    se = math.sqrt(s / n)
    return float(d.mean()) / se, se


def test_dm_wektor_zgodny_z_wzorem_recznym():
    rng = np.random.default_rng(1)
    szum = rng.standard_normal(600) * 0.01
    d = 0.002 + szum + 0.5 * np.concatenate([[0.0], szum[:-1]])  # skorelowane: HAC ≠ zwykły
    t, se = _dm_reczny(d)
    w = pl.dm_wektor(d)
    assert w["t"] == pytest.approx(t, rel=1e-10)
    assert w["se"] == pytest.approx(se, rel=1e-10)
    assert w["srednia"] == pytest.approx(d.mean(), rel=1e-12)


def test_dm_wektor_znak_dodatnie_t_oznacza_ze_b_lepsza():
    rng = np.random.default_rng(2)
    d = 0.01 + 0.02 * rng.standard_normal(400)  # A − B > 0: A ma większą stratę
    assert pl.dm_wektor(d)["t"] > 5
    assert pl.dm_wektor(-d)["t"] < -5


def test_dm_wektor_stala_roznica_daje_nan_a_nie_blad():
    w = pl.dm_wektor(np.full(100, 0.3))
    assert math.isnan(w["t"]) and math.isnan(w["se"]) and w["srednia"] == pytest.approx(0.3)


def test_opoznienie_newey_west_jak_w_pre_rejestracji():
    assert newey_west_lag(1600) == newey_west_lag(1700) == 7


# --- własny estymator GARCH(1,1)-t -------------------------------------------------------------


def _seria_garch(
    n: int = 1500, seed: int = 5, omega: float = 2e-6, alpha: float = 0.08, beta: float = 0.90
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    eps = rng.standard_t(5.0, n) * math.sqrt(3.0 / 5.0)
    r, s2 = np.empty(n), omega / (1.0 - alpha - beta)
    for t in range(n):
        r[t] = math.sqrt(s2) * eps[t]
        s2 = omega + alpha * r[t] ** 2 + beta * s2
    return r


def test_filtr_sigma2_zgodny_z_rekurencja_reczna():
    x2 = np.array([4.0, 1.0, 0.25, 9.0, 0.0]) * 1e-4
    om, al, be, s0 = 2e-6, 0.1, 0.85, 3e-4
    wyn = gt.filtr_sigma2(x2, om, al, be, s0)
    oczek = [s0]
    for v in x2:
        oczek.append(om + al * v + be * oczek[-1])
    assert len(wyn) == len(x2) + 1  # σ²_0 … σ²_n; ostatnia = prognoza na dzień n
    np.testing.assert_allclose(wyn, oczek, rtol=1e-12)


def test_loglik_t_zgodna_z_logpdf_scipy():
    rng = np.random.default_rng(6)
    r = rng.standard_t(6.0, 300) * 0.02
    s2 = 0.0004 * (1.0 + 0.5 * rng.random(300))
    nu = 6.0
    skala = np.sqrt(s2 * (nu - 2.0) / nu)
    oczek = student_t.logpdf(r, nu, scale=skala).mean()
    assert gt.loglik_t(r * r, s2, nu) == pytest.approx(oczek, abs=1e-10)


def test_dopasowanie_odtwarza_parametry_generatora():
    f = gt.dopasuj_garch_t(_seria_garch(n=3000, seed=11))
    assert f.zbiezny and not f.brzeg
    assert 0.95 < f.alpha + f.beta < 0.995  # prawda 0,98
    assert 3.5 < f.nu < 8.0  # prawda 5
    assert 0.03 < f.alpha < 0.15 and 0.80 < f.beta < 0.96


def test_dopasowanie_zgodne_z_pakietem_arch_przy_tym_samym_backcast():
    arch = pytest.importorskip("arch")
    for seed in (21, 22, 23):
        x = _seria_garch(n=900, seed=seed)
        f = gt.dopasuj_garch_t(x)
        am = arch.arch_model(x * 100.0, mean="Zero", vol="GARCH", p=1, q=1, dist="t")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = am.fit(disp="off", backcast=float(np.mean((x * 100.0) ** 2)))
        n = len(x)
        # moja log-wiarygodność jest liczona na zmiennej bez skali (r²/backcast): dodajemy jakobian
        ll_moja = -f.nll * n - 0.5 * n * math.log(f.backcast * 1e4)
        assert abs(ll_moja - res.loglikelihood) < 0.02, (seed, ll_moja, res.loglikelihood)
        assert abs((f.alpha + f.beta) - (res.params["alpha[1]"] + res.params["beta[1]"])) < 0.02
        assert abs(f.nu - res.params["nu"]) / res.params["nu"] < 0.10


def test_cieply_start_daje_to_samo_optimum_co_zimny():
    x = _seria_garch(n=1100, seed=31)
    poprzednie = gt.dopasuj_garch_t(x[:900])
    cieple = gt.dopasuj_garch_t(x[:1000], start=poprzednie)
    zimne = gt.dopasuj_garch_t(x[:1000])
    assert cieple.zbiezny and zimne.zbiezny
    assert abs(cieple.nll - zimne.nll) < 1e-6
    assert abs((cieple.alpha + cieple.beta) - (zimne.alpha + zimne.beta)) < 0.01


def test_zepsuty_cieply_start_wraca_do_startow_zimnych():
    x = _seria_garch(n=1000, seed=32)
    zimne = gt.dopasuj_garch_t(x)
    zly = zimne._replace(omega=1e-12, alpha=0.0005, beta=gt.P_MAX - 0.0005, nu=99.0)
    f = gt.dopasuj_garch_t(x, start=zly)
    assert f.zbiezny and abs(f.nll - zimne.nll) < 1e-5


def test_dopasowanie_nie_zalezy_od_jednostek_zwrotu():
    x = _seria_garch(n=800, seed=33)
    a, b = gt.dopasuj_garch_t(x), gt.dopasuj_garch_t(1000.0 * x)
    assert b.alpha == pytest.approx(a.alpha, rel=1e-5)  # różnica = szum zatrzymania optymalizatora
    assert b.beta == pytest.approx(a.beta, rel=1e-5)
    assert b.nu == pytest.approx(a.nu, rel=1e-5)
    assert b.omega == pytest.approx(a.omega * 1e6, rel=1e-4)


def test_dopasowanie_jest_deterministyczne():
    x = _seria_garch(n=700, seed=34)
    assert gt.dopasuj_garch_t(x) == gt.dopasuj_garch_t(x)


@pytest.mark.parametrize(
    "x",
    [np.zeros(200), np.full(50, 0.01), np.array([0.01] * 150 + [np.nan]), np.ones((150, 2)) * 0.01],
)
def test_dopasowanie_odrzuca_zle_dane(x):
    with pytest.raises(ValueError):
        gt.dopasuj_garch_t(x)


@given(st.floats(-20.0, 3.0), st.floats(-6.0, 9.2), st.floats(-8.0, 8.0), st.floats(-0.69, 4.58))
@settings(max_examples=200, deadline=None)
def test_parametryzacja_daje_stacjonarny_garch_i_odwraca_sie(om, pers, udzial, lnu):
    theta = np.array([om, pers, udzial, lnu])
    omega, alpha, beta, nu = gt._parametry(theta)
    assert omega > 0 and alpha > 0 and beta > 0
    assert alpha + beta < 1.0 and alpha + beta <= gt.P_MAX + 1e-12
    assert nu > 2.0
    np.testing.assert_allclose(gt._theta(omega, alpha, beta, nu), theta, atol=1e-5)


# --- prognozy estymowane: struktura, brak wglądu w przyszłość (R7), zagnieżdżenie --------------------

N_MIKRO, START_MIKRO, K_MIKRO = 520, 400, 3  # 120 dni oceny = 4 bloki po 30 dni


@pytest.fixture(scope="module")
def panel_mikro():
    return generuj_panel(N_MIKRO, K_MIKRO, seed=2026, rho=0.8)


@pytest.fixture(scope="module")
def zrodla_mikro(panel_mikro):
    return pz.zbuduj_zrodla(panel_mikro, start=START_MIKRO)


def _przytnij(panel: dict, n: int | None = None, k: int | None = None) -> dict:
    return {nazwa: df.iloc[:n, :k].copy() for nazwa, df in panel.items()}


def _rowne(a: pz.Zrodla, b: pz.Zrodla, wiersze: slice, pomin_ogon_ep: bool = False) -> None:
    """Wszystkie źródła σ i ogony zgodne co do bitu na wskazanych wierszach okresu oceny."""
    np.testing.assert_array_equal(a.r[wiersze], b.r[wiersze])
    assert a.sigma.keys() == b.sigma.keys()
    for z in a.sigma:
        np.testing.assert_array_equal(a.sigma[z][wiersze], b.sigma[z][wiersze], err_msg=z)
    for klucz in a.ogon:
        if pomin_ogon_ep and klucz[1] == "ep":
            continue
        for i in (0, 1):
            np.testing.assert_array_equal(
                a.ogon[klucz][i][wiersze], b.ogon[klucz][i][wiersze], err_msg=str(klucz)
            )


def test_zrodla_ksztalt_klucze_i_dodatnie_sigmy(zrodla_mikro, panel_mikro):
    zr, n_oos = zrodla_mikro, N_MIKRO - START_MIKRO
    assert zr.r.shape == (n_oos, K_MIKRO)
    np.testing.assert_array_equal(zr.r, panel_mikro["r"].to_numpy()[START_MIKRO:])
    assert set(zr.sigma) == {"wyr", "okno60", "ewma94", "garch", "har"}
    for z, s in zr.sigma.items():
        assert s.shape == (n_oos, K_MIKRO) and np.isfinite(s).all() and (s > 0).all(), z
    oczekiwane = {
        (z, t, p) for z in ("okno60", "ewma94", "garch") for t in ("ec", "ep") for p in pz.POZIOMY
    } | {("garch", "tnu", p) for p in pz.POZIOMY}
    assert set(zr.ogon) == oczekiwane
    for (z, t, p), (q, es) in zr.ogon.items():
        assert q.shape == es.shape == (n_oos, K_MIKRO)
        assert (q < 0).all() and (es <= q + 1e-12).all(), (z, t, p)


def test_diagnostyka_garch_liczy_dopasowania_wszystkich_blokow_i_monet(zrodla_mikro):
    d = zrodla_mikro.diag
    assert d["dopasowania"] == math.ceil((N_MIKRO - START_MIKRO) / pz.KROK) * K_MIKRO == 12
    assert 0 <= d["nie_zbiezne"] <= d["brzeg"] + d["dopasowania"]
    assert 0.5 < d["persystencja"] < 1.0 and 2.0 < d["nu"] < 100.0


def test_tabela_prognoz_i_podpanel():
    assert len(pz.PROGNOZY) == 19
    for nazwa, (zrodlo, mnoznik, ogon) in pz.PROGNOZY.items():
        assert zrodlo in {"wyr", "okno60", "ewma94", "garch", "har"} and 0 < mnoznik <= 1
        assert ogon in {"t5", "tnu", "ec", "ep"}, nazwa
    assert set(pz.PROGNOZY_PODPANEL) == {n for n, (_, _, o) in pz.PROGNOZY.items() if o != "ep"}
    assert not any(n.endswith("_ep") for n in pz.PROGNOZY_PODPANEL)


@pytest.mark.parametrize("p", pz.POZIOMY)
def test_wszystkie_prognozy_maja_es_nie_wyzej_niz_var_i_sa_ujemne(zrodla_mikro, p):
    for nazwa in pz.PROGNOZY:
        q, es = pz.prognoza(zrodla_mikro, nazwa, p)
        assert q.shape == zrodla_mikro.r.shape
        assert (q < 0).all() and (es <= q + 1e-12).all(), nazwa


@pytest.mark.parametrize("p", pz.POZIOMY)
def test_wyrocznia_zanizenia_i_mnozniki_prognoz(zrodla_mikro, panel_mikro, p):
    zr = zrodla_mikro
    q0, e0 = (float(x) for x in var_es_t(1.0, p, pz.NU))
    sigma = np.sqrt(panel_mikro["sigma2"].to_numpy()[START_MIKRO:])
    q, es = pz.prognoza(zr, "wyr_t5", p)
    np.testing.assert_allclose(q, sigma * q0, rtol=1e-12)
    np.testing.assert_allclose(es, sigma * e0, rtol=1e-12)
    for nazwa, x in pz.ZANIZENIA.items():
        qx, ex = pz.prognoza(zr, nazwa, p)
        np.testing.assert_allclose(qx, (1 - x) * q, rtol=1e-12)
        np.testing.assert_allclose(ex, (1 - x) * es, rtol=1e-12)
    for nazwa, x in (("garch_tnu_zan10", 0.10), ("garch_tnu_zan20", 0.20)):
        bazowa, _ = pz.prognoza(zr, "garch_tnu", p)
        np.testing.assert_allclose(pz.prognoza(zr, nazwa, p)[0], (1 - x) * bazowa, rtol=1e-12)
    for c in (1.0, 0.8):
        qc, ec = pz.prognoza_wyrocznia_skala(zr, c, p)
        np.testing.assert_allclose(qc, c * q, rtol=1e-12)
        np.testing.assert_allclose(ec, c * es, rtol=1e-12)
    with pytest.raises(ValueError, match="c > 0"):
        pz.prognoza_wyrocznia_skala(zr, 0.0, p)


def test_ogony_sa_stale_w_blokach_i_odswiezane_miedzy_blokami(zrodla_mikro):
    for klucz in (("garch", "tnu", 0.05), ("ewma94", "ec", 0.01), ("okno60", "ep", 0.05)):
        q, es = zrodla_mikro.ogon[klucz]
        for tab in (q, es):
            for b in range(0, 120, pz.KROK):
                blok = tab[b : b + pz.KROK]
                assert (blok == blok[0]).all(), (klucz, b)
        assert not np.allclose(q[0], q[pz.KROK]), klucz
        # ES (średnia kilku najgorszych reszt) zostaje, gdy nowe 30 dni nie wnosi nowych skrajności
        assert len({tuple(es[b]) for b in range(0, 120, pz.KROK)}) > 1, klucz


def test_ogon_zbiorczy_jest_wspolny_dla_monet_a_per_moneta_nie(zrodla_mikro):
    q_ep, _ = zrodla_mikro.ogon[("ewma94", "ep", 0.05)]
    q_ec, _ = zrodla_mikro.ogon[("ewma94", "ec", 0.05)]
    assert (q_ep == q_ep[:, [0]]).all()
    assert not (q_ec == q_ec[:, [0]]).all()


def test_ogon_empiryczny_wartosci_reczne():
    z = np.column_stack([np.arange(-10.0, 11.0), 2.0 * np.arange(-10.0, 11.0)])
    qk, esk, qz, esz = pz.ogon_empiryczny(z, 0.1)
    np.testing.assert_allclose(qk, [-8.0, -16.0])  # kwantyl 0,1 z 21 punktów = trzeci najmniejszy
    np.testing.assert_allclose(esk, [-9.0, -18.0])  # średnia z trzech najmniejszych
    wszystkie = np.sort(z.ravel())  # 42 punkty
    q_ref = float(np.quantile(wszystkie, 0.1))
    assert qz == pytest.approx(q_ref)
    assert esz == pytest.approx(wszystkie[wszystkie <= q_ref].mean())


@given(
    st.lists(st.floats(-8.0, 8.0), min_size=60, max_size=120),
    st.sampled_from([0.01, 0.05, 0.10]),
)
@settings(max_examples=80, deadline=None)
def test_ogon_empiryczny_es_nie_wyzej_niz_kwantyl(lista, p):
    z = np.column_stack([lista, np.array(lista)[::-1] * 1.5])
    qk, esk, qz, esz = pz.ogon_empiryczny(z, p)
    assert (esk <= qk + 1e-12).all() and esz <= qz + 1e-12


# R7: prognoza dnia t jest funkcją wyłącznie zwrotów (i RV) z dni < t ---------------------------------


def test_prognozy_nie_zalezą_od_przyszlosci_obciecie_panelu(panel_mikro, zrodla_mikro):
    """Prognozy na pierwsze 40 dni oceny liczone na panelu uciętym w dniu 440 = te same co na pełnym."""
    ucięty = _przytnij(panel_mikro, n=START_MIKRO + 40)
    zr_krotki = pz.zbuduj_zrodla(ucięty, start=START_MIKRO)
    assert zr_krotki.r.shape[0] == 40
    _rowne(zr_krotki, zrodla_mikro, slice(0, 40))


def test_zaburzenie_dnia_t_nie_zmienia_prognoz_na_dni_do_t_wlacznie(panel_mikro, zrodla_mikro):
    """Skrajny zwrot w dniu t zmienia σ dopiero od dnia t + 1, a ogony dopiero od następnego bloku."""
    i_gw = 45  # dzień oceny w środku drugiego bloku (dni 30–59)
    zab = _przytnij(panel_mikro)
    zab["r"].iloc[START_MIKRO + i_gw, :] = -0.5
    zab["rv"].iloc[START_MIKRO + i_gw, :] *= 16.0
    zr1, zr2 = zrodla_mikro, pz.zbuduj_zrodla(zab, start=START_MIKRO)
    for z in ("okno60", "ewma94", "garch", "har"):
        np.testing.assert_array_equal(zr1.sigma[z][: i_gw + 1], zr2.sigma[z][: i_gw + 1], err_msg=z)
        assert not np.allclose(zr1.sigma[z][i_gw + 1 :], zr2.sigma[z][i_gw + 1 :]), z
    np.testing.assert_array_equal(zr1.sigma["wyr"], zr2.sigma["wyr"])
    do_bloku_1 = slice(0, 2 * pz.KROK)
    blok_2 = slice(2 * pz.KROK, 3 * pz.KROK)  # pierwszy blok, którego ogon widzi zaburzony dzień
    for klucz in zr1.ogon:
        for i in (0, 1):
            np.testing.assert_array_equal(
                zr1.ogon[klucz][i][do_bloku_1], zr2.ogon[klucz][i][do_bloku_1], err_msg=str(klucz)
            )
        assert not np.allclose(zr1.ogon[klucz][0][blok_2], zr2.ogon[klucz][0][blok_2]), klucz


def test_podpanel_pierwszych_monet_to_to_samo_co_panel_z_tych_monet(panel_mikro, zrodla_mikro):
    """Monety są dla prognoz wymienne i niezależne: `pierwsze(k)` = zbudowanie źródeł na k monetach."""
    zr_k = zrodla_mikro.pierwsze(2)
    zr_ref = pz.zbuduj_zrodla(_przytnij(panel_mikro, k=2), start=START_MIKRO)
    assert not any(klucz[1] == "ep" for klucz in zr_k.ogon)
    assert zr_k.r.shape[1] == 2
    for klucz in zr_k.ogon:
        assert klucz in zr_ref.ogon
    for z in zr_k.sigma:
        np.testing.assert_array_equal(zr_k.sigma[z], zr_ref.sigma[z], err_msg=z)
    for klucz in zr_k.ogon:
        for i in (0, 1):
            np.testing.assert_array_equal(zr_k.ogon[klucz][i], zr_ref.ogon[klucz][i])


def test_zbuduj_zrodla_odrzuca_zly_start(panel_mikro):
    with pytest.raises(ValueError, match="start"):
        pz.zbuduj_zrodla(panel_mikro, start=100)
    with pytest.raises(ValueError, match="start"):
        pz.zbuduj_zrodla(panel_mikro, start=N_MIKRO)


# --- silnik LV2: tabela porównań, statystyki komórki ----------------------------------------------------


def test_tabela_porownan_ma_36_unikalnych_kodow_o_rozwiazywalnych_prognozach():
    por = lv2.POROWNANIA
    assert len(por) == 36 == len({p["kod"] for p in por})
    liczba = {r: sum(p["rola"] == r for p in por) for r in ("zero", "moc", "wyr", "real")}
    assert liczba == {"zero": 4, "moc": 10, "wyr": 10, "real": 12}
    zero = {lv2._klucz_zerowy(s, c) for s in pl.STRATY for c in lv2.C_ZERO}
    for i, p in enumerate(por):
        assert lv2.POR_IDX[p["kod"]] == i and p["strata"] in pl.STRATY
        assert all(p[strona] in pz.PROGNOZY or p[strona] in zero for strona in ("a", "b")), p
        if (
            p["rola"] == "zero"
        ):  # A = wyrocznia × c_A, B = wyrocznia × c_B o tej samej oczekiwanej stracie
            c_a = {"90": 0.9, "80": 0.8}[p["kod"].rsplit("_", 1)[1]]
            assert pz.PROGNOZY[p["a"]][1] == pytest.approx(c_a)
            assert p["b"] == lv2._klucz_zerowy(p["strata"], c_a)
        elif p["rola"] == "moc":
            assert p["b"] == "wyr_t5" and pz.PROGNOZY[p["a"]][0] == "wyr"
        elif p["rola"] == "wyr":
            assert p["b"] == "wyr_t5" and p["a"] in lv2.ESTYMOWANE
    pary = {(p["a"], p["b"]) for p in por if p["rola"] == "real" and p["strata"] == "fz0"}
    assert pary == set(lv2.PARY_REALNE)


def test_klucz_zerowy_i_c_zerowe_sa_zgodne_z_mnoznikiem_zerowym():
    assert lv2._klucz_zerowy("fz0", 0.9) == "nul_fz0_90"
    assert lv2._klucz_zerowy("pinb", 0.8) == "nul_pinb_80"
    lv2._c_zerowe.cache_clear()
    c_b = lv2._c_zerowe("fz0", 0.9, 0.05)
    assert c_b == pl.mnoznik_zerowy(0.9, 0.05, 5.0, "fz0") and c_b > 1.0
    assert lv2._c_zerowe("fz0", 0.9, 0.05) == c_b and lv2._c_zerowe.cache_info().hits == 1


def _dane_t5(seed: int, n: int = 300, k: int = 5, p: float = 0.05, c: float = 1.0):
    """Zwroty t5 o σ = 0,02 i prognoza t5 ze σ pomnożonym przez c (c < 1: za płytko, c > 1: za głęboko)."""
    rng = np.random.default_rng(seed)
    r = rng.standard_t(5, size=(n, k)) * 0.02 * math.sqrt(3 / 5)
    q, es = var_es_t(np.full((n, k), 0.02 * c), p, 5.0)
    return r, q, es


def test_statystyki_komorki_czytaja_pola_zgodnie_z_definicjami():
    n, k, p = 300, 5, 0.05
    r, q, es = _dane_t5(3, n, k, p)
    r[0, 0] = q[0, 0]  # remis nie jest trafieniem (ścisła nierówność, jak w miarze)
    idx = np.random.default_rng(1).integers(0, n, size=(99, n))
    w = lv2.statystyki_komorki(r, q, es, p, idx)
    assert w.shape == (len(lv2.STAT),)
    trafienia = r < q
    assert not trafienia[0, 0] and w[lv2.IDX["hit"]] == trafienia.mean()
    u = np.where(trafienia, r / es, 0.0) / p
    assert w[lv2.IDX["u_sr"]] == pytest.approx(u.mean(), rel=1e-12)
    suma_dnia = trafienia.sum(axis=1)
    assert w[lv2.IDX["vr"]] == pytest.approx(suma_dnia.var(ddof=1) / (k * p * (1 - p)), rel=1e-12)
    zb = mv.testy_zbiorcze(r, q, es, p, idx)
    prog = lv2.ALFA / 3
    skladniki = [w[lv2.IDX[n_]] for n_ in ("zb_a", "zb_b", "zb_c")]
    assert skladniki == [float(zb[f"p_{x}"] < prog) for x in "abc"]
    assert w[lv2.IDX["zb_bonf"]] == float(min(zb["p_a"], zb["p_b"], zb["p_c"]) < prog)
    assert w[lv2.IDX["niezdef"]] == 0.0


def test_zb_a_prawa_odrzuca_tylko_przy_zbyt_wielu_trafieniach():
    n, k, p = 400, 5, 0.05
    # dwustronna p-wartość bootstrapu ma minimum 2/(B + 1): przy B = 99 nie zejdzie poniżej α/3
    idx = np.random.default_rng(2).integers(0, n, size=(399, n))
    za_malo = lv2.statystyki_komorki(*_dane_t5(4, n, k, p, c=1.8), p, idx)  # VaR za głęboko
    za_duzo = lv2.statystyki_komorki(*_dane_t5(4, n, k, p, c=0.5), p, idx)  # VaR za płytko
    assert za_malo[lv2.IDX["zb_a"]] == za_duzo[lv2.IDX["zb_a"]] == 1.0
    assert za_malo[lv2.IDX["zb_a_prawa"]] == 0.0 and za_duzo[lv2.IDX["zb_a_prawa"]] == 1.0
    assert za_duzo[lv2.IDX["hit"]] > p > za_malo[lv2.IDX["hit"]]


def test_statystyki_komorki_bez_trafien_to_niezdefiniowane_a_nie_odrzucenie():
    n, k, p = 100, 4, 0.05
    r, q, es = np.full((n, k), 0.01), np.full((n, k), -0.05), np.full((n, k), -0.08)
    idx = np.random.default_rng(0).integers(0, n, size=(19, n))
    w = lv2.statystyki_komorki(r, q, es, p, idx)
    assert w[lv2.IDX["hit"]] == w[lv2.IDX["u_sr"]] == w[lv2.IDX["vr"]] == 0.0
    assert w[lv2.IDX["niezdef"]] == 3.0
    assert w[lv2.IDX["zb_bonf"]] == 0.0 and w[lv2.IDX["zb_a_prawa"]] == 0.0


def test_porownania_komorki_licza_dm_na_roznicy_a_minus_b_i_daja_nan_gdy_brak_prognozy():
    rng = np.random.default_rng(5)
    baza, szum = rng.normal(0.0, 1.0, 300), rng.normal(0.0, 0.1, 300)
    straty = {
        "wyr_t5": {"fz0": baza, "pinb": baza},
        "okno60_t5": {"fz0": baza + 0.2 + szum, "pinb": baza - 0.2 + szum},
    }
    wyn = lv2.porownania_komorki(straty)
    assert wyn.shape == (len(lv2.POROWNANIA), 3)
    policzone = [lv2.POROWNANIA[j]["kod"] for j in np.flatnonzero(~np.isnan(wyn[:, 0]))]
    assert policzone == ["wyr_fz0_okno60_t5", "wyr_pinb_okno60_t5"]
    d = pl.dm_wektor(0.2 + szum)
    np.testing.assert_allclose(
        wyn[lv2.POR_IDX["wyr_fz0_okno60_t5"]], [d["t"], d["srednia"], d["se"]], rtol=1e-10
    )  # A − B > 0: wyrocznia (B) lepsza, t > 0
    assert wyn[lv2.POR_IDX["wyr_fz0_okno60_t5"], 0] > 0 > wyn[lv2.POR_IDX["wyr_pinb_okno60_t5"], 0]


# --- panel w miniaturze: silnik `przetworz_panel` (kształty, zagnieżdżenie, kontrole R8) -----------------

MIKRO = {
    "panele": 12,
    "boot": 199,  # dwustronna p-wartość bootstrapu ≥ 2/200 = 0,01 < α/3: testy A i B mogą odrzucać
    "n_dni": 660,
    "start": 400,
    "k_panel": 5,
    "komorki": ((5, 250), (3, 200)),
}
SEED_MIKRO = 202_610


@pytest.fixture(scope="module")
def mikro():
    ss = np.random.SeedSequence(SEED_MIKRO).spawn(MIKRO["panele"])
    czesci = [lv2.przetworz_panel((s, MIKRO)) for s in ss]
    return {n: np.stack([c[i] for c in czesci]) for i, n in enumerate(("abs", "dm", "diag"))}


def test_mikro_ksztalty_i_puste_miejsca_tylko_tam_gdzie_brak_prognozy(mikro):
    b = MIKRO["panele"]
    assert mikro["abs"].shape == (b, 2, 2, len(pz.PROGNOZY), len(lv2.STAT))
    assert mikro["dm"].shape == (b, 2, 2, len(lv2.POROWNANIA), 3)
    assert mikro["diag"].shape == (b, len(lv2.DIAG))
    ep = [i for i, nazwa in enumerate(pz.PROGNOZY) if nazwa.endswith("_ep")]
    reszta = [i for i in range(len(pz.PROGNOZY)) if i not in ep]
    assert len(ep) == 3
    assert np.isfinite(mikro["abs"][:, 0]).all()  # komórka główna: wszystkie prognozy
    assert np.isfinite(mikro["abs"][:, 1][:, :, reszta]).all()
    assert np.isnan(mikro["abs"][:, 1][:, :, ep]).all()  # podpanel nie ma ogonów zbiorczych
    brak = {p["kod"] for p in lv2.POROWNANIA if "ewma94_ep" in (p["a"], p["b"])}
    assert brak == {"real_fz0_ewma94_t5__ewma94_ep", "real_pinb_ewma94_t5__ewma94_ep"}
    assert np.isfinite(mikro["dm"][:, 0]).all()
    for j, por in enumerate(lv2.POROWNANIA):
        blok = mikro["dm"][:, 1, :, j]
        assert np.isnan(blok).all() == (por["kod"] in brak), por["kod"]
        assert np.isfinite(blok).all() == (por["kod"] not in brak), por["kod"]


def test_mikro_diagnostyka_garch_liczy_dopasowania_wszystkich_blokow_i_monet(mikro):
    bloki = math.ceil((MIKRO["n_dni"] - MIKRO["start"]) / pz.KROK)
    d = mikro["diag"]
    assert (d[:, 0] == bloki * MIKRO["k_panel"]).all() and (d[:, 1] <= d[:, 0]).all()
    assert (d[:, 2] <= d[:, 0]).all() and (d[:, 3] > 0.5).all() and (d[:, 4] > 2.0).all()


def test_mikro_komorka_podpanelowa_to_pierwsze_monety_i_dni_tego_samego_panelu(mikro):
    """Ponowne policzenie komórek jednego panelu ręcznie (bez `przetworz_panel`): te same liczby."""
    i_panel = 3
    ss_gen, ss_boot = np.random.SeedSequence(SEED_MIKRO).spawn(MIKRO["panele"])[i_panel].spawn(2)
    panel = generuj_panel(
        MIKRO["n_dni"], MIKRO["k_panel"], seed=lv2._ziarno_int(ss_gen), nu=5.0, rho=lv2.RHO
    )
    zr = pz.zbuduj_zrodla(panel, start=MIKRO["start"])
    gen = np.random.default_rng(ss_boot)
    idx = {
        n: gen.integers(0, n, size=(MIKRO["boot"], n))
        for n in sorted({n for _, n in MIKRO["komorki"]})
    }
    for ic, (k, n) in enumerate(MIKRO["komorki"]):
        zk, waga = zr.pierwsze(k), zr.pierwsze(k).sigma["ewma94"][:n]
        for ip, p in enumerate(lv2.POZIOMY):
            straty = {}
            for nazwa in ("okno60_t5", "ewma94_t5", "garch_tnu", "wyr_t5"):
                q, es = pz.prognoza(zk, nazwa, p)
                np.testing.assert_array_equal(
                    mikro["abs"][i_panel, ic, ip, lv2.PROG_IDX[nazwa]],
                    lv2.statystyki_komorki(zk.r[:n], q[:n], es[:n], p, idx[n]),
                )
                straty[nazwa] = pl.straty_dzienne(zk.r[:n], q[:n], es[:n], p, waga)
            dm = pl.dm_wektor(straty["ewma94_t5"]["fz0"] - straty["garch_tnu"]["fz0"])
            np.testing.assert_array_equal(
                mikro["dm"][i_panel, ic, ip, lv2.POR_IDX["real_fz0_ewma94_t5__garch_tnu"]],
                [dm["t"], dm["srednia"], dm["se"]],
            )


def test_mikro_trafien_przybywa_ze_zanizeniem_sigma_w_kazdym_panelu(mikro):
    kolumny = [lv2.PROG_IDX[f] for f in lv2.GRID]
    trafienia = mikro["abs"][:, :, :, kolumny, lv2.IDX["hit"]]
    assert (np.diff(trafienia, axis=-1) >= 0).all()  # VaR bliżej zera ⇒ nie mniej trafień
    assert (trafienia[..., -1] > trafienia[..., 0]).all()


def test_mikro_kontrola_negatywna_wyrocznia_ma_poprawny_rozmiar_i_trafienia(mikro):
    for ip, p in enumerate(lv2.POZIOMY):
        zb, _ = lv2._odsetek(mikro, 0, ip, "wyr_t5", "zb_bonf")
        hit, _ = lv2._odsetek(mikro, 0, ip, "wyr_t5", "hit")
        assert zb <= 0.20 and 0.5 * p < hit < 1.5 * p  # nominalnie ≤ 5 %; hojne granice (12 paneli)


def test_mikro_kontrola_pozytywna_zanizenie_30_proc_jest_wykrywane(mikro):
    for ip in range(2):
        assert lv2._odsetek(mikro, 0, ip, lv2.KONTROLA_X, "zb_bonf")[0] >= 0.75


def test_mikro_dm_kontrola_negatywna_pary_zerowe_nie_odrzucaja_zbyt_czesto(mikro):
    for ic in (0, 1):
        for ip in (0, 1):
            for kod in ("zero_fz0_90", "zero_fz0_80", "zero_pinb_90", "zero_pinb_80"):
                assert lv2._dm_odsetek(mikro, ic, ip, kod, "dwu")[0] <= 0.42, (ic, ip, kod)


@pytest.mark.parametrize("ip", [0, 1])
def test_mikro_roznica_fz0_zanizonej_wyroczni_zgodna_ze_wzorem_zamknietym(mikro, ip):
    p = lv2.POZIOMY[ip]
    srednie = mikro["dm"][:, 0, ip, lv2.POR_IDX["moc_fz0_zan30"], 1]
    teoria = pl.oczekiwana_strata(0.7, p, 5.0, "fz0") - pl.oczekiwana_strata(1.0, p, 5.0, "fz0")
    se = srednie.std(ddof=1) / math.sqrt(len(srednie))
    assert teoria > 0 and abs(srednie.mean() - teoria) < 4 * se
    assert lv2._dm_odsetek(mikro, 0, ip, "moc_fz0_zan30", "prawa")[0] > 0.3  # test DM coś widzi


# --- redukcje: tablice wyników paneli → liczby do reguł (na sztucznych tablicach) ------------------


def _pusty_wyn(b: int) -> dict:
    return {
        "abs": np.full((b, 2, 2, len(pz.PROGNOZY), len(lv2.STAT)), np.nan),
        "dm": np.full((b, 2, 2, len(lv2.POROWNANIA), 3), np.nan),
        "diag": np.zeros((b, len(lv2.DIAG))),
    }


def _wpisz_abs(wyn, ic, ip, nazwa, stat, v):
    wyn["abs"][:, ic, ip, lv2.PROG_IDX[nazwa], lv2.IDX[stat]] = v


def _wpisz_dm(wyn, ic, ip, kod, t=0.0, sr=0.01, se=0.005):
    j = lv2.POR_IDX[kod]
    for i, v in enumerate((t, sr, se)):
        wyn["dm"][:, ic, ip, j, i] = v


def _zdarzenia(b: int, m: int) -> np.ndarray:
    """Wektor długości b: m jedynek, reszta zer."""
    return np.r_[np.ones(m), np.zeros(b - m)]


def _se01(b: int, m: int) -> float:
    """SE średniej wektora 0/1 długości b z m jedynkami (odchylenie z ddof = 1, dzielone przez √b)."""
    return math.sqrt(m * (b - m) / (b * b * (b - 1)))


KOD_PARY_GLOWNEJ = "real_fz0_ewma94_t5__garch_tnu"
T_PROBA = np.array([3.0, -3.0, 1.0, 2.5, np.nan])
SR_PROBA = np.array([0.1, -0.1, 0.01, 0.2, np.nan])
SE_PROBA = np.array([0.03, 0.03, 0.01, 0.08, np.nan])


@pytest.mark.parametrize(
    "tryb, oczekiwane",
    [
        ("prawa", [1, 0, 0, 1, np.nan]),
        ("lewa", [0, 1, 0, 0, np.nan]),
        ("dwu", [1, 1, 0, 1, np.nan]),
        ("centr", [0, 1, 1, 0, np.nan]),  # średnia d̄ = 0,05: t_c = (1,67; −5; −4; 1,88)
    ],
)
def test_dm_zdarzenia_czyta_wlasciwy_ogon_i_zostawia_brak_porownania_jako_nan(tryb, oczekiwane):
    wyn = _pusty_wyn(5)
    j = lv2.POR_IDX[KOD_PARY_GLOWNEJ]
    wyn["dm"][:, 0, 0, j, 0], wyn["dm"][:, 0, 0, j, 1] = T_PROBA, SR_PROBA
    wyn["dm"][:, 0, 0, j, 2] = SE_PROBA
    z = lv2._dm_zdarzenia(wyn, 0, 0, KOD_PARY_GLOWNEJ, tryb)
    np.testing.assert_array_equal(z, oczekiwane)


def test_dm_zdarzenia_nieznany_tryb_to_blad_a_brak_porownania_to_same_nan_bez_ostrzezen():
    wyn = _pusty_wyn(4)
    with pytest.raises(ValueError, match="tryb"):
        lv2._dm_zdarzenia(wyn, 0, 0, KOD_PARY_GLOWNEJ, "obustronnie")
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # np.nanmean(puste) ostrzega — kod ma tego unikać
        for tryb in ("prawa", "lewa", "dwu", "centr"):
            assert np.isnan(lv2._dm_zdarzenia(wyn, 0, 0, KOD_PARY_GLOWNEJ, tryb)).all()
        m, se = lv2._dm_odsetek(wyn, 0, 0, KOD_PARY_GLOWNEJ, "centr")
    assert np.isnan(m) and np.isnan(se)


def test_krzywa_dm_kotwica_x0_to_rozmiar_na_parach_zerowych_a_moc_czyta_prawy_ogon():
    b = 10
    wyn = _pusty_wyn(b)
    _wpisz_dm(wyn, 0, 1, "zero_fz0_90", t=np.r_[3.0, np.zeros(9)])
    _wpisz_dm(wyn, 0, 1, "zero_fz0_80", t=np.r_[-3.0, -3.0, 3.0, np.zeros(7)])  # dwustronnie: 3/10
    _wpisz_dm(wyn, 0, 1, "zero_pinb_90", t=9.0)  # inna strata nie może wejść do krzywej FZ0
    _wpisz_dm(wyn, 0, 1, "zero_pinb_80", t=9.0)
    moc = {"zan05": 2, "zan10": 5, "zan15": 8, "zan20": 10, "zan30": 10}
    for nazwa, m in moc.items():  # t < 0 (A lepsza) nie jest mocą
        _wpisz_dm(wyn, 0, 1, f"moc_fz0_{nazwa}", t=np.r_[np.full(m, 3.0), np.full(b - m, -3.0)])
        _wpisz_dm(wyn, 0, 1, f"moc_pinb_{nazwa}", t=0.0)
    krz, se = lv2.krzywa_dm(wyn, 0, 1, "fz0")
    np.testing.assert_allclose(krz, [0.2, 0.2, 0.5, 0.8, 1.0, 1.0], atol=1e-15)
    assert se[0] == pytest.approx(0.5 * (_se01(b, 1) + _se01(b, 3)), abs=1e-15)
    assert se[2] == pytest.approx(_se01(b, 5), abs=1e-15) and se[4] == 0.0
    krz_p, _ = lv2.krzywa_dm(wyn, 0, 1, "pinb")
    assert krz_p[0] == 1.0 and (krz_p[1:] == 0.0).all()


def test_krzywa_abs_to_odsetek_odrzucen_zbiorczych_na_siatce_zanizen():
    b = 10
    wyn = _pusty_wyn(b)
    liczby = [1, 2, 5, 7, 8, 10]
    for nazwa, m in zip(lv2.GRID, liczby):
        _wpisz_abs(wyn, 1, 0, nazwa, "zb_bonf", _zdarzenia(b, m))
        _wpisz_abs(wyn, 1, 0, nazwa, "zb_a", 0.0)  # tylko `zb_bonf` wchodzi do krzywej
    krz, se = lv2.krzywa_abs(wyn, 1, 0)
    np.testing.assert_allclose(krz, np.array(liczby) / b, atol=1e-15)
    np.testing.assert_allclose(se, [_se01(b, m) for m in liczby], atol=1e-15)
    assert lv2.GRID[0] == "wyr_t5" and lv2.X_GRID[0] == 0.0 and len(lv2.GRID) == len(lv2.X_GRID)


def test_liczby_k7_to_srednie_po_panelach_a_odsetki_licza_sie_w_panelu():
    wyn = _pusty_wyn(4)
    wyn["diag"] = np.array(  # dopasowania, nie_zbiezne, brzeg, persystencja, nu
        [
            [100, 2, 5, 0.97, 5.0],
            [100, 0, 3, 0.98, 5.2],
            [200, 4, 10, 0.99, 4.8],
            [100, 1, 2, 0.96, 5.4],
        ]
    )
    k7 = lv2.liczby_k7(wyn)
    assert set(k7) == {"nu", "pers", "nie_zbiezne", "brzeg"}
    assert k7["nu"] == pytest.approx((5.1, np.std([5.0, 5.2, 4.8, 5.4], ddof=1) / 2))
    assert k7["pers"][0] == pytest.approx(0.975)
    assert k7["nie_zbiezne"][0] == pytest.approx(np.mean([0.02, 0.0, 0.02, 0.01]))
    assert k7["brzeg"][0] == pytest.approx(np.mean([0.05, 0.03, 0.05, 0.02]))
    assert k7["brzeg"][1] == pytest.approx(np.std([0.05, 0.03, 0.05, 0.02], ddof=1) / 2)


def test_liczby_k_czyta_wlasciwe_prognozy_komorke_i_poziom():
    b = 20
    wyn = _pusty_wyn(b)
    oczekiwane = {
        "wyr_t5": 1,
        "zan30": 20,
        "garch_tnu": 2,
        "garch_tnu_zan10": 17,
    }  # odrzucenia z 20
    for ic, ip in ((0, 0), (1, 0), (1, 1)):  # inne komórki i poziom: pomyłka indeksu zmieni wynik
        for nazwa in oczekiwane:
            _wpisz_abs(wyn, ic, ip, nazwa, "zb_bonf", _zdarzenia(b, 10))
    for nazwa, m in oczekiwane.items():
        _wpisz_abs(wyn, 0, 1, nazwa, "zb_bonf", _zdarzenia(b, m))
    wyn["diag"][:] = [200, 2, 5, 0.97, 5.0]
    liczby = lv2.liczby_k(wyn, 0, 1)
    assert set(liczby) == {"k1", "k2", "k7", "ka", "kb"}
    assert [liczby[k][0] for k in ("k1", "k2", "ka", "kb")] == pytest.approx(
        [0.05, 1.0, 0.10, 0.85]
    )
    assert liczby["ka"][1] == pytest.approx(_se01(b, 2))
    assert liczby["k7"]["nie_zbiezne"][0] == pytest.approx(0.01)


NAZWY_K4 = tuple(f"{s}, c_A = {c}" for s in ("fz0", "pinb") for c in (0.9, 0.8))
NAZWY_K6 = tuple(f"{x} → {y}" for x, y in lv2.PARY_REALNE)


def test_liczby_p_czyta_wlasciwe_porownania_straty_i_tryby():
    b = 20
    wyn = _pusty_wyn(b)
    # K4: cztery pary zerowe, dwustronnie; różne odsetki, by pomyłka nazwy była widoczna
    for kod, m in (
        ("zero_fz0_90", 1),
        ("zero_fz0_80", 2),
        ("zero_pinb_90", 3),
        ("zero_pinb_80", 4),
    ):
        _wpisz_dm(wyn, 1, 0, kod, t=np.r_[np.full(m, -3.0), np.zeros(b - m)])
    # K5 i krzywa: tylko FZ0, prawy ogon; PINB ma zostać pominięta
    for nazwa in lv2.ZANIZENIA:
        _wpisz_dm(wyn, 1, 0, f"moc_fz0_{nazwa}", t=np.r_[np.full(19, 3.0), [0.0]])
        _wpisz_dm(wyn, 1, 0, f"moc_pinb_{nazwa}", t=0.0)
    # K6: sześć par realistycznych po wyśrodkowaniu (średnia d̄ = 0, |d̄|/se = 5 w 2·i panelach)
    for i, (x, y) in enumerate(lv2.PARY_REALNE):
        sr = np.r_[np.full(i, 0.05), np.full(i, -0.05), np.zeros(b - 2 * i)]
        _wpisz_dm(wyn, 1, 0, f"real_fz0_{x}__{y}", t=0.0, sr=sr, se=0.01)
    # P-b: para główna, prawy ogon (14 z 20); jej wiersz ma też wzorzec K6 powyżej
    j = lv2.POR_IDX[KOD_PARY_GLOWNEJ]
    wyn["dm"][:, 1, 0, j, 0] = np.r_[np.full(14, 3.0), np.zeros(6)]
    wyn["diag"][:] = [200, 2, 5, 0.97, 5.0]
    liczby = lv2.liczby_p(wyn, 1, 0)
    assert set(liczby) == {"k4", "k5", "k6", "k7", "krzywa", "krzywa_se", "pb"}
    assert set(liczby["k4"]) == set(NAZWY_K4) and set(liczby["k6"]) == set(NAZWY_K6)
    assert [liczby["k4"][n][0] for n in NAZWY_K4] == pytest.approx([0.05, 0.10, 0.15, 0.20])
    assert liczby["k5"][0] == pytest.approx(0.95)
    assert [liczby["k6"][n][0] for n in NAZWY_K6] == pytest.approx([0.0, 0.1, 0.2, 0.3, 0.4, 0.5])
    assert liczby["pb"][0] == pytest.approx(0.70)
    assert liczby["krzywa"][1:] == pytest.approx([0.95] * 5)  # moc FZ0 na całej siatce zaniżeń
    assert liczby["krzywa"][0] == pytest.approx(0.075)  # średnia rozmiarów dwóch par zerowych FZ0
    assert len(liczby["krzywa"]) == len(lv2.X_GRID) == len(liczby["krzywa_se"])


def _wyn_do_przewidywan(b=100, o60=75, ew=80, regret=(0.30, 0.20, 0.10)):
    wyn = _pusty_wyn(b)
    for ip in range(2):
        for ic in range(2):
            _wpisz_abs(
                wyn, ic, ip, "okno60_t5", "zb_bonf", _zdarzenia(b, 1)
            )  # tylko ic = 0 się liczy
            _wpisz_abs(wyn, ic, ip, "ewma94_t5", "zb_bonf", _zdarzenia(b, 1))
        _wpisz_abs(wyn, 0, ip, "okno60_t5", "zb_bonf", _zdarzenia(b, o60))
        _wpisz_abs(wyn, 0, ip, "ewma94_t5", "zb_bonf", _zdarzenia(b, ew))
        for nazwa, w in zip(("okno60_t5", "ewma94_t5", "garch_tnu"), regret):
            wyn["dm"][:, 0, ip, lv2.POR_IDX[f"wyr_fz0_{nazwa}"], 1] = w
            wyn["dm"][:, 1, ip, lv2.POR_IDX[f"wyr_fz0_{nazwa}"], 1] = -w  # odwrotny porządek
    return wyn


def _oceny(pa_ok=False, pb_ok=False, pb_wartosc=0.35):
    ocena = {
        "P": {"kryteria": [{"ok": pa_ok, "wartosc": 0.14}, {"ok": pb_ok, "wartosc": pb_wartosc}]}
    }
    return {p: ocena for p in lv2.POZIOMY}


def _przew(wyn, oceny):
    return {(w["kod"], w["p"]): w for w in lv2.przewidywania(wyn, oceny)}


def test_przewidywania_cztery_na_poziom_i_wszystkie_trafione_dla_zgodnych_liczb():
    przew = _przew(_wyn_do_przewidywan(), _oceny())
    assert len(przew) == 8 and {k for k, _ in przew} == {"W1", "W2", "W3", "W4"}
    assert all(w["ok"] for w in przew.values())
    assert przew[("W1", 0.01)]["wartosc"] == pytest.approx(0.75)
    assert przew[("W2", 0.05)]["wartosc"] == pytest.approx(0.20)  # 0,30 − 0,10
    assert przew[("W4", 0.01)]["wartosc"] == 0.35 and np.isnan(przew[("W3", 0.01)]["wartosc"])


@pytest.mark.parametrize(
    "o60, ew, ok", [(70, 90, True), (69, 90, False), (90, 69, False), (70, 70, True)]
)
def test_przewidywanie_w1_wymaga_70_proc_dla_obu_prognoz(o60, ew, ok):
    przew = _przew(_wyn_do_przewidywan(o60=o60, ew=ew), _oceny())
    assert przew[("W1", 0.05)]["ok"] is ok and przew[("W2", 0.05)]["ok"] is True


@pytest.mark.parametrize(
    "regret, ok",
    [
        ((0.3, 0.2, 0.1), True),
        ((0.3, 0.3, 0.1), False),
        ((0.1, 0.2, 0.3), False),
        ((0.3, 0.1, 0.2), False),
    ],
)
def test_przewidywanie_w2_wymaga_scisle_malejacych_strat_ponad_wyrocznie(regret, ok):
    assert _przew(_wyn_do_przewidywan(regret=regret), _oceny())[("W2", 0.01)]["ok"] is ok


def test_przewidywania_w3_i_w4_sa_trafione_tylko_gdy_kryteria_p_sa_niespelnione():
    assert _przew(_wyn_do_przewidywan(), _oceny(pa_ok=True))[("W3", 0.01)]["ok"] is False
    assert _przew(_wyn_do_przewidywan(), _oceny(pb_ok=True))[("W4", 0.01)]["ok"] is False
    przew = _przew(_wyn_do_przewidywan(), _oceny(pa_ok=True, pb_ok=True))
    assert not przew[("W3", 0.05)]["ok"] and not przew[("W4", 0.05)]["ok"]
    assert przew[("W1", 0.05)]["ok"] and przew[("W2", 0.05)]["ok"]


# --- okablowanie reguł K i P: MIERZALNE / NIEMIERZALNE / WSTRZYMANE -------------------------------

K7_DOBRE = {
    "nu": (5.2, 0.02),
    "pers": (0.975, 0.001),
    "nie_zbiezne": (0.004, 0.001),
    "brzeg": (0.02, 0.003),
}


def _lk(**zmiany):
    return {
        "k1": (0.048, 0.003),
        "k2": (1.0, 0.0),
        "ka": (0.06, 0.004),
        "kb": (0.92, 0.005),
        "k7": dict(K7_DOBRE),
        **zmiany,
    }


def _k7(**zmiany):
    return {**K7_DOBRE, **zmiany}


def _lp(**zmiany):
    return {
        "k4": {n: (0.05, 0.004) for n in NAZWY_K4},
        "k5": (1.0, 0.0),
        "k6": {n: (0.05, 0.004) for n in NAZWY_K6},
        "k7": dict(K7_DOBRE),
        "krzywa": [0.05, 0.40, 0.85, 0.99, 1.0, 1.0],
        "krzywa_se": [0.004] * 6,
        "pb": (0.90, 0.01),
        **zmiany,
    }


def _ok(ocena):
    return {k["kod"]: k["ok"] for k in (*ocena["kontrole"], *ocena["kryteria"])}


def _k6(**zmiany):
    """Słownik K6 z jednym odsetkiem zmienionym na (v, SE)."""
    return {n: zmiany.get(f"p{i}", (0.05, 0.004)) for i, n in enumerate(NAZWY_K6)}


def test_ocen_k_dobre_wejscie_daje_tak_a_kontrole_bramkuja_oba_wnioski():
    o = lv2.ocen_k(_lk())
    assert o["werdykt"] == "TAK"
    assert [k["kod"] for k in o["kontrole"]] == ["K1", "K2", "K7a", "K7b", "K7c", "K7d"]
    assert [k["kod"] for k in o["kryteria"]] == ["K-a", "K-b"]
    assert all(_ok(o).values()) and all(k["bramka"] == "obie" for k in o["kontrole"])


@pytest.mark.parametrize(
    "kod, zmiana",
    [
        ("K1", {"k1": (0.0249, 0.003)}),
        ("K1", {"k1": (0.0751, 0.003)}),
        ("K2", {"k2": (0.9499, 0.01)}),
        ("K7a", {"k7": _k7(nu=(3.99, 0.02))}),
        ("K7a", {"k7": _k7(nu=(6.51, 0.02))}),
        ("K7b", {"k7": _k7(pers=(0.949, 0.001))}),
        ("K7b", {"k7": _k7(pers=(0.9951, 0.001))}),
        ("K7c", {"k7": _k7(nie_zbiezne=(0.0201, 0.001))}),
        ("K7d", {"k7": _k7(brzeg=(0.0501, 0.003))}),
    ],
)
def test_ocen_k_zawodzaca_kontrola_wstrzymuje_nawet_przy_spelnionych_kryteriach(kod, zmiana):
    o = lv2.ocen_k(_lk(**zmiana))
    assert o["werdykt"] == "WSTRZYMANE"
    assert [k for k, ok in _ok(o).items() if not ok] == [kod]


def test_ocen_k_kontrola_ma_pierwszenstwo_przed_kryteriami():
    o = lv2.ocen_k(_lk(k1=(0.10, 0.003), ka=(0.30, 0.01), kb=(0.1, 0.01)))
    assert o["werdykt"] == "WSTRZYMANE" and not _ok(o)["K-a"] and not _ok(o)["K-b"]


@pytest.mark.parametrize(
    "zmiana, kod",
    [
        ({"ka": (0.1001, 0.004)}, ["K-a"]),
        ({"kb": (0.7999, 0.005)}, ["K-b"]),
        ({"ka": (0.2, 0.004), "kb": (0.5, 0.005)}, ["K-a", "K-b"]),
    ],
)
def test_ocen_k_niespelnione_kryterium_przy_dobrych_kontrolach_daje_nie(zmiana, kod):
    o = lv2.ocen_k(_lk(**zmiana))
    assert o["werdykt"] == "NIE"
    assert [k for k, ok in _ok(o).items() if not ok] == kod


def test_ocen_k_progi_sa_domkniete_dokladnie_na_granicy():
    lo, hi = lv2.ROZMIAR
    graniczne = _lk(
        k1=(lo, 0.003),
        k2=(lv2.MOC_KONTROLA, 0.0),
        ka=(lv2.ROZMIAR_ESTYMOWANY_MAX, 0.004),
        kb=(lv2.MOC_MIN, 0.005),
        k7=_k7(
            nu=(lv2.GARCH_NU[0], 0.0),
            pers=(lv2.GARCH_PERS[1], 0.0),
            nie_zbiezne=(lv2.GARCH_NIEZBIEZNE_MAX, 0.0),
            brzeg=(lv2.GARCH_BRZEG_MAX, 0.0),
        ),
    )
    assert lv2.ocen_k(graniczne)["werdykt"] == "TAK"
    assert lv2.ocen_k(_lk(k1=(hi, 0.003), k7=_k7(nu=(lv2.GARCH_NU[1], 0.0))))["werdykt"] == "TAK"
    assert lv2.ocen_k(_lk(k7=_k7(pers=(lv2.GARCH_PERS[0], 0.0))))["werdykt"] == "TAK"


def test_ocen_k_flaga_granicy_zapala_sie_w_2_se_od_progu():
    blisko = {k["kod"]: k["granica"] for k in lv2.ocen_k(_lk(ka=(0.098, 0.004)))["kryteria"]}
    daleko = {k["kod"]: k["granica"] for k in lv2.ocen_k(_lk(ka=(0.060, 0.004)))["kryteria"]}
    assert blisko["K-a"] and not daleko["K-a"] and not blisko["K-b"]
    assert lv2._blisko(0.10, 0.004, 0.10) and not lv2._blisko(0.109, 0.004, 0.10)
    assert lv2._blisko(0.107, 0.004, 0.0, 0.10)  # którykolwiek próg


@settings(max_examples=200, deadline=None)
@given(ka=st.floats(0.0, 0.3), kb=st.floats(0.0, 1.0))
def test_ocen_k_tak_wtedy_i_tylko_wtedy_gdy_ka_i_kb_przy_dobrych_kontrolach(ka, kb):
    o = lv2.ocen_k(_lk(ka=(ka, 0.004), kb=(kb, 0.005)))
    assert (o["werdykt"] == "TAK") == (ka <= lv2.ROZMIAR_ESTYMOWANY_MAX and kb >= lv2.MOC_MIN)
    assert o["werdykt"] in ("TAK", "NIE")


def test_ocen_p_dobre_wejscie_daje_tak_a_k6_bramkuje_po_jednym_wniosku():
    o = lv2.ocen_p(_lp())
    assert o["werdykt"] == "TAK"
    assert [k["kod"] for k in o["kontrole"]] == [
        "K4",
        "K5",
        "K6a",
        "K6b",
        "K7a",
        "K7b",
        "K7c",
        "K7d",
    ]
    assert [k["kod"] for k in o["kryteria"]] == ["P-a", "P-b"]
    assert {k["kod"]: k["bramka"] for k in o["kontrole"] if k["bramka"] != "obie"} == {
        "K6a": "TAK",
        "K6b": "NIE",
    }
    assert all(_ok(o).values())


@pytest.mark.parametrize(
    "kod, zmiana",
    [
        ("K4", {"k4": {**{n: (0.05, 0.004) for n in NAZWY_K4}, NAZWY_K4[2]: (0.0249, 0.004)}}),
        ("K4", {"k4": {**{n: (0.05, 0.004) for n in NAZWY_K4}, NAZWY_K4[3]: (0.0751, 0.004)}}),
        ("K5", {"k5": (0.9499, 0.01)}),
        ("K7a", {"k7": _k7(nu=(6.51, 0.02))}),
        ("K7b", {"k7": _k7(pers=(0.949, 0.001))}),
        ("K7c", {"k7": _k7(nie_zbiezne=(0.0201, 0.001))}),
        ("K7d", {"k7": _k7(brzeg=(0.0501, 0.003))}),
    ],
)
@pytest.mark.parametrize("kryteria_ok", [True, False])
def test_ocen_p_kontrole_obie_wstrzymuja_niezaleznie_od_kryteriow(kod, zmiana, kryteria_ok):
    bazowe = {} if kryteria_ok else {"pb": (0.3, 0.01)}
    o = lv2.ocen_p(_lp(**bazowe, **zmiana))
    assert o["werdykt"] == "WSTRZYMANE"
    assert [k for k, ok in _ok(o).items() if k not in ("P-a", "P-b") and not ok] == [kod]


def test_ocen_p_k4_nazywa_najgorsza_pare_i_pomija_pary_bez_wyniku():
    k4 = {n: (0.05, 0.004) for n in NAZWY_K4}
    k4[NAZWY_K4[1]] = (np.nan, np.nan)
    k4[NAZWY_K4[2]] = (0.09, 0.004)
    k4[NAZWY_K4[3]] = (0.06, 0.004)
    wiersz = {k["kod"]: k for k in lv2.ocen_p(_lp(k4=k4))["kontrole"]}["K4"]
    assert NAZWY_K4[2] in wiersz["opis"] and wiersz["wartosc"] == 0.09 and not wiersz["ok"]
    assert lv2._w_przedziale({"a": (0.05, 0.004), "b": (np.nan, np.nan)})[0] is True


def test_k6_za_liberalny_podwaza_tylko_wniosek_tak_a_nie_zostaje_wazne():
    k6 = _k6(p1=(0.08, 0.004))  # jedna para realistyczna: rozmiar 8 % > 7,5 %
    ok_kryteria = lv2.ocen_p(_lp(k6=k6))
    assert not _ok(ok_kryteria)["K6a"] and _ok(ok_kryteria)["K6b"]
    assert ok_kryteria["werdykt"] == "WSTRZYMANE"  # TAK byłoby zawyżone przez liberalny test
    zle_kryteria = lv2.ocen_p(_lp(k6=k6, pb=(0.35, 0.01)))
    assert zle_kryteria["werdykt"] == "NIE"  # liberalny test zawyża moc, więc brak mocy jest pewny
    assert not _ok(zle_kryteria)["P-b"]


def test_k6_za_zachowawczy_podwaza_tylko_wniosek_nie_a_tak_zostaje_wazne():
    k6 = _k6(p4=(0.02, 0.004))  # rozmiar 2 % < 2,5 %
    dobre = lv2.ocen_p(_lp(k6=k6))
    assert _ok(dobre)["K6a"] and not _ok(dobre)["K6b"]
    assert dobre["werdykt"] == "TAK"  # zachowawczy test zaniża moc, więc wykryta moc jest pewna
    assert lv2.ocen_p(_lp(k6=k6, pb=(0.35, 0.01)))["werdykt"] == "WSTRZYMANE"


def test_k6_czyta_skrajne_pary_i_pomija_brak_porownania():
    k6 = _k6(p0=(0.07, 0.004), p5=(np.nan, np.nan), p2=(0.03, 0.004), p3=(0.071, 0.004))
    wiersze = {k["kod"]: k for k in lv2.ocen_p(_lp(k6=k6))["kontrole"]}
    assert wiersze["K6a"]["wartosc"] == 0.071 and NAZWY_K6[3] in wiersze["K6a"]["opis"]
    assert wiersze["K6b"]["wartosc"] == 0.03 and NAZWY_K6[2] in wiersze["K6b"]["opis"]
    assert wiersze["K6a"]["ok"] and wiersze["K6b"]["ok"] and wiersze["K6a"]["granica"]
    assert lv2._skrajna({"a": (0.1, 0.0), "b": (np.nan, np.nan), "c": (0.2, 0.3)}, True) == (
        "c",
        0.2,
        0.3,
    )
    assert lv2._skrajna({"a": (0.1, 0.0), "b": (np.nan, np.nan), "c": (0.2, 0.3)}, False) == (
        "a",
        0.1,
        0.0,
    )


@pytest.mark.parametrize(
    "krzywa, pb, pa, pb_ok",
    [
        ([0.05, 0.40, 0.85, 0.99, 1.0, 1.0], 0.90, True, True),
        ([0.05, 0.40, 0.79, 0.99, 1.0, 1.0], 0.90, False, True),
        ([0.05, 0.40, 0.85, 0.99, 1.0, 1.0], 0.79, True, False),
        ([0.05, 0.10, 0.20, 0.30, 0.40, 0.50], 0.50, False, False),
        ([0.05, 0.90, 0.70, 0.99, 1.0, 1.0], 0.90, True, True),  # moc nie rośnie: wygładzenie maks.
    ],
)
def test_ocen_p_kryteria_z_krzywej_mocy_i_mocy_pary_glownej(krzywa, pb, pa, pb_ok):
    o = lv2.ocen_p(_lp(krzywa=krzywa, pb=(pb, 0.01)))
    assert (_ok(o)["P-a"], _ok(o)["P-b"]) == (pa, pb_ok)
    assert o["werdykt"] == ("TAK" if pa and pb_ok else "NIE")


def test_ocen_p_p_a_na_dokladnym_progu_mocy_przechodzi_mimo_zaokraglen_interpolacji():
    krzywa = [0.05, 0.4, 0.8, 0.95, 1.0, 1.0]  # moc przy x* = 0,10 dokładnie 80 %
    o = lv2.ocen_p(_lp(krzywa=krzywa))
    pa = {k["kod"]: k for k in o["kryteria"]}["P-a"]
    assert pa["ok"] and pa["wartosc"] == pytest.approx(0.10, abs=1e-12)
    assert not lv2.ocen_p(_lp(krzywa=[0.05, 0.4, np.nextafter(0.8, 0), 0.95, 1.0, 1.0]))[
        "kryteria"
    ][0]["ok"]


def test_ocen_p_p_a_wartosc_to_mde_a_gdy_nieosiagalne_pisze_wiekszy_niz_siatka():
    o = lv2.ocen_p(_lp(krzywa=[0.05, 0.3, 0.5, 0.85, 1.0, 1.0]))
    pa = o["kryteria"][0]
    assert pa["wartosc"] == pytest.approx(0.10 + 0.05 * 0.3 / 0.35) and not pa["ok"]
    assert lv2._wart_txt(pa) == f"{pa['wartosc']:.3f}"
    nieosiagalne = lv2.ocen_p(_lp(krzywa=[0.05, 0.1, 0.2, 0.3, 0.4, 0.5]))["kryteria"][0]
    assert np.isnan(nieosiagalne["wartosc"]) and lv2._wart_txt(nieosiagalne) == ">0.30"


@settings(max_examples=200, deadline=None)
@given(
    krzywa=st.lists(st.floats(0.0, 1.0), min_size=6, max_size=6),
    pb=st.floats(0.0, 1.0),
)
def test_ocen_p_tak_wtedy_i_tylko_wtedy_gdy_moc_przy_x_gwiazdka_i_pb_przy_dobrych_kontrolach(
    krzywa, pb
):
    o = lv2.ocen_p(_lp(krzywa=krzywa, pb=(pb, 0.01)))
    moc_x = max(krzywa[: lv2.X_GRID.index(lv2.X_MAX) + 1])
    assert (o["werdykt"] == "TAK") == (moc_x >= lv2.MOC_MIN and pb >= lv2.MOC_MIN)
    assert o["werdykt"] in ("TAK", "NIE")


@pytest.mark.parametrize(
    "wk, wp, runda, dozwolone",
    [
        ("TAK", "TAK", "MIERZALNA", ["K bezwzględne", "P porównawcze"]),
        ("TAK", "NIE", "MIERZALNA", ["K bezwzględne"]),
        ("NIE", "TAK", "MIERZALNA", ["P porównawcze"]),
        ("TAK", "WSTRZYMANE", "MIERZALNA", ["K bezwzględne"]),
        ("WSTRZYMANE", "TAK", "MIERZALNA", ["P porównawcze"]),
        ("NIE", "NIE", "NIEMIERZALNA", []),
        ("NIE", "WSTRZYMANE", "WSTRZYMANA", []),
        ("WSTRZYMANE", "NIE", "WSTRZYMANA", []),
        ("WSTRZYMANE", "WSTRZYMANE", "WSTRZYMANA", []),
    ],
)
def test_regula_rundy_tabela_prawdy(wk, wp, runda, dozwolone):
    assert lv2.regula_rundy(wk, wp) == (runda, dozwolone)


def test_w_przedziale_wybiera_najgorsza_wedlug_odleglosci_od_5_proc_i_zna_granice():
    pary = {"a": (0.05, 0.004), "b": (np.nan, np.nan), "c": (0.08, 0.004), "d": (0.03, 0.004)}
    ok, granica, najgorsza = lv2._w_przedziale(pary)
    assert (ok, granica, najgorsza) == (False, True, "c")
    assert lv2._w_przedziale({"a": (0.05, 0.004), "d": (0.04, 0.004)}) == (True, False, "d")
    lo, hi = lv2.ROZMIAR
    assert lv2._w_przedziale({"a": (lo, 0.0), "b": (hi, 0.0)})[0] is True  # progi domknięte


def test_wydruk_oceny_opisuje_bramke_kontroli_k6(capsys):
    lv2._wypisz_ocene(lv2.ocen_p(_lp()), "reguła P — próba")
    out = capsys.readouterr().out
    assert "K6a" in out and "K6b" in out and "bramkuje tylko wniosek TAK" in out
    assert "bramkuje tylko wniosek NIE" in out and "WYNIK reguły: MIERZALNE" in out
    assert out.count("bramkuje tylko wniosek") == 2  # K4, K5, K7a–d dotyczą obu wniosków


# --- determinizm względem liczby procesów i wydruk ------------------------------------------------

KONFIG_MALY = {
    "panele": 3,
    "boot": 19,
    "n_dni": 520,
    "start": 400,
    "k_panel": 3,
    "komorki": ((3, 100), (2, 120)),
}


def test_wynik_nie_zalezy_od_liczby_procesow_a_panele_sa_rozne():
    w1 = lv2.uruchom(KONFIG_MALY, 1)
    w3 = lv2.uruchom(KONFIG_MALY, 3)
    assert w1.keys() == w3.keys() == {"abs", "dm", "diag"}
    for klucz in w1:
        np.testing.assert_array_equal(w1[klucz], w3[klucz])  # także identyczne NaN
    assert w1["abs"].shape == (3, 2, 2, len(pz.PROGNOZY), len(lv2.STAT))
    trafienia = w1["abs"][:, 0, 1, lv2.PROG_IDX["okno60_t5"], lv2.IDX["hit"]]
    assert len(np.unique(trafienia)) == 3  # każdy panel ma własne ziarno
    inne = lv2.uruchom(KONFIG_MALY, 2, ziarno=lv2.SEED + 1)
    assert not np.array_equal(inne["abs"], w1["abs"], equal_nan=True)


def test_smoke_stdout_identyczny_dla_roznych_procesow(capsys):
    lv2.main(["--smoke", "--workers", "2"])
    a = capsys.readouterr()
    lv2.main(["--smoke", "--workers", "3"])
    b = capsys.readouterr()
    assert a.out == b.out
    for fraza in (
        "PILOTAŻ — NIE JEST PRZEBIEGIEM REJESTROWYM",
        "KRYTERIA z pre-rejestracji",
        "REGUŁA PIERWSZEJ RUNDY VaR/ES NA DANYCH",
        "PRZEWIDYWANIA z pre-rejestracji",
        "MOC NA SIATCE ZANIŻENIA σ i MDE",
        "DIAGNOSTYKA ESTYMATORA GARCH-t (K7)",
        "OPIS (K6)",
        "bramkuje tylko wniosek TAK",
    ):
        assert fraza in a.out, fraza
    assert "PILOTAŻ: powyższe wyniki reguł nie są werdyktem." in a.out
    assert "Czas przebiegu" in a.err and "Czas" not in a.out  # czas tylko na stderr


def test_pilotaz_z_innym_ziarnem_lub_liczba_paneli_jest_oznaczony(capsys):
    lv2.main(["--smoke", "--panele", "2", "--ziarno", "5", "--workers", "2"])
    out = capsys.readouterr().out
    assert "NIE JEST PRZEBIEGIEM REJESTROWYM" in out
    assert "ziarno 5." in out and "2 paneli" in out


# --- zamrożenie konfiguracji z pre-rejestracji ----------------------------------------------------


def test_konfiguracja_progi_i_prognozy_zgodne_z_pre_rejestracja():
    """Zmiana któregokolwiek zapisanego tu progu po commicie pre-rejestracji musi być widoczna w diffie."""
    assert lv2.KONFIG == {
        "panele": 5000,
        "boot": 999,
        "n_dni": 2100,
        "start": 400,
        "k_panel": 20,
        "komorki": ((20, 1600), (15, 1700)),
    }
    assert (lv2.SEED, lv2.RHO, lv2.POZIOMY, lv2.ALFA, lv2.Z_KRYT) == (
        20_261_016,
        0.8,
        (0.01, 0.05),
        0.05,
        1.959964,
    )
    assert (lv2.ROZMIAR, lv2.ROZMIAR_ESTYMOWANY_MAX, lv2.MOC_MIN, lv2.MOC_KONTROLA, lv2.X_MAX) == (
        (0.025, 0.075),
        0.10,
        0.80,
        0.95,
        0.10,
    )
    assert (lv2.GARCH_NU, lv2.GARCH_PERS, lv2.GARCH_NIEZBIEZNE_MAX, lv2.GARCH_BRZEG_MAX) == (
        (4.0, 6.5),
        (0.95, 0.995),
        0.02,
        0.05,
    )
    assert lv2.PRZEW_ODRZUCANE_MIN == 0.70
    assert lv2.GRID == ("wyr_t5", "zan05", "zan10", "zan15", "zan20", "zan30")
    assert lv2.X_GRID == (0.0, 0.05, 0.10, 0.15, 0.20, 0.30) and lv2.KONTROLA_X == "zan30"
    assert lv2.ESTYMOWANE == ("okno60_t5", "ewma94_t5", "garch_t5", "garch_tnu", "har_t5")
    assert lv2.PARA_GLOWNA == ("ewma94_t5", "garch_tnu")
    assert lv2.PARY_REALNE == (
        ("okno60_t5", "ewma94_t5"),
        ("ewma94_t5", "garch_tnu"),
        ("okno60_t5", "garch_tnu"),
        ("garch_tnu", "garch_t5"),
        ("ewma94_t5", "har_t5"),
        ("ewma94_t5", "ewma94_ep"),
    )
    assert lv2.C_ZERO == (0.9, 0.8) and lv2.WAGA_PINB == "ewma94"
    assert (pz.N_DNI, pz.START, pz.KROK, pz.ROZGRZEWKA_RESZT) == (2100, 400, 30, 60)
    assert (pz.NU, pz.EWMA_LAMBDA, pz.POZIOMY, mv.NU) == (5.0, 0.94, (0.01, 0.05), 5.0)
    assert pz.ZANIZENIA == {
        "zan05": 0.05,
        "zan10": 0.10,
        "zan15": 0.15,
        "zan20": 0.20,
        "zan30": 0.30,
    }
    assert pz.PROGNOZY == {
        "wyr_t5": ("wyr", 1.0, "t5"),
        "zan05": ("wyr", 0.95, "t5"),
        "zan10": ("wyr", 0.90, "t5"),
        "zan15": ("wyr", 0.85, "t5"),
        "zan20": ("wyr", 0.80, "t5"),
        "zan30": ("wyr", 0.70, "t5"),
        "okno60_t5": ("okno60", 1.0, "t5"),
        "ewma94_t5": ("ewma94", 1.0, "t5"),
        "garch_t5": ("garch", 1.0, "t5"),
        "garch_tnu": ("garch", 1.0, "tnu"),
        "garch_tnu_zan10": ("garch", 0.90, "tnu"),
        "garch_tnu_zan20": ("garch", 0.80, "tnu"),
        "har_t5": ("har", 1.0, "t5"),
        "okno60_ep": ("okno60", 1.0, "ep"),
        "ewma94_ep": ("ewma94", 1.0, "ep"),
        "garch_ep": ("garch", 1.0, "ep"),
        "okno60_ec": ("okno60", 1.0, "ec"),
        "ewma94_ec": ("ewma94", 1.0, "ec"),
        "garch_ec": ("garch", 1.0, "ec"),
    }
    assert [(s, c) for s, c in lv2.KONFIG["komorki"]] == [(20, 1600), (15, 1700)]
    assert lv2.KONFIG["start"] + max(n for _, n in lv2.KONFIG["komorki"]) <= lv2.KONFIG["n_dni"]


def test_rozdzielczosc_bootstrapu_pozwala_testom_a_i_b_odrzucac_na_poziomie_alfa_przez_3():
    """Dwustronna p-wartość bootstrapu ma minimum 2/(B + 1); musi być poniżej α/3 (inaczej A i B nie mogą odrzucać)."""
    assert 2.0 / (lv2.KONFIG["boot"] + 1) < lv2.ALFA / 3 / 5  # zapas ≥ 5× do progu


def test_domyslne_wywolanie_to_przebieg_rejestrowy_bez_znacznika_pilotazu(
    monkeypatch, capsys, mikro
):
    wywolania = []

    def atrapa(konfig, workers, ziarno=lv2.SEED):
        wywolania.append((konfig, workers, ziarno))
        return mikro

    monkeypatch.setattr(lv2, "uruchom", atrapa)
    lv2.main(["--workers", "7"])
    out = capsys.readouterr().out
    assert wywolania == [(lv2.KONFIG, 7, lv2.SEED)]
    assert "PILOTAŻ" not in out and "5000 paneli, bootstrap po dniach 999" in out
    assert f"ziarno {lv2.SEED}." in out and "REGUŁA PIERWSZEJ RUNDY" in out
