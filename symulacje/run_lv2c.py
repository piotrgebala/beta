"""
run_lv2c.py — karta 019: laboratorium LV2c dla K = 4 (BTC, ETH, SOL, BNB). Neutralny reporter (R14).
Pre-rejestracja: `runs/2026-10-08_019-lv2c-4-monety/README.md` (commit przed pilotażami i przebiegiem).

    python -m symulacje.run_lv2c kontrola-n --workers 28
    python -m symulacje.run_lv2c kalibruj --workers 28 --wyjscie runs/.../kalibracja.json
    python -m symulacje.run_lv2c rejestr --kalibracja runs/.../kalibracja.json --workers 28 \
        --zapisz data/lv2c_wyniki_paneli.npz > runs/.../raw_output.txt

Pilotaż (kontrola-n, kalibruj) liczy WYŁĄCZNIE VR, ρ̂, odsetek dopasowań przy granicy, odsetek niezbieżnych,
persystencję i ν̂ (funkcja `pilot_panel` nie woła testu zbiorczego ani nie liczy odsetka trafień).
Przebieg rejestrowy używa zamrożonych `zbuduj_zrodla`, `prognoza`, `statystyki_komorki`, `ocen_k`, `_werdykt`.
Wynik nie zależy od liczby procesów: ziarna rozdziela SeedSequence per panel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing as mp
import os
import sys
import time
from contextlib import contextmanager
from importlib.metadata import version
from pathlib import Path

import numpy as np

from modele.pomiar_rho_h import prognoza_garch_tnu, vr_rho
from symulacje.garch_panel_wspolny_szok import generuj_panel_lv2c
from symulacje.moc_var_es import NU, mde
from symulacje.prognozy_lv2 import prognoza, zbuduj_zrodla
from symulacje.run_lv2 import (
    DIAG,
    GARCH_NIEZBIEZNE_MAX,
    IDX,
    MOC_MIN,
    STAT,
    WERDYKT_TXT,
    _blisko,
    _potomne,
    _se,
    _werdykt,
    _wiersz,
    _wypisz_ocene,
    _ziarno_int,
    liczby_k7,
    ocen_k,
    statystyki_komorki,
)

K = 4
P = 0.05
KONFIG = {"n_dni": 2091, "start": 400, "boot": 999}
KONFIG_SMOKE = {"n_dni": 700, "start": 400, "boot": 99}
SEED_PILOT = 20_261_091
SEED_REJ = 20_261_019

PERS_GRAN = 0.9999
ALFA_LV2 = 0.08
ALFA_SIATKA = (0.08, 0.12, 0.16, 0.20, 0.25, 0.30)
SZOK_SIATKA = (0.0, 0.25, 0.5, 0.75, 1.0)
RHO_SIATKA = (0.80, 0.85, 0.90, 0.95)
SZOK_KROK1 = 0.5
RHO_BAZA = 0.8

CEL_VR = {"A1": 2.264, "A2": 2.811}
VR_A0 = 1.846
TOL_VR = 0.14
TOL_VR_A0 = 0.09
BRZEG_CEL = (0.463, 0.563)
PANELE_PILOT = {"krok1": 400, "krok2a": 300, "krok2b": 300, "potwierdzenie": 400}
PANELE_SMOKE = {"krok1": 3, "krok2a": 3, "krok2b": 3, "potwierdzenie": 3}
PANELE_KONTROLA_N = 200
KONTROLA_N_PRZEDZIAL = (-0.02, 0.02)
ZAOKR = 3
MAX_POTWIERDZEN = 3  # potwierdzenie + najwyżej 2 korekty

POLA_PILOT = ("vr", "rho", "brzeg", "niezb", "pers", "nu")

# kolejność prognoz w przebiegu rejestrowym; mnożnik σ̂ GARCH-t dla krzywej mocy
MNOZNIKI = {
    "garch_x1.00": 1.0,
    "garch_x0.95": 0.95,
    "garch_x0.90": 0.90,
    "garch_x0.85": 0.85,
    "garch_x0.80": 0.80,
    "garch_x0.70": 0.70,
}
PROG_C = ("wyr_t5", "zan30", *MNOZNIKI)
ZAMROZONE = {
    "wyr_t5": "wyr_t5",
    "zan30": "zan30",
    "garch_x1.00": "garch_tnu",
    "garch_x0.90": "garch_tnu_zan10",
    "garch_x0.80": "garch_tnu_zan20",
}
KA, KB = "garch_x1.00", "garch_x0.90"


# --- równoległość ---------------------------------------------------------------------------------


@contextmanager
def pula_procesow(workers: int):
    """Pula forkserver (jak w LV2); `workers <= 1` daje None, czyli obliczenia szeregowe."""
    if workers <= 1:
        yield None
        return
    for zmienna in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[zmienna] = "1"
    with mp.get_context("forkserver").Pool(workers) as pula:
        yield pula


def _mapuj(funkcja, zadania: list, pula) -> list:
    if pula is None:
        return [funkcja(z) for z in zadania]
    return list(pula.imap(funkcja, zadania, chunksize=1))


def _ss_pilot(etap: int, *klucz: int) -> np.random.SeedSequence:
    return np.random.SeedSequence(SEED_PILOT, spawn_key=(etap, *klucz))


# --- pilotaż: tylko VR, przy granicy, niezbieżne, persystencja, ν̂ ---------------------------------


def pilot_panel(arg) -> np.ndarray:
    """Jeden panel → (VR, ρ̂, odsetek przy granicy, odsetek niezbieżnych, persystencja, ν̂)."""
    ss, par, konfig = arg
    panel = generuj_panel_lv2c(konfig["n_dni"], K, seed=_ziarno_int(ss), nu=NU, **par)
    r = panel["r"].to_numpy()
    q, diag = prognoza_garch_tnu(r, P, konfig["start"])
    s = (r[konfig["start"] :] < q).sum(axis=1).astype(float)
    vr, rho = vr_rho(s, K, P)
    n_fit = diag["dopasowania"]
    return np.array(
        [
            vr,
            rho,
            diag["brzeg"] / n_fit,
            diag["nie_zbiezne"] / n_fit,
            diag["persystencja"],
            diag["nu"],
        ]
    )


def pilot(par: dict, ss: np.random.SeedSequence, panele: int, pula, konfig: dict) -> dict:
    """Średnie i SE po panelach pól `POLA_PILOT`."""
    zadania = [(s, par, konfig) for s in _potomne(ss, panele)]
    m = np.array(_mapuj(pilot_panel, zadania, pula))
    return {
        pole: (float(m[:, i].mean()), _se(m[:, i]) if panele > 1 else float("nan"))
        for i, pole in enumerate(POLA_PILOT)
    } | {"panele": panele}


def _opis_pilota(w: dict) -> str:
    vr, br, nz = w["vr"], w["brzeg"], w["niezb"]
    return (
        f"VR {vr[0]:.3f} ± {vr[1]:.3f}, ρ̂ {w['rho'][0]:.4f}, przy granicy {100 * br[0]:.1f} % ± "
        f"{100 * br[1]:.1f} pp, niezbieżne {100 * nz[0]:.2f} %, persystencja {w['pers'][0]:.4f}, "
        f"ν̂ {w['nu'][0]:.2f} ({w['panele']} paneli)"
    )


def _json(w: dict) -> dict:
    return {k: (list(v) if isinstance(v, tuple) else v) for k, v in w.items()}


# --- narzędzia kalibracji -------------------------------------------------------------------------


def odwrotna_liniowa(x, v, cel: float) -> float | None:
    """x* z v(x*) = cel; v wygładzone maksimum narastającym, interpolacja liniowa po pierwszym
    odcinku obejmującym cel. None, gdy cel poza zakresem wygładzonego v."""
    x, v = np.asarray(x, dtype=float), np.maximum.accumulate(np.asarray(v, dtype=float))
    if not v[0] <= cel <= v[-1]:
        return None
    for i in range(len(x) - 1):
        if v[i] <= cel <= v[i + 1]:
            if v[i + 1] == v[i]:
                return float(x[i])
            return float(x[i] + (cel - v[i]) * (x[i + 1] - x[i]) / (v[i + 1] - v[i]))
    return float(x[-1])


def korekta_sieczna(x_c, v_c, x_g, v_g, cel: float) -> float | None:
    """Sieczna przez punkt potwierdzenia (x_c, v_c) i punkt siatki po stronie celu, którego
    wygładzone v jest najbliższe celowi; wynik obcięty do zakresu siatki. None, gdy brak punktu."""
    v_g = np.maximum.accumulate(np.asarray(v_g, dtype=float))
    kier = 1.0 if v_c < cel else -1.0
    kand = [(xg, vg) for xg, vg in zip(x_g, v_g) if (xg - x_c) * kier > 0 and vg != v_c]
    if not kand:
        return None
    xg, vg = min(kand, key=lambda t: abs(t[1] - cel))
    x_nowe = x_c + (cel - v_c) * (xg - x_c) / (vg - v_c)
    return float(np.clip(x_nowe, min(x_g), max(x_g)))


def _par_pg(rho: float, rho_szok: float, alfa: float) -> dict:
    return {"rho": rho, "rho_szok": rho_szok, "persystencja": PERS_GRAN, "alpha": alfa}


def wybierz_alfa(wyniki: list[dict]) -> float | None:
    """Najmniejsze α z przy-granicznym ≥ dolnej granicy i niezbieżnymi ≤ 2 % (None = STOP 1)."""
    for w in wyniki:
        if w["brzeg"][0] >= BRZEG_CEL[0] and w["niezb"][0] <= GARCH_NIEZBIEZNE_MAX:
            return w["alfa"]
    return None


def potwierdz(
    nr: str,
    cel: float,
    os_x: str,
    x_start: float,
    x_g,
    v_g,
    stale: dict,
    alfa: float,
    pula,
    konfig: dict,
    panele: int,
    log=print,
) -> dict:
    """Potwierdzenie na świeżych panelach i najwyżej dwie korekty sieczną. `os_x`: rho_szok albo rho."""
    x, proby = round(x_start, ZAOKR), []
    for runda in range(MAX_POTWIERDZEN):
        par = _par_pg(stale.get("rho", RHO_BAZA), stale.get("rho_szok", 1.0), alfa) | {os_x: x}
        w = pilot(par, _ss_pilot(4, 1 if nr == "A1" else 2, runda), panele, pula, konfig)
        ok_vr = abs(w["vr"][0] - cel) <= TOL_VR
        ok_br = BRZEG_CEL[0] <= w["brzeg"][0] <= BRZEG_CEL[1]
        proby.append(
            {"runda": runda, "x": x, "par": par, "wynik": _json(w), "ok_vr": ok_vr, "ok_br": ok_br}
        )
        log(
            f"  {nr} potwierdzenie {runda}: {os_x} = {x:.3f}: {_opis_pilota(w)} → "
            f"VR {'TAK' if ok_vr else 'NIE'} (cel {cel:.3f} ± {TOL_VR}), przy granicy {'TAK' if ok_br else 'NIE'}"
        )
        if ok_vr and ok_br:
            return {"status": "ok", "os": os_x, "par": par, "proby": proby}
        if runda == MAX_POTWIERDZEN - 1:
            break
        nowe = korekta_sieczna(x, w["vr"][0], x_g, v_g, cel)
        if nowe is None:
            break
        x = round(nowe, ZAOKR)
    return {"status": "stop2", "os": os_x, "par": proby[-1]["par"], "proby": proby}


def kalibruj(pula, konfig: dict, panele: dict, log=print) -> dict:
    """Krok 1 (α*), 2a (ρ_szok), 2b (ρ, tylko gdy trzeba), potwierdzenia A1 i A2 wg pre-rejestracji."""
    wyn: dict = {
        "seed_pilot": SEED_PILOT,
        "konfig": konfig,
        "krok1": [],
        "krok2a": [],
        "krok2b": None,
    }
    log("KROK 1: α* (ρ = 0.8, ρ_szok = 0.5, α + β = 0.9999)")
    for j, alfa in enumerate(ALFA_SIATKA):
        w = pilot(
            _par_pg(RHO_BAZA, SZOK_KROK1, alfa), _ss_pilot(1, j), panele["krok1"], pula, konfig
        )
        wyn["krok1"].append({"alfa": alfa, **_json(w)})
        log(f"  α = {alfa:.2f}: {_opis_pilota(w)}")
    alfa_s = wybierz_alfa(wyn["krok1"])
    wyn["alfa_star"] = alfa_s
    if alfa_s is None:
        wyn["stop"] = (
            "STOP 1: żadne α nie daje odsetka przy granicy ≥ 46,3 % przy niezbieżnych ≤ 2 %"
        )
        log(wyn["stop"])
        return wyn
    log(f"  → α* = {alfa_s:.2f}\nKROK 2a: ρ_szok (ρ = 0.8, α = {alfa_s:.2f})")
    for j, rs in enumerate(SZOK_SIATKA):
        w = pilot(_par_pg(RHO_BAZA, rs, alfa_s), _ss_pilot(2, j), panele["krok2a"], pula, konfig)
        wyn["krok2a"].append({"rho_szok": rs, **_json(w)})
        log(f"  ρ_szok = {rs:.2f}: {_opis_pilota(w)}")
    v_szok = [r["vr"][0] for r in wyn["krok2a"]]
    wyn["komorki"] = {}
    for nr, cel in CEL_VR.items():
        x0 = odwrotna_liniowa(SZOK_SIATKA, v_szok, cel)
        if x0 is not None:
            wyn["komorki"][nr] = potwierdz(
                nr,
                cel,
                "rho_szok",
                x0,
                SZOK_SIATKA,
                v_szok,
                {"rho": RHO_BAZA},
                alfa_s,
                pula,
                konfig,
                panele["potwierdzenie"],
                log,
            )
            continue
        if cel < v_szok[0]:
            wyn["komorki"][nr] = {
                "status": "niedostepna",
                "powod": "cel poniżej VR przy ρ_szok = 0",
            }
            continue
        if wyn["krok2b"] is None:
            log(f"KROK 2b: ρ (ρ_szok = 1.0, α = {alfa_s:.2f})")
            wyn["krok2b"] = []
            for j, rho in enumerate(RHO_SIATKA):
                w = pilot(
                    _par_pg(rho, 1.0, alfa_s), _ss_pilot(3, j), panele["krok2b"], pula, konfig
                )
                wyn["krok2b"].append({"rho": rho, **_json(w)})
                log(f"  ρ = {rho:.2f}: {_opis_pilota(w)}")
        v_rho = [r["vr"][0] for r in wyn["krok2b"]]
        x0 = odwrotna_liniowa(RHO_SIATKA, v_rho, cel)
        if x0 is None:
            wyn["komorki"][nr] = {
                "status": "niedostepna",
                "powod": "cel poza VR przy ρ_szok = 1, ρ ≤ 0.95",
            }
            log(f"  {nr}: cel {cel:.3f} nieosiągalny na siatce ρ → niedostępna")
            continue
        wyn["komorki"][nr] = potwierdz(
            nr,
            cel,
            "rho",
            x0,
            RHO_SIATKA,
            v_rho,
            {"rho_szok": 1.0},
            alfa_s,
            pula,
            konfig,
            panele["potwierdzenie"],
            log,
        )
    return wyn


# --- kontrola ujemna generatora (R8, K-gen-N) -----------------------------------------------------


def kontrola_n(pula, konfig: dict, panele: int = PANELE_KONTROLA_N) -> dict:
    """ρ = 0, ρ_szok = 0, α + β = 0.98 (LV2 bez wspólnego czynnika): średnie ρ̂ ma być ≈ 0."""
    par = {"rho": 0.0, "rho_szok": 0.0, "persystencja": None, "alpha": ALFA_LV2}
    w = pilot(par, _ss_pilot(5, 0), panele, pula, konfig)
    lo, hi = KONTROLA_N_PRZEDZIAL
    return {"wynik": w, "ok": lo <= w["rho"][0] <= hi}


# --- przebieg rejestrowy: jeden panel -------------------------------------------------------------


def prognoza_c(zr, nazwa: str, p: float = P) -> tuple[np.ndarray, np.ndarray]:
    """(q, es) prognozy z `PROG_C`; punkty 1.00 / 0.90 / 0.80 liczy zamrożone `prognoza`."""
    if nazwa in ZAMROZONE:
        return prognoza(zr, ZAMROZONE[nazwa], p)
    q0, e0 = zr.ogon[("garch", "tnu", p)]
    s = zr.sigma["garch"] * MNOZNIKI[nazwa]
    return s * q0, s * e0


def przetworz_panel_c(arg) -> tuple[np.ndarray, np.ndarray, float]:
    """Panel → (STAT: prognozy × STAT, DIAG, VR z `vr_rho` na trafieniach garch_tnu)."""
    ss, par, konfig = arg
    ss_gen, ss_boot = _potomne(ss, 2)
    panel = generuj_panel_lv2c(konfig["n_dni"], K, seed=_ziarno_int(ss_gen), nu=NU, **par)
    zr = zbuduj_zrodla(panel, start=konfig["start"])
    n = konfig["n_dni"] - konfig["start"]
    idx = np.random.default_rng(ss_boot).integers(0, n, size=(konfig["boot"], n))
    stat = np.empty((len(PROG_C), len(STAT)))
    for i, nazwa in enumerate(PROG_C):
        q, es = prognoza_c(zr, nazwa)
        stat[i] = statystyki_komorki(zr.r, q, es, P, idx)
    q, _ = prognoza_c(zr, KA)
    vr_pom = vr_rho((zr.r < q).sum(axis=1).astype(float), K, P)[0]
    return stat, np.array([zr.diag[d] for d in DIAG], dtype=float), vr_pom


def uruchom_komorke(par: dict, ss: np.random.SeedSequence, panele: int, pula, konfig: dict) -> dict:
    zadania = [(s, par, konfig) for s in _potomne(ss, panele)]
    czesci = _mapuj(przetworz_panel_c, zadania, pula)
    return {
        "stat": np.stack([c[0] for c in czesci]),
        "diag": np.stack([c[1] for c in czesci]),
        "vr_pom": np.array([c[2] for c in czesci]),
    }


# --- liczby i reguły ------------------------------------------------------------------------------


def odsetek_c(wyn: dict, nazwa: str, stat: str) -> tuple[float, float]:
    v = wyn["stat"][:, PROG_C.index(nazwa), IDX[stat]]
    return float(np.mean(v)), _se(v)


def ocen_komorke(wyn: dict, spec: dict) -> dict:
    """Reguła K z zamrożonego `ocen_k`; K7b/K7d bramkują tylko przy `spec["k7bd"]`; KAL-VR i KAL-BRZEG
    dla komórek skalibrowanych (spec["cel_vr"], spec["kal_brzeg"])."""
    k7 = liczby_k7(wyn)
    oc = ocen_k(
        {
            "k1": odsetek_c(wyn, "wyr_t5", "zb_bonf"),
            "k2": odsetek_c(wyn, "zan30", "zb_bonf"),
            "k7": k7,
            "ka": odsetek_c(wyn, KA, "zb_bonf"),
            "kb": odsetek_c(wyn, KB, "zb_bonf"),
        }
    )
    kontrole = [k for k in oc["kontrole"] if spec["k7bd"] or k["kod"] not in ("K7b", "K7d")]
    opis_k7bd = (
        [k for k in oc["kontrole"] if k["kod"] in ("K7b", "K7d")] if not spec["k7bd"] else []
    )
    if spec.get("cel_vr") is not None:
        cel, (vr, se) = spec["cel_vr"], odsetek_c(wyn, KA, "vr")
        lo, hi = cel - TOL_VR, cel + TOL_VR
        kontrole.append(
            _wiersz(
                "KAL-VR",
                "ZGODNOŚĆ KALIBRACJI",
                f"średnie VR trafień garch_tnu (cel {cel:.3f})",
                vr,
                f"∈ [{lo:.3f}; {hi:.3f}]",
                lo <= vr <= hi,
                _blisko(vr, se, lo, hi),
                "num3",
            )
        )
    if spec.get("kal_brzeg"):
        br, se = k7["brzeg"]
        lo, hi = BRZEG_CEL
        kontrole.append(
            _wiersz(
                "KAL-BRZEG",
                "ZGODNOŚĆ KALIBRACJI",
                "odsetek dopasowań przy granicy (cel 51,3 %)",
                br,
                f"∈ [{100 * lo:.1f}; {100 * hi:.1f}] %",
                lo <= br <= hi,
                _blisko(br, se, lo, hi),
            )
        )
    return {
        "kontrole": kontrole,
        "kryteria": oc["kryteria"],
        "opis_k7bd": opis_k7bd,
        "werdykt": _werdykt(kontrole, oc["kryteria"]),
    }


def krzywa_mocy(wyn: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(x = 1 − mnożnik, moc testu zbiorczego, SE) dla garch_tnu × mnożnik; x = 0 to rozmiar."""
    x = np.array([1.0 - m for m in MNOZNIKI.values()])
    pary = [odsetek_c(wyn, n, "zb_bonf") for n in MNOZNIKI]
    return x, np.array([m for m, _ in pary]), np.array([s for _, s in pary])


