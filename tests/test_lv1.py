"""Testy laboratorium LV1 (symulacje/moc_var_es.py, symulacje/run_lv1.py): ręczne wzory, własności
(hypothesis), mikro-kontrole R8, determinizm względem liczby procesów i okablowanie reguły."""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

import symulacje.moc_var_es as mv
import symulacje.run_lv1 as lv
from miara.var_es import as_z2_h0_polozenie_skala, christoffersen_cc, kupiec_uc, var_es_t
from symulacje.garch_panel import generuj_panel

P = 0.05
K = 5


def _dane(seed: int, n: int = 120, k: int = K, p: float = P):
    """Mały panel zwrotów z prognozą t5 o stałym σ: wystarczająco dużo trafień do testów."""
    rng = np.random.default_rng(seed)
    r = rng.standard_t(5, size=(n, k)) * 0.02 * math.sqrt(3 / 5)
    q, es = var_es_t(np.full((n, k), 0.02), p, mv.NU)
    return r, q, es


# --- wzory ręczne ---------------------------------------------------------------------------------


def _t_srednia_reczna(x, mu):
    n = len(x)
    m = sum(x) / n
    s = math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1))
    return (m - mu) / (s / math.sqrt(n))


def _t_klaster_reczny(x, lag):
    n = len(x)
    m = sum(x) / n
    c = [v - m for v in x]
    licznik = mianownik = 0.0
    for t in range(lag, n):
        a = sum(c[t - lag : t]) / lag
        licznik += c[t] * a
        mianownik += (c[t] * a) ** 2
    return licznik / math.sqrt(mianownik)


def test_t_srednia_i_t_klaster_zgodne_z_wzorem_recznym():
    x = np.random.default_rng(1).normal(size=40) ** 2
    assert mv.t_srednia(x, 0.7) == pytest.approx(_t_srednia_reczna(list(x), 0.7), rel=1e-12)
    assert mv.t_klaster(x, 10) == pytest.approx(_t_klaster_reczny(list(x), 10), rel=1e-12)
    macierz = np.stack([x, x[::-1]])  # ostatnia oś = czas, osie wiodące się nie mieszają
    assert mv.t_klaster(macierz, 10)[1] == pytest.approx(_t_klaster_reczny(list(x[::-1]), 10))


def test_t_srednia_stala_seria_to_nan_nie_blad():
    assert np.isnan(mv.t_srednia(np.ones(30), 1.0))
    assert np.isnan(mv.t_klaster(np.ones(30), 10))


def test_wklady_dzienne_zgodne_z_petla():
    r, q, es = _dane(2)
    s, d = mv.wklady_dzienne(r, q, es, P)
    for t in range(r.shape[0]):
        trafienia = [i for i in range(K) if r[t, i] < q[t, i]]
        assert s[t] == len(trafienia)
        assert d[t] == pytest.approx(sum(r[t, i] / es[t, i] / P for i in trafienia) - K)


def test_wklady_dzienne_remis_nie_jest_trafieniem():
    r = np.array([[-1.0, -1.0], [-2.0, 0.5]])
    q = np.array([[-1.0, -0.9], [-1.5, -1.5]])  # r = q w (0, 0): ostra nierówność, bez trafienia
    s, d = mv.wklady_dzienne(r, q, 1.4 * q, 0.1)
    assert s.tolist() == [1.0, 1.0]
    assert d[1] == pytest.approx(-2.0 / (1.4 * -1.5) / 0.1 - 2)


def test_p_boot_reczne_liczenie_stron_i_nan():
    tb = np.array([-2.0, -0.5, 0.1, 1.0, 2.5, np.nan])
    assert mv.p_boot(1.0, tb, "prawa") == pytest.approx((1 + 2) / (1 + 5))  # t* ≥ 1: 1.0 i 2.5
    # równe ogony: lewa (1 + #{t* ≤ −2}) / 6 = 2/6, prawa 6/6 → 2 · 2/6
    assert mv.p_boot(-2.0, tb, "rowne") == pytest.approx(2 * 2 / 6)
    assert mv.p_boot(1.0, tb, "rowne") == pytest.approx(2 * 3 / 6)  # prawa 3/6, lewa 5/6
    assert mv.p_boot(0.0, tb, "rowne") == 1.0  # obcięte do 1
    assert np.isnan(mv.p_boot(float("nan"), tb, "rowne"))
    for zla in ("lewa", "dwu"):
        with pytest.raises(ValueError):
            mv.p_boot(1.0, tb, zla)


