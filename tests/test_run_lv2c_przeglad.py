"""Testy dopisane po przeglądzie kodu karty 019 (runner `run_lv2c.py` bez zmian): przypięcie pilotażu do
niezależnego obliczenia, bramka potwierdzenia, szok w kroku 1, rozdział ziaren komórek, rozłączność ziaren
pilotażowych i rejestrowych oraz znane braki zapisane jako `xfail(strict=True)` (do naprawy przy karcie 021).
"""

from __future__ import annotations

import numpy as np
import pytest

import symulacje.run_lv2c as rc
from modele.pomiar_rho_h import prognoza_garch_tnu, vr_rho
from symulacje.garch_panel_wspolny_szok import generuj_panel_lv2c
from symulacje.moc_var_es import NU
from symulacje.run_lv2 import _potomne, _ziarno_int

MIKRO = {"n_dni": 520, "start": 400, "boot": 19}
PAR_PG = {"rho": 0.8, "rho_szok": 0.6, "persystencja": 0.9999, "alpha": 0.16}


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
        "panele": 1,
    }


# --- pilot_panel przypięty do niezależnego obliczenia -----------------------------------------------


@pytest.mark.parametrize("klucz", [1, 2, 5])
def test_pilot_panel_zgadza_sie_z_obliczeniem_pisanym_od_nowa(klucz):
    ss = _ss(klucz)
    wynik = rc.pilot_panel((ss, PAR_PG, MIKRO))
    r = generuj_panel_lv2c(MIKRO["n_dni"], rc.K, seed=_ziarno_int(ss), nu=NU, **PAR_PG)["r"]
    r = r.to_numpy()
    q, diag = prognoza_garch_tnu(r, rc.P, MIKRO["start"])
    s = np.array(
        [
            sum(1 for j in range(rc.K) if r[MIKRO["start"] + t, j] < q[t, j])
            for t in range(q.shape[0])
        ],
        dtype=float,
    )
    vr, rho = vr_rho(s, rc.K, rc.P)
    n_fit = diag["dopasowania"]
    assert (
        diag["brzeg"] != diag["nie_zbiezne"]
    )  # kolumny odróżnialne: zamiana miejscami zostanie wykryta
    assert wynik[0] == pytest.approx(vr, abs=1e-12)
    assert wynik[1] == pytest.approx(rho, abs=1e-12)
    assert wynik[2] == pytest.approx(diag["brzeg"] / n_fit, abs=1e-12)
    assert wynik[3] == pytest.approx(diag["nie_zbiezne"] / n_fit, abs=1e-12)
    assert wynik[4] == pytest.approx(diag["persystencja"], abs=1e-12)
    assert wynik[5] == pytest.approx(diag["nu"], abs=1e-12)


def test_vr_nie_odroznia_trafien_od_ich_dopelnienia():
    s = np.array([0, 1, 0, 2, 0, 0, 3, 1, 0, 0, 4, 0], dtype=float)
    assert vr_rho(s, rc.K, rc.P)[0] == pytest.approx(vr_rho(rc.K - s, rc.K, rc.P)[0], abs=1e-12)


# --- bramka potwierdzenia (ok_br) -------------------------------------------------------------------


def _potwierdz_ze_stalym_pilotem(monkeypatch, brzeg, vr=2.264):
    monkeypatch.setattr(rc, "pilot", lambda *a, **k: _pole(vr=vr, brzeg=brzeg))
    return rc.potwierdz(
        "A1",
        rc.CEL_VR["A1"],
        "rho_szok",
        0.5,
        rc.SZOK_SIATKA,
        [1.5, 1.9, 2.2, 2.5, 2.9],
        {"rho": rc.RHO_BAZA},
        0.16,
        None,
        rc.KONFIG_SMOKE,
        1,
        log=lambda *_: None,
    )


@pytest.mark.parametrize(
    "brzeg, status",
    [(0.462, "stop2"), (0.463, "ok"), (0.50, "ok"), (0.563, "ok"), (0.564, "stop2")],
)
def test_potwierdzenie_wymaga_odsetka_przy_granicy_w_przedziale_z_pre_rejestracji(
    monkeypatch, brzeg, status
):
    assert rc.BRZEG_CEL == (0.463, 0.563)
    assert _potwierdz_ze_stalym_pilotem(monkeypatch, brzeg)["status"] == status


