"""Runner LV2c (karta 019): narzędzia kalibracji, brak podglądu reguły K w pilotażu, parytet z zamrożonym
torem LV2, ocena komórek (K7b/K7d, KAL), logika kalibracji na sztucznym pilotażu."""

from __future__ import annotations

import inspect
import json

import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

import symulacje.run_lv2c as rc
from modele.pomiar_rho_h import prognoza_garch_tnu, vr_rho
from symulacje.garch_panel_wspolny_szok import generuj_panel_lv2c
from symulacje.prognozy_lv2 import prognoza, zbuduj_zrodla
from symulacje.run_lv2 import DIAG, IDX, STAT, _potomne, _ziarno_int

MIKRO = {"n_dni": 520, "start": 400, "boot": 19}
PAR_LV2 = {"rho": 0.8, "rho_szok": 0.0, "persystencja": None, "alpha": 0.08}
PAR_PG = {"rho": 0.8, "rho_szok": 0.6, "persystencja": 0.9999, "alpha": 0.16}


def _ss(*klucz):
    return np.random.SeedSequence(7, spawn_key=klucz)


# --- odwrotna_liniowa, korekta_sieczna ------------------------------------------------------------


def test_odwrotna_liniowa_interpoluje_na_odcinku():
    assert rc.odwrotna_liniowa([0, 1, 2], [1.0, 2.0, 4.0], 3.0) == pytest.approx(1.5)
    assert rc.odwrotna_liniowa([0, 1, 2], [1.0, 2.0, 4.0], 1.0) == pytest.approx(0.0)
    assert rc.odwrotna_liniowa([0, 1, 2], [1.0, 2.0, 4.0], 4.0) == pytest.approx(2.0)


def test_odwrotna_liniowa_poza_zakresem_daje_none():
    assert rc.odwrotna_liniowa([0, 1, 2], [1.0, 2.0, 4.0], 4.5) is None
    assert rc.odwrotna_liniowa([0, 1, 2], [1.0, 2.0, 4.0], 0.9) is None


def test_odwrotna_liniowa_wygladza_szum_maksimum_narastajacym():
    # v nie rośnie monotonicznie (szum pilotażu): spadek na środku jest spłaszczony do plateau
    v = [1.0, 2.0, 1.8, 3.0]
    assert rc.odwrotna_liniowa([0, 1, 2, 3], v, 2.0) == pytest.approx(1.0)
    assert rc.odwrotna_liniowa([0, 1, 2, 3], v, 2.5) == pytest.approx(2.5)


@settings(max_examples=60, deadline=None)
@given(
    v=st.lists(st.floats(0.5, 5.0), min_size=5, max_size=5),
    u=st.floats(0.0, 1.0),
)
def test_odwrotna_liniowa_odtwarza_cel_na_wygladzonym_v(v, u):
    x = np.array(rc.SZOK_SIATKA)
    vm = np.maximum.accumulate(v)
    cel = vm[0] + u * (vm[-1] - vm[0])
    wynik = rc.odwrotna_liniowa(x, v, cel)
    assert wynik is not None and x[0] <= wynik <= x[-1]
    assert np.interp(wynik, x, vm) == pytest.approx(cel, abs=1e-9)


def test_korekta_sieczna_wartosc_reczna_i_obciecie():
    x_g, v_g = [0.0, 0.5, 1.0], [1.0, 1.5, 2.6]
    # v(0.5) = 1.5 < cel: sieczna przez (0.5; 1.5) i (1.0; 2.6) trafia w cel liniowo
    assert rc.korekta_sieczna(0.5, 1.5, x_g, v_g, 2.05) == pytest.approx(0.75)
    # wynik poza siatką jest obcięty do jej końca
    assert rc.korekta_sieczna(0.5, 1.5, x_g, v_g, 9.0) == pytest.approx(1.0)
    # brak punktu siatki po stronie celu → None
    assert rc.korekta_sieczna(1.0, 2.6, x_g, v_g, 3.5) is None