def test_rowne_ogony_dziela_rozmiar_po_rowno_przy_skosnym_t():
    """Pod H0 przy skośnych danych każda strona testu „rowne” odrzuca ok. połowę poziomu.

    Dane: wykładnicze (silnie prawoskośne jak S_t), n = 40, test średniej bootstrapem-t.
    Symetryczne |t*| ≥ |t| oddaje tu prawie cały rozmiar lewej stronie (dla porównania).
    """
    rng = np.random.default_rng(31)
    x = rng.exponential(size=(1500, 40))
    idx = rng.integers(0, 40, size=(199, 40))
    lewa = prawa = lewa_sym = prawa_sym = 0
    for wiersz in x:
        t = float(mv.t_srednia(wiersz, 1.0))
        tb = mv.t_srednia(wiersz[idx], wiersz.mean())
        if mv.p_boot(t, tb, "rowne") < 0.10:
            lewa, prawa = lewa + (t < 0), prawa + (t > 0)
        if (1 + np.count_nonzero(np.abs(tb) >= abs(t))) / 200 < 0.10:
            lewa_sym, prawa_sym = lewa_sym + (t < 0), prawa_sym + (t > 0)
    assert 0.025 < lewa / 1500 < 0.08 and 0.025 < prawa / 1500 < 0.08  # nominalnie 5 % i 5 %
    assert prawa_sym < 0.5 * lewa_sym  # stara wersja: prawa strona wyraźnie słabsza


def test_testy_zbiorcze_zgodne_z_petla_bootstrapu():
    r, q, es = _dane(3, n=80)
    b = 30
    idx = np.random.default_rng(4).integers(0, 80, size=(b, 80))
    out = mv.testy_zbiorcze(r, q, es, P, idx)
    s, d = mv.wklady_dzienne(r, q, es, P)
    s, d = list(s), list(d)
    t_a = _t_srednia_reczna(s, K * P)
    t_b = _t_klaster_reczny(s, mv.LAG_KLASTER)
    t_c = _t_srednia_reczna(d, 0.0)
    assert (out["t_a"], out["t_b"], out["t_c"]) == pytest.approx((t_a, t_b, t_c), rel=1e-10)
    ma, md = sum(s) / 80, sum(d) / 80
    ta = [_t_srednia_reczna([s[j] for j in row], ma) for row in idx]
    tb = [_t_klaster_reczny([s[j] for j in row], mv.LAG_KLASTER) for row in idx]
    tc = [_t_srednia_reczna([d[j] for j in row], md) for row in idx]

    def rowne(t, boot):
        prawa = (1 + sum(v >= t for v in boot)) / (1 + b)
        lewa = (1 + sum(v <= t for v in boot)) / (1 + b)
        return min(1.0, 2 * min(prawa, lewa))

    assert out["p_a"] == pytest.approx(rowne(t_a, ta))
    assert out["p_b"] == pytest.approx(rowne(t_b, tb))
    assert out["p_c"] == pytest.approx((1 + sum(v >= t_c for v in tc)) / (1 + b))


def test_bootstrap_partiami_nie_zmienia_wyniku(monkeypatch):
    r, q, es = _dane(5, n=80)
    idx = np.random.default_rng(6).integers(0, 80, size=(31, 80))  # 31 nie dzieli się przez 7
    duze = mv.testy_zbiorcze(r, q, es, P, idx)
    monkeypatch.setattr(mv, "CHUNK_BOOT", 7)
    assert mv.testy_zbiorcze(r, q, es, P, idx) == duze


def test_odrzuca_zbiorczo_bonferroni_i_nan():
    nan = float("nan")
    assert mv.odrzuca_zbiorczo([0.016, 1.0, 1.0], 0.05)  # < 0,05/3
    assert not mv.odrzuca_zbiorczo([0.017, 0.5, 0.2], 0.05)
    assert not mv.odrzuca_zbiorczo([nan, nan, 0.02], 0.05)
    assert mv.odrzuca_zbiorczo([nan, 0.001, nan], 0.05)
    assert mv.odrzuca_zbiorczo([0.024, 1.0], 0.05) and not mv.odrzuca_zbiorczo([0.026, 1.0], 0.05)


def test_mde_reczne_przypadki():
    x = np.array([0.0, 0.05, 0.10, 0.15])
    assert mv.mde(x, np.array([0.05, 0.5, 0.9, 1.0])) == pytest.approx(0.05 + 0.3 / 0.4 * 0.05)
    assert mv.mde(x, np.array([0.9, 0.9, 0.9, 0.9])) == 0.0  # już przy x = 0 (rozmiar ≥ cel)
    assert np.isnan(mv.mde(x, np.array([0.05, 0.3, 0.5, 0.7])))
    # moc wygładzona maksimum narastającym: spadek szumu w środku nie cofa MDE
    assert mv.mde(x, np.array([0.05, 0.85, 0.7, 1.0])) == pytest.approx(0.05 * 0.75 / 0.80)
    # tu wygładzenie zmienia wynik: m = [0.05, 0.6, 0.6, 0.9] zamiast [.., 0.5, ..]
    assert mv.mde(x, np.array([0.05, 0.6, 0.5, 0.9])) == pytest.approx(0.10 + 0.2 / 0.3 * 0.05)