def kgen_d(wyn_a0: dict) -> tuple[float, bool]:
    vr = odsetek_c(wyn_a0, KA, "vr")[0]
    return vr, abs(vr - VR_A0) <= TOL_VR_A0


def roznica_se(a: tuple[float, float], b: tuple[float, float]) -> float:
    """(a − b) / SE różnicy dwóch niezależnych średnich; przy SE = 0 (np. zero odrzuceń w obu komórkach)
    0 dla równych średnich, ±∞ dla różnych."""
    se, d = float(np.hypot(a[1], b[1])), a[0] - b[0]
    if se > 0.0:
        return d / se
    return 0.0 if d == 0.0 else math.copysign(math.inf, d)


# --- komórki rejestrowe ---------------------------------------------------------------------------

NAZWY_KOMOREK = ("A0", "A1", "A2", "A3", "A4")
OPIS_KOMOREK = {
    "A0": "scenariusz LV2 dla K = 4 (dół przedziału z 020)",
    "A1": "środek przedziału z 020 (komórka główna)",
    "A2": "góra przedziału z 020 (ρ̂ + 2 SE)",
    "A3": "tylko trwałość przy granicy (opis dekompozycji)",
    "A4": "tylko wspólny szok (opis dekompozycji)",
}
PANELE_REJ = {"A0": 4000, "A1": 4000, "A2": 4000, "A3": 2000, "A4": 2000}