@settings(max_examples=60, deadline=None)
@given(
    x_c=st.floats(0.0, 1.0),
    v_c=st.floats(0.5, 5.0),
    cel=st.floats(0.5, 5.0),
    v=st.lists(st.floats(0.5, 5.0), min_size=5, max_size=5),
)
def test_korekta_sieczna_zostaje_w_zakresie_siatki(x_c, v_c, cel, v):
    x_g = list(rc.SZOK_SIATKA)
    nowe = rc.korekta_sieczna(x_c, v_c, x_g, v, cel)
    assert nowe is None or min(x_g) <= nowe <= max(x_g)


def test_wybierz_alfa_najmniejsze_z_warunkiem_na_brzeg_i_niezbiezne():
    def w(alfa, brzeg, niezb):
        return {"alfa": alfa, "brzeg": (brzeg, 0.0), "niezb": (niezb, 0.0)}

    wyniki = [w(0.08, 0.30, 0.0), w(0.12, 0.50, 0.03), w(0.16, 0.50, 0.01), w(0.20, 0.60, 0.0)]
    assert rc.wybierz_alfa(wyniki) == 0.16  # 0,12 ma zbyt wiele niezbieżnych
    assert rc.wybierz_alfa([w(0.08, 0.30, 0.0), w(0.12, 0.40, 0.0)]) is None
    assert rc.wybierz_alfa([w(0.08, 0.463, 0.02)]) == 0.08  # progi włącznie


# --- pilotaż: pola, determinizm, brak podglądu reguły K --------------------------------------------


def test_pilot_panel_zwraca_szesc_skonczonych_pol_i_jest_deterministyczny():
    a = rc.pilot_panel((_ss(0), PAR_LV2, MIKRO))
    b = rc.pilot_panel((_ss(0), PAR_LV2, MIKRO))
    assert a.shape == (len(rc.POLA_PILOT),) and np.isfinite(a).all()
    assert np.array_equal(a, b)
    assert 0.0 <= a[2] <= 1.0 and 0.0 <= a[3] <= 1.0 and a[5] > 2.0
    assert not np.array_equal(a, rc.pilot_panel((_ss(1), PAR_LV2, MIKRO)))


@pytest.mark.parametrize(
    "funkcja",
    [rc.pilot_panel, rc.pilot, rc.kalibruj, rc.potwierdz, rc.kontrola_n, rc.wybierz_alfa],
)
def test_pilotaz_nie_ma_dostepu_do_testu_zbiorczego_ani_odsetka_trafien(funkcja):
    zrodlo = inspect.getsource(funkcja)
    for zakazane in (
        "statystyki_komorki",
        "zbuduj_zrodla",
        "ocen_k",
        "zb_bonf",
        "testy_zbiorcze",
        "prognoza(",
        "przetworz_panel_c",
        "IDX[",
        "STAT",
    ):
        assert zakazane not in zrodlo, (funkcja.__name__, zakazane)


def test_pilot_liczy_tylko_pola_dozwolone_w_pre_rejestracji():
    assert rc.POLA_PILOT == ("vr", "rho", "brzeg", "niezb", "pers", "nu")
    w = rc.pilot(PAR_LV2, _ss(2), 2, None, MIKRO)
    assert set(w) == {*rc.POLA_PILOT, "panele"} and w["panele"] == 2


def test_pilot_nie_zalezy_od_liczby_procesow():
    zad = [(s, PAR_PG, MIKRO) for s in _potomne(_ss(3), 3)]
    szereg = rc._mapuj(rc.pilot_panel, zad, None)
    with rc.pula_procesow(2) as pula:
        rownolegle = rc._mapuj(rc.pilot_panel, zad, pula)
    assert all(np.array_equal(a, b) for a, b in zip(szereg, rownolegle))


# --- parytet toru pilotażowego i rejestrowego -----------------------------------------------------


def test_pilotaz_i_przebieg_rejestrowy_maja_te_same_kwantyle_garch_tnu():
    panel = generuj_panel_lv2c(MIKRO["n_dni"], rc.K, seed=11, **PAR_PG)
    q_pilot, _ = prognoza_garch_tnu(panel["r"].to_numpy(), rc.P, MIKRO["start"])
    zr = zbuduj_zrodla(panel, start=MIKRO["start"])
    q_rej, _ = prognoza(zr, "garch_tnu", rc.P)
    assert np.allclose(q_pilot, q_rej, rtol=0, atol=1e-12)


