"""pomiar_rho_h (karta 017) — parytet z zamrożonym kodem LV2, leakage, VR/ρ̂, bootstrap, brak odsetka trafień."""

from __future__ import annotations

import re
import statistics

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from modele import pomiar_rho_h as m
from symulacje.garch_panel import generuj_panel
from symulacje.moc_var_es import wklady_dzienne
from symulacje.prognozy_lv2 import START, prognoza, zbuduj_zrodla

N_PARYTET = 520  # START + 120 dni: cztery bloki refitu (400, 430, 460, 490)


@pytest.fixture(scope="module")
def panel_parytetu():
    return generuj_panel(N_PARYTET, 2, seed=3, m_intraday=24)


@pytest.fixture(scope="module")
def zrodla(panel_parytetu):
    return zbuduj_zrodla(panel_parytetu)


# ── parytet z zamrożonym kodem (symulacje/prognozy_lv2.py) ──────────────────────────────────────────
@pytest.mark.parametrize("p", [0.05, 0.01])
def test_prognoza_zgodna_z_zamrozonym_zbuduj_zrodla(panel_parytetu, zrodla, p):
    q_ref, _ = prognoza(zrodla, "garch_tnu", p)
    q, _ = m.prognoza_garch_tnu(panel_parytetu["r"].to_numpy(), p)
    np.testing.assert_allclose(q, q_ref, rtol=1e-12, atol=0.0)


def test_diagnostyka_zgodna_z_zamrozonym_kodem(panel_parytetu, zrodla):
    _, diag = m.prognoza_garch_tnu(panel_parytetu["r"].to_numpy())
    for klucz in ("dopasowania", "nie_zbiezne", "brzeg"):
        assert diag[klucz] == zrodla.diag[klucz]
    assert diag["persystencja"] == pytest.approx(zrodla.diag["persystencja"], rel=1e-12)
    assert diag["nu"] == pytest.approx(zrodla.diag["nu"], rel=1e-12)


def test_prognoza_jest_deterministyczna(panel_parytetu):
    r = panel_parytetu["r"].to_numpy()
    np.testing.assert_array_equal(m.prognoza_garch_tnu(r)[0], m.prognoza_garch_tnu(r)[0])


# ── leakage: prognoza dnia t nie widzi zwrotu z dnia ≥ t (R7) ───────────────────────────────────────
def test_prognoza_dnia_t_nie_zalezy_od_zwrotow_z_dni_od_t(panel_parytetu):
    r = panel_parytetu["r"].to_numpy()
    t0 = 470
    r2 = r.copy()
    r2[t0:] *= 2.5
    q, _ = m.prognoza_garch_tnu(r)
    q2, _ = m.prognoza_garch_tnu(r2)
    i0 = t0 - START
    np.testing.assert_array_equal(q[: i0 + 1], q2[: i0 + 1])
    assert np.any(q[i0 + 1 :] != q2[i0 + 1 :], axis=1).all()


# ── walidacja wejścia ───────────────────────────────────────────────────────────────────────────────
def test_prognoza_wymaga_macierzy_dni_x_monety():
    with pytest.raises(ValueError, match="macierzą"):
        m.prognoza_garch_tnu(np.zeros(600))


def test_prognoza_odrzuca_nan(panel_parytetu):
    r = panel_parytetu["r"].to_numpy().copy()
    r[10, 0] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        m.prognoza_garch_tnu(r)


@pytest.mark.parametrize("start", [100, N_PARYTET, N_PARYTET + 5])
def test_prognoza_odrzuca_zly_start(panel_parytetu, start):
    with pytest.raises(ValueError, match="start"):
        m.prognoza_garch_tnu(panel_parytetu["r"].to_numpy(), start=start)


# ── VR i ρ̂ ──────────────────────────────────────────────────────────────────────────────────────────
def test_vr_rho_monety_calkiem_zsynchronizowane():
    n, k, p = 100, 15, 0.05
    h = np.zeros(n)
    h[:5] = 1.0  # odsetek trafień dokładnie p
    vr, rho = m.vr_rho(k * h, k, p)
    assert vr == pytest.approx(k * n / (n - 1), rel=1e-12)
    assert rho == pytest.approx((vr - 1) / (k - 1), rel=1e-12)


def test_vr_rho_zera_to_dolna_granica():
    vr, rho = m.vr_rho(np.zeros(50), 15, 0.05)
    assert vr == 0.0 and rho == pytest.approx(-1 / 14)


@settings(max_examples=60, deadline=None)
@given(
    s=st.lists(st.integers(min_value=0, max_value=15), min_size=2, max_size=300),
    p=st.sampled_from([0.01, 0.05]),
)
def test_vr_rho_zgodne_z_drugim_liczeniem(s, p):
    k = 15
    vr, rho = m.vr_rho(np.array(s, dtype=float), k, p)
    assert vr == pytest.approx(statistics.variance(s) / (k * p * (1 - p)), rel=1e-9, abs=1e-12)
    assert rho == pytest.approx((vr - 1) / (k - 1), rel=1e-9, abs=1e-12)
    assert rho >= -1 / (k - 1) - 1e-12