# --- własności (hypothesis) ----------------------------------------------------------------------

SERIA = st.lists(st.floats(-50, 50), min_size=15, max_size=60).map(np.array)


@settings(max_examples=100, deadline=None)
@given(SERIA, st.floats(0.1, 10), st.floats(-20, 20))
def test_skala_i_przesuniecie_t_srednia_i_t_klaster(x, c, a):
    assume(x.std() > 1e-3)
    mu = float(x.mean()) + 0.3
    assert mv.t_srednia(c * x, c * mu) == pytest.approx(mv.t_srednia(x, mu), rel=1e-6, abs=1e-9)
    t0 = mv.t_klaster(x, 10)
    assume(np.isfinite(t0))
    assert mv.t_klaster(c * x + a, 10) == pytest.approx(t0, rel=1e-5, abs=1e-8)


@settings(max_examples=100, deadline=None)
@given(SERIA)
def test_t_srednia_zero_gdy_srednia_rowna_mu(x):
    assume(x.std() > 1e-3)
    assert mv.t_srednia(x, float(x.mean())) == pytest.approx(0.0, abs=1e-9)


@settings(max_examples=40, deadline=None)
@given(st.integers(10, 40))
def test_z_zero_gdy_srednia_sumy_trafien_rowna_K_razy_p(pol):
    # K = 20, p = 5 %: co drugi dzień trafiają 2 monety → S_t ∈ {0, 2}, średnia = 1 = K·p
    n, k, p = 2 * pol, 20, 0.05
    r = np.zeros((n, k))
    r[::2, :2] = -1.0
    q, es = np.full((n, k), -0.5), np.full((n, k), -0.7)
    idx = np.random.default_rng(0).integers(0, n, size=(20, n))
    out = mv.testy_zbiorcze(r, q, es, p, idx)
    assert out["t_a"] == pytest.approx(0.0, abs=1e-12)


@settings(max_examples=40, deadline=None)
@given(st.integers(0, 10**6), st.permutations(range(K)))
def test_permutacja_monet_nie_zmienia_testow_zbiorczych(seed, perm):
    r, q, es = _dane(seed, n=60)
    idx = np.random.default_rng(seed).integers(0, 60, size=(20, 60))
    a = mv.testy_zbiorcze(r, q, es, P, idx)
    b = mv.testy_zbiorcze(r[:, perm], q[:, perm], es[:, perm], P, idx)
    for klucz in ("t_a", "t_b", "t_c"):
        assert b[klucz] == pytest.approx(a[klucz], rel=1e-9, abs=1e-12, nan_ok=True)
    for klucz in ("p_a", "p_b", "p_c"):
        assert b[klucz] == pytest.approx(a[klucz], abs=2 / 21, nan_ok=True)


@settings(max_examples=40, deadline=None)
@given(st.integers(0, 10**6), st.floats(0.1, 10))
def test_wspolna_skala_zwrotow_q_i_es_nie_zmienia_testow(seed, c):
    r, q, es = _dane(seed, n=60)
    idx = np.random.default_rng(seed).integers(0, 60, size=(20, 60))
    a = mv.testy_zbiorcze(r, q, es, P, idx)
    b = mv.testy_zbiorcze(c * r, c * q, c * es, P, idx)
    for klucz, wart in a.items():
        assert b[klucz] == pytest.approx(wart, rel=1e-7, abs=1e-9, nan_ok=True)


@settings(max_examples=40, deadline=None)
@given(st.integers(0, 10**6))
def test_a_i_c_nie_zaleza_od_kolejnosci_dni(seed):
    r, q, es = _dane(seed, n=60)
    perm = np.random.default_rng(seed + 1).permutation(60)
    s, d = mv.wklady_dzienne(r, q, es, P)
    s2, d2 = mv.wklady_dzienne(r[perm], q[perm], es[perm], P)
    assert mv.t_srednia(s2, K * P) == pytest.approx(mv.t_srednia(s, K * P), nan_ok=True)
    assert mv.t_srednia(d2, 0.0) == pytest.approx(mv.t_srednia(d, 0.0), nan_ok=True)