def test_prognoza_c_zgodna_z_zamrozonymi_prognozami_i_mnoznikami():
    panel = generuj_panel_lv2c(MIKRO["n_dni"], rc.K, seed=5, **PAR_LV2)
    zr = zbuduj_zrodla(panel, start=MIKRO["start"])
    for nazwa, zamr in rc.ZAMROZONE.items():
        q, es = rc.prognoza_c(zr, nazwa)
        q0, es0 = prognoza(zr, zamr, rc.P)
        assert np.array_equal(q, q0) and np.array_equal(es, es0), nazwa
    q90, es90 = rc.prognoza_c(zr, "garch_x0.90")
    q95, es95 = rc.prognoza_c(zr, "garch_x0.95")
    assert np.allclose(q95, q90 * 0.95 / 0.90) and np.allclose(es95, es90 * 0.95 / 0.90)
    q70, _ = rc.prognoza_c(zr, "garch_x0.70")
    assert np.allclose(q70, q90 * 0.70 / 0.90)


def test_przetworz_panel_c_ksztalt_determinizm_i_parytet_vr():
    arg = (_ss(4), PAR_PG, MIKRO)
    stat, diag, vr_pom = rc.przetworz_panel_c(arg)
    stat2, diag2, vr_pom2 = rc.przetworz_panel_c(arg)
    assert stat.shape == (len(rc.PROG_C), len(STAT)) and diag.shape == (len(DIAG),)
    assert np.array_equal(stat, stat2) and np.array_equal(diag, diag2) and vr_pom == vr_pom2
    assert stat[rc.PROG_C.index(rc.KA), IDX["vr"]] == pytest.approx(vr_pom, abs=1e-12)
    # liczba trafień tego panelu liczona niezależnie z wygenerowanego panelu
    ss_gen, _ = _potomne(_ss(4), 2)
    panel = generuj_panel_lv2c(MIKRO["n_dni"], rc.K, seed=_ziarno_int(ss_gen), **PAR_PG)
    zr = zbuduj_zrodla(panel, start=MIKRO["start"])
    q, _ = prognoza(zr, "garch_tnu", rc.P)
    s = (zr.r < q).sum(axis=1).astype(float)
    assert vr_rho(s, rc.K, rc.P)[0] == pytest.approx(vr_pom, abs=1e-12)


def test_uruchom_komorke_nie_zalezy_od_liczby_procesow():
    a = rc.uruchom_komorke(PAR_LV2, _ss(6), 2, None, MIKRO)
    with rc.pula_procesow(2) as pula:
        b = rc.uruchom_komorke(PAR_LV2, _ss(6), 2, pula, MIKRO)
    for klucz in a:
        assert np.array_equal(a[klucz], b[klucz]), klucz


# --- ocena komórek na sztucznych wynikach ---------------------------------------------------------


def _wyn(odsetki: dict, n=400, vr=2.264, nu=5.0, pers=0.98, niezb=0.0, brzeg=0.0):
    stat = np.zeros((n, len(rc.PROG_C), len(STAT)))
    for nazwa, ulamek in odsetki.items():
        stat[: round(ulamek * n), rc.PROG_C.index(nazwa), IDX["zb_bonf"]] = 1.0
    stat[:, rc.PROG_C.index(rc.KA), IDX["vr"]] = vr
    diag = np.tile([100.0, 100.0 * niezb, 100.0 * brzeg, pers, nu], (n, 1))
    return {"stat": stat, "diag": diag, "vr_pom": np.full(n, vr)}


BAZA = {"wyr_t5": 0.05, "zan30": 1.0, "garch_x1.00": 0.05, "garch_x0.90": 0.9}
SPEC_OPIS = {"k7bd": False, "cel_vr": None, "kal_brzeg": False, "werdykt": True}
SPEC_KAL = {"k7bd": False, "cel_vr": 2.264, "kal_brzeg": True, "werdykt": True}
SPEC_A0 = {"k7bd": True, "cel_vr": None, "kal_brzeg": False, "werdykt": True}


def _kody(oc):
    return [k["kod"] for k in oc["kontrole"]]


def test_ocena_tak_gdy_kryteria_i_kontrole_przechodza():
    assert rc.ocen_komorke(_wyn(BAZA), SPEC_OPIS)["werdykt"] == "TAK"