@settings(max_examples=40, deadline=None)
@given(
    s=st.lists(st.integers(min_value=0, max_value=15), min_size=2, max_size=200),
    zwrot=st.integers(min_value=0, max_value=199),
)
def test_vr_rho_nie_zalezy_od_kolejnosci_dni(s, zwrot):
    a = np.array(s, dtype=float)
    assert m.vr_rho(a, 15)[1] == pytest.approx(m.vr_rho(np.roll(a, zwrot), 15)[1], rel=1e-9)
    assert m.vr_rho(a, 15)[1] == pytest.approx(m.vr_rho(a[::-1], 15)[1], rel=1e-9)


# ── bootstrap blokowy ───────────────────────────────────────────────────────────────────────────────
def test_bootstrap_blok_rowny_n_to_przesuniecie_kolowe_czyli_stale_rho():
    s = np.random.default_rng(1).binomial(15, 0.05, size=120).astype(float)
    rho = m.vr_rho(s, 15)[1]
    wyn = m.rho_bootstrap(s, 15, 0.05, blok=len(s), b=50, ziarno=3)
    np.testing.assert_allclose(wyn, rho, rtol=1e-12)


def test_bootstrap_deterministyczny_z_ziarnem_i_zalezny_od_ziarna():
    s = np.random.default_rng(2).binomial(15, 0.05, size=300).astype(float)
    a = m.rho_bootstrap(s, 15, 0.05, 20, 100, 7)
    np.testing.assert_array_equal(a, m.rho_bootstrap(s, 15, 0.05, 20, 100, 7))
    assert not np.array_equal(a, m.rho_bootstrap(s, 15, 0.05, 20, 100, 8))


@settings(max_examples=30, deadline=None)
@given(
    s=st.lists(st.integers(min_value=0, max_value=15), min_size=5, max_size=120),
    blok=st.integers(min_value=1, max_value=5),
)
def test_bootstrap_ma_ksztalt_i_dolna_granice(s, blok):
    wyn = m.rho_bootstrap(np.array(s, dtype=float), 15, 0.05, blok, 40, 11)
    assert wyn.shape == (40,) and np.isfinite(wyn).all()
    assert (wyn >= -1 / 14 - 1e-12).all()


@pytest.mark.parametrize("blok", [0, -1, 51])
def test_bootstrap_odrzuca_zly_blok(blok):
    with pytest.raises(ValueError, match="blok"):
        m.rho_bootstrap(np.zeros(50), 15, 0.05, blok, 10, 1)


def test_bootstrap_iid_blok_1_odtwarza_zmiennosc_ro_hat():
    rng = np.random.default_rng(5)
    powtorzenia = [m.vr_rho(rng.binomial(15, 0.05, 1700).astype(float), 15)[1] for _ in range(400)]
    s = rng.binomial(15, 0.05, 1700).astype(float)
    se = np.std(m.rho_bootstrap(s, 15, 0.05, 1, 1000, 7), ddof=1)
    assert 0.75 < se / np.std(powtorzenia, ddof=1) < 1.3