def zbuduj_komorki(kal: dict, panele: dict | None = None) -> dict:
    """Specyfikacje komórek z pliku kalibracji; komórka niedostępna wypada (A2) albo przerywa (A1)."""
    panele = panele or PANELE_REJ
    if kal.get("alfa_star") is None or kal["komorki"]["A1"]["status"] != "ok":
        raise SystemExit("STOP: kalibracja A1 nie powiodła się — przebiegu rejestrowego nie ma")
    alfa, p1 = kal["alfa_star"], kal["komorki"]["A1"]["par"]
    spec = {
        "A0": {
            "par": {"rho": RHO_BAZA, "rho_szok": 0.0, "persystencja": None, "alpha": ALFA_LV2},
            "k7bd": True,
            "cel_vr": None,
            "kal_brzeg": False,
            "werdykt": True,
        },
        "A1": {
            "par": p1,
            "k7bd": False,
            "cel_vr": CEL_VR["A1"],
            "kal_brzeg": True,
            "werdykt": True,
        },
        "A3": {
            "par": _par_pg(RHO_BAZA, 0.0, alfa),
            "k7bd": False,
            "cel_vr": None,
            "kal_brzeg": True,
            "werdykt": False,
        },
        "A4": {
            "par": {
                "rho": p1["rho"],
                "rho_szok": p1["rho_szok"],
                "persystencja": None,
                "alpha": ALFA_LV2,
            },
            "k7bd": True,
            "cel_vr": None,
            "kal_brzeg": False,
            "werdykt": False,
        },
    }
    a2 = kal["komorki"].get("A2", {})
    if a2.get("status") == "ok":
        spec["A2"] = {
            "par": a2["par"],
            "k7bd": False,
            "cel_vr": CEL_VR["A2"],
            "kal_brzeg": True,
            "werdykt": True,
        }
    return {n: spec[n] | {"panele": panele[n]} for n in NAZWY_KOMOREK if n in spec}