# --- prognozy: brak podglądania przyszłości ------------------------------------------------------


def test_prognozy_sa_znane_w_t_minus_1():
    n = 150
    panel = generuj_panel(n + mv.WARM, 3, seed=7, rho=0.8)
    pierwotne = mv.sigmy_prognoz(panel)
    t0 = 100  # dzień oceny nr t0 (po rozgrzewce); zmieniamy jego zwrot
    zmieniony = {k: v.copy() for k, v in panel.items()}
    zmieniony["r"].iloc[mv.WARM + t0] *= 5.0
    nowe = mv.sigmy_prognoz(zmieniony)
    assert set(pierwotne) == set(mv.PROGNOZY)
    for nazwa in mv.PROGNOZY:
        assert pierwotne[nazwa].shape == (n, 3)
        np.testing.assert_array_equal(nowe[nazwa][: t0 + 1], pierwotne[nazwa][: t0 + 1])
    assert not np.array_equal(nowe["okno10"][t0 + 1], pierwotne["okno10"][t0 + 1])
    assert not np.array_equal(nowe["ewma94"][t0 + 1], pierwotne["ewma94"][t0 + 1])
    np.testing.assert_array_equal(nowe["prawdziwa"], pierwotne["prawdziwa"])  # wyrocznia ≠ f(r)


def test_prognozy_maja_zamierzone_sigmy():
    panel = generuj_panel(100 + mv.WARM, 3, seed=8, rho=0.5)
    sig = mv.sigmy_prognoz(panel)
    wyrocznia = np.sqrt(panel["sigma2"].to_numpy()[mv.WARM :])
    for nazwa in ("prawdziwa", "normalna", "es_za_niski"):
        np.testing.assert_array_equal(sig[nazwa], wyrocznia)  # różnią się tylko q/es
    assert (sig["stala"] == mv.SIGMA_STALA).all()
    for nazwa, x in mv.ZANIZENIA.items():
        np.testing.assert_allclose(sig[nazwa], (1 - x) * wyrocznia)


def test_prognoza_q_es_es_za_niski_ma_prawdziwe_q_i_nizsze_es():
    sigma = np.full((4, 2), 0.03)
    for p in (0.01, 0.05):
        q, es = mv.prognoza_q_es(sigma, "prawdziwa", p)
        q2, es2 = mv.prognoza_q_es(sigma, "es_za_niski", p)
        np.testing.assert_array_equal(q2, q)
        assert (es2 > es).all()  # ES ujemne: „za niskie” co do modułu = mniej ujemne
        zan, _ = mv.prognoza_q_es(sigma * 0.9, "zanizenie_10", p)
        np.testing.assert_allclose(zan, 0.9 * q)  # σ·(1 − x) skaluje kwantyl liniowo
    assert mv.rodzina_prognozy("normalna") == "normal"
    assert mv.rodzina_prognozy("stala") == "t"


# --- mikro-kontrole R8 na silniku ---------------------------------------------------------------


@pytest.fixture(scope="module")
def mikro():
    """30 paneli n = 250, ρ = 0,8, bootstrap 99: silnik `przetworz_panel` w miniaturze."""
    ns = (250,)
    h0 = {
        (250, p, rod): as_z2_h0_polozenie_skala(
            250, p, rod, mv.NU if rod == "t" else None, 300, seed=11
        )
        for p in lv.POZIOMY
        for rod in ("t", "normal")
    }
    lv._init(h0)
    ss = np.random.SeedSequence(2024).spawn(30)
    return np.stack([lv.przetworz_panel((0.8, ns, 99, s)) for s in ss])


def _odsetek(mikro, ip, nazwa, stat):
    return mikro[:, ip, 0, mv.PROGNOZY.index(nazwa), mv.IDX[stat]].mean()


def test_mikro_ksztalt_i_brak_nan(mikro):
    assert mikro.shape == (30, 2, 1, len(mv.PROGNOZY), len(mv.STAT))
    assert np.isfinite(mikro).all()


def test_mikro_kontrola_negatywna_rozmiar_prawdziwej_prognozy(mikro):
    for ip in range(2):
        assert _odsetek(mikro, ip, "prawdziwa", "zb_bonf") <= 0.20  # nominalnie ≤ 5 %
        assert 0.7 * lv.POZIOMY[ip] < _odsetek(mikro, ip, "prawdziwa", "hit") < 1.3 * lv.POZIOMY[ip]


def test_mikro_kontrola_pozytywna_zanizenie_30_proc(mikro):
    for ip in range(2):
        assert _odsetek(mikro, ip, "zanizenie_30", "zb_bonf") >= 0.8