def test_bootstrap_blokowy_widzi_skupienia_rozrzutu_ktorych_iid_nie_widzi():
    # ta sama średnia w obu reżimach; w reżimie „stres” rozrzut dziennej liczby trafień jest duży
    rng = np.random.default_rng(9)
    n, dl = 1700, 20
    stres = np.repeat(rng.random(-(-n // dl)) < 0.5, dl)[:n]
    s = np.where(stres, 3.0 * rng.binomial(1, 0.25, n), rng.binomial(1, 0.75, n)).astype(float)
    se_iid = np.std(m.rho_bootstrap(s, 15, 0.05, 1, 1000, 7), ddof=1)
    se_blok = np.std(m.rho_bootstrap(s, 15, 0.05, 20, 1000, 7), ddof=1)
    assert se_blok > 1.5 * se_iid


# ── pomiar, bramka, kontrola ────────────────────────────────────────────────────────────────────────
def _pom(rho: float, se20: float) -> m.Pomiar:
    return m.Pomiar(k=15, n_oos=100, vr=1.0, rho=rho, se={20: se20, 10: se20, 40: se20}, diag={})


def test_bramka_zgodna_z_progiem():
    assert _pom(0.20, 0.03).bramka
    assert not _pom(0.20, 0.05).bramka
    assert _pom(0.20, 0.03).gorna == pytest.approx(0.26)
    assert not _pom(0.30, 0.0).bramka


def test_bramka_bierze_se_z_bloku_20_nie_z_opisowych():
    pom = m.Pomiar(k=15, n_oos=100, vr=1, rho=0.2, se={20: 0.03, 10: 0.5, 40: 0.5}, diag={})
    assert pom.bramka


def test_pomiar_nie_przechowuje_odsetka_trafien():
    assert set(m.Pomiar.__dataclass_fields__) == {"k", "n_oos", "vr", "rho", "se", "diag"}
    pom = m.pomiar(generuj_panel(520, 2, seed=4, m_intraday=24)["r"].to_numpy(), b=50)
    assert not any("traf" in str(k).lower() for k in pom.diag)
    assert pom.n_oos == 120 and pom.k == 2 and set(pom.se) == {20, 10, 40}


def test_kontrola_zwraca_po_jednym_rho_na_panel():
    wyn = m.kontrola(0.8, [1], k=3, n=520)
    assert len(wyn) == 1 and np.isfinite(wyn[0])


# ── dopasowanie trafień do prognoz: ta sama liczba co zamrożony łańcuch LV2 (przegląd kodu 017, uwaga 1) ──
def test_pomiar_zgodny_z_zamrozonym_lancuchem_wklady_dzienne(panel_parytetu, zrodla):
    q_ref, es_ref = prognoza(zrodla, "garch_tnu", m.P)
    s_ref, _ = wklady_dzienne(zrodla.r, q_ref, es_ref, m.P)
    k = zrodla.r.shape[1]
    vr_ref = float(s_ref.var(ddof=1)) / (k * m.P * (1 - m.P))
    pom = m.pomiar(panel_parytetu["r"].to_numpy(), b=20)
    assert pom.n_oos == len(s_ref)
    assert pom.vr == pytest.approx(vr_ref, rel=1e-12)
    assert pom.rho == pytest.approx((vr_ref - 1) / (k - 1), rel=1e-12)


@pytest.mark.parametrize("rho_gen", [0.8, 0.0])
def test_kontrola_zgodna_z_zamrozonym_lancuchem(rho_gen):
    k, n, ziarno = 3, 520, 5
    wyn = m.kontrola(rho_gen, [ziarno], k=k, n=n)[0]
    zr = zbuduj_zrodla(generuj_panel(n, k, seed=ziarno, rho=rho_gen))
    q, es = prognoza(zr, "garch_tnu", m.P)
    s, _ = wklady_dzienne(zr.r, q, es, m.P)
    vr = float(s.var(ddof=1)) / (k * m.P * (1 - m.P))
    assert wyn == pytest.approx((vr - 1) / (k - 1), rel=1e-12)


def test_kontrola_dodatnia_wieksza_niz_ujemna():
    dodatnia = m.kontrola(0.8, [1, 2, 3], k=5, n=520)
    ujemna = m.kontrola(0.0, [101, 102, 103], k=5, n=520)
    assert np.mean(dodatnia) > np.mean(ujemna) + 0.05


# ── stałe z pre-rejestracji (c9bee1c) przypięte testem ──────────────────────────────────────────────
def test_stale_z_pre_rejestracji():
    assert (m.P, m.PROG_RHO, m.BLOK, m.BLOKI_OPIS) == (0.05, 0.282, 20, (10, 40))
    assert (m.B_BOOT, m.ZIARNO, m.N_C2) == (2000, 20261007, 2100)
    assert (m.K_KONTROLI, m.N_KONTROLI) == (15, 2100)
    assert list(m.ZIARNA_DODATNIEJ) == list(range(1, 11))
    assert list(m.ZIARNA_UJEMNEJ) == list(range(101, 111))
    assert m.PRZEDZIAL_DODATNIEJ == (0.242, 0.322) and m.PROG_UJEMNEJ == 0.03


# ── bootstrap: struktura bloków przy n niepodzielnym przez blok, SE z ddof = 1 ─────────────────────
def _bootstrap_petla(s, k, p, blok, b, ziarno):
    n = len(s)
    rng = np.random.default_rng(ziarno)
    starty = rng.integers(0, n, size=(b, -(-n // blok)))
    wyn = []
    for wiersz in starty:
        x = np.concatenate([s[(a + np.arange(blok)) % n] for a in wiersz])[:n]
        wyn.append((x.var(ddof=1) / (k * p * (1 - p)) - 1) / (k - 1))
    return np.array(wyn)


@pytest.mark.parametrize("n, blok", [(1691, 20), (97, 10), (97, 40), (100, 20)])
def test_bootstrap_zgodny_z_naiwna_petla(n, blok):
    s = np.random.default_rng(n).binomial(15, 0.05, size=n).astype(float)
    np.testing.assert_allclose(
        m.rho_bootstrap(s, 15, 0.05, blok, 30, 12345),
        _bootstrap_petla(s, 15, 0.05, blok, 30, 12345),
        rtol=1e-12,
    )


def test_se_w_pomiarze_to_odchylenie_z_ddof_1():
    r = generuj_panel(520, 2, seed=4, m_intraday=24)["r"].to_numpy()
    pom = m.pomiar(r, b=40, ziarno=9)
    q, _ = m.prognoza_garch_tnu(r)
    s = (r[START:] < q).sum(axis=1).astype(float)
    for blok in (20, 10, 40):
        assert pom.se[blok] == pytest.approx(
            np.std(m.rho_bootstrap(s, 2, m.P, blok, 40, 9), ddof=1), rel=1e-12
        )


# ── granica bramki: równość przechodzi (≤) ──────────────────────────────────────────────────────────
def test_bramka_na_granicy_przechodzi_a_tuz_nad_nie(monkeypatch):
    pom = _pom(0.2, 0.03)
    monkeypatch.setattr(m, "PROG_RHO", pom.gorna)
    assert pom.bramka
    monkeypatch.setattr(m, "PROG_RHO", np.nextafter(pom.gorna, 0.0))
    assert not pom.bramka


# ── teksty ──────────────────────────────────────────────────────────────────────────────────────────
def test_okno_nie_domyka_sie_dzis():
    assert "NIE DOMYKA SIĘ (brakuje 9)" in m.tekst_okna(2091)


@pytest.mark.parametrize("n", [2100, 2122])
def test_okno_domyka_sie(n):
    t = m.tekst_okna(n)
    assert "DOMYKA SIĘ" in t and "NIE DOMYKA" not in t


def test_tekst_kontroli_ocenia_kryteria():
    t = m.tekst_kontroli([0.28] * 10, [0.0] * 10)
    assert t.count("ZALICZONA") == 2 and "NIEZALICZONA" not in t
    t = m.tekst_kontroli([0.10] * 10, [0.2] * 10)
    assert t.count("NIEZALICZONA") == 2


# ── main na syntetycznych świecach: reporter nie ujawnia odsetka trafień, nic nie zapisuje ──────────
@pytest.fixture(scope="module")
def katalog_swiec(tmp_path_factory):
    kat = tmp_path_factory.mktemp("swiece_1d")
    r = generuj_panel(560, 3, seed=6, m_intraday=24)["r"].to_numpy()
    dni = pd.date_range("2021-01-01", periods=560, freq="D", tz="UTC")
    for j, sym in enumerate(("AAA", "BBB", "CCC")):
        close = 100.0 * np.exp(np.cumsum(r[:, j]))
        pd.DataFrame({"timestamp": dni, "close": close}).to_parquet(kat / f"{sym}.parquet")
    return kat, str(dni[-1].date())


def _tokeny(tekst: str) -> set[str]:
    return set(re.findall(r"-?\d+(?:[.,]\d+)?", tekst))


def test_main_drukuje_bramke_i_nie_ujawnia_odsetka_trafien(katalog_swiec, capsys):
    kat, do = katalog_swiec
    monety = ("AAA", "BBB", "CCC")
    przed = sorted(p.name for p in kat.iterdir())
    kod = m.main(
        ["--katalog", str(kat), "--do", do, "--monety", ",".join(monety), "--bez-kontroli"]
    )
    wyjscie = capsys.readouterr().out
    assert kod == 0
    assert "Bramka zależności" in wyjscie and "Inwentarz świec 1d" in wyjscie
    for zakazane in ("Kupiec", "Christoffersen", "odsetek trafień", "hit rate"):
        assert zakazane not in wyjscie
    assert sorted(p.name for p in kat.iterdir()) == przed

    ceny = [pd.read_parquet(kat / f"{s}.parquet").set_index("timestamp")["close"] for s in monety]
    r = np.log(pd.concat(ceny, axis=1)).diff().dropna().to_numpy()
    q, _ = m.prognoza_garch_tnu(r)
    odsetek = float((r[START:] < q).mean())
    zakazane = {f"{odsetek:.3f}", f"{odsetek:.4f}", f"{100 * odsetek:.2f}", f"{100 * odsetek:.3f}"}
    assert not (zakazane & _tokeny(wyjscie))


def test_main_ostatnie_wiersze_i_blad_przy_zbyt_duzym_oknie(katalog_swiec, capsys):
    kat, do = katalog_swiec
    baza = ["--katalog", str(kat), "--do", do, "--monety", "AAA,BBB,CCC", "--bez-kontroli"]
    assert m.main([*baza, "--ostatnie", "550"]) == 0
    wyjscie = capsys.readouterr().out
    assert "Okno pomiaru: ostatnie 550 wierszy" in wyjscie and "dni oceny: 150" in wyjscie
    with pytest.raises(ValueError, match="potrzeba"):
        m.main([*baza, "--ostatnie", "9999"])