def test_ocena_nie_gdy_moc_za_mala_a_kontrole_ok():
    oc = rc.ocen_komorke(_wyn(BAZA | {"garch_x0.90": 0.4}), SPEC_OPIS)
    assert oc["werdykt"] == "NIE"


def test_ocena_wstrzymana_gdy_kontrola_negatywna_zawodzi():
    assert rc.ocen_komorke(_wyn(BAZA | {"wyr_t5": 0.0}), SPEC_OPIS)["werdykt"] == "WSTRZYMANE"
    assert rc.ocen_komorke(_wyn(BAZA | {"zan30": 0.5}), SPEC_OPIS)["werdykt"] == "WSTRZYMANE"


def test_k7b_i_k7d_bramkuja_tylko_gdy_spec_k7bd():
    wyn = _wyn(BAZA, pers=0.9999, brzeg=0.5)
    oc_a0 = rc.ocen_komorke(wyn, SPEC_A0)
    assert {"K7b", "K7d"} <= set(_kody(oc_a0)) and oc_a0["werdykt"] == "WSTRZYMANE"
    oc_a1 = rc.ocen_komorke(wyn, SPEC_OPIS)
    assert "K7b" not in _kody(oc_a1) and "K7d" not in _kody(oc_a1)
    assert [k["kod"] for k in oc_a1["opis_k7bd"]] == ["K7b", "K7d"]
    assert oc_a1["werdykt"] == "TAK"
    assert rc.ocen_komorke(wyn, SPEC_A0)["opis_k7bd"] == []


def test_k7a_i_k7c_bramkuja_zawsze():
    assert rc.ocen_komorke(_wyn(BAZA, nu=9.0), SPEC_OPIS)["werdykt"] == "WSTRZYMANE"
    assert rc.ocen_komorke(_wyn(BAZA, niezb=0.05), SPEC_OPIS)["werdykt"] == "WSTRZYMANE"


def test_kalibracja_bramkuje_tak_i_nie():
    ok = rc.ocen_komorke(_wyn(BAZA, vr=2.3, brzeg=0.51), SPEC_KAL)
    assert {"KAL-VR", "KAL-BRZEG"} <= set(_kody(ok)) and ok["werdykt"] == "TAK"
    za_male_vr = rc.ocen_komorke(_wyn(BAZA, vr=2.0, brzeg=0.51), SPEC_KAL)
    assert za_male_vr["werdykt"] == "WSTRZYMANE"
    za_maly_brzeg = rc.ocen_komorke(_wyn(BAZA, vr=2.264, brzeg=0.30), SPEC_KAL)
    assert za_maly_brzeg["werdykt"] == "WSTRZYMANE"
    nie_bez_kalibracji = rc.ocen_komorke(_wyn(BAZA | {"garch_x0.90": 0.4}, vr=2.0), SPEC_KAL)
    assert nie_bez_kalibracji["werdykt"] == "WSTRZYMANE"  # NIE też wymaga zgodnej kalibracji


def test_granice_kalibracji_przedzial_domkniety_w_okolicy_progow():
    # 46,3 % i 56,3 % dzielone przez 100 w diagnostyce mają błąd zaokrąglenia, więc sprawdzamy tuż obok progów
    for brzeg, vr, oczekiwane in (
        (0.4631, 2.264 + rc.TOL_VR - 0.001, True),
        (0.5629, 2.264 - rc.TOL_VR + 0.001, True),
        (0.4629, 2.264, False),
        (0.5631, 2.264, False),
        (0.51, 2.264 + rc.TOL_VR + 0.001, False),
    ):
        oc = rc.ocen_komorke(_wyn(BAZA, vr=vr, brzeg=brzeg), SPEC_KAL)
        assert (on_ok(oc, "KAL-VR") and on_ok(oc, "KAL-BRZEG")) is oczekiwane, (brzeg, vr)


def on_ok(oc, kod):
    return next(k for k in oc["kontrole"] if k["kod"] == kod)["ok"]