def test_mikro_naiwny_test_ma_zly_rozmiar_a_zbiorczy_nie(mikro):
    ip = lv.POZIOMY.index(0.05)  # ρ = 0,8: 20·n trafień to nie 20·n niezależnych obserwacji (R12)
    assert _odsetek(mikro, ip, "prawdziwa", "naiwny") >= 0.25
    assert _odsetek(mikro, ip, "prawdziwa", "zb_bonf") <= 0.20


def test_statystyki_komorki_naiwny_to_kupiec_a_vr_z_sum_dziennych():
    """Trafienia w 10 dniach po rzędu na wszystkich monetach: Kupiec nie odrzuca (liczba trafień
    równa oczekiwanej), Christoffersen cc odrzuca — więc widać, który test jest „naiwny”."""
    n, k, p = 200, 5, 0.05
    r = np.zeros((n, k))
    r[50:60] = -1.0  # 50 trafień = n·k·p, wszystkie zgrupowane
    q, es = np.full((n, k), -0.5), np.full((n, k), -0.7)
    hit = (r < q).ravel()
    assert kupiec_uc(hit, p)["p_wartosc"] > lv.ALFA > christoffersen_cc(hit, p)["p_wartosc"]
    idx = np.random.default_rng(5).integers(0, n, size=(99, n))
    w = lv.statystyki_komorki(r, q, es, p, np.linspace(-3, 1, 200), idx)
    assert w[mv.IDX["naiwny"]] == 0.0
    s = (r < q).sum(axis=1)
    assert w[mv.IDX["vr"]] == pytest.approx(s.var(ddof=1) / (k * p * (1 - p)))
    zb = mv.testy_zbiorcze(r, q, es, p, idx)
    assert w[mv.IDX["zb_ac"]] == float(min(zb["p_a"], zb["p_c"]) < lv.ALFA / 2)
    prawa = zb["p_a"] < lv.ALFA / 3 and zb["t_a"] > 0
    assert w[mv.IDX["zb_a_prawa"]] == float(prawa)


def test_zagniezdzenie_n_w_jednym_panelu():
    """Komórka n w `przetworz_panel` = statystyki na r[:n], q[:n], es[:n] z bootstrapem po
    indeksach 0..n−1 i rozkładem zerowym Z2 dla tego samego n (mniejsze n = początek panelu)."""
    ns, boot, ziarno = (100, 150), 29, 77
    h0 = {
        (n, p, rod): as_z2_h0_polozenie_skala(
            n, p, rod, mv.NU if rod == "t" else None, 200, seed=n + int(1000 * p) + len(rod)
        )
        for n in ns
        for p in lv.POZIOMY
        for rod in ("t", "normal")
    }
    lv._init(h0)
    wyn = lv.przetworz_panel((0.8, ns, boot, np.random.SeedSequence(ziarno)))
    ss_gen, ss_boot = np.random.SeedSequence(ziarno).spawn(2)
    panel = generuj_panel(max(ns) + mv.WARM, lv.K, seed=lv._ziarno_int(ss_gen), nu=mv.NU, rho=0.8)
    r = panel["r"].to_numpy()[mv.WARM :]
    sig = mv.sigmy_prognoz(panel)
    gen = np.random.default_rng(ss_boot)
    idx = {n: gen.integers(0, n, size=(boot, n)) for n in ns}
    for jn, n in enumerate(ns):
        assert idx[n].shape == (boot, n) and idx[n].max() < n
        for ip, p in enumerate(lv.POZIOMY):
            for nazwa in ("prawdziwa", "normalna", "okno10"):
                q, es = mv.prognoza_q_es(sig[nazwa], nazwa, p)
                h = h0[(n, p, mv.rodzina_prognozy(nazwa))]
                oczek = lv.statystyki_komorki(r[:n], q[:n], es[:n], p, h, idx[n])
                jf = mv.PROGNOZY.index(nazwa)
                np.testing.assert_array_equal(wyn[ip, jn, jf], oczek)


# --- determinizm względem liczby procesów --------------------------------------------------------

KONFIG_MALY = {"ns": (100, 150), "panele": 3, "boot": 19, "h0": 120, "glowne_n": 150}