def przebieg(spec: dict, pula, konfig: dict, log=None) -> dict:
    wyniki = {}
    for n in NAZWY_KOMOREK:
        if n not in spec:
            continue
        t0 = time.time()
        ss = np.random.SeedSequence(SEED_REJ, spawn_key=(NAZWY_KOMOREK.index(n),))
        wyniki[n] = uruchom_komorke(spec[n]["par"], ss, spec[n]["panele"], pula, konfig)
        if log:
            log(f"  komórka {n}: {spec[n]['panele']} paneli w {time.time() - t0:.0f} s")
    return wyniki


# --- wydruk (neutralny reporter, R14) -------------------------------------------------------------


def _pc(v: float) -> str:
    return f"{100 * v:5.1f}"


def _wypisz_wiersz_prognozy(wyn: dict, nazwa: str) -> str:
    v = {st: odsetek_c(wyn, nazwa, st) for st in STAT if st != "niezdef"}
    return (
        f"{nazwa:12s} {100 * v['hit'][0]:6.2f} {v['u_sr'][0]:6.3f} |"
        f" {_pc(v['zb_a'][0])} {_pc(v['zb_b'][0])} {_pc(v['zb_c'][0])} |"
        f" {_pc(v['zb_bonf'][0])} ± {100 * v['zb_bonf'][1]:4.2f} | {_pc(v['zb_a_prawa'][0])} {v['vr'][0]:5.2f}"
    )