def test_krzywa_mocy_i_kgen_d_i_roznica_se():
    wyn = _wyn(BAZA | {"garch_x0.80": 0.97, "garch_x0.70": 1.0}, vr=1.846)
    x, moc, se = rc.krzywa_mocy(wyn)
    assert x == pytest.approx([0.0, 0.05, 0.10, 0.15, 0.20, 0.30])
    assert moc[0] == pytest.approx(0.05) and moc[2] == pytest.approx(0.9) and moc[-1] == 1.0
    assert se.shape == x.shape
    assert rc.kgen_d(wyn) == (pytest.approx(1.846), True)
    assert rc.kgen_d(_wyn(BAZA, vr=2.1))[1] is False
    assert rc.roznica_se((0.5, 0.03), (0.4, 0.04)) == pytest.approx(2.0)
    assert rc.roznica_se((0.0, 0.0), (0.0, 0.0)) == 0.0  # np. 0 odrzuceń w obu komórkach
    assert rc.roznica_se((0.1, 0.0), (0.0, 0.0)) == float("inf")
    assert rc.roznica_se((0.0, 0.0), (0.1, 0.0)) == float("-inf")


def test_wypisz_komorke_i_przewidywania_dzialaja_na_sztucznych_wynikach(capsys):
    wyn = _wyn(BAZA | {"garch_x0.80": 0.97, "garch_x0.70": 1.0}, vr=2.3, brzeg=0.5)
    spec = SPEC_KAL | {"par": PAR_PG, "panele": 400}
    oc = rc.wypisz_komorke("A1", spec, wyn)
    wyjscie = capsys.readouterr().out
    assert "Komórka A1" in wyjscie and "KAL-VR" in wyjscie and "MDE" in wyjscie
    assert oc["werdykt"] == "TAK"
    kal = {"alfa_star": 0.16, "komorki": {"A2": {"par": {"rho": 0.9}}}}
    pred = rc.przewidywania({"A1": oc}, {"A1": wyn}, kal)
    assert all(isinstance(t, str) and isinstance(ok, bool) for t, ok in pred)
    assert ("A2 wymagała kroku 2b (ρ > 0,8)", True) in pred
    rc.wypisz_dekompozycje({"A1": wyn, "A3": wyn})
    assert "A3 − A1" in capsys.readouterr().out


# --- logika kalibracji na sztucznym pilotażu ------------------------------------------------------

BRZEG_PO_ALFA = {0.08: 0.30, 0.12: 0.40, 0.16: 0.50, 0.20: 0.55, 0.25: 0.60, 0.30: 0.65}


def _fikcyjny_pilot(vr_funkcja, brzeg=lambda a: BRZEG_PO_ALFA[a], przesuniecie_potw=0.0):
    wywolania = []

    def pilot(par, ss, panele, pula, konfig):
        wywolania.append((par, ss.spawn_key))
        vr = vr_funkcja(par["rho"], par["rho_szok"])
        if ss.spawn_key[0] == 4:
            vr += przesuniecie_potw
        return {
            "vr": (vr, 0.01),
            "rho": ((vr - 1) / 3, 0.003),
            "brzeg": (brzeg(par["alpha"]), 0.01),
            "niezb": (0.0, 0.0),
            "pers": (0.99, 0.001),
            "nu": (4.5, 0.05),
            "panele": panele,
        }

    pilot.wywolania = wywolania
    return pilot


def _kal(monkeypatch, pilot):
    monkeypatch.setattr(rc, "pilot", pilot)
    return rc.kalibruj(None, MIKRO, rc.PANELE_SMOKE, log=lambda t: None)


def vr_liniowe(rho, rs):
    return 1.2 + 1.2 * rs + 4.0 * (rho - 0.8)


def test_kalibracja_wybiera_alfa_a1_przez_rho_szok_a2_przez_krok_2b(monkeypatch):
    pilot = _fikcyjny_pilot(vr_liniowe)
    wyn = _kal(monkeypatch, pilot)
    assert wyn["alfa_star"] == 0.16 and "stop" not in wyn
    a1, a2 = wyn["komorki"]["A1"], wyn["komorki"]["A2"]
    assert a1["status"] == "ok" and a1["os"] == "rho_szok"
    assert a1["par"] == {"rho": 0.8, "rho_szok": 0.887, "persystencja": 0.9999, "alpha": 0.16}
    assert a2["status"] == "ok" and a2["os"] == "rho"
    assert a2["par"]["rho_szok"] == 1.0 and a2["par"]["rho"] == pytest.approx(0.903, abs=2e-3)
    assert [len(wyn["krok1"]), len(wyn["krok2a"]), len(wyn["krok2b"])] == [6, 5, 4]
    json.dumps(wyn)  # wynik musi się serializować do kalibracja.json


