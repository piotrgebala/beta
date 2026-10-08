"""
run_lv2d.py — karta 021: laboratorium LV2d dla K = 4 (BTC, ETH, SOL, BNB) z przesunięciami poziomu wariancji.
Neutralny reporter (R14). Pre-rejestracja: `runs/2026-10-08_021-lv2d-regimy-wariancji/README.md`.

    python -m symulacje.run_lv2d kontrola-n --workers 28
    python -m symulacje.run_lv2d kalibruj --workers 28 --wyjscie runs/.../kalibracja.json
    python -m symulacje.run_lv2d rejestr --kalibracja runs/.../kalibracja.json --workers 28 \
        --zapisz data/lv2d_wyniki_paneli.npz > runs/.../raw_output.txt

Pilotaż (kontrola-n, kalibruj) liczy WYŁĄCZNIE VR, ρ̂, odsetek dopasowań przy granicy, odsetek niezbieżnych,
persystencję, ν̂ i opisowy rozrzut skali (`pilot_panel` nie woła testu zbiorczego ani nie liczy odsetka trafień).
Przebieg rejestrowy używa zamrożonych `zbuduj_zrodla`, `prognoza`, `statystyki_komorki`, `ocen_k`, `_werdykt`
(przez `run_lv2c` i `run_lv2`). Wynik nie zależy od liczby procesów: ziarna rozdziela SeedSequence per panel.

Poprawki względem `run_lv2c` (przegląd kodu 019): NaN w pilotażu → STOP; sieczna ze strażą znaku nachylenia;
`potwierdz` nie marnuje korekt, gdy VR jest w tolerancji; cel poniżej początku siatki daje początek siatki;
zmienne BLAS ustawione przed importem numpy także dla `--workers 1`; K-gen-N na 400 panelach.
"""

from __future__ import annotations

import os

for _zmienna in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_zmienna] = "1"  # musi być przed importem numpy; dotyczy też pracy szeregowej

import argparse
import hashlib
import json
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

import symulacje.run_lv2c as rc
from modele.pomiar_rho_h import prognoza_garch_tnu, vr_rho
from symulacje.garch_panel_regimy import DLUGOSC, generuj_panel_lv2d
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

K, P = rc.K, rc.P
KONFIG = dict(rc.KONFIG)
KONFIG_SMOKE = dict(rc.KONFIG_SMOKE)

SEED_PILOT = 20_262_101
SEED_REJ = 20_262_021
SEED_SMOKE = 20_269_999
SEED_DRUGA = 27_182_818

ALFA_LV2 = rc.ALFA_LV2
RHO_BAZA = rc.RHO_BAZA
SZOK_KROK1 = 0.5
DLUGOSCI = (DLUGOSC, 150.0)
AMP_SIATKA = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5)
BRZEG_OKNO = (0.413, 0.613)
BRZEG_SRODEK = 0.513
BRZEG_STARE = rc.BRZEG_CEL
BRZEG_ZERO_MAX = 0.10  # punkt zerowy siatki (bez poziomu) musi leżeć rzędu LV2

CEL_VR = {"B1": 1.717, "B2": 2.264, "B3": 2.811}
VR_A0 = rc.VR_A0
TOL_VR = rc.TOL_VR
TOL_VR_A0 = rc.TOL_VR_A0
MAX_POTWIERDZEN = rc.MAX_POTWIERDZEN  # potwierdzenie + najwyżej 2 korekty
ZAOKR = rc.ZAOKR

SCIEZKI = {
    "S": {"os": "rho_szok", "siatka": (0.0, 0.25, 0.5, 0.75, 1.0), "stale": {"rho": RHO_BAZA}},
    "R_gora": {"os": "rho", "siatka": (0.80, 0.85, 0.90, 0.95), "stale": {"rho_szok": 1.0}},
    "R_dol": {"os": "rho", "siatka": (0.20, 0.35, 0.50, 0.65, 0.80), "stale": {"rho_szok": 0.0}},
}
NR_SCIEZKI = {nazwa: i for i, nazwa in enumerate(SCIEZKI)}
NR_KOMORKI_B = {"B1": 0, "B2": 1, "B3": 2}

PANELE_PILOT = {"krok1": 1000, "sciezka": 500, "potwierdzenie": 1000, "n2": 500, "kontrola_n": 400}
PANELE_SMOKE = {"krok1": 3, "sciezka": 3, "potwierdzenie": 3, "n2": 3, "kontrola_n": 3}
KONTROLA_N_PRZEDZIAL = rc.KONTROLA_N_PRZEDZIAL

POLA_PILOT = (*rc.POLA_PILOT, "skala")

PROG_D = (*rc.PROG_C, "zan10", "zan20")
KA, KB = rc.KA, rc.KB
KONTROLE_BRAMKUJACE_B = ("K1", "K2", "K7c")  # w komórkach B K7a, K7b, K7d są opisem


class StopBlad(RuntimeError):
    """Reguła STOP z pre-rejestracji (NaN w wynikach, brak kalibracji) — runner przerywa."""


def ss_pilot(ent: int, etap: int, *klucz: int) -> np.random.SeedSequence:
    return np.random.SeedSequence(ent, spawn_key=(etap, *klucz))


# --- pilotaż: tylko VR, przy granicy, niezbieżne, persystencja, ν̂, rozrzut skali -------------------