def wypisz_komorke(nazwa: str, spec: dict, wyn: dict) -> dict:
    ocena = ocen_komorke(wyn, spec)
    par, k7 = spec["par"], liczby_k7(wyn)
    print(f"\n=== Komórka {nazwa}: {OPIS_KOMOREK[nazwa]} ===")
    print(f"parametry generatora: {par}; {wyn['stat'].shape[0]} paneli, K = {K}")
    print(
        f"  diagnostyka GARCH-t: ν̂ {k7['nu'][0]:.3f}, persystencja {k7['pers'][0]:.4f}, "
        f"niezbieżne {100 * k7['nie_zbiezne'][0]:.2f} %, przy granicy {100 * k7['brzeg'][0]:.2f} % "
        f"(± {100 * k7['brzeg'][1]:.2f} pp)"
    )
    vr, se_vr = odsetek_c(wyn, KA, "vr")
    rho_p = (wyn["stat"][:, PROG_C.index(KA), IDX["vr"]] - 1.0) / (K - 1.0)
    q = np.quantile(rho_p, [0.05, 0.5, 0.95])
    print(
        f"  VR trafień garch_tnu: {vr:.3f} ± {se_vr:.3f}; ρ̂ = (VR − 1)/(K − 1): średnia {rho_p.mean():.4f}, "
        f"kwantyle 5/50/95 % po panelach: {q[0]:.3f} / {q[1]:.3f} / {q[2]:.3f}"
    )
    print(f"  odsetek trafień garch_tnu: {100 * odsetek_c(wyn, KA, 'hit')[0]:.2f} % (cel 5 %)")
    print(
        f"  parytet VR runnera z `vr_rho`: max |różnica| = "
        f"{np.max(np.abs(wyn['stat'][:, PROG_C.index(KA), IDX['vr']] - wyn['vr_pom'])):.2e}"
    )
    print(
        f"  REGUŁA K, p = 5 %, K = {K}, n = 1 691"
        + ("" if spec["werdykt"] else "  (komórka opisowa)")
    )
    _wypisz_ocene(ocena, "kontrole i kryteria")
    for k in ocena["opis_k7bd"]:
        w = k["wartosc"]
        txt = f"{w:.3f}" if k["kod"] == "K7b" else f"{100 * w:.1f} %"
        print(f"    {k['kod']} (opis, nie bramkuje w tej komórce): {txt} — {k['wymaganie']}")
    x, moc, se = krzywa_mocy(wyn)
    print("  KRZYWA MOCY garch_tnu × (1 − x) [opis]: x = " + " ".join(f"{v:5.2f}" for v in x))
    print("                                  moc % = " + " ".join(_pc(m) for m in moc))
    print("                                  SE pp = " + " ".join(f"{100 * s:5.2f}" for s in se))
    o = np.argsort(x)
    m = mde(x[o], moc[o], MOC_MIN)
    print(
        f"  MDE (najmniejsze x z mocą ≥ 80 %): {m:.3f}"
        if np.isfinite(m)
        else f"  MDE: >{x.max():.2f} (nieosiągalne na siatce)"
    )
    print(
        f"  {'prognoza':12s} {'hit':>6s} {'U':>6s} |   A     B     C  | zbiorczy ± SE |  A>0    VR"
    )
    for n in PROG_C:
        print("  " + _wypisz_wiersz_prognozy(wyn, n))
    return ocena