def test_wynik_nie_zalezy_od_liczby_procesow():
    wyn1, h01 = lv.uruchom(KONFIG_MALY, 1)
    wyn3, h03 = lv.uruchom(KONFIG_MALY, 3)
    assert wyn1.keys() == wyn3.keys() == set(lv.RHOS)
    for rho in lv.RHOS:
        assert wyn1[rho].shape == (3, 2, 2, len(mv.PROGNOZY), len(mv.STAT))
        np.testing.assert_array_equal(wyn1[rho], wyn3[rho])
    assert h01.keys() == h03.keys()
    for k in h01:
        np.testing.assert_array_equal(h01[k], h03[k])
    hit = mv.IDX["hit"]
    for rho in lv.RHOS:  # każdy panel ma własne ziarno: panele się różnią
        assert len(np.unique(wyn1[rho][:, 0, -1, 0, hit])) == KONFIG_MALY["panele"]
    assert not np.array_equal(wyn1[0.5], wyn1[0.8])


def test_smoke_stdout_identyczny_dla_roznych_procesow(capsys):
    lv.main(["--smoke", "--workers", "2"])
    a = capsys.readouterr()
    lv.main(["--smoke", "--workers", "3"])
    b = capsys.readouterr()
    assert a.out == b.out
    assert "TRYB SMOKE" in a.out and "KRYTERIA" in a.out and "MDE zaniżenia" in a.out
    assert "Czas przebiegu" in a.err and "Czas" not in a.out  # czas tylko na stderr


# --- okablowanie reguły MIERZALNA / NIEMIERZALNA -------------------------------------------------

DOBRE = {
    "rozmiar": (0.048, 0.003),
    "moc_normalna": (0.99, 0.002),
    "moc_stala": (0.90, 0.004),
    "kontrola30": (1.0, 0.0),
    "naiwny": (0.27, 0.006),
    "krzywa": [0.05, 0.50, 0.95, 1.0, 1.0, 1.0],  # MDE = 0,05 + 0,3/0,45 · 0,05 ≈ 0,083
    "krzywa_se": [0.003, 0.007, 0.003, 0.0, 0.0, 0.0],
}


def _inne(**zmiany):
    return {**DOBRE, **zmiany}


def _ok(wynik):
    return {k["kod"]: k["ok"] for k in (*wynik["kontrole"], *wynik["kryteria"])}


def test_siatka_x_zgodna_z_prognozami():
    assert lv.GRID[0] == "prawdziwa" and set(lv.GRID) <= set(mv.PROGNOZY)
    assert lv.X_GRID == (0.0, 0.05, 0.10, 0.15, 0.20, 0.30)
    assert [mv.ZANIZENIA[g] for g in lv.GRID[1:]] == list(lv.X_GRID[1:])
    assert set(lv.X_MAX) == set(lv.POZIOMY)


def test_regula_dobre_liczby_to_mierzalna():
    wynik = lv.ocen(DOBRE, 0.01)
    assert wynik["werdykt"] == "TAK" and all(_ok(wynik).values())
    assert len(wynik["kontrole"]) == 3 and len(wynik["kryteria"]) == 3


@pytest.mark.parametrize(
    ("zmiana", "zawodzi"),
    [
        ({"moc_normalna": (0.79, 0.004)}, "ii-a"),
        ({"moc_stala": (0.79, 0.004)}, "ii-b"),
        ({"krzywa": [0.05, 0.30, 0.60, 0.90, 1.0, 1.0]}, "iii"),  # MDE = 0,10 + 0,2/0,3·0,05
        ({"krzywa": [0.05, 0.10, 0.30, 0.50, 0.70, 0.79]}, "iii"),  # nieosiągalne na siatce
    ],
)
def test_regula_jedno_kryterium_zawodzi_to_niemierzalna(zmiana, zawodzi):
    wynik = lv.ocen(_inne(**zmiana), 0.01)
    assert wynik["werdykt"] == "NIE"
    assert [k for k, ok in _ok(wynik).items() if not ok] == [zawodzi]


@pytest.mark.parametrize(
    ("zmiana", "zawodzi"),
    [
        ({"rozmiar": (0.080, 0.003)}, "K1"),
        ({"rozmiar": (0.020, 0.003)}, "K1"),
        ({"kontrola30": (0.90, 0.01)}, "K2"),
        ({"naiwny": (0.06, 0.003)}, "K3"),
    ],
)
def test_regula_kontrola_zawodzi_to_werdykt_wstrzymany(zmiana, zawodzi):
    wynik = lv.ocen(_inne(**zmiana), 0.01)
    assert wynik["werdykt"] == "WSTRZYMANE" and not _ok(wynik)[zawodzi]
    # wstrzymanie ma pierwszeństwo także wtedy, gdy kryteria mierzalności też zawodzą
    gorzej = lv.ocen(_inne(**zmiana, moc_normalna=(0.1, 0.01)), 0.01)
    assert gorzej["werdykt"] == "WSTRZYMANE"