def test_kalibracja_stop_1_gdy_zaden_alfa_nie_daje_brzegu(monkeypatch):
    pilot = _fikcyjny_pilot(vr_liniowe, brzeg=lambda a: 0.2)
    wyn = _kal(monkeypatch, pilot)
    assert wyn["alfa_star"] is None and wyn["stop"].startswith("STOP 1")
    assert wyn["krok2a"] == [] and "komorki" not in wyn
    assert len(pilot.wywolania) == len(rc.ALFA_SIATKA)
    with pytest.raises(SystemExit):
        rc.zbuduj_komorki(wyn)


def test_kalibracja_a2_niedostepna_gdy_cel_poza_siatka_rho(monkeypatch):
    wyn = _kal(monkeypatch, _fikcyjny_pilot(lambda rho, rs: 1.2 + 1.2 * rs + 0.5 * (rho - 0.8)))
    assert wyn["komorki"]["A1"]["status"] == "ok"
    assert wyn["komorki"]["A2"]["status"] == "niedostepna"
    assert "A2" not in rc.zbuduj_komorki(wyn)


def test_kalibracja_a1_niedostepna_gdy_cel_ponizej_vr_przy_zerowym_szoku(monkeypatch):
    wyn = _kal(monkeypatch, _fikcyjny_pilot(lambda rho, rs: 2.5 + 1.2 * rs))
    assert wyn["komorki"]["A1"]["status"] == "niedostepna"
    assert wyn["krok2b"] is None or wyn["komorki"]["A2"]["status"] != "ok"
    with pytest.raises(SystemExit):
        rc.zbuduj_komorki(wyn)


def test_kalibracja_potwierdzenie_z_jedna_korekta_sieczna(monkeypatch):
    # silnie wypukła zależność: interpolacja po siatce pudłuje o > 0,14, sieczna trafia
    pilot = _fikcyjny_pilot(lambda rho, rs: 1.0 + 1.6 * rs**6)
    wyn = _kal(monkeypatch, pilot)
    a1 = wyn["komorki"]["A1"]
    assert a1["status"] == "ok" and len(a1["proby"]) == 2
    assert [p["ok_vr"] for p in a1["proby"]] == [False, True]
    assert a1["proby"][1]["x"] != a1["proby"][0]["x"]


def test_kalibracja_stop_2_po_trzech_nieudanych_potwierdzeniach(monkeypatch):
    pilot = _fikcyjny_pilot(vr_liniowe, przesuniecie_potw=0.5)
    wyn = _kal(monkeypatch, pilot)
    a1 = wyn["komorki"]["A1"]
    assert a1["status"] == "stop2" and len(a1["proby"]) == rc.MAX_POTWIERDZEN == 3
    with pytest.raises(SystemExit):
        rc.zbuduj_komorki(wyn)


def test_potwierdzenia_uzywaja_swiezych_ziaren_innych_niz_siatka(monkeypatch):
    pilot = _fikcyjny_pilot(lambda rho, rs: 1.0 + 1.6 * rs**6)
    _kal(monkeypatch, pilot)
    klucze = [k for _, k in pilot.wywolania]
    assert len(klucze) == len(set(klucze))  # żadne dwa wywołania nie dzielą ziarna
    assert {k[0] for k in klucze} == {1, 2, 3, 4}  # 2b wchodzi, bo A2 jest poza zasięgiem ρ_szok


# --- komórki, ziarna, kontrola ujemna --------------------------------------------------------------


def _kal_ok(a2=True):
    return {
        "alfa_star": 0.16,
        "komorki": {
            "A1": {
                "status": "ok",
                "par": {"rho": 0.8, "rho_szok": 0.887, "persystencja": 0.9999, "alpha": 0.16},
            },
            "A2": {
                "status": "ok" if a2 else "niedostepna",
                "par": {"rho": 0.903, "rho_szok": 1.0, "persystencja": 0.9999, "alpha": 0.16},
            },
        },
    }