def wypisz_dekompozycje(wyniki: dict) -> None:
    if "A1" not in wyniki:
        return
    print(
        "\nDEKOMPOZYCJA (opis): różnica wobec A1 w jednostkach SE różnicy; |z| > 3 = wyraźna różnica"
    )
    for n in ("A3", "A4"):
        if n not in wyniki:
            continue
        for kod, prog in (("K-a", KA), ("K-b", KB)):
            z = roznica_se(
                odsetek_c(wyniki[n], prog, "zb_bonf"), odsetek_c(wyniki["A1"], prog, "zb_bonf")
            )
            print(f"  {n} − A1, {kod}: {z:+.2f}" + ("  [> 3 SE]" if abs(z) > 3 else ""))


def przewidywania(oceny: dict, wyniki: dict, kal: dict) -> list[tuple[str, bool]]:
    """Sprawdzenie przewidywań z pre-rejestracji (NIE kryteria)."""
    w = [("α* ∈ {0,16; 0,20; 0,25} (przewidywane 0,20)", kal["alfa_star"] in (0.16, 0.20, 0.25))]
    a2 = kal["komorki"].get("A2", {}).get("par", {})
    w.append(("A2 wymagała kroku 2b (ρ > 0,8)", a2.get("rho", RHO_BAZA) > RHO_BAZA))
    zakresy = {
        "A0": ((0.05, 0.08), (0.40, 0.75)),
        "A1": ((0.06, 0.10), (0.30, 0.65)),
        "A2": ((0.06, 0.11), (0.25, 0.60)),
    }
    for n, (ra, rb) in zakresy.items():
        if n not in wyniki:
            continue
        ka, kb = odsetek_c(wyniki[n], KA, "zb_bonf")[0], odsetek_c(wyniki[n], KB, "zb_bonf")[0]
        w.append((f"{n}: K-a ∈ [{ra[0]:.0%}; {ra[1]:.0%}]", ra[0] <= ka <= ra[1]))
        w.append((f"{n}: K-b ∈ [{rb[0]:.0%}; {rb[1]:.0%}]", rb[0] <= kb <= rb[1]))
        k1, k2 = (
            odsetek_c(wyniki[n], "wyr_t5", "zb_bonf")[0],
            odsetek_c(wyniki[n], "zan30", "zb_bonf")[0],
        )
        w.append((f"{n}: K1 ∈ [2,5; 7,5] %", 0.025 <= k1 <= 0.075))
        w.append((f"{n}: K2 ≥ 95 %", k2 >= 0.95))
    if "A1" in oceny:
        w.append(("werdykt A1 = NIE", oceny["A1"]["werdykt"] == "NIE"))
    return w


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="019 — LV2c: laboratorium VaR/ES, K = 4")
    ap.add_argument("tryb", choices=("kontrola-n", "kalibruj", "rejestr"))
    ap.add_argument("--smoke", action="store_true", help="małe panele; tylko test działania kodu")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--wyjscie", default=None, help="kalibruj: plik JSON z wynikiem kalibracji")
    ap.add_argument("--kalibracja", default=None, help="rejestr: plik JSON z kalibracji")
    ap.add_argument(
        "--zapisz", default=None, help="rejestr: plik .npz na surowe tablice (poza gitem)"
    )
    a = ap.parse_args(argv)
    konfig = dict(KONFIG_SMOKE if a.smoke else KONFIG)
    t0 = time.time()
    print("019 — LV2c: laboratorium VaR/ES dla K = 4 (karta 019)")
    if a.smoke:
        print("SMOKE — NIE JEST PRZEBIEGIEM: małe panele, tylko test działania kodu.")
    print(
        "Wersje: python "
        + sys.version.split()[0]
        + "".join(f", {p} {version(p)}" for p in ("numpy", "scipy", "pandas"))
        + "."
    )
    with pula_procesow(a.workers) as pula:
        if a.tryb == "kontrola-n":
            _tryb_kontrola_n(pula, konfig, a.smoke)
        elif a.tryb == "kalibruj":
            _tryb_kalibruj(pula, konfig, a)
        else:
            _tryb_rejestr(pula, konfig, a)
    print(f"Czas {time.time() - t0:.0f} s ({a.workers} procesów)", file=sys.stderr)