def test_regula_progi_sa_domkniete_po_stronie_spelnienia():
    graniczne = _inne(rozmiar=(0.075, 0.0), moc_normalna=(0.80, 0.0), moc_stala=(0.80, 0.0))
    assert lv.ocen(graniczne, 0.01)["werdykt"] == "TAK"
    assert lv.ocen(_inne(rozmiar=(0.025, 0.0)), 0.01)["werdykt"] == "TAK"


def test_regula_prog_mde_ten_sam_dla_obu_p():
    assert lv.X_MAX == {0.01: 0.10, 0.05: 0.10}
    krzywa = [0.05, 0.70, 0.90, 1.0, 1.0, 1.0]  # MDE = 0,05 + 0,1/0,2 · 0,05 = 0,075
    wolna = [0.05, 0.30, 0.70, 0.90, 1.0, 1.0]  # MDE = 0,10 + 0,1/0,2 · 0,05 = 0,125
    for p in lv.POZIOMY:
        assert lv.ocen(_inne(krzywa=krzywa), p)["werdykt"] == "TAK"
        assert lv.ocen(_inne(krzywa=wolna), p)["werdykt"] == "NIE"


def test_regula_ii_a_jest_kryterium_tylko_przy_1_proc():
    slaba = _inne(moc_normalna=(0.45, 0.007))
    assert lv.ocen(slaba, 0.01)["werdykt"] == "NIE"
    przy5 = lv.ocen(slaba, 0.05)
    assert przy5["werdykt"] == "TAK"
    assert [k["kod"] for k in przy5["kryteria"]] == ["ii-b", "iii"]
    assert [k["kod"] for k in przy5["opis"]] == ["ii-a"] and not przy5["opis"][0]["ok"]


def test_regula_k3_poza_ρ_glownym_jest_opisem():
    slaby_naiwny = _inne(naiwny=(0.06, 0.003))
    assert lv.ocen(slaby_naiwny, 0.01)["werdykt"] == "WSTRZYMANE"
    bez_k3 = lv.ocen(slaby_naiwny, 0.01, z_k3=False)
    assert bez_k3["werdykt"] == "TAK"
    assert [k["kod"] for k in bez_k3["kontrole"]] == ["K1", "K2"]
    assert [k["kod"] for k in bez_k3["opis"]] == ["K3"]


def test_regula_oznacza_wyniki_blisko_progu():
    blisko = lv.ocen(_inne(moc_normalna=(0.81, 0.01)), 0.01)
    daleko = lv.ocen(DOBRE, 0.01)
    assert [k["kod"] for k in blisko["kryteria"] if k["granica"]] == ["ii-a"]
    assert not any(k["granica"] for k in (*daleko["kontrole"], *daleko["kryteria"]))
    # iii: flaga z mocy przy x* = 0,10 i jej SE (MDE ≈ 0,098, moc przy x* 81 % ± 1 pp)
    iii = _inne(krzywa=[0.05, 0.50, 0.81, 1.0, 1.0, 1.0], krzywa_se=[0.003, 0.007, 0.01, 0, 0, 0])
    wynik = lv.ocen(iii, 0.05)
    assert wynik["werdykt"] == "TAK"
    assert [k["kod"] for k in wynik["kryteria"] if k["granica"]] == ["iii"]


def test_liczby_komorki_czyta_wlasciwe_pola():
    f, s = len(mv.PROGNOZY), len(mv.STAT)
    w = np.zeros((4, 2, 3, f, s))
    for jf, nazwa in enumerate(mv.PROGNOZY):
        w[:, 1, 2, jf, mv.IDX["zb_bonf"]] = 0.01 * (jf + 1)  # p = 5 %, trzecie n
        w[:, 1, 2, jf, mv.IDX["naiwny"]] = 0.5 + 0.01 * jf
    w[::2, 1, 2, mv.PROGNOZY.index("prawdziwa"), mv.IDX["zb_bonf"]] = 0.1  # różna po panelach
    liczby = lv.liczby_komorki(w, 1, 2)

    def zb(nazwa):
        return 0.01 * (mv.PROGNOZY.index(nazwa) + 1)

    assert liczby["rozmiar"][0] == pytest.approx(0.5 * (0.1 + 0.01))
    assert liczby["rozmiar"][1] > 0
    assert liczby["moc_normalna"][0] == pytest.approx(zb("normalna"))
    assert liczby["moc_stala"][0] == pytest.approx(zb("stala"))
    assert liczby["kontrola30"][0] == pytest.approx(zb("zanizenie_30"))
    assert liczby["naiwny"][0] == pytest.approx(0.5)
    assert liczby["krzywa"][1:] == pytest.approx([zb(g) for g in lv.GRID[1:]])
    assert liczby["krzywa"][0] == liczby["rozmiar"][0]
    assert liczby["krzywa_se"][0] == liczby["rozmiar"][1] and not liczby["krzywa_se"][1:].any()