def par_poziom(rho: float, rho_szok: float, amplituda: float, dlugosc: float) -> dict:
    return {
        "rho": rho,
        "rho_szok": rho_szok,
        "persystencja": None,
        "alpha": ALFA_LV2,
        "amplituda": amplituda,
        "dlugosc": dlugosc,
    }


def rozrzut_skali(r0: np.ndarray) -> float:
    """Stosunek 90. do 10. percentyla 60-dniowego odchylenia standardowego (opis, bez progu)."""
    sd = pd.Series(r0).rolling(60).std().dropna().to_numpy()
    return float(np.quantile(sd, 0.9) / np.quantile(sd, 0.1))


def pilot_panel(arg) -> np.ndarray:
    """Jeden panel → (VR, ρ̂, odsetek przy granicy, odsetek niezbieżnych, persystencja, ν̂, rozrzut skali)."""
    ss, par, konfig = arg
    panel = generuj_panel_lv2d(konfig["n_dni"], K, seed=_ziarno_int(ss), nu=NU, **par)
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
            rozrzut_skali(r[:, 0]),
        ]
    )


def pilot(par: dict, ss: np.random.SeedSequence, panele: int, pula, konfig: dict) -> dict:
    """Średnie i SE po panelach pól `POLA_PILOT`; NaN w którymkolwiek panelu = STOP (nie „zaliczone”)."""
    zadania = [(s, par, konfig) for s in _potomne(ss, panele)]
    m = np.array(rc._mapuj(pilot_panel, zadania, pula))
    if not np.isfinite(m).all():
        raise StopBlad(f"STOP: NaN albo nieskończoność w pilotażu (parametry {par})")
    return {
        pole: (float(m[:, i].mean()), _se(m[:, i]) if panele > 1 else float("nan"))
        for i, pole in enumerate(POLA_PILOT)
    } | {"panele": panele}


def opis_pilota(w: dict) -> str:
    return rc._opis_pilota(w) + f", rozrzut skali P90/P10 {w['skala'][0]:.2f}"


# --- narzędzia kalibracji -------------------------------------------------------------------------


def odwrotna_liniowa(
    x, v, cel: float, tol_dol: float = float("inf"), tol_gora: float = 0.0
) -> float | None:
    """x* z v(x*) = cel; v wygładzone maksimum narastającym, interpolacja liniowa na pierwszym odcinku
    obejmującym cel. Cel nie powyżej v[0] daje początek siatki, gdy v[0] − cel ≤ `tol_dol` (inaczej None);
    cel powyżej v[-1] daje koniec siatki, gdy cel − v[-1] ≤ `tol_gora` (inaczej None)."""
    x, v = np.asarray(x, dtype=float), np.maximum.accumulate(np.asarray(v, dtype=float))
    if not (np.isfinite(x).all() and np.isfinite(v).all() and np.isfinite(cel)):
        raise StopBlad("STOP: NaN w odwrotnej interpolacji")
    if cel > v[-1]:
        return float(x[-1]) if cel - v[-1] <= tol_gora else None
    if cel <= v[0]:
        return float(x[0]) if v[0] - cel <= tol_dol else None
    for i in range(len(x) - 1):
        if v[i] <= cel <= v[i + 1]:
            if v[i + 1] == v[i]:
                return float(x[i])
            return float(x[i] + (cel - v[i]) * (x[i + 1] - x[i]) / (v[i + 1] - v[i]))
    return float(x[-1])


def korekta_sieczna(x_c, v_c, x_g, v_g, cel: float) -> float | None:
    """Sieczna przez punkt potwierdzenia (x_c, v_c) i punkt siatki po stronie celu, którego wygładzone v jest
    najbliższe celowi i ma właściwy znak nachylenia (v rośnie z x). Gdy takiego punktu nie ma: środek między
    x_c a najbliższym punktem siatki po stronie celu. Wynik obcięty do zakresu siatki; None, gdy po stronie
    celu nie ma punktu siatki."""
    x_g = np.asarray(x_g, dtype=float)
    v_g = np.maximum.accumulate(np.asarray(v_g, dtype=float))
    if not (np.isfinite(x_c) and np.isfinite(v_c) and np.isfinite(v_g).all()):
        raise StopBlad("STOP: NaN w korekcie siecznej")
    kier = 1.0 if v_c < cel else -1.0
    kand = [(xg, vg) for xg, vg in zip(x_g, v_g) if (xg - x_c) * kier > 0]
    if not kand:
        return None
    dobre = [(xg, vg) for xg, vg in kand if (vg - v_c) * kier > 0]
    if dobre:
        xg, vg = min(dobre, key=lambda t: abs(t[1] - cel))
        x_nowe = x_c + (cel - v_c) * (xg - x_c) / (vg - v_c)
    else:
        x_nowe = 0.5 * (x_c + min(kand, key=lambda t: abs(t[0] - x_c))[0])
    return float(np.clip(x_nowe, x_g.min(), x_g.max()))


# --- krok 1: amplituda poziomu wariancji ----------------------------------------------------------