def _tryb_kontrola_n(pula, konfig: dict, smoke: bool) -> None:
    panele = 3 if smoke else PANELE_KONTROLA_N
    res = kontrola_n(pula, konfig, panele)
    print(
        f"K-gen-N (R8, ujemna): ρ = 0, ρ_szok = 0, α + β = 0.98, ziarna pilotażowe (etap 5), {panele} paneli"
    )
    print(f"  {_opis_pilota(res['wynik'])}")
    lo, hi = KONTROLA_N_PRZEDZIAL
    print(
        f"  średnie ρ̂ {res['wynik']['rho'][0]:+.4f} ± {res['wynik']['rho'][1]:.4f}; wymaganie ∈ [{lo}; {hi}]: "
        f"{'ZALICZONA' if res['ok'] else 'NIEZALICZONA'}"
    )


def _tryb_kalibruj(pula, konfig: dict, a) -> None:
    print(
        f"KALIBRACJA (pilotaż): ziarno {SEED_PILOT}, konfig {konfig}; drukowane tylko VR, ρ̂, odsetek przy "
        "granicy, niezbieżne, persystencja, ν̂."
    )
    wyn = kalibruj(pula, konfig, PANELE_SMOKE if a.smoke else PANELE_PILOT)
    for nr, k in wyn.get("komorki", {}).items():
        print(f"WYNIK {nr}: {k['status']}" + (f", parametry {k['par']}" if "par" in k else ""))
    if a.wyjscie:
        os.makedirs(os.path.dirname(os.path.abspath(a.wyjscie)), exist_ok=True)
        with open(a.wyjscie, "w", encoding="utf-8") as f:
            json.dump(wyn, f, indent=1, ensure_ascii=False)
            f.write("\n")