def test_mapa_stosuje_k3_tylko_przy_rho_glownym():
    f, s = len(mv.PROGNOZY), len(mv.STAT)
    w = np.zeros((4, 2, 1, f, s))
    zb = mv.IDX["zb_bonf"]
    w[..., zb] = 1.0  # moc 100 % wobec każdej złej prognozy
    w[..., mv.PROGNOZY.index("prawdziwa"), zb] = 0.05  # rozmiar 5 %
    w[:, :, :, :, mv.IDX["naiwny"]] = 0.0  # naiwny test bez zawyżenia: K3 zawodzi
    mapa = lv.mapa_regul({0.5: w, 0.8: w}, (1600,))
    assert {mapa[(0.5, p, 1600)] for p in lv.POZIOMY} == {"TAK"}
    assert {mapa[(0.8, p, 1600)] for p in lv.POZIOMY} == {"WSTRZYMANE"}


def test_przewidywanie_per_moneta_czyta_testy_per_moneta():
    f, s = len(mv.PROGNOZY), len(mv.STAT)
    w = np.zeros((2, 2, 1, f, s))
    for stat, normalna, stala in (("kupiec", 0.4, 0.3), ("cc", 0.85, 0.9), ("z2_rej", 0.9, 0.2)):
        w[:, 0, 0, mv.PROGNOZY.index("normalna"), mv.IDX[stat]] = normalna
        w[:, 0, 0, mv.PROGNOZY.index("stala"), mv.IDX[stat]] = stala
    wiersze = {v["test"]: v["sprawdza"] for v in lv.przewidywanie_per_moneta(w, 0, 0)}
    assert wiersze == {"Kupiec": True, "Christoff. cc": False, "Z2": True}
    w[:, 0, 0, mv.PROGNOZY.index("normalna"), mv.IDX["z2_rej"]] = 0.97  # poza [60; 95] %
    wiersze = {v["test"]: v["sprawdza"] for v in lv.przewidywanie_per_moneta(w, 0, 0)}
    assert not wiersze["Z2"]


def test_konfiguracja_przypieta_do_pre_rejestracji():
    assert lv.SEED == 20_261_009
    assert lv.KONFIG == {
        "ns": (600, 1000, 1600, 2100),
        "panele": 5000,
        "boot": 999,
        "h0": 20_000,
        "glowne_n": 1600,
    }
    assert (lv.RHOS, lv.RHO_GLOWNE, lv.II_A_POZIOMY) == ((0.5, 0.8), 0.8, (0.01,))
    assert (lv.ROZMIAR, lv.MOC_MIN, lv.MOC_KONTROLA, lv.NAIWNY_MIN) == (
        (0.025, 0.075),
        0.8,
        0.95,
        0.1,
    )
    assert lv.P1C_Z2_NORMALNA == (0.60, 0.95)


def test_konfiguracja_pre_rejestracji_spojna():
    assert lv.KONFIG["glowne_n"] in lv.KONFIG["ns"] and lv.KONFIG_SMOKE["glowne_n"] in (
        lv.KONFIG_SMOKE["ns"]
    )
    assert math.sqrt(0.25 / lv.KONFIG["panele"]) <= 0.0072  # SE odsetka ≤ ~0,7 pp przy 50 %
    assert 1 / (lv.KONFIG["boot"] + 1) <= lv.ALFA / 30  # najmniejsza p-wartość ≪ α/3
    assert lv.RHO_GLOWNE in lv.RHOS and lv.POZIOMY == (0.01, 0.05)
    assert lv.K == 20 and lv.ALFA == 0.05
    assert (mv.LAG_KLASTER, mv.WARM, mv.NU, mv.SIGMA_STALA, mv.EWMA_LAMBDA) == (
        10,
        60,
        5.0,
        0.04,
        0.94,
    )


def test_regula_pierwotna_tylko_opis_i_ostrzejsza_przy_5():
    slaba_normalna = _inne(moc_normalna=(0.40, 0.01))
    assert lv.ocen(slaba_normalna, 0.05)["werdykt"] == "TAK"
    stara = lv.ocen(slaba_normalna, 0.05, True, lv.X_MAX_PIERWOTNE, lv.II_A_PIERWOTNE)
    assert stara["werdykt"] == "NIE"
    assert lv.X_MAX_PIERWOTNE[0.01] == lv.X_MAX[0.01] and lv.X_MAX_PIERWOTNE[0.05] == 0.05