def test_zbuduj_komorki_zgodnie_z_pre_rejestracja():
    spec = rc.zbuduj_komorki(_kal_ok())
    assert list(spec) == ["A0", "A1", "A2", "A3", "A4"]
    assert [spec[n]["panele"] for n in spec] == [4000, 4000, 4000, 2000, 2000]
    assert spec["A0"]["par"] == PAR_LV2 and spec["A0"]["cel_vr"] is None
    assert spec["A1"]["cel_vr"] == 2.264 and spec["A2"]["cel_vr"] == 2.811
    assert spec["A3"]["par"] == {
        "rho": 0.8,
        "rho_szok": 0.0,
        "persystencja": 0.9999,
        "alpha": 0.16,
    }
    assert spec["A4"]["par"] == {
        "rho": 0.8,
        "rho_szok": 0.887,
        "persystencja": None,
        "alpha": 0.08,
    }
    assert [spec[n]["werdykt"] for n in spec] == [True, True, True, False, False]
    assert [spec[n]["k7bd"] for n in spec] == [True, False, False, False, True]
    assert [spec[n]["kal_brzeg"] for n in spec] == [False, True, True, True, False]
    for s in spec.values():  # nazwy parametrów zgadzają się z generatorem
        generuj_panel_lv2c(30, rc.K, seed=1, burn=10, **s["par"])
    assert "A2" not in rc.zbuduj_komorki(_kal_ok(a2=False))


def test_ziarna_pilotazowe_i_rejestrowe_sa_rozlaczne():
    pilotazowe = {
        _ziarno_int(rc._ss_pilot(e, *k))
        for e in (1, 2, 3, 4, 5)
        for k in [(j,) for j in range(6)] + [(1, r) for r in range(3)] + [(2, r) for r in range(3)]
    }
    rejestrowe = {
        _ziarno_int(np.random.SeedSequence(rc.SEED_REJ, spawn_key=(i,))) for i in range(5)
    }
    assert len(pilotazowe) > 20 and pilotazowe.isdisjoint(rejestrowe)
    assert rc.SEED_PILOT != rc.SEED_REJ


def test_kontrola_n_ocenia_srednie_rho_w_przedziale(monkeypatch):
    def pilot(rho_sr):
        return lambda par, ss, panele, pula, konfig: {"rho": (rho_sr, 0.005)}

    for rho_sr, oczekiwane in ((0.0, True), (0.019, True), (0.03, False), (-0.05, False)):
        monkeypatch.setattr(rc, "pilot", pilot(rho_sr))
        assert rc.kontrola_n(None, MIKRO, 5)["ok"] is oczekiwane


def test_kontrola_n_na_prawdziwym_generatorze_daje_rho_bliskie_zera():
    w = rc.kontrola_n(None, MIKRO, 6)["wynik"]
    assert w["panele"] == 6 and abs(w["rho"][0]) < 0.25  # tylko spójność; progi sprawdza pilotaż


def test_main_rejestr_smoke_zapisuje_surowe_tablice_i_wypisuje_werdykty(tmp_path, capsys):
    kal = tmp_path / "kal.json"
    kal.write_text(json.dumps(_kal_ok(a2=False)))
    npz = tmp_path / "surowe.npz"
    rc.main(
        ["rejestr", "--smoke", "--workers", "1", "--kalibracja", str(kal), "--zapisz", str(npz)]
    )
    out = capsys.readouterr().out
    assert "A2: NIEDOSTĘPNA" in out and "WERDYKTY KOMÓREK" in out and "K-gen-D" in out
    surowe = np.load(npz)
    assert {"A0_stat", "A1_diag", "A4_vr_pom"} <= set(
        surowe.files
    ) and "A2_stat" not in surowe.files


def test_main_rejestr_bez_kalibracji_przerywa():
    with pytest.raises(SystemExit):
        rc.main(["rejestr", "--smoke", "--workers", "1"])


@settings(max_examples=5, deadline=None)
@given(seed=st.integers(0, 2**31 - 1))
def test_pilot_panel_jest_funkcja_ziarna(seed):
    ss = np.random.SeedSequence(seed)
    a, b = rc.pilot_panel((ss, PAR_LV2, MIKRO)), rc.pilot_panel((ss, PAR_LV2, MIKRO))
    assume(np.isfinite(a).all())
    assert np.array_equal(a, b)