def test_potwierdzenie_wymaga_vr_w_tolerancji(monkeypatch):
    cel, tol = rc.CEL_VR["A1"], rc.TOL_VR
    assert tol == 0.14
    assert _potwierdz_ze_stalym_pilotem(monkeypatch, 0.5, vr=cel + tol - 1e-9)["status"] == "ok"
    assert _potwierdz_ze_stalym_pilotem(monkeypatch, 0.5, vr=cel + tol + 1e-3)["status"] == "stop2"
    assert _potwierdz_ze_stalym_pilotem(monkeypatch, 0.5, vr=cel - tol - 1e-3)["status"] == "stop2"


# --- krok 1 kalibracji: szok i ziarna ---------------------------------------------------------------


def _krok1_z_zapisem_wywolan(monkeypatch):
    wywolania = []

    def falszywy(par, ss, panele, pula, konfig):
        wywolania.append((par, ss, panele))
        return _pole(brzeg=0.30)

    monkeypatch.setattr(rc, "pilot", falszywy)
    wyn = rc.kalibruj(None, rc.KONFIG_SMOKE, rc.PANELE_SMOKE, log=lambda *_: None)
    return wyn, wywolania


def test_krok1_uzywa_szoku_i_parametrow_z_pre_rejestracji(monkeypatch):
    wyn, wywolania = _krok1_z_zapisem_wywolan(monkeypatch)
    assert wyn["alfa_star"] is None and "STOP 1" in wyn["stop"]
    assert len(wywolania) == len(rc.ALFA_SIATKA) == 6
    for (par, _, panele), alfa in zip(wywolania, (0.08, 0.12, 0.16, 0.20, 0.25, 0.30)):
        assert par == {"rho": 0.8, "rho_szok": 0.5, "persystencja": 0.9999, "alpha": alfa}
        assert panele == rc.PANELE_SMOKE["krok1"]


def test_krok1_ma_osobne_ziarno_dla_kazdego_alfa(monkeypatch):
    _, wywolania = _krok1_z_zapisem_wywolan(monkeypatch)
    klucze = [w[1].spawn_key for w in wywolania]
    assert klucze == [(1, j) for j in range(6)]
    assert all(w[1].entropy == rc.SEED_PILOT for w in wywolania)


# --- rozdział ziaren komórek i rozłączność torów ------------------------------------------------------


def test_komorki_rejestrowe_maja_rozne_ziarna_o_entropii_rejestrowej(monkeypatch):
    zapis = {}

    def falszywa(par, ss, panele, pula, konfig):
        zapis[len(zapis)] = ss
        return {"stat": np.zeros((1, 1, 1))}

    monkeypatch.setattr(rc, "uruchom_komorke", falszywa)
    spec = {n: {"par": PAR_PG, "panele": 1} for n in rc.NAZWY_KOMOREK}
    rc.przebieg(spec, None, rc.KONFIG_SMOKE)
    assert [s.spawn_key for s in zapis.values()] == [(i,) for i in range(len(rc.NAZWY_KOMOREK))]
    assert {s.entropy for s in zapis.values()} == {rc.SEED_REJ}


def test_ziarna_paneli_pilotazowych_i_rejestrowych_sie_nie_pokrywaja():
    pilot = {
        _ziarno_int(c)
        for etap, j in ((1, 0), (1, 5), (2, 0), (2, 4), (4, 1), (4, 2))
        for c in _potomne(rc._ss_pilot(etap, j), 100)
    }
    rej = {
        _ziarno_int(c)
        for i in range(len(rc.NAZWY_KOMOREK))
        for c in _potomne(np.random.SeedSequence(rc.SEED_REJ, spawn_key=(i,)), 100)
    }
    assert len(pilot) == 600 and len(rej) == 500
    assert not pilot & rej


# --- znane braki z przeglądu (naprawa przy karcie 021) ------------------------------------------------


@pytest.mark.xfail(strict=True, reason="przegląd 019, pkt 6: sieczna bez straży znaku nachylenia")
def test_korekta_sieczna_nie_oddala_sie_od_celu_przy_ujemnym_nachyleniu():
    nowe = rc.korekta_sieczna(0.6, 2.30, rc.SZOK_SIATKA, [1.0, 1.8, 2.1, 2.2, 2.25], 2.5)
    assert nowe is not None and nowe > 0.6


@pytest.mark.xfail(
    strict=True,
    reason="przegląd 019, pkt 8: cel tuż poniżej v na początku siatki daje None w kroku 2b",
)
def test_odwrotna_liniowa_cel_tuz_ponizej_poczatku_siatki_daje_poczatek_siatki():
    x = rc.odwrotna_liniowa(rc.RHO_SIATKA, [2.72, 2.9, 3.1, 3.3], 2.70)
    assert x == pytest.approx(0.80)
