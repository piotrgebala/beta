"""Testy runnera LV2d (karta 021): parytet z LV2c przy s = 0, pilotaż przypięty do niezależnego obliczenia,
pilotaż bez statystyk testu, bramki potwierdzeń i naprawy z przeglądu 019 (straż znaku siecznej, korekty nie
marnowane, cel tuż poniżej początku siatki, NaN = STOP), wybór amplitudy i ścieżki, bramkowanie K7 tylko w A0,
rozdział i rozłączność ziaren.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import symulacje.run_lv2c as rc
import symulacje.run_lv2d as rd
from modele.pomiar_rho_h import prognoza_garch_tnu, vr_rho
from symulacje.garch_panel_regimy import generuj_panel_lv2d
from symulacje.moc_var_es import NU
from symulacje.prognozy_lv2 import prognoza, zbuduj_zrodla
from symulacje.run_lv2 import DIAG, IDX, STAT, _potomne, _ziarno_int

MIKRO = {"n_dni": 520, "start": 400, "boot": 19}
PAR_Z_POZIOMEM = {
    "rho": 0.8,
    "rho_szok": 0.5,
    "persystencja": None,
    "alpha": 0.08,
    "amplituda": 0.8,
    "dlugosc": 300.0,
}
PAR_A0 = rd.par_poziom(0.8, 0.0, 0.0, 300.0)
PAR_LV2C = {"rho": 0.8, "rho_szok": 0.0, "persystencja": None, "alpha": 0.08}


def CISZA(*_):
    return None


def _ss(*klucz):
    return np.random.SeedSequence(7, spawn_key=klucz)


def _pole(vr=2.264, brzeg=0.5, niezb=0.0):
    return {
        "vr": (vr, 0.0),
        "rho": ((vr - 1) / 3, 0.0),
        "brzeg": (brzeg, 0.0),
        "niezb": (niezb, 0.0),
        "pers": (0.99, 0.0),
        "nu": (5.0, 0.0),
        "skala": (2.0, 0.0),
        "panele": 1,
    }


# --- pilot_panel przypięty do niezależnego obliczenia -----------------------------------------------


@pytest.mark.parametrize("klucz", [1, 2, 5])
def test_pilot_panel_zgadza_sie_z_obliczeniem_pisanym_od_nowa(klucz):
    ss = _ss(klucz)
    wynik = rd.pilot_panel((ss, PAR_Z_POZIOMEM, MIKRO))
    r = generuj_panel_lv2d(MIKRO["n_dni"], rd.K, seed=_ziarno_int(ss), nu=NU, **PAR_Z_POZIOMEM)
    r = r["r"].to_numpy()
    q, diag = prognoza_garch_tnu(r, rd.P, MIKRO["start"])
    s = np.array(
        [
            sum(1 for j in range(rd.K) if r[MIKRO["start"] + t, j] < q[t, j])
            for t in range(q.shape[0])
        ],
        dtype=float,
    )
    vr, rho = vr_rho(s, rd.K, rd.P)
    n_fit = diag["dopasowania"]
    okno = np.lib.stride_tricks.sliding_window_view(r[:, 0], 60).std(axis=1, ddof=1)
    skala = np.quantile(okno, 0.9) / np.quantile(okno, 0.1)
    assert diag["brzeg"] != diag["nie_zbiezne"]  # zamiana kolumn miejscami zostałaby wykryta
    assert len(wynik) == len(rd.POLA_PILOT) == 7
    assert wynik[0] == pytest.approx(vr, abs=1e-12)
    assert wynik[1] == pytest.approx(rho, abs=1e-12)
    assert wynik[2] == pytest.approx(diag["brzeg"] / n_fit, abs=1e-12)
    assert wynik[3] == pytest.approx(diag["nie_zbiezne"] / n_fit, abs=1e-12)
    assert wynik[4] == pytest.approx(diag["persystencja"], abs=1e-12)
    assert wynik[5] == pytest.approx(diag["nu"], abs=1e-12)
    assert wynik[6] == pytest.approx(skala, rel=1e-9)


def test_pilotaz_nie_liczy_statystyk_testu_zbiorczego_ani_odsetka_trafien(monkeypatch):
    def zakazane(*_, **__):
        raise AssertionError("pilotaż nie może wołać funkcji testu zbiorczego ani źródeł prognoz")

    for nazwa in ("statystyki_komorki", "zbuduj_zrodla", "prognoza", "prognoza_d"):
        monkeypatch.setattr(rd, nazwa, zakazane, raising=False)
    monkeypatch.setattr(rc, "prognoza_c", zakazane)
    wynik = rd.pilot_panel((_ss(1), PAR_Z_POZIOMEM, MIKRO))
    assert rd.POLA_PILOT == ("vr", "rho", "brzeg", "niezb", "pers", "nu", "skala")
    assert wynik.shape == (7,) and np.isfinite(wynik).all()


def test_nan_w_pilotazu_to_stop_a_nie_zaliczone(monkeypatch):
    monkeypatch.setattr(rd, "pilot_panel", lambda arg: np.array([np.nan] + [0.0] * 6))
    with pytest.raises(rd.StopBlad, match="NaN"):
        rd.pilot(PAR_A0, _ss(1), 2, None, MIKRO)


# --- parytet z LV2c i wyrocznia z poziomem -------------------------------------------------------------


def test_komorka_bez_poziomu_daje_te_same_tablice_co_lv2c():
    ss = _ss(3)
    d = rd.przetworz_panel_d((ss, PAR_A0, MIKRO))
    c = rc.przetworz_panel_c((ss, PAR_LV2C, MIKRO))
    np.testing.assert_array_equal(d[0][: len(rc.PROG_C)], c[0])
    np.testing.assert_array_equal(d[1], c[1])
    assert d[2] == c[2]


def test_kolejnosc_prognoz_dopisuje_kolumny_wyroczni_na_koncu():
    assert rd.PROG_D[: len(rc.PROG_C)] == rc.PROG_C
    assert rd.PROG_D[len(rc.PROG_C) :] == ("zan10", "zan20")


@pytest.fixture(scope="module")
def zrodla_z_poziomem():
    panel = generuj_panel_lv2d(MIKRO["n_dni"], rd.K, seed=11, nu=NU, **PAR_Z_POZIOMEM)
    return panel, zbuduj_zrodla(panel, start=MIKRO["start"])


def test_wyrocznia_widzi_poziom_wariancji(zrodla_z_poziomem):
    panel, zr = zrodla_z_poziomem
    wzorzec = np.sqrt(panel["sigma2"].to_numpy()[MIKRO["start"] :])
    np.testing.assert_allclose(zr.sigma["wyr"], wzorzec)
    bez = generuj_panel_lv2d(MIKRO["n_dni"], rd.K, seed=11, nu=NU, **PAR_A0)
    assert not np.allclose(zr.sigma["wyr"], np.sqrt(bez["sigma2"].to_numpy()[MIKRO["start"] :]))


def test_kolumny_wyroczni_to_dokladne_zanizenia_sigma(zrodla_z_poziomem):
    _, zr = zrodla_z_poziomem
    q_wyr, _ = rd.prognoza_d(zr, "wyr_t5")
    for nazwa, mnoznik in (("zan10", 0.90), ("zan20", 0.80)):
        q, _ = rd.prognoza_d(zr, nazwa)
        np.testing.assert_allclose(q / q_wyr, mnoznik)
    q_a, _ = rd.prognoza_d(zr, rd.KA)
    q_ref, _ = prognoza(zr, "garch_tnu", rd.P)
    np.testing.assert_array_equal(q_a, q_ref)


def test_wynik_panelu_nie_zalezy_od_liczby_paneli_w_komorce():
    ss = _ss(9)
    dwa = rd.uruchom_komorke(PAR_Z_POZIOMEM, ss, 2, None, MIKRO)
    trzy = rd.uruchom_komorke(PAR_Z_POZIOMEM, ss, 3, None, MIKRO)
    np.testing.assert_array_equal(dwa["stat"], trzy["stat"][:2])
    np.testing.assert_array_equal(dwa["diag"], trzy["diag"][:2])


# --- odwrotna_liniowa: naprawy z przeglądu 019 --------------------------------------------------------


def test_odwrotna_liniowa_interpoluje_na_pierwszym_przejsciu_wygladzonego_v():
    assert rd.odwrotna_liniowa([0, 1, 2], [1, 2, 3], 2.5) == pytest.approx(1.5)
    assert rd.odwrotna_liniowa([0, 1, 2, 3], [1, 3, 2, 4], 2.5) == pytest.approx(0.75)
    assert rd.odwrotna_liniowa([0, 1, 2, 3], [1, 2, 2, 3], 2.0) == pytest.approx(1.0)


def test_cel_tuz_ponizej_poczatku_siatki_daje_poczatek_siatki():
    x = rd.odwrotna_liniowa(rc.RHO_SIATKA, [2.72, 2.9, 3.1, 3.3], 2.70, tol_dol=0.14)
    assert x == pytest.approx(0.80)


def test_cel_daleko_ponizej_poczatku_albo_powyzej_konca_jest_poza_zakresem():
    assert rd.odwrotna_liniowa([0, 1], [2.72, 3.0], 2.70, tol_dol=0.01) is None
    assert rd.odwrotna_liniowa([0, 1], [1.0, 2.0], 2.05, tol_gora=0.14) == pytest.approx(1.0)
    assert rd.odwrotna_liniowa([0, 1], [1.0, 2.0], 2.20, tol_gora=0.14) is None
    assert rd.odwrotna_liniowa([0, 1], [1.0, 2.0], 2.01) is None  # domyślnie bez tolerancji u góry


def test_odwrotna_liniowa_z_nan_to_stop():
    with pytest.raises(rd.StopBlad):
        rd.odwrotna_liniowa([0, 1, 2], [1.0, np.nan, 3.0], 2.0)


@settings(max_examples=60, deadline=None)
@given(
    v=st.lists(st.floats(0.0, 5.0, allow_nan=False), min_size=2, max_size=8),
    u=st.floats(0.0, 1.0),
)
def test_odwrotna_liniowa_zwraca_punkt_w_siatce_i_odtwarza_cel(v, u):
    x = np.linspace(0.0, 1.0, len(v))
    gl = np.maximum.accumulate(v)
    cel = min(gl[0] + u * (gl[-1] - gl[0]), gl[-1])
    wynik = rd.odwrotna_liniowa(x, v, cel)
    assert -1e-9 <= wynik <= 1.0 + 1e-9
    assert np.interp(wynik, x, gl) == pytest.approx(cel, abs=1e-9)


# --- korekta sieczna: straż znaku nachylenia -----------------------------------------------------------


def test_sieczna_nie_oddala_sie_od_celu_przy_ujemnym_nachyleniu():
    nowe = rd.korekta_sieczna(0.6, 2.30, rc.SZOK_SIATKA, [1.0, 1.8, 2.1, 2.2, 2.25], 2.5)
    assert nowe is not None and nowe > 0.6
    assert nowe == pytest.approx(
        0.675
    )  # środek między punktem potwierdzenia a następnym punktem siatki


def test_sieczna_przy_dobrym_nachyleniu_idzie_przez_punkt_o_v_najblizszym_celowi():
    x_g, v_g = [0, 0.25, 0.5, 0.75, 1.0], [1.0, 1.5, 2.0, 2.5, 3.0]
    assert rd.korekta_sieczna(0.5, 2.0, x_g, v_g, 2.6) == pytest.approx(0.8)
    # w dół: punkt siatki x = 0,25 (v = 1,5) leży najbliżej celu 2,0; nachylenie (2,8 − 1,5)/0,25 = 5,2
    assert rd.korekta_sieczna(0.5, 2.8, x_g, v_g, 2.0) == pytest.approx(0.5 - 0.8 / 5.2)


def test_sieczna_przycina_do_zakresu_siatki_i_zwraca_none_bez_punktu_po_stronie_celu():
    x_g, v_g = [0, 0.5, 1.0], [1.0, 1.1, 1.2]
    assert rd.korekta_sieczna(0.5, 1.1, x_g, v_g, 9.0) == pytest.approx(1.0)
    assert rd.korekta_sieczna(1.0, 1.2, x_g, v_g, 9.0) is None
    assert rd.korekta_sieczna(0.0, 1.0, x_g, v_g, -9.0) is None


def test_sieczna_z_nan_to_stop():
    with pytest.raises(rd.StopBlad):
        rd.korekta_sieczna(0.5, np.nan, [0, 1], [1.0, 2.0], 1.5)


@settings(max_examples=80, deadline=None)
@given(
    v=st.lists(st.floats(0.0, 5.0, allow_nan=False), min_size=2, max_size=8),
    x_c=st.floats(0.0, 1.0),
    v_c=st.floats(0.0, 5.0),
    cel=st.floats(0.0, 5.0),
)
def test_sieczna_zawsze_w_zakresie_siatki(v, x_c, v_c, cel):
    x_g = np.linspace(0.0, 1.0, len(v))
    nowe = rd.korekta_sieczna(x_c, v_c, x_g, v, cel)
    assert nowe is None or 0.0 <= nowe <= 1.0


# --- wybór amplitudy i ścieżki ------------------------------------------------------------------------

X7 = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5)


def _krok1_wyniki(brzegi, se=0.01):
    return [{"amplituda": x, "brzeg": [b, se]} for x, b in zip(X7, brzegi)]


def test_wybor_amplitudy_none_gdy_wygladzone_maksimum_ponizej_okna():
    s, powod = rd.wybierz_amplitude(_krok1_wyniki([0, 0.05, 0.1, 0.2, 0.3, 0.41, 0.35]))
    assert s is None and "41.3" in powod


def test_wybor_amplitudy_interpoluje_do_srodka_celu():
    s, jak = rd.wybierz_amplitude(_krok1_wyniki([0.02, 0.1, 0.3, 0.45, 0.55, 0.6, 0.58]))
    assert s == pytest.approx(0.9075, abs=6e-4) and "interpolacja" in jak


def test_wybor_amplitudy_na_plaskowyzu_to_dolna_mediana_a_nie_zwyciezca():
    s, jak = rd.wybierz_amplitude(_krok1_wyniki([0.01, 0.02, 0.1, 0.30, 0.44, 0.45, 0.44]))
    assert (
        s == 1.25 and "mediana" in jak
    )  # punkty ≥ 0,43: 1,0; 1,25; 1,5 → dolna mediana 1,25 (nie max 1,25)
    # szerszy błąd standardowy obniża próg płaskowyżu i wciąga więcej punktów
    brzegi = [0.01, 0.02, 0.1, 0.45, 0.46, 0.50, 0.47]
    wasko, _ = rd.wybierz_amplitude(_krok1_wyniki(brzegi, se=0.01))  # próg 0,48 → {1,25}
    szeroko, _ = rd.wybierz_amplitude(
        _krok1_wyniki(brzegi, se=0.03)
    )  # próg 0,44 → {0,75; 1; 1,25; 1,5}
    assert wasko == 1.25 and szeroko == 1.0


def test_wybor_amplitudy_dolna_mediana_dla_parzystej_liczby_punktow():
    # próg = max(0,413; 0,50 − 0,06) = 0,44 → punkty 1,0; 1,25; 1,5 (po 0,45 / 0,50 / 0,45): mediana = 1,25
    s, _ = rd.wybierz_amplitude(_krok1_wyniki([0, 0, 0, 0.1, 0.45, 0.50, 0.45], se=0.03))
    assert s == 1.25
    # dwa punkty (0,45 i 0,46) → dolna mediana to pierwszy z nich
    s2, _ = rd.wybierz_amplitude(_krok1_wyniki([0, 0, 0, 0.1, 0.1, 0.45, 0.46]))
    assert s2 == 1.25


def test_wybor_amplitudy_z_nan_to_stop():
    with pytest.raises(rd.StopBlad):
        rd.wybierz_amplitude(_krok1_wyniki([0, 0, 0, 0.1, np.nan, 0.45, 0.46]))


def test_wybor_sciezki_wedlug_pre_rejestracji():
    def sciezki(vr_s):
        return {"S": [{"x": i, "vr": (v, 0.0)} for i, v in enumerate(vr_s)]}

    s = sciezki([1.5, 1.9, 2.3, 2.6, 3.0])
    assert rd.wybierz_sciezke(1.49, s) == "R_dol"
    assert rd.wybierz_sciezke(1.5, s) == "S"
    assert rd.wybierz_sciezke(3.0, s) == "S"
    assert rd.wybierz_sciezke(3.01, s) == "R_gora"
    assert (
        rd.wybierz_sciezke(2.0, sciezki([1.5, 2.8, 2.0, 2.6, 2.4])) == "S"
    )  # max wygładzone = 2,8
    with pytest.raises(rd.StopBlad):
        rd.wybierz_sciezke(2.0, sciezki([1.5, np.nan, 2.0]))


# --- potwierdzenia: bramki i marnowanie korekt ---------------------------------------------------------

PKT_S = [
    {"x": x, "vr": (v, 0.0)} for x, v in zip((0, 0.25, 0.5, 0.75, 1.0), (1.5, 1.9, 2.3, 2.6, 3.0))
]


def _potwierdz_komorke(monkeypatch, vr, niezb=0.0):
    wywolania = []

    def falszywy(par, ss, panele, pula, konfig):
        wywolania.append((par, ss))
        return _pole(vr=vr, niezb=niezb)

    monkeypatch.setattr(rd, "pilot", falszywy)
    wyn = rd.potwierdz_komorke(
        "B2", 2.264, "S", 0.5, PKT_S, 0.8, 300.0, None, rd.KONFIG_SMOKE, 1, 20, log=CISZA
    )
    return wyn, wywolania


def test_potwierdzenie_komorki_przyjmuje_vr_w_tolerancji_od_razu(monkeypatch):
    wyn, wywolania = _potwierdz_komorke(monkeypatch, 2.264 + rd.TOL_VR - 1e-9)
    assert wyn["status"] == "ok" and len(wywolania) == 1 and rd.TOL_VR == 0.14


def test_potwierdzenie_komorki_nie_marnuje_korekt_gdy_vr_dobre_a_niezbiezne_zle(monkeypatch):
    wyn, wywolania = _potwierdz_komorke(monkeypatch, 2.264, niezb=0.03)
    assert wyn["status"] == "stop2" and len(wywolania) == 1


def test_potwierdzenie_komorki_koryguje_do_dwoch_razy_w_strone_celu(monkeypatch):
    wyn, wywolania = _potwierdz_komorke(monkeypatch, 2.8)
    assert wyn["status"] == "stop2" and len(wywolania) == rd.MAX_POTWIERDZEN == 3
    szoki = [p["rho_szok"] for p, _ in wywolania]
    assert szoki[0] == 0.5 and szoki[1] < 0.5  # VR za wysokie → w dół wzdłuż ścieżki S
    assert wywolania[0][1].spawn_key == (4, 1, 0) and wywolania[1][1].spawn_key == (4, 1, 1)


def _potwierdz_amplitude(monkeypatch, brzeg, niezb=0.0):
    wywolania = []

    def falszywy(par, ss, panele, pula, konfig):
        wywolania.append(par)
        return _pole(brzeg=brzeg, niezb=niezb)

    monkeypatch.setattr(rd, "pilot", falszywy)
    w1 = _krok1_wyniki([0, 0.05, 0.1, 0.3, 0.45, 0.5, 0.52])
    wyn = rd.potwierdz_amplitude(1.0, 0, w1, None, rd.KONFIG_SMOKE, 1, 20, log=CISZA)
    return wyn, wywolania


@pytest.mark.parametrize(
    "brzeg, status",
    [(0.412, "stop2"), (0.414, "ok"), (0.50, "ok"), (0.612, "ok"), (0.614, "stop2")],
)
def test_potwierdzenie_amplitudy_wymaga_odsetka_przy_granicy_w_oknie(monkeypatch, brzeg, status):
    assert rd.BRZEG_OKNO == (0.413, 0.613)
    assert _potwierdz_amplitude(monkeypatch, brzeg)[0]["status"] == status


def test_potwierdzenie_amplitudy_przy_zlej_zbieznosci_konczy_bez_korekt(monkeypatch):
    wyn, wywolania = _potwierdz_amplitude(monkeypatch, 0.5, niezb=0.03)
    assert wyn["status"] == "stop2" and len(wywolania) == 1


def test_potwierdzenie_amplitudy_ma_najwyzej_dwie_korekty(monkeypatch):
    wyn, wywolania = _potwierdz_amplitude(monkeypatch, 0.2)
    assert wyn["status"] == "stop2" and len(wywolania) == 3
    amplitudy = [p["amplituda"] for p in wywolania]
    assert amplitudy[0] == 1.0 and amplitudy[1] > 1.0  # odsetek za niski → większa amplituda


# --- kalibruj na modelu zastępczym ---------------------------------------------------------------------


def _model(b0=0.9, plaskie_dla_300=False):
    """Zastępczy pilotaż: odsetek przy granicy rośnie z amplitudą; VR liniowe w ρ_szok (S) i ρ (R↑, R↓)."""
    zapis = []

    def falszywy(par, ss, panele, pula, konfig):
        zapis.append((par, ss))
        amp = par["amplituda"]
        brzeg = min(0.60, 0.1 + 0.5 * amp)
        if plaskie_dla_300 and par["dlugosc"] == 300.0:
            brzeg = min(0.30, brzeg)
        vr = (
            b0
            + 1.5 * par["rho_szok"]
            + (par["rho"] - 0.8) * (4.0 if par["rho_szok"] >= 0.5 else 1.0)
        )
        return _pole(vr=vr, brzeg=brzeg)

    return falszywy, zapis


def _kalibruj(monkeypatch, **kw):
    falszywy, zapis = _model(**kw)
    monkeypatch.setattr(rd, "pilot", falszywy)
    return rd.kalibruj(None, rd.KONFIG_SMOKE, rd.PANELE_SMOKE, ent=20, log=CISZA), zapis


def test_kalibracja_na_modelu_zastepczym_wybiera_amplitude_i_parametry_komorek(monkeypatch):
    wyn, _ = _kalibruj(monkeypatch)
    assert wyn["amp_star"] == pytest.approx(0.826, abs=1e-3) and wyn["dlugosc_star"] == 300.0
    # VR = 0,9 + 1,5·ρ_szok na ścieżce S: cele 1,717 i 2,264 dają ρ_szok = 0,545 i 0,909
    for nr, szok in (("B1", 0.545), ("B2", 0.909)):
        k = wyn["komorki"][nr]
        assert k["status"] == "ok" and k["sciezka"] == "S"
        assert k["par"]["rho_szok"] == pytest.approx(szok, abs=1e-3)
        assert k["par"]["rho"] == 0.8
    for k in wyn["komorki"].values():
        assert k["par"]["amplituda"] == wyn["amp_star"] and k["par"]["dlugosc"] == 300.0
        assert k["par"]["alpha"] == 0.08 and k["par"]["persystencja"] is None
    assert wyn["n2"]["vr"][0] == pytest.approx(0.9 + 0.0 + (0.0 - 0.8) * 1.0)


def test_kalibracja_kieruje_cele_na_wlasciwe_sciezki(monkeypatch):
    wyn, _ = _kalibruj(monkeypatch, b0=2.0)  # VR(S, 0) = 2,0 > 1,717 → B1 na R↓
    assert wyn["komorki"]["B1"]["sciezka"] == "R_dol" and wyn["komorki"]["B1"]["status"] == "ok"
    assert wyn["komorki"]["B1"]["par"]["rho"] == pytest.approx(0.517, abs=2e-3)
    assert wyn["komorki"]["B1"]["par"]["rho_szok"] == 0.0
    wyn, _ = _kalibruj(monkeypatch, b0=0.9)  # S kończy się na 2,4 < 2,811 → B3 na R↑
    assert wyn["komorki"]["B3"]["sciezka"] == "R_gora" and wyn["komorki"]["B3"]["status"] == "ok"
    assert wyn["komorki"]["B3"]["par"]["rho_szok"] == 1.0
    assert wyn["komorki"]["B3"]["par"]["rho"] == pytest.approx(0.903, abs=2e-3)


def test_kalibracja_cel_daleko_poza_zakresem_sciezki_to_komorka_niedostepna(monkeypatch):
    wyn, _ = _kalibruj(monkeypatch, b0=2.5)  # R↓ zaczyna się na 1,9 > 1,717 + 0,14
    assert (
        wyn["komorki"]["B1"]["status"] == "niedostepna"
        and "poza zakresem" in wyn["komorki"]["B1"]["powod"]
    )
    assert wyn["komorki"]["B2"]["status"] in ("ok", "stop2")


def test_stop1_gdy_zadna_dlugosc_rezimu_nie_daje_odsetka(monkeypatch):
    monkeypatch.setattr(
        rd, "pilot", lambda par, ss, *a: _pole(brzeg=0.30 if par["amplituda"] > 0 else 0.0)
    )
    wyn = rd.kalibruj(None, rd.KONFIG_SMOKE, rd.PANELE_SMOKE, ent=20, log=CISZA)
    assert wyn["amp_star"] is None and "STOP 1" in wyn["stop"] and not wyn["komorki"]


def test_stop1_probuje_najpierw_d_300_potem_d_150_z_osobnymi_ziarnami(monkeypatch):
    zapis = []

    def falszywy(par, ss, panele, pula, konfig):
        zapis.append((par, ss))
        return _pole(brzeg=0.30 if par["amplituda"] > 0 else 0.0)

    monkeypatch.setattr(rd, "pilot", falszywy)
    rd.kalibruj(None, rd.KONFIG_SMOKE, rd.PANELE_SMOKE, ent=20, log=CISZA)
    assert [p["dlugosc"] for p, _ in zapis] == [300.0] * 7 + [150.0] * 7
    klucze = [s.spawn_key for _, s in zapis]
    assert klucze == [(1, 0, j) for j in range(7)] + [(1, 1, j) for j in range(7)]
    assert all(p["rho"] == 0.8 and p["rho_szok"] == 0.5 for p, _ in zapis)
    assert all(s.entropy == 20 for _, s in zapis)


def test_kalibracja_schodzi_do_d_150_gdy_d_300_nie_wystarcza(monkeypatch):
    wyn, zapis = _kalibruj(monkeypatch, plaskie_dla_300=True)
    assert wyn["dlugosc_star"] == 150.0 and wyn["amp_star"] is not None
    assert {p["dlugosc"] for p, s in zapis if s.spawn_key[0] >= 3} == {150.0}


def test_punkt_zerowy_siatki_z_duzym_odsetkiem_przy_granicy_to_stop_bledu(monkeypatch):
    monkeypatch.setattr(rd, "pilot", lambda *a: _pole(brzeg=0.2))
    with pytest.raises(rd.StopBlad, match="zepsute"):
        rd.kalibruj(None, rd.KONFIG_SMOKE, rd.PANELE_SMOKE, ent=20, log=CISZA)


def test_nieudane_potwierdzenie_amplitudy_to_stop2_bez_prob_d_150_i_bez_kroku_2(monkeypatch):
    zapis = []

    def falszywy(par, ss, panele, pula, konfig):
        zapis.append(ss.spawn_key)
        etap = ss.spawn_key[0]
        return _pole(brzeg=0.2 if etap == 2 else min(0.6, 0.1 + 0.5 * par["amplituda"]))

    monkeypatch.setattr(rd, "pilot", falszywy)
    wyn = rd.kalibruj(None, rd.KONFIG_SMOKE, rd.PANELE_SMOKE, ent=20, log=CISZA)
    assert wyn["amp_star"] is None and "STOP 2" in wyn["stop"]
    assert [k[0] for k in zapis].count(2) == 3
    assert all(k[0] in (1, 2) and k[1] == 0 for k in zapis)


# --- kontrola ujemna generatora ----------------------------------------------------------------------


def test_kontrola_n_uzywa_parametrow_z_pre_rejestracji(monkeypatch):
    zapis = []

    def falszywy(par, ss, panele, pula, konfig):
        zapis.append((par, ss, panele))
        return _pole(vr=1.0) | {"rho": (0.01, 0.0)}

    monkeypatch.setattr(rd, "pilot", falszywy)
    wyn = rd.kontrola_n(None, rd.KONFIG_SMOKE, 400, ent=20)
    par, ss, panele = zapis[0]
    assert par == {
        "rho": 0.0,
        "rho_szok": 0.0,
        "persystencja": None,
        "alpha": 0.08,
        "amplituda": 0.0,
        "dlugosc": 300.0,
    }
    assert ss.spawn_key == (5, 0) and panele == rd.PANELE_PILOT["kontrola_n"] == 400
    assert wyn["ok"] is True
    monkeypatch.setattr(rd, "pilot", lambda *a: _pole() | {"rho": (0.03, 0.0)})
    assert rd.kontrola_n(None, rd.KONFIG_SMOKE, 400, ent=20)["ok"] is False


# --- reguła K: bramkowanie K7 tylko w A0, bramki KAL ------------------------------------------------------


def _wyn(k1=0.05, k2=1.0, ka=0.05, kb=0.9, nu=5.0, pers=0.98, nz=0.0, brzeg=0.02, vr=2.264, n=100):
    stat = np.zeros((n, len(rd.PROG_D), len(STAT)))
    zb = IDX["zb_bonf"]
    for nazwa, wartosc in (("wyr_t5", k1), ("zan30", k2), (rd.KA, ka), (rd.KB, kb)):
        stat[: round(wartosc * n), rd.PROG_D.index(nazwa), zb] = 1.0
    stat[:, rd.PROG_D.index(rd.KA), IDX["vr"]] = vr
    diag = np.zeros((n, len(DIAG)))
    diag[:, DIAG.index("dopasowania")] = 1000.0
    diag[:, DIAG.index("nie_zbiezne")] = nz * 1000.0
    diag[:, DIAG.index("brzeg")] = brzeg * 1000.0
    diag[:, DIAG.index("persystencja")] = pers
    diag[:, DIAG.index("nu")] = nu
    return {"stat": stat, "diag": diag, "vr_pom": np.full(n, vr)}


SPEC_A0 = {"k7_pelne": True, "cel_vr": None, "kal_brzeg": False}
SPEC_B = {"k7_pelne": False, "cel_vr": 2.264, "kal_brzeg": True}


def _kody(ocena):
    return [k["kod"] for k in ocena["kontrole"]]


def test_a0_bramkuje_wszystkie_kontrole_k7_a_komorka_b_tylko_k7c():
    wyn = _wyn(brzeg=0.50, pers=0.999, nu=7.0)  # K7a, K7b, K7d zawodzą
    a0 = rd.ocen_komorke(wyn, SPEC_A0)
    assert {"K7a", "K7b", "K7c", "K7d"} <= set(_kody(a0)) and a0["werdykt"] == "WSTRZYMANE"
    b = rd.ocen_komorke(wyn, SPEC_B | {"cel_vr": 2.264})
    assert not {"K7a", "K7b", "K7d"} & set(_kody(b)) and "K7c" in _kody(b)
    assert {k["kod"] for k in b["opis_k7"]} == {"K7a", "K7b", "K7d"}
    assert b["werdykt"] == "TAK"


def test_zle_k7c_wstrzymuje_takze_komorke_b():
    assert rd.ocen_komorke(_wyn(nz=0.03, brzeg=0.5), SPEC_B)["werdykt"] == "WSTRZYMANE"


@pytest.mark.parametrize(
    "ka, kb, werdykt", [(0.05, 0.9, "TAK"), (0.12, 0.9, "NIE"), (0.05, 0.5, "NIE")]
)
def test_werdykt_komorki_to_zamrozony_werdykt_z_kryteriow(ka, kb, werdykt):
    assert rd.ocen_komorke(_wyn(ka=ka, kb=kb, brzeg=0.5), SPEC_B)["werdykt"] == werdykt


def test_zawodzace_k1_albo_k2_wstrzymuje_werdykt():
    assert rd.ocen_komorke(_wyn(k1=0.0), SPEC_A0)["werdykt"] == "WSTRZYMANE"
    assert rd.ocen_komorke(_wyn(k2=0.5), SPEC_A0)["werdykt"] == "WSTRZYMANE"


@pytest.mark.parametrize(
    "brzeg, ok", [(0.412, False), (0.414, True), (0.513, True), (0.612, True), (0.614, False)]
)
def test_kal_brzeg_to_okno_z_pre_rejestracji(brzeg, ok):
    oc = rd.ocen_komorke(_wyn(brzeg=brzeg), SPEC_B)
    kal = next(k for k in oc["kontrole"] if k["kod"] == "KAL-BRZEG")
    assert kal["ok"] is ok
    assert (oc["werdykt"] == "WSTRZYMANE") is (not ok)


@pytest.mark.parametrize(
    "vr, ok", [(2.12, False), (2.13, True), (2.264, True), (2.40, True), (2.41, False)]
)
def test_kal_vr_to_tolerancja_014_wokol_celu(vr, ok):
    oc = rd.ocen_komorke(_wyn(vr=vr, brzeg=0.5), SPEC_B)
    assert next(k for k in oc["kontrole"] if k["kod"] == "KAL-VR")["ok"] is ok


def test_a0_nie_ma_wierszy_kalibracji():
    assert not {"KAL-VR", "KAL-BRZEG"} & set(_kody(rd.ocen_komorke(_wyn(), SPEC_A0)))


# --- specyfikacje komórek i ziarna ---------------------------------------------------------------------


def _kal(**komorki):
    par = {
        "rho": 0.8,
        "rho_szok": 0.4,
        "persystencja": None,
        "alpha": 0.08,
        "amplituda": 0.9,
        "dlugosc": 300.0,
    }
    return {
        "amp_star": 0.9,
        "dlugosc_star": 300.0,
        "komorki": {n: {"status": s, "par": par, "sciezka": "S"} for n, s in komorki.items()},
    }


def test_zbuduj_komorki_a0_zawsze_a_b_tylko_ze_statusem_ok():
    spec = rd.zbuduj_komorki(_kal(B1="niedostepna", B2="ok", B3="stop2"))
    assert list(spec) == ["A0", "B2"]
    assert spec["A0"]["par"] == PAR_A0 and spec["A0"]["k7_pelne"] is True
    assert (
        spec["B2"]["cel_vr"] == 2.264
        and spec["B2"]["k7_pelne"] is False
        and spec["B2"]["kal_brzeg"]
    )
    assert spec["A0"]["panele"] == spec["B2"]["panele"] == 4000
    assert list(rd.zbuduj_komorki({"stop": "STOP 1", "komorki": {}})) == ["A0"]


def test_rejestr_ma_wlasne_ziarno_komorki_takze_gdy_b1_niedostepna(monkeypatch):
    zapis = {}

    def falszywa(par, ss, panele, pula, konfig):
        zapis[len(zapis)] = ss
        return {"stat": np.zeros((1, 1, 1))}

    monkeypatch.setattr(rd, "uruchom_komorke", falszywa)
    spec = rd.zbuduj_komorki(_kal(B2="ok", B3="ok"))
    rd.przebieg(spec, None, rd.KONFIG_SMOKE)
    assert [s.spawn_key for s in zapis.values()] == [(0,), (2,), (3,)]  # B2 zachowuje indeks 2
    assert {s.entropy for s in zapis.values()} == {rd.SEED_REJ}


def test_nowe_ziarna_nie_pokrywaja_sie_z_uzytymi_dotad():
    nowe = {rd.SEED_PILOT, rd.SEED_REJ, rd.SEED_SMOKE, rd.SEED_DRUGA}
    uzyte = {
        20_261_091,
        20_261_019,
        31_415_926,
        20_261_016,
        9_999_021,
        rc.SEED_PILOT,
        rc.SEED_REJ,
    }
    assert len(nowe) == 4 and not nowe & uzyte
    assert (rd.SEED_PILOT, rd.SEED_REJ, rd.SEED_SMOKE, rd.SEED_DRUGA) == (
        20_262_101,
        20_262_021,
        20_269_999,
        27_182_818,
    )


def test_klucze_etapow_pilotazu_sa_parami_rozne():
    klucze = (
        [(1, d, j) for d in range(2) for j in range(7)]
        + [(2, d, r) for d in range(2) for r in range(3)]
        + [(3, s, j) for s in range(3) for j in range(5)]
        + [(4, n, r) for n in range(3) for r in range(3)]
        + [(5, 0), (6, 0)]
    )
    assert len(set(klucze)) == len(klucze)
    assert [rd.NR_SCIEZKI[n] for n in rd.SCIEZKI] == [0, 1, 2]
    assert list(rd.NR_KOMORKI_B.values()) == [0, 1, 2]


def test_ziarna_paneli_pilotazowych_i_rejestrowych_sie_nie_pokrywaja():
    pilot = {
        _ziarno_int(c)
        for klucz in (
            (1, 0, 0),
            (1, 1, 6),
            (2, 0, 0),
            (2, 1, 2),
            (3, 2, 4),
            (4, 1, 2),
            (5, 0),
            (6, 0),
        )
        for c in _potomne(rd.ss_pilot(rd.SEED_PILOT, *klucz), 100)
    }
    rej = {
        _ziarno_int(c)
        for i in range(len(rd.NAZWY_KOMOREK))
        for c in _potomne(np.random.SeedSequence(rd.SEED_REJ, spawn_key=(i,)), 100)
    }
    assert len(pilot) == 800 and len(rej) == 400
    assert not pilot & rej


# --- narzędzia i interfejs -----------------------------------------------------------------------------


def test_rozrzut_skali_nie_zalezy_od_jednostki_i_rosnie_z_przesunieciem_poziomu():
    x = np.random.default_rng(1).standard_normal(1000)
    assert rd.rozrzut_skali(7.0 * x) == pytest.approx(rd.rozrzut_skali(x))
    y = np.concatenate([x[:500], 4.0 * x[500:]])
    assert rd.rozrzut_skali(y) > 2 * rd.rozrzut_skali(x)


def test_zmienne_blas_ustawione_przed_importem_numpy():
    zrodlo = Path(rd.__file__).read_text(encoding="utf-8")
    assert zrodlo.index('os.environ[_zmienna] = "1"') < zrodlo.index("import numpy")


def test_kontrola_n_w_main_drukuje_wynik_i_oznacza_smoke(capsys):
    rd.main(["kontrola-n", "--smoke", "--workers", "1"])
    out = capsys.readouterr().out
    assert "SMOKE" in out and "K-gen-N" in out and ("ZALICZONA" in out or "NIEZALICZONA" in out)


def test_rejestr_wymaga_pliku_kalibracji():
    with pytest.raises(SystemExit):
        rd.main(["rejestr", "--smoke", "--workers", "1"])


def test_rejestr_smoke_na_kalibracji_z_niedostepnymi_komorkami(tmp_path, capsys):
    par = {
        "rho": 0.8,
        "rho_szok": 0.4,
        "persystencja": None,
        "alpha": 0.08,
        "amplituda": 0.9,
        "dlugosc": 300.0,
    }
    kal = {
        "seed_pilot": 1,
        "amp_star": 0.9,
        "dlugosc_star": 300.0,
        "krok1": {},
        "komorki": {
            "B1": {"status": "niedostepna", "powod": "poza zakresem"},
            "B2": {"status": "ok", "sciezka": "S", "cel": 2.264, "par": par},
            "B3": {"status": "stop2", "sciezka": "S", "cel": 2.811, "par": par},
        },
    }
    plik = tmp_path / "kal.json"
    plik.write_text(json.dumps(kal), encoding="utf-8")
    rd.main(["rejestr", "--smoke", "--workers", "1", "--kalibracja", str(plik)])
    out = capsys.readouterr().out
    assert "=== Komórka A0" in out and "=== Komórka B2" in out and "=== Komórka B3" not in out
    assert "B1: NIEDOSTĘPNA" in out and "B3: NIEDOSTĘPNA" in out
    assert "K-gen-D" in out and "WERDYKTY KOMÓREK" in out and "PRZEWIDYWANIA" in out
    assert "K = 4, n = 300" in out  # smoke: 700 − 400 dni oceny, nie wpisane na sztywno 1 691


# --- druk i przewidywania (opis, nie kryteria) ----------------------------------------------------------


@pytest.mark.parametrize("n_oceny, tekst", [(1691, "K = 4, n = 1 691"), (300, "K = 4, n = 300")])
def test_wypisz_komorke_drukuje_prawdziwa_liczbe_dni_oceny(capsys, n_oceny, tekst):
    spec = SPEC_B | {"par": PAR_Z_POZIOMEM}
    rd.wypisz_komorke("B2", spec, _wyn(), n_oceny)
    assert tekst in capsys.readouterr().out


def test_porownanie_z_a0_drukuje_z_roznicy_i_oznacza_ponad_3_se(capsys):
    a0, b2 = _wyn(ka=0.05), _wyn(ka=0.45)
    rd.wypisz_porownanie({"A0": a0, "B2": b2})
    out = capsys.readouterr().out
    ka_a, ka_b = (w["stat"][:, rd.PROG_D.index(rd.KA), IDX["zb_bonf"]] for w in (b2, a0))
    se = np.hypot(ka_a.std(ddof=1), ka_b.std(ddof=1)) / np.sqrt(len(ka_a))
    oczekiwane = (ka_a.mean() - ka_b.mean()) / se
    linia = next(w for w in out.splitlines() if w.strip().startswith("B2 − A0, K-a"))
    assert float(linia.split(":")[1].split()[0]) == pytest.approx(oczekiwane, abs=0.01)
    assert "[> 3 SE]" in linia
    assert "B1 − A0" not in out


def test_porownanie_bez_a0_nic_nie_drukuje(capsys):
    rd.wypisz_porownanie({"B2": _wyn()})
    assert capsys.readouterr().out == ""


def _kal_przew(**zmiany):
    kal = {
        "amp_star": 1.086,
        "dlugosc_star": 300.0,
        "krok1": {"1.0": [{"brzeg": (0.52, 0.01)}], "0.5": [{"brzeg": (0.40, 0.01)}]},
        "komorki": {
            "B1": {"status": "ok", "sciezka": "R_dol"},
            "B2": {"status": "ok", "sciezka": "S"},
            "B3": {"status": "ok", "sciezka": "R_gora"},
        },
    }
    return kal | zmiany


def test_przewidywania_licza_sie_z_wyniku_i_kalibracji():
    wyniki = {"A0": _wyn(ka=0.06, kb=0.5), "B2": _wyn(ka=0.40, kb=0.07, nz=0.0)}
    oceny = {"A0": {"werdykt": "NIE"}, "B2": {"werdykt": "NIE"}}
    w = dict(rd.przewidywania(oceny, wyniki, _kal_przew()))
    assert w["D* = 300 (przewidywane)"] and w["s* ∈ [0,5; 1,25]"] and w["B3 na ścieżce R↑"]
    assert w["odsetek przy granicy w ogóle sięga 51,3 % (surowy punkt siatki)"]
    assert w["A0: K-a ∈ [5%; 8%]"] and w["B2: K-a ∈ [8%; 16%]"] is False
    assert w["B2: K-a ≤ 10 % (przewidywane 40 %)"] is False
    assert w["B2: K-b ≥ 80 % (przewidywane 7 %)"] is False
    assert w["werdykt A0 = NIE"] and w["werdykt B2 = NIE"]
    assert "B1: K-a ∈ [7%; 14%]" not in w  # komórek bez wyniku nie oceniamy


def test_przewidywania_przy_stop_1_nie_zakladaja_amplitudy():
    kal = _kal_przew(amp_star=None, dlugosc_star=None, krok1={})
    w = dict(rd.przewidywania({}, {}, kal))
    assert w["kalibracja odsetka możliwa (nie STOP 1)"] is False
    assert w["s* ∈ [0,5; 1,25]"] is False
    assert w["odsetek przy granicy w ogóle sięga 51,3 % (surowy punkt siatki)"] is False


def test_ziarno_drugiej_drogi_w_skrypcie_jest_tym_z_modulu():
    skrypt = (
        Path(rd.__file__).parents[1] / "runs/2026-10-08_021-lv2d-regimy-wariancji/druga_droga.py"
    )
    tekst = skrypt.read_text(encoding="utf-8")
    assert f"ZIARNO = {rd.SEED_DRUGA:_}" in tekst