def krok1(pula, konfig: dict, panele: int, ent: int, i_d: int, log=print) -> list[dict]:
    wyniki = []
    for j, amp in enumerate(AMP_SIATKA):
        par = par_poziom(RHO_BAZA, SZOK_KROK1, amp, DLUGOSCI[i_d])
        w = pilot(par, ss_pilot(ent, 1, i_d, j), panele, pula, konfig)
        wyniki.append({"amplituda": amp, **rc._json(w)})
        log(f"  D = {DLUGOSCI[i_d]:.0f}, s = {amp:.2f}: {opis_pilota(w)}")
    return wyniki


def wybierz_amplitude(wyniki: list[dict]) -> tuple[float | None, str]:
    """s* z wyników kroku 1. None = wygładzone maksimum odsetka poniżej dolnej granicy okna."""
    x = np.array([w["amplituda"] for w in wyniki])
    surowe = np.array([w["brzeg"][0] for w in wyniki])
    if not np.isfinite(surowe).all():
        raise StopBlad("STOP: NaN w odsetku przy granicy (krok 1)")
    gladkie = np.maximum.accumulate(surowe)
    if gladkie[-1] < BRZEG_OKNO[0]:
        return None, f"wygładzone maksimum {100 * gladkie[-1]:.1f} % < {100 * BRZEG_OKNO[0]:.1f} %"
    if gladkie[-1] >= BRZEG_SRODEK:
        s = odwrotna_liniowa(x, gladkie, BRZEG_SRODEK)
        return round(s, ZAOKR), "interpolacja do środka celu (51,3 %)"
    i_max = int(np.argmax(surowe))
    prog = max(BRZEG_OKNO[0], surowe[i_max] - 2.0 * wyniki[i_max]["brzeg"][1])
    kand = sorted(float(x[i]) for i in range(len(x)) if surowe[i] >= prog)
    return round(kand[(len(kand) - 1) // 2], ZAOKR), "dolna mediana płaskowyżu"


def potwierdz_amplitude(
    s_start: float, i_d: int, wyniki1: list[dict], pula, konfig, panele, ent, log=print
) -> dict:
    """Potwierdzenie amplitudy na świeżych panelach i najwyżej dwie korekty sieczną (po odsetku przy granicy)."""
    x_g = [w["amplituda"] for w in wyniki1]
    v_g = [w["brzeg"][0] for w in wyniki1]
    s, proby = round(s_start, ZAOKR), []
    for runda in range(MAX_POTWIERDZEN):
        par = par_poziom(RHO_BAZA, SZOK_KROK1, s, DLUGOSCI[i_d])
        w = pilot(par, ss_pilot(ent, 2, i_d, runda), panele, pula, konfig)
        br, nz = w["brzeg"][0], w["niezb"][0]
        ok_br = BRZEG_OKNO[0] <= br <= BRZEG_OKNO[1]
        ok_nz = nz <= GARCH_NIEZBIEZNE_MAX
        proby.append({"runda": runda, "amplituda": s, "par": par, "wynik": rc._json(w)})
        log(
            f"  potwierdzenie amplitudy {runda}: s = {s:.3f}: {opis_pilota(w)} → przy granicy "
            f"{'TAK' if ok_br else 'NIE'} (okno {100 * BRZEG_OKNO[0]:.1f}–{100 * BRZEG_OKNO[1]:.1f} %), "
            f"niezbieżne {'TAK' if ok_nz else 'NIE'}"
        )
        if ok_br and ok_nz:
            return {"status": "ok", "amplituda": s, "proby": proby}
        if not ok_br and runda < MAX_POTWIERDZEN - 1:
            nowe = korekta_sieczna(s, br, x_g, v_g, BRZEG_SRODEK)
            if nowe is not None:
                s = round(nowe, ZAOKR)
                continue
        break
    return {"status": "stop2", "amplituda": s, "proby": proby}


# --- krok 2: ścieżki VR i komórki B ----------------------------------------------------------------


def par_sciezki(sciezka: str, x: float, amp: float, dlugosc: float) -> dict:
    opis = SCIEZKI[sciezka]
    pelne = {"rho": RHO_BAZA, "rho_szok": 0.0} | opis["stale"] | {opis["os"]: x}
    return par_poziom(pelne["rho"], pelne["rho_szok"], amp, dlugosc)


def policz_sciezki(
    pula, konfig: dict, panele: int, ent: int, amp: float, dlugosc: float, log=print
):
    wyn: dict = {}
    for nazwa, opis in SCIEZKI.items():
        wyn[nazwa] = []
        for j, x in enumerate(opis["siatka"]):
            w = pilot(
                par_sciezki(nazwa, x, amp, dlugosc),
                ss_pilot(ent, 3, NR_SCIEZKI[nazwa], j),
                panele,
                pula,
                konfig,
            )
            wyn[nazwa].append({"x": x, **rc._json(w)})
            log(f"  ścieżka {nazwa}, {opis['os']} = {x:.2f}: {opis_pilota(w)}")
    return wyn


def wybierz_sciezke(cel: float, sciezki: dict) -> str:
    """T < VR(S, 0) → R↓; VR(S, 0) ≤ T ≤ VR(S, 1) → S; T > VR(S, 1) → R↑."""
    vr_s = [p["vr"][0] for p in sciezki["S"]]
    if not np.isfinite(vr_s).all():
        raise StopBlad("STOP: NaN w VR ścieżki S")
    v0, v1 = vr_s[0], max(vr_s)
    if cel < v0:
        return "R_dol"
    return "S" if cel <= v1 else "R_gora"


def potwierdz_komorke(
    nr: str, cel: float, sciezka: str, x_start: float, pkt: list[dict], amp: float, dlugosc: float,
    pula, konfig, panele, ent, log=print,
) -> dict:  # fmt: skip
    """Potwierdzenie VR komórki B na świeżych panelach i najwyżej dwie korekty sieczną wzdłuż tej samej ścieżki.
    Korekta tylko, gdy VR jest poza tolerancją (niezbieżne ponad 2 % kończy komórkę bez korekty)."""
    x_g, v_g = [p["x"] for p in pkt], [p["vr"][0] for p in pkt]
    opis = SCIEZKI[sciezka]
    x, proby = round(x_start, ZAOKR), []
    for runda in range(MAX_POTWIERDZEN):
        par = par_sciezki(sciezka, x, amp, dlugosc)
        w = pilot(par, ss_pilot(ent, 4, NR_KOMORKI_B[nr], runda), panele, pula, konfig)
        vr, nz = w["vr"][0], w["niezb"][0]
        ok_vr, ok_nz = abs(vr - cel) <= TOL_VR, nz <= GARCH_NIEZBIEZNE_MAX
        proby.append({"runda": runda, "x": x, "par": par, "wynik": rc._json(w), "ok_vr": ok_vr})
        log(
            f"  {nr} potwierdzenie {runda}: {opis['os']} = {x:.3f}: {opis_pilota(w)} → "
            f"VR {'TAK' if ok_vr else 'NIE'} (cel {cel:.3f} ± {TOL_VR}), niezbieżne {'TAK' if ok_nz else 'NIE'}"
        )
        if ok_vr and ok_nz:
            return {"status": "ok", "sciezka": sciezka, "cel": cel, "par": par, "proby": proby}
        if not ok_vr and runda < MAX_POTWIERDZEN - 1:
            nowe = korekta_sieczna(x, vr, x_g, v_g, cel)
            if nowe is not None:
                x = round(nowe, ZAOKR)
                continue
        break
    return {
        "status": "stop2",
        "sciezka": sciezka,
        "cel": cel,
        "par": proby[-1]["par"],
        "proby": proby,
    }


def kalibruj(pula, konfig: dict, panele: dict, ent: int = SEED_PILOT, log=print) -> dict:
    """Krok 1 (s*, D*), potwierdzenie amplitudy, N2, ścieżki VR, potwierdzenia komórek B1–B3."""
    wyn: dict = {
        "seed_pilot": ent,
        "konfig": konfig,
        "krok1": {},
        "amp_star": None,
        "dlugosc_star": None,
        "komorki": {},
    }
    for i_d, dlugosc in enumerate(DLUGOSCI):
        log(f"KROK 1: amplituda s przy D = {dlugosc:.0f} (ρ = 0.8, ρ_szok = 0.5, α + β = 0.98)")
        w1 = krok1(pula, konfig, panele["krok1"], ent, i_d, log)
        wyn["krok1"][f"D{dlugosc:.0f}"] = w1
        if i_d == 0 and w1[0]["brzeg"][0] > BRZEG_ZERO_MAX:
            raise StopBlad(
                f"STOP: odsetek przy granicy bez poziomu wariancji {100 * w1[0]['brzeg'][0]:.1f} % > "
                f"{100 * BRZEG_ZERO_MAX:.0f} % — generator albo miara zepsute"
            )
        s_star, jak = wybierz_amplitude(w1)
        if s_star is None:
            log(f"  brak s* ({jak})")
            continue
        log(f"  s* = {s_star:.3f} ({jak})")
        pot = potwierdz_amplitude(s_star, i_d, w1, pula, konfig, panele["potwierdzenie"], ent, log)
        wyn[f"potwierdzenie_amplitudy_D{dlugosc:.0f}"] = pot
        if pot["status"] == "ok":
            wyn["amp_star"], wyn["dlugosc_star"] = pot["amplituda"], dlugosc
            wyn["jak_wybrano"] = jak
            break
        log("  potwierdzenie amplitudy nie powiodło się (STOP 2 dla tej długości reżimu)")
        wyn["stop"] = "STOP 2: potwierdzenie amplitudy nie powiodło się po 2 korektach"
        break
    if wyn["amp_star"] is None:
        wyn["stop"] = wyn.get("stop") or (
            "STOP 1: żadna amplituda nie daje wygładzonego odsetka przy granicy ≥ 41,3 % "
            "ani dla D = 300, ani dla D = 150"
        )
        log(wyn["stop"])
        return wyn
    amp, dlugosc = wyn["amp_star"], wyn["dlugosc_star"]
    log(f"N2 (opis): ρ = 0, ρ_szok = 0, s = {amp:.3f}, D = {dlugosc:.0f}")
    w = pilot(par_poziom(0.0, 0.0, amp, dlugosc), ss_pilot(ent, 6, 0), panele["n2"], pula, konfig)
    wyn["n2"] = rc._json(w)
    log(f"  {opis_pilota(w)}")
    log("KROK 2: ścieżki VR przy (s*, D*)")
    wyn["sciezki"] = policz_sciezki(pula, konfig, panele["sciezka"], ent, amp, dlugosc, log)
    for nr, cel in CEL_VR.items():
        sc = wybierz_sciezke(cel, wyn["sciezki"])
        pkt = wyn["sciezki"][sc]
        x0 = odwrotna_liniowa(
            [p["x"] for p in pkt], [p["vr"][0] for p in pkt], cel, tol_dol=TOL_VR, tol_gora=TOL_VR
        )
        if x0 is None:
            wyn["komorki"][nr] = {
                "status": "niedostepna",
                "sciezka": sc,
                "cel": cel,
                "powod": f"cel {cel:.3f} poza zakresem VR ścieżki {sc} o więcej niż {TOL_VR}",
            }
            log(f"  {nr}: ścieżka {sc}, cel {cel:.3f} poza zakresem → niedostępna")
            continue
        wyn["komorki"][nr] = potwierdz_komorke(
            nr, cel, sc, x0, pkt, amp, dlugosc, pula, konfig, panele["potwierdzenie"], ent, log
        )
    return wyn


# --- kontrola ujemna generatora (R8, K-gen-N) -----------------------------------------------------


def kontrola_n(pula, konfig: dict, panele: int, ent: int = SEED_PILOT) -> dict:
    """ρ = 0, ρ_szok = 0, α + β = 0.98, bez poziomu wariancji: średnie ρ̂ ma być ≈ 0."""
    w = pilot(par_poziom(0.0, 0.0, 0.0, DLUGOSC), ss_pilot(ent, 5, 0), panele, pula, konfig)
    lo, hi = KONTROLA_N_PRZEDZIAL
    return {"wynik": w, "ok": lo <= w["rho"][0] <= hi}


# --- przebieg rejestrowy: jeden panel -------------------------------------------------------------


def prognoza_d(zr, nazwa: str, p: float = P) -> tuple[np.ndarray, np.ndarray]:
    if nazwa in ("zan10", "zan20"):
        return prognoza(zr, nazwa, p)
    return rc.prognoza_c(zr, nazwa, p)


def przetworz_panel_d(arg) -> tuple[np.ndarray, np.ndarray, float]:
    """Panel → (STAT: prognozy × STAT, DIAG, VR z `vr_rho` na trafieniach garch_tnu)."""
    ss, par, konfig = arg
    ss_gen, ss_boot = _potomne(ss, 2)
    panel = generuj_panel_lv2d(konfig["n_dni"], K, seed=_ziarno_int(ss_gen), nu=NU, **par)
    zr = zbuduj_zrodla(panel, start=konfig["start"])
    n = konfig["n_dni"] - konfig["start"]
    idx = np.random.default_rng(ss_boot).integers(0, n, size=(konfig["boot"], n))
    stat = np.empty((len(PROG_D), len(STAT)))
    for i, nazwa in enumerate(PROG_D):
        q, es = prognoza_d(zr, nazwa)
        stat[i] = statystyki_komorki(zr.r, q, es, P, idx)
    q, _ = prognoza_d(zr, KA)
    vr_pom = vr_rho((zr.r < q).sum(axis=1).astype(float), K, P)[0]
    return stat, np.array([zr.diag[d] for d in DIAG], dtype=float), vr_pom


def uruchom_komorke(par: dict, ss: np.random.SeedSequence, panele: int, pula, konfig: dict) -> dict:
    zadania = [(s, par, konfig) for s in _potomne(ss, panele)]
    czesci = rc._mapuj(przetworz_panel_d, zadania, pula)
    return {
        "stat": np.stack([c[0] for c in czesci]),
        "diag": np.stack([c[1] for c in czesci]),
        "vr_pom": np.array([c[2] for c in czesci]),
    }


# --- liczby i reguły ------------------------------------------------------------------------------


def odsetek_d(wyn: dict, nazwa: str, stat: str) -> tuple[float, float]:
    v = wyn["stat"][:, PROG_D.index(nazwa), IDX[stat]]
    return float(np.mean(v)), _se(v)


def ocen_komorke(wyn: dict, spec: dict) -> dict:
    """Reguła K z zamrożonego `ocen_k`. `spec["k7_pelne"]` (tylko A0): K7a, K7b, K7c, K7d bramkują; w komórkach B
    bramkuje tylko K7c, a K7a, K7b, K7d są opisem. KAL-VR i KAL-BRZEG dla komórek skalibrowanych."""
    k7 = liczby_k7(wyn)
    oc = ocen_k(
        {
            "k1": odsetek_d(wyn, "wyr_t5", "zb_bonf"),
            "k2": odsetek_d(wyn, "zan30", "zb_bonf"),
            "k7": k7,
            "ka": odsetek_d(wyn, KA, "zb_bonf"),
            "kb": odsetek_d(wyn, KB, "zb_bonf"),
        }
    )
    pelne = spec["k7_pelne"]
    kontrole = [k for k in oc["kontrole"] if pelne or k["kod"] in KONTROLE_BRAMKUJACE_B]
    opis_k7 = [] if pelne else [k for k in oc["kontrole"] if k["kod"] not in KONTROLE_BRAMKUJACE_B]
    if spec.get("cel_vr") is not None:
        cel, (vr, se) = spec["cel_vr"], odsetek_d(wyn, KA, "vr")
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
        lo, hi = BRZEG_OKNO
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
        "opis_k7": opis_k7,
        "werdykt": _werdykt(kontrole, oc["kryteria"]),
    }


# --- komórki rejestrowe ---------------------------------------------------------------------------

NAZWY_KOMOREK = ("A0", "B1", "B2", "B3")
OPIS_KOMOREK = {
    "A0": "scenariusz LV2 dla K = 4 (bez poziomu wariancji)",
    "B1": "dół przedziału z 020 (VR 1,717)",
    "B2": "środek przedziału z 020 (komórka główna, VR 2,264)",
    "B3": "góra przedziału z 020 (VR 2,811)",
}
PANELE_REJ = {"A0": 4000, "B1": 4000, "B2": 4000, "B3": 4000}


def zbuduj_komorki(kal: dict, panele: dict | None = None) -> dict:
    """Specyfikacje komórek z pliku kalibracji. A0 idzie zawsze; komórka B tylko ze statusem `ok`."""
    panele = panele or PANELE_REJ
    spec = {
        "A0": {
            "par": par_poziom(RHO_BAZA, 0.0, 0.0, kal.get("dlugosc_star") or DLUGOSC),
            "k7_pelne": True,
            "cel_vr": None,
            "kal_brzeg": False,
        }
    }
    for nr in ("B1", "B2", "B3"):
        k = kal.get("komorki", {}).get(nr, {})
        if k.get("status") == "ok":
            spec[nr] = {
                "par": k["par"],
                "k7_pelne": False,
                "cel_vr": CEL_VR[nr],
                "kal_brzeg": True,
            }
    return {n: spec[n] | {"panele": panele[n]} for n in NAZWY_KOMOREK if n in spec}


def przebieg(spec: dict, pula, konfig: dict, ent: int = SEED_REJ, log=None) -> dict:
    wyniki = {}
    for n in NAZWY_KOMOREK:
        if n not in spec:
            continue
        t0 = time.time()
        ss = np.random.SeedSequence(ent, spawn_key=(NAZWY_KOMOREK.index(n),))
        wyniki[n] = uruchom_komorke(spec[n]["par"], ss, spec[n]["panele"], pula, konfig)
        if log:
            log(f"  komórka {n}: {spec[n]['panele']} paneli w {time.time() - t0:.0f} s")
    return wyniki


# --- wydruk (neutralny reporter, R14) -------------------------------------------------------------


def _pc(v: float) -> str:
    return f"{100 * v:5.1f}"


def _wiersz_prognozy(wyn: dict, nazwa: str) -> str:
    v = {st: odsetek_d(wyn, nazwa, st) for st in STAT if st != "niezdef"}
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
    br, se_br = k7["brzeg"]
    print(
        f"  diagnostyka GARCH-t: ν̂ {k7['nu'][0]:.3f}, persystencja {k7['pers'][0]:.4f}, "
        f"niezbieżne {100 * k7['nie_zbiezne'][0]:.2f} %, przy granicy {100 * br:.2f} % (± {100 * se_br:.2f} pp); "
        f"stare okno 019 [{100 * BRZEG_STARE[0]:.1f}; {100 * BRZEG_STARE[1]:.1f}] %: "
        f"{'TAK' if BRZEG_STARE[0] <= br <= BRZEG_STARE[1] else 'NIE'}"
    )
    vr, se_vr = odsetek_d(wyn, KA, "vr")
    rho_p = (wyn["stat"][:, PROG_D.index(KA), IDX["vr"]] - 1.0) / (K - 1.0)
    q = np.quantile(rho_p, [0.05, 0.5, 0.95])
    print(
        f"  VR trafień garch_tnu: {vr:.3f} ± {se_vr:.3f}; ρ̂ = (VR − 1)/(K − 1): średnia {rho_p.mean():.4f}, "
        f"kwantyle 5/50/95 % po panelach: {q[0]:.3f} / {q[1]:.3f} / {q[2]:.3f}"
    )
    print(f"  odsetek trafień garch_tnu: {100 * odsetek_d(wyn, KA, 'hit')[0]:.2f} % (cel 5 %)")
    print(
        f"  parytet VR runnera z `vr_rho`: max |różnica| = "
        f"{np.max(np.abs(wyn['stat'][:, PROG_D.index(KA), IDX['vr']] - wyn['vr_pom'])):.2e}"
    )
    print(f"  REGUŁA K, p = 5 %, K = {K}, n = 1 691")
    _wypisz_ocene(ocena, "kontrole i kryteria")
    for k in ocena["opis_k7"]:
        w = k["wartosc"]
        txt = f"{w:.3f}" if k["kod"] in ("K7a", "K7b") else f"{100 * w:.1f} %"
        print(f"    {k['kod']} (opis, nie bramkuje w tej komórce): {txt} — {k['wymaganie']}")
    for kod, nazwa_p in (("zan10", "σ wyroczni × 0,90"), ("zan20", "σ wyroczni × 0,80")):
        m, s = odsetek_d(wyn, kod, "zb_bonf")
        print(f"  MOC WYROCZNI [opis] {kod} ({nazwa_p}): {100 * m:.1f} % ± {100 * s:.2f} pp")
    x, moc, se = rc.krzywa_mocy(wyn)
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
    for n in PROG_D:
        print("  " + _wiersz_prognozy(wyn, n))
    return ocena


def wypisz_porownanie(wyniki: dict) -> None:
    if "A0" not in wyniki:
        return
    print("\nPORÓWNANIE Z A0 (opis): różnica w jednostkach SE różnicy; |z| > 3 = wyraźna różnica")
    for n in ("B1", "B2", "B3"):
        if n not in wyniki:
            continue
        for kod, prog in (("K-a", KA), ("K-b", KB), ("zan10", "zan10")):
            z = rc.roznica_se(
                odsetek_d(wyniki[n], prog, "zb_bonf"), odsetek_d(wyniki["A0"], prog, "zb_bonf")
            )
            print(f"  {n} − A0, {kod}: {z:+.2f}" + ("  [> 3 SE]" if abs(z) > 3 else ""))


def wypisz_kalibracje(kal: dict) -> None:
    print(
        f"  s* = {kal.get('amp_star')}, D* = {kal.get('dlugosc_star')} ({kal.get('jak_wybrano')}); "
        f"ziarno pilotażu {kal.get('seed_pilot')}"
    )
    if kal.get("n2"):
        n2 = kal["n2"]
        print(
            f"  N2 (opis, ρ = 0, ρ_szok = 0, z poziomem): VR {n2['vr'][0]:.3f} ± {n2['vr'][1]:.3f}, "
            f"przy granicy {100 * n2['brzeg'][0]:.1f} %"
        )
    for nr, k in kal.get("komorki", {}).items():
        print(f"  {nr}: {k['status']}, ścieżka {k.get('sciezka')}, parametry {k.get('par')}")


def przewidywania(oceny: dict, wyniki: dict, kal: dict) -> list[tuple[str, bool]]:
    """Sprawdzenie przewidywań z pre-rejestracji (NIE kryteria)."""
    s = kal.get("amp_star")
    w = [
        ("kalibracja odsetka możliwa (nie STOP 1)", s is not None),
        ("D* = 300 (przewidywane)", kal.get("dlugosc_star") == DLUGOSC),
        ("s* ∈ [0,5; 1,25]", s is not None and 0.5 <= s <= 1.25),
        (
            "B2 przeszła potwierdzenie VR",
            kal.get("komorki", {}).get("B2", {}).get("status") == "ok",
        ),
        ("B1 osiągalna", kal.get("komorki", {}).get("B1", {}).get("status") == "ok"),
        ("B3 na ścieżce R↑", kal.get("komorki", {}).get("B3", {}).get("sciezka") == "R_gora"),
        (
            "odsetek przy granicy w ogóle sięga 51,3 % (surowy punkt siatki)",
            any(
                max(p["brzeg"][0] for p in punkty) >= BRZEG_SRODEK
                for punkty in kal.get("krok1", {}).values()
            ),
        ),
    ]
    if kal.get("n2"):
        w.append(("N2: sam poziom daje VR ∈ [1,3; 1,9]", 1.3 <= kal["n2"]["vr"][0] <= 1.9))
    zakresy = {
        "A0": ((0.05, 0.08), (0.40, 0.75)),
        "B1": ((0.07, 0.14), (0.35, 0.72)),
        "B2": ((0.08, 0.16), (0.30, 0.68)),
        "B3": ((0.09, 0.18), (0.25, 0.62)),
    }
    for n, (ra, rb) in zakresy.items():
        if n not in wyniki:
            continue
        ka, kb = odsetek_d(wyniki[n], KA, "zb_bonf")[0], odsetek_d(wyniki[n], KB, "zb_bonf")[0]
        w.append((f"{n}: K-a ∈ [{ra[0]:.0%}; {ra[1]:.0%}]", ra[0] <= ka <= ra[1]))
        w.append((f"{n}: K-b ∈ [{rb[0]:.0%}; {rb[1]:.0%}]", rb[0] <= kb <= rb[1]))
        k1, k2 = (
            odsetek_d(wyniki[n], "wyr_t5", "zb_bonf")[0],
            odsetek_d(wyniki[n], "zan30", "zb_bonf")[0],
        )
        w.append((f"{n}: K1 ∈ [2,5; 7,5] %", 0.025 <= k1 <= 0.075))
        w.append((f"{n}: K2 ≥ 95 %", k2 >= 0.95))
        if n != "A0":
            nz = liczby_k7(wyniki[n])["nie_zbiezne"][0]
            w.append((f"{n}: K7c niezbieżne ≤ 2 %", nz <= GARCH_NIEZBIEZNE_MAX))
    if "B2" in wyniki:
        z10 = odsetek_d(wyniki["B2"], "zan10", "zb_bonf")[0]
        w.append(("B2: moc wyroczni zan10 ∈ [35; 68] %", 0.35 <= z10 <= 0.68))
        w.append(
            (
                "B2: K-a ≤ 10 % (przewidywane 40 %)",
                odsetek_d(wyniki["B2"], KA, "zb_bonf")[0] <= 0.10,
            )
        )
        w.append(
            ("B2: K-b ≥ 80 % (przewidywane 7 %)", odsetek_d(wyniki["B2"], KB, "zb_bonf")[0] >= 0.80)
        )
    if "A0" in wyniki:
        w.append(("K-gen-D zaliczona", rc.kgen_d(wyniki["A0"])[1]))
    for n in ("A0", "B2"):
        if n in oceny:
            w.append((f"werdykt {n} = NIE", oceny[n]["werdykt"] == "NIE"))
    return w


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(
        description="021 — LV2d: laboratorium VaR/ES, K = 4, poziom wariancji"
    )
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
    print("021 — LV2d: laboratorium VaR/ES dla K = 4 z poziomem wariancji (karta 021)")
    if a.smoke:
        print("SMOKE — NIE JEST PRZEBIEGIEM: małe panele, tylko test działania kodu.")
    print(
        "Wersje: python "
        + sys.version.split()[0]
        + "".join(f", {p} {version(p)}" for p in ("numpy", "scipy", "pandas"))
        + "."
    )
    try:
        with rc.pula_procesow(a.workers) as pula:
            if a.tryb == "kontrola-n":
                _tryb_kontrola_n(pula, konfig, a.smoke)
            elif a.tryb == "kalibruj":
                _tryb_kalibruj(pula, konfig, a)
            else:
                _tryb_rejestr(pula, konfig, a)
    except StopBlad as e:
        print(str(e))
        raise SystemExit(1) from e
    print(f"Czas {time.time() - t0:.0f} s ({a.workers} procesów)", file=sys.stderr)


def _tryb_kontrola_n(pula, konfig: dict, smoke: bool) -> None:
    ent = SEED_SMOKE if smoke else SEED_PILOT
    panele = (PANELE_SMOKE if smoke else PANELE_PILOT)["kontrola_n"]
    res = kontrola_n(pula, konfig, panele, ent)
    print(
        f"K-gen-N (R8, ujemna): ρ = 0, ρ_szok = 0, α + β = 0.98, bez poziomu wariancji, ziarno {ent}, {panele} paneli"
    )
    print(f"  {opis_pilota(res['wynik'])}")
    lo, hi = KONTROLA_N_PRZEDZIAL
    print(
        f"  średnie ρ̂ {res['wynik']['rho'][0]:+.4f} ± {res['wynik']['rho'][1]:.4f}; wymaganie ∈ [{lo}; {hi}]: "
        f"{'ZALICZONA' if res['ok'] else 'NIEZALICZONA'}"
    )


def _tryb_kalibruj(pula, konfig: dict, a) -> None:
    ent = SEED_SMOKE if a.smoke else SEED_PILOT
    print(
        f"KALIBRACJA (pilotaż): ziarno {ent}, konfig {konfig}; drukowane tylko VR, ρ̂, odsetek przy granicy, "
        "niezbieżne, persystencja, ν̂, rozrzut skali."
    )
    wyn = kalibruj(pula, konfig, PANELE_SMOKE if a.smoke else PANELE_PILOT, ent)
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
    ent = SEED_SMOKE if a.smoke else SEED_REJ
    surowe = Path(a.kalibracja).read_bytes()
    kal = json.loads(surowe)
    spec = zbuduj_komorki(kal, {n: 4 for n in NAZWY_KOMOREK} if a.smoke else None)
    print(f"Kalibracja: {a.kalibracja} (sha256 {hashlib.sha256(surowe).hexdigest()[:16]})")
    wypisz_kalibracje(kal)
    print(
        f"Ziarno rejestrowe {ent} (komórka i = SeedSequence(ziarno, spawn_key=(i,))), konfig {konfig}, "
        f"poziom testów 5 %, B = {konfig['boot']}."
    )
    for n, s in spec.items():
        print(f"  {n}: {s['par']}, {s['panele']} paneli")
    for nr in ("B1", "B2", "B3"):
        if nr not in spec:
            k = kal.get("komorki", {}).get(nr, {})
            print(f"  {nr}: NIEDOSTĘPNA ({k.get('powod') or k.get('status') or kal.get('stop')})")
    if "B2" not in spec:
        print("STOP: komórka główna B2 niedostępna — werdykt rundy co najwyżej Revision.")
    wyniki = przebieg(spec, pula, konfig, ent, log=lambda t: print(t, file=sys.stderr, flush=True))
    if a.zapisz:
        os.makedirs(os.path.dirname(os.path.abspath(a.zapisz)), exist_ok=True)
        np.savez_compressed(
            a.zapisz, **{f"{n}_{k}": v for n, w in wyniki.items() for k, v in w.items()}
        )
    oceny = {n: wypisz_komorke(n, spec[n], wyniki[n]) for n in wyniki}
    wypisz_porownanie(wyniki)
    vr_a0, ok_d = rc.kgen_d(wyniki["A0"])
    print(
        f"\nK-gen-D (R8, dodatnia): średnie VR komórki A0 = {vr_a0:.3f}; wymaganie {VR_A0} ± {TOL_VR_A0}: "
        f"{'ZALICZONA' if ok_d else 'NIEZALICZONA'}"
    )
    print("\nWERDYKTY KOMÓREK (zamrożony `_werdykt`):")
    for n in NAZWY_KOMOREK:
        if n in oceny:
            print(f"  {n}: {oceny[n]['werdykt']} ({WERDYKT_TXT[oceny[n]['werdykt']]})")
    print("\nPRZEWIDYWANIA z pre-rejestracji (NIE kryteria):")
    for tekst, ok in przewidywania(oceny, wyniki, kal):
        print(f"  {tekst}: {'TAK' if ok else 'NIE'}")
    if a.smoke:
        print("\nSMOKE: powyższe wyniki nie są werdyktem.")


if __name__ == "__main__":
    main()