def _tryb_rejestr(pula, konfig: dict, a) -> None:
    if not a.kalibracja:
        raise SystemExit("rejestr wymaga --kalibracja")
    surowe = Path(a.kalibracja).read_bytes()
    kal = json.loads(surowe)
    spec = zbuduj_komorki(kal, {n: 4 for n in NAZWY_KOMOREK} if a.smoke else None)
    print(
        f"Kalibracja: {a.kalibracja} (sha256 {hashlib.sha256(surowe).hexdigest()[:16]}), α* = {kal['alfa_star']}"
    )
    print(
        f"Ziarno rejestrowe {SEED_REJ} (komórka i = SeedSequence(ziarno, spawn_key=(i,))), konfig {konfig}, "
        f"poziom testów 5 %, B = {konfig['boot']}."
    )
    for n, s in spec.items():
        print(f"  {n}: {s['par']}, {s['panele']} paneli")
    if "A2" not in spec:
        print(
            f"  A2: NIEDOSTĘPNA ({kal['komorki'].get('A2', {}).get('powod', kal['komorki'].get('A2', {}).get('status'))})"
        )
    wyniki = przebieg(spec, pula, konfig, log=lambda t: print(t, file=sys.stderr, flush=True))
    if a.zapisz:
        os.makedirs(os.path.dirname(os.path.abspath(a.zapisz)), exist_ok=True)
        np.savez_compressed(
            a.zapisz, **{f"{n}_{k}": v for n, w in wyniki.items() for k, v in w.items()}
        )
    oceny = {n: wypisz_komorke(n, spec[n], wyniki[n]) for n in wyniki}
    wypisz_dekompozycje(wyniki)
    vr_a0, ok_d = kgen_d(wyniki["A0"])
    print(
        f"\nK-gen-D (R8, dodatnia): średnie VR komórki A0 = {vr_a0:.3f}; wymaganie {VR_A0} ± {TOL_VR_A0}: "
        f"{'ZALICZONA' if ok_d else 'NIEZALICZONA'}"
    )
    print("\nWERDYKTY KOMÓREK (zamrożony `_werdykt`):")
    for n in ("A0", "A1", "A2"):
        if n in oceny:
            print(f"  {n}: {oceny[n]['werdykt']} ({WERDYKT_TXT[oceny[n]['werdykt']]})")
    print("\nPRZEWIDYWANIA z pre-rejestracji (NIE kryteria):")
    for tekst, ok in przewidywania(oceny, wyniki, kal):
        print(f"  {tekst}: {'TAK' if ok else 'NIE'}")
    if a.smoke:
        print("\nSMOKE: powyższe wyniki nie są werdyktem.")


if __name__ == "__main__":
    main()
