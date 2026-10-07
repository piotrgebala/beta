"""
LV2 — laboratorium VaR/ES dla prognoz ESTYMOWANYCH (okno, EWMA, GARCH-t, HAR). Zadanie 016.
Pre-rejestracja: `runs/2026-10-07_lv2-var-es-estymowane/README.md`. Neutralny reporter (R14).

    python -m symulacje.run_lv2 --workers 16 > runs/2026-10-07_lv2-var-es-estymowane/raw_output.txt
    python -m symulacje.run_lv2 --smoke      # małe panele: TYLKO sprawdzenie, że kod działa

Pytania: (K) czy zbiorczy test wsteczny LV1 uczciwie ocenia prognozę ESTYMOWANĄ i poprawnie określoną
(GARCH-t dopasowany walk-forward), (P) czy test porównawczy (FZ0 / strata kwantylowa + Diebold–Mariano
na dziennych średnich po monetach) odróżnia dwie prognozy estymowane. Dane WYŁĄCZNIE syntetyczne.

Wynik nie zależy od liczby procesów (`--workers`): ziarna rozdziela SeedSequence.spawn per panel.
Na stdout (raw_output.txt) idą tylko liczby odtwarzalne; czas przebiegu i postęp idą na stderr.
Panel generujemy RAZ (K_MAX monet, `n_dni` dni); komórka (K, n) to pierwsze K monet i pierwsze n dni
okresu oceny tego samego panelu (zagnieżdżone), każda z własnymi indeksami bootstrapu.
"""

from __future__ import annotations

import argparse
import math
import multiprocessing as mp
import os
import sys
import time
from functools import cache

import numpy as np

from symulacje.garch_panel import generuj_panel
from symulacje.moc_var_es import NU, mde, odrzuca_zbiorczo, testy_zbiorcze, wklady_dzienne
from symulacje.porownanie_lv2 import STRATY, dm_wektor, mnoznik_zerowy, straty_dzienne
from symulacje.prognozy_lv2 import (
    PROGNOZY,
    PROGNOZY_PODPANEL,
    ZANIZENIA,
    prognoza,
    prognoza_wyrocznia_skala,
    zbuduj_zrodla,
)

SEED = 20_261_016
RHO = 0.8
POZIOMY = (0.01, 0.05)
ALFA = 0.05  # zbiorczy test: Bonferroni, każde z A, B, C na ALFA / 3
Z_KRYT = 1.959964  # DM: dwustronnie 5 % z rozkładu normalnego

KONFIG = {
    "panele": 5000,  # SE odsetka ≤ 0,71 pp (0,57 pp przy mocy 80 %, 0,31 pp przy 5 %)
    "boot": 999,
    "n_dni": 2100,
    "start": 400,
    "k_panel": 20,
    "komorki": (
        (20, 1600),
        (15, 1700),
    ),  # (K, n); pierwsza = komórka główna (LV1), druga = populacja F2-1b
}
KONFIG_SMOKE = {
    "panele": 4,
    "boot": 99,
    "n_dni": 700,
    "start": 400,
    "k_panel": 8,
    "komorki": ((8, 250), (6, 300)),
}

# Progi pre-rejestracji (README rundy, „Kryteria”). Zapisane przed pełnym przebiegiem.
ROZMIAR = (0.025, 0.075)  # K1, K4, K6: rozmiar testu pod prawdziwą H0
ROZMIAR_ESTYMOWANY_MAX = (
    0.10  # K-a: rozmiar testu zbiorczego dla estymowanej, poprawnie określonej prognozy
)
MOC_MIN = 0.80  # K-b, P-a, P-b
MOC_KONTROLA = 0.95  # K2, K5: moc wobec σ zaniżonego o 30 %
X_MAX = 0.10  # P-a: największe dopuszczalne zaniżenie σ, które test porównawczy ma wykrywać
GARCH_NU = (4.0, 6.5)  # K7: średnia ν̂ (prawda 5)
GARCH_PERS = (0.95, 0.995)  # K7: średnia α̂ + β̂ (prawda 0,98)
GARCH_NIEZBIEZNE_MAX = 0.02  # K7: odsetek dopasowań bez zbieżności
GARCH_BRZEG_MAX = 0.05  # K7: odsetek dopasowań przy granicy zakresu parametrów

GRID = ("wyr_t5", *ZANIZENIA)  # oś x zaniżenia σ wyroczni; pierwsza = x 0 (rozmiar)
X_GRID = (0.0, *ZANIZENIA.values())
KONTROLA_X = "zan30"
ESTYMOWANE = ("okno60_t5", "ewma94_t5", "garch_t5", "garch_tnu", "har_t5")
PARA_GLOWNA = ("ewma94_t5", "garch_tnu")  # „baseline vs poprawna klasa modelu dopasowana na danych”
PARY_REALNE = (
    ("okno60_t5", "ewma94_t5"),
    PARA_GLOWNA,
    ("okno60_t5", "garch_tnu"),
    ("garch_tnu", "garch_t5"),
    ("ewma94_t5", "har_t5"),
    ("ewma94_t5", "ewma94_ep"),
)
C_ZERO = (0.9, 0.8)  # c_A par „dokładnie zerowych” (c_B z równości oczekiwanych strat)
WAGA_PINB = "ewma94"  # wspólna waga σ̂ straty kwantylowej (znana w t − 1)

STAT = ("hit", "u_sr", "zb_a", "zb_b", "zb_c", "zb_bonf", "zb_a_prawa", "vr", "niezdef")
IDX = {nazwa: i for i, nazwa in enumerate(STAT)}
DIAG = ("dopasowania", "nie_zbiezne", "brzeg", "persystencja", "nu")


def _klucz_zerowy(strata: str, c_a: float) -> str:
    return f"nul_{strata}_{round(100 * c_a)}"


def zbuduj_porownania() -> list[dict]:
    """Lista porównań DM: A − B, t > 0 ⇒ B lepsza. `rola`: zero, moc, wyr, real."""
    lista = []
    for c_a in C_ZERO:
        for s in STRATY:
            lista.append(
                {
                    "kod": f"zero_{s}_{round(100 * c_a)}",
                    "rola": "zero",
                    "a": f"zan{round(100 * (1 - c_a)):02d}",
                    "b": _klucz_zerowy(s, c_a),
                    "strata": s,
                }
            )
    for nazwa in ZANIZENIA:
        for s in STRATY:
            lista.append(
                {"kod": f"moc_{s}_{nazwa}", "rola": "moc", "a": nazwa, "b": "wyr_t5", "strata": s}
            )
    for nazwa in ESTYMOWANE:
        for s in STRATY:
            lista.append(
                {"kod": f"wyr_{s}_{nazwa}", "rola": "wyr", "a": nazwa, "b": "wyr_t5", "strata": s}
            )
    for a, b in PARY_REALNE:
        for s in STRATY:
            lista.append({"kod": f"real_{s}_{a}__{b}", "rola": "real", "a": a, "b": b, "strata": s})
    return lista


POROWNANIA = zbuduj_porownania()
POR_IDX = {por["kod"]: i for i, por in enumerate(POROWNANIA)}


def _ziarno_int(ss: np.random.SeedSequence) -> int:
    return int(ss.generate_state(1, dtype=np.uint64)[0])


@cache
def _c_zerowe(strata: str, c_a: float, p: float) -> float:
    return mnoznik_zerowy(c_a, p, NU, strata)


def statystyki_komorki(r, q, es, p: float, idx: np.ndarray) -> np.ndarray:
    """Wektor STAT dla jednej komórki (p, K, n, prognoza): trafienia i test zbiorczy po dniach."""
    k = r.shape[1]
    hit = r < q
    s, d = wklady_dzienne(r, q, es, p)
    zb = testy_zbiorcze(r, q, es, p, idx)
    pz = np.array([zb["p_a"], zb["p_b"], zb["p_c"]])
    w = np.empty(len(STAT))
    w[IDX["hit"]] = hit.mean()
    w[IDX["u_sr"]] = 1.0 + d.mean() / k
    w[IDX["zb_a"]], w[IDX["zb_b"]], w[IDX["zb_c"]] = (pz < ALFA / 3).astype(float)
    w[IDX["zb_bonf"]] = float(odrzuca_zbiorczo(pz, ALFA))
    w[IDX["zb_a_prawa"]] = float(zb["p_a"] < ALFA / 3 and zb["t_a"] > 0)
    w[IDX["vr"]] = s.var(ddof=1) / (k * p * (1 - p))
    w[IDX["niezdef"]] = float(np.isnan(pz).sum())
    return w


def porownania_komorki(straty: dict) -> np.ndarray:
    """(t, średnia różnicy, se) każdego porównania z `POROWNANIA`; NaN, gdy brak którejś prognozy."""
    wyn = np.full((len(POROWNANIA), 3), np.nan)
    for j, por in enumerate(POROWNANIA):
        if por["a"] in straty and por["b"] in straty:
            delta = straty[por["a"]][por["strata"]] - straty[por["b"]][por["strata"]]
            dm = dm_wektor(delta)
            wyn[j] = (dm["t"], dm["srednia"], dm["se"])
    return wyn


def przetworz_panel(arg) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Jeden panel → (STAT: komórki × p × prognozy × STAT, DM: komórki × p × porównania × 3, DIAG)."""
    ss, konfig = arg
    ss_gen, ss_boot = ss.spawn(2)
    panel = generuj_panel(
        konfig["n_dni"], konfig["k_panel"], seed=_ziarno_int(ss_gen), nu=NU, rho=RHO
    )
    zr = zbuduj_zrodla(panel, start=konfig["start"])
    gen = np.random.default_rng(ss_boot)
    ns = sorted({n for _, n in konfig["komorki"]})
    idx = {n: gen.integers(0, n, size=(konfig["boot"], n)) for n in ns}
    abs_ = np.full((len(konfig["komorki"]), len(POZIOMY), len(PROGNOZY), len(STAT)), np.nan)
    dm = np.full((len(konfig["komorki"]), len(POZIOMY), len(POROWNANIA), 3), np.nan)
    for ic, (k, n) in enumerate(konfig["komorki"]):
        zk = zr if k == konfig["k_panel"] else zr.pierwsze(k)
        nazwy = list(PROGNOZY) if k == konfig["k_panel"] else list(PROGNOZY_PODPANEL)
        r, waga = zk.r[:n], zk.sigma[WAGA_PINB][:n]
        for ip, p in enumerate(POZIOMY):
            straty = {}
            for nazwa in nazwy:
                q, es = prognoza(zk, nazwa, p)
                abs_[ic, ip, list(PROGNOZY).index(nazwa)] = statystyki_komorki(
                    r, q[:n], es[:n], p, idx[n]
                )
                straty[nazwa] = straty_dzienne(r, q[:n], es[:n], p, waga)
            for s in STRATY:
                for c_a in C_ZERO:
                    q, es = prognoza_wyrocznia_skala(zk, _c_zerowe(s, c_a, p), p)
                    straty[_klucz_zerowy(s, c_a)] = straty_dzienne(r, q[:n], es[:n], p, waga)
            dm[ic, ip] = porownania_komorki(straty)
    diag = np.array([zr.diag[nazwa] for nazwa in DIAG], dtype=float)
    return abs_, dm, diag


# --- przebieg -------------------------------------------------------------------------------------

PROG_IDX = {nazwa: i for i, nazwa in enumerate(PROGNOZY)}


def uruchom(konfig: dict, workers: int, ziarno: int = SEED) -> dict:
    """Wszystkie panele → {"abs": B × komórki × p × prognozy × STAT, "dm": B × komórki × p ×
    porównania × 3, "diag": B × DIAG}. `imap` zachowuje kolejność, więc wynik nie zależy od liczby
    procesów. Procesy startują przez forkserver, więc skrypt wołający musi mieć `__main__`.
    """
    for zmienna in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(zmienna, "1")
    zadania = [(ss, konfig) for ss in np.random.SeedSequence(ziarno).spawn(konfig["panele"])]
    czesci: list[tuple] = []
    with mp.get_context("forkserver").Pool(workers) as pool:
        for i, wynik in enumerate(pool.imap(przetworz_panel, zadania, chunksize=1), 1):
            czesci.append(wynik)
            if i % 100 == 0:
                print(f"  gotowe panele: {i}/{len(zadania)}", file=sys.stderr, flush=True)
    return {
        "abs": np.stack([c[0] for c in czesci]),
        "dm": np.stack([c[1] for c in czesci]),
        "diag": np.stack([c[2] for c in czesci]),
    }


# --- liczby do reguł ------------------------------------------------------------------------------


def _se(v: np.ndarray) -> float:
    return float(np.std(v, ddof=1) / math.sqrt(len(v)))


def _odsetek(wyn: dict, ic: int, ip: int, nazwa: str, stat: str) -> tuple[float, float]:
    """(średnia, SE po panelach) statystyki STAT prognozy `nazwa` w komórce (ic, ip)."""
    v = wyn["abs"][:, ic, ip, PROG_IDX[nazwa], IDX[stat]]
    return float(np.mean(v)), _se(v)


def _dm_zdarzenia(wyn: dict, ic: int, ip: int, kod: str, tryb: str) -> np.ndarray:
    """Po panelach 1/0: czy test DM porównania `kod` odrzuca; NaN, gdy porównania nie ma w komórce.

    tryb: prawa (t > z: B lepsza), lewa (A lepsza), dwu (|t| > z), centr (|t| > z po odjęciu
    średniej różnic po panelach — rozmiar testu przy prawdziwej H0 „średnia różnica = jej średnia”).
    """
    t, sr, se = (wyn["dm"][:, ic, ip, POR_IDX[kod], j] for j in range(3))
    brak = np.isnan(sr)
    with np.errstate(invalid="ignore"):
        if tryb == "prawa":
            z = t > Z_KRYT
        elif tryb == "lewa":
            z = t < -Z_KRYT
        elif tryb == "dwu":
            z = np.abs(t) > Z_KRYT
        elif tryb == "centr":
            z = np.abs((sr - np.nanmean(sr)) / se) > Z_KRYT if not brak.all() else brak
        else:
            raise ValueError(f"tryb: prawa, lewa, dwu, centr; jest {tryb!r}")
    return np.where(brak, np.nan, z.astype(float))


def _dm_odsetek(wyn: dict, ic: int, ip: int, kod: str, tryb: str) -> tuple[float, float]:
    z = _dm_zdarzenia(wyn, ic, ip, kod, tryb)
    return float(np.mean(z)), _se(z)


def krzywa_abs(wyn: dict, ic: int, ip: int) -> tuple[np.ndarray, np.ndarray]:
    """Moc testu zbiorczego na siatce X_GRID (x = 0: rozmiar na prognozie wyroczni) i jej SE."""
    pary = [_odsetek(wyn, ic, ip, f, "zb_bonf") for f in GRID]
    return np.array([m for m, _ in pary]), np.array([s for _, s in pary])


def krzywa_dm(wyn: dict, ic: int, ip: int, strata: str) -> tuple[np.ndarray, np.ndarray]:
    """Moc DM (t > z, B = wyrocznia lepsza) na siatce X_GRID; x = 0 to średni rozmiar na parach
    „dokładnie zerowych” tej straty (pary identyczne nie mają testu)."""
    zero = [_dm_odsetek(wyn, ic, ip, f"zero_{strata}_{round(100 * c)}", "dwu") for c in C_ZERO]
    pary = [(float(np.mean([m for m, _ in zero])), float(np.mean([s for _, s in zero])))]
    pary += [_dm_odsetek(wyn, ic, ip, f"moc_{strata}_{nazwa}", "prawa") for nazwa in ZANIZENIA]
    return np.array([m for m, _ in pary]), np.array([s for _, s in pary])


def liczby_k7(wyn: dict) -> dict:
    """Diagnostyka estymatora GARCH-t: średnie po panelach (SE po panelach); odsetki per panel."""
    d = wyn["diag"]
    nie_zb, brzeg = d[:, 1] / d[:, 0], d[:, 2] / d[:, 0]
    return {
        "nu": (float(d[:, 4].mean()), _se(d[:, 4])),
        "pers": (float(d[:, 3].mean()), _se(d[:, 3])),
        "nie_zbiezne": (float(nie_zb.mean()), _se(nie_zb)),
        "brzeg": (float(brzeg.mean()), _se(brzeg)),
    }


def liczby_k(wyn: dict, ic: int, ip: int) -> dict:
    """Wejście reguły K (test bezwzględny) z tablic wyników: komórka ic, poziom ip."""
    return {
        "k1": _odsetek(wyn, ic, ip, "wyr_t5", "zb_bonf"),
        "k2": _odsetek(wyn, ic, ip, KONTROLA_X, "zb_bonf"),
        "k7": liczby_k7(wyn),
        "ka": _odsetek(wyn, ic, ip, "garch_tnu", "zb_bonf"),
        "kb": _odsetek(wyn, ic, ip, "garch_tnu_zan10", "zb_bonf"),
    }


def liczby_p(wyn: dict, ic: int, ip: int) -> dict:
    """Wejście reguły P (test porównawczy, strata FZ0) z tablic wyników: komórka ic, poziom ip."""
    krzywa, krzywa_se = krzywa_dm(wyn, ic, ip, "fz0")
    a, b = PARA_GLOWNA
    return {
        "k4": {
            f"{s}, c_A = {c}": _dm_odsetek(wyn, ic, ip, f"zero_{s}_{round(100 * c)}", "dwu")
            for s in STRATY
            for c in C_ZERO
        },
        "k5": _dm_odsetek(wyn, ic, ip, f"moc_fz0_{KONTROLA_X}", "prawa"),
        "k6": {
            f"{x} → {y}": _dm_odsetek(wyn, ic, ip, f"real_fz0_{x}__{y}", "centr")
            for x, y in PARY_REALNE
        },
        "k7": liczby_k7(wyn),
        "krzywa": krzywa,
        "krzywa_se": krzywa_se,
        "pb": _dm_odsetek(wyn, ic, ip, f"real_fz0_{a}__{b}", "prawa"),
    }


# --- reguły MIERZALNA / NIEMIERZALNA --------------------------------------------------------------


def _blisko(wartosc: float, se: float, *progi: float) -> bool:
    """Wynik w odległości < 2 SE od któregoś progu: werdykt może zależeć od losowości przebiegu."""
    return any(abs(wartosc - prog) < 2 * se for prog in progi)


def _wiersz(
    kod, grupa, opis, wartosc, wymaganie, ok, granica=False, jednostka="pct", bramka="obie"
):
    """`bramka`: czego dotyczy kontrola — „obie” (każdy wniosek), „TAK” lub „NIE” (tylko ten wniosek)."""
    return {
        "kod": kod,
        "grupa": grupa,
        "opis": opis,
        "wartosc": wartosc,
        "wymaganie": wymaganie,
        "ok": bool(ok),
        "granica": bool(granica),
        "jednostka": jednostka,
        "bramka": bramka,
    }


def _wiersze_k7(k7: dict) -> list[dict]:
    (nu, s_nu), (per, s_per) = k7["nu"], k7["pers"]
    (nz, s_nz), (br, s_br) = k7["nie_zbiezne"], k7["brzeg"]
    grupa = "KONTROLA ESTYMATORA"
    return [
        _wiersz(
            "K7a",
            grupa,
            "średnia ν̂ GARCH-t (prawda 5)",
            nu,
            f"∈ [{GARCH_NU[0]}; {GARCH_NU[1]}]",
            GARCH_NU[0] <= nu <= GARCH_NU[1],
            _blisko(nu, s_nu, *GARCH_NU),
            "num",
        ),
        _wiersz(
            "K7b",
            grupa,
            "średnia persystencja α̂ + β̂ (prawda 0,98)",
            per,
            f"∈ [{GARCH_PERS[0]}; {GARCH_PERS[1]}]",
            GARCH_PERS[0] <= per <= GARCH_PERS[1],
            _blisko(per, s_per, *GARCH_PERS),
            "num3",
        ),
        _wiersz(
            "K7c",
            grupa,
            "odsetek dopasowań bez zbieżności",
            nz,
            f"≤ {100 * GARCH_NIEZBIEZNE_MAX:.0f} %",
            nz <= GARCH_NIEZBIEZNE_MAX,
            _blisko(nz, s_nz, GARCH_NIEZBIEZNE_MAX),
        ),
        _wiersz(
            "K7d",
            grupa,
            "odsetek dopasowań przy granicy zakresu parametrów",
            br,
            f"≤ {100 * GARCH_BRZEG_MAX:.0f} %",
            br <= GARCH_BRZEG_MAX,
            _blisko(br, s_br, GARCH_BRZEG_MAX),
        ),
    ]


def _werdykt(kontrole: list[dict], kryteria: list[dict]) -> str:
    """WSTRZYMANE, gdy zawodzi kontrola „obie” albo kontrola bramkująca wyciągnięty wniosek.

    Wniosek: TAK, gdy wszystkie kryteria spełnione, inaczej NIE. Kontrola „TAK” („NIE”) bramkuje
    tylko wniosek TAK (NIE): zbyt liberalny test może tylko zawyżać moc (nie podważa NIE), zbyt
    zachowawczy — tylko zaniżać (nie podważa TAK).
    """

    def spelnione(*bramki: str) -> bool:
        return all(k["ok"] for k in kontrole if k["bramka"] in bramki)

    if not spelnione("obie"):
        return "WSTRZYMANE"
    wniosek = "TAK" if all(k["ok"] for k in kryteria) else "NIE"
    return wniosek if spelnione(wniosek) else "WSTRZYMANE"


def ocen_k(liczby: dict) -> dict:
    """Reguła K (test bezwzględny dla prognozy estymowanej) dla jednego p w jednej komórce.

    `liczby`: k1, k2, ka, kb — pary (odsetek, SE) — oraz k7 (liczby_k7). Werdykt: WSTRZYMANE, gdy
    któraś kontrola (K1, K2, K7a–d) zawodzi; inaczej TAK wtedy i tylko wtedy, gdy K-a i K-b; inaczej NIE.
    """
    lo, hi = ROZMIAR
    (k1, s1), (k2, s2) = liczby["k1"], liczby["k2"]
    (ka, sa), (kb, sb) = liczby["ka"], liczby["kb"]
    kontrole = [
        _wiersz(
            "K1",
            "KONTROLA NEGATYWNA",
            "rozmiar testu zbiorczego, prognoza wyroczni",
            k1,
            f"odsetek ∈ [{100 * lo:.1f}; {100 * hi:.1f}] %",
            lo <= k1 <= hi,
            _blisko(k1, s1, lo, hi),
        ),
        _wiersz(
            "K2",
            "KONTROLA POZYTYWNA",
            "moc testu zbiorczego wobec σ wyroczni zaniżonego o 30 %",
            k2,
            f"odsetek ≥ {100 * MOC_KONTROLA:.0f} %",
            k2 >= MOC_KONTROLA,
            _blisko(k2, s2, MOC_KONTROLA),
        ),
        *_wiersze_k7(liczby["k7"]),
    ]
    kryteria = [
        _wiersz(
            "K-a",
            "KALIBRACJA",
            "rozmiar testu zbiorczego, GARCH-t estymowany (poprawny model)",
            ka,
            f"odsetek ≤ {100 * ROZMIAR_ESTYMOWANY_MAX:.0f} %",
            ka <= ROZMIAR_ESTYMOWANY_MAX,
            _blisko(ka, sa, ROZMIAR_ESTYMOWANY_MAX),
        ),
        _wiersz(
            "K-b",
            "KALIBRACJA",
            "moc testu zbiorczego, GARCH-t estymowany ze σ zaniżonym o 10 %",
            kb,
            f"odsetek ≥ {100 * MOC_MIN:.0f} %",
            kb >= MOC_MIN,
            _blisko(kb, sb, MOC_MIN),
        ),
    ]
    return {"kontrole": kontrole, "kryteria": kryteria, "werdykt": _werdykt(kontrole, kryteria)}


def _w_przedziale(pary: dict) -> tuple[bool, bool, str]:
    """(wszystkie ∈ ROZMIAR, któraś blisko progu, nazwa najgorszej) po parach niepustych (nie NaN)."""
    lo, hi = ROZMIAR
    ok = {k: v for k, v in pary.items() if np.isfinite(v[0])}
    najgorsza = max(ok, key=lambda k: abs(ok[k][0] - 0.05))
    return (
        all(lo <= v[0] <= hi for v in ok.values()),
        any(_blisko(v[0], v[1], lo, hi) for v in ok.values()),
        najgorsza,
    )


def _skrajna(pary: dict, najwieksza: bool) -> tuple[str, float, float]:
    """(nazwa, odsetek, SE) pary z największym (najmniejszym) odsetkiem; pary NaN pomijamy."""
    ok = {k: v for k, v in pary.items() if np.isfinite(v[0])}
    nazwa = (max if najwieksza else min)(ok, key=lambda k: ok[k][0])
    return nazwa, ok[nazwa][0], ok[nazwa][1]


def ocen_p(liczby: dict) -> dict:
    """Reguła P (test porównawczy DM-FZ0) dla jednego p w jednej komórce.

    `liczby`: k4, k6 — słowniki nazwa → (odsetek, SE); k5, pb — pary; k7; krzywa, krzywa_se — moc DM
    na siatce X_GRID. Kontrole „obie” (bramkują każdy wniosek): K4 (rozmiar na parach zerowych),
    K5 (moc wobec σ − 30 %), K7a–d. Kontrole HAC po wyśrodkowaniu na parach realistycznych: K6a
    (największy rozmiar ≤ 7,5 %: test nie jest zbyt liberalny) bramkuje tylko wniosek TAK, K6b
    (najmniejszy ≥ 2,5 %: nie jest zbyt zachowawczy) tylko wniosek NIE. Kryteria: P-a (MDE ≤ X_MAX),
    P-b (moc pary głównej).
    """
    lo, hi = ROZMIAR
    k4_ok, k4_gr, k4_naj = _w_przedziale(liczby["k4"])
    k6a_naj, k6a, k6a_se = _skrajna(liczby["k6"], najwieksza=True)
    k6b_naj, k6b, k6b_se = _skrajna(liczby["k6"], najwieksza=False)
    k5, s5 = liczby["k5"]
    pb, spb = liczby["pb"]
    krz, krz_se = np.asarray(liczby["krzywa"], dtype=float), np.asarray(liczby["krzywa_se"])
    m = mde(np.asarray(X_GRID), krz, MOC_MIN)
    jx = X_GRID.index(X_MAX)  # x* leży na siatce, więc MDE ≤ x* ⇔ moc przy x* ≥ MOC_MIN
    moc_xmax = float(np.maximum.accumulate(krz)[jx])  # bez zaokrągleń interpolacji na progu
    zakres = f"odsetek ∈ [{100 * lo:.1f}; {100 * hi:.1f}] %"
    kontrole = [
        _wiersz(
            "K4",
            "KONTROLA NEGATYWNA",
            f"rozmiar DM na parach zerowych (najgorsza: {k4_naj})",
            liczby["k4"][k4_naj][0],
            zakres,
            k4_ok,
            k4_gr,
        ),
        _wiersz(
            "K5",
            "KONTROLA POZYTYWNA",
            "moc DM-FZ0: σ wyroczni − 30 % wobec wyroczni",
            k5,
            f"odsetek ≥ {100 * MOC_KONTROLA:.0f} %",
            k5 >= MOC_KONTROLA,
            _blisko(k5, s5, MOC_KONTROLA),
        ),
        _wiersz(
            "K6a",
            "KONTROLA HAC",
            f"rozmiar DM-FZ0 po wyśrodkowaniu, pary realistyczne: największy ({k6a_naj})",
            k6a,
            f"odsetek ≤ {100 * hi:.1f} %",
            k6a <= hi,
            _blisko(k6a, k6a_se, hi),
            bramka="TAK",
        ),
        _wiersz(
            "K6b",
            "KONTROLA HAC",
            f"rozmiar DM-FZ0 po wyśrodkowaniu, pary realistyczne: najmniejszy ({k6b_naj})",
            k6b,
            f"odsetek ≥ {100 * lo:.1f} %",
            k6b >= lo,
            _blisko(k6b, k6b_se, lo),
            bramka="NIE",
        ),
        *_wiersze_k7(liczby["k7"]),
    ]
    kryteria = [
        _wiersz(
            "P-a",
            "MIERZALNOŚĆ",
            "MDE zaniżenia σ testu DM-FZ0 (moc 80 %, siatka X_GRID)",
            m,
            f"MDE ≤ {X_MAX:.2f}",
            moc_xmax >= MOC_MIN,
            _blisko(krz[jx], krz_se[jx], MOC_MIN),
            "mde",
        ),
        _wiersz(
            "P-b",
            "MIERZALNOŚĆ",
            f"moc DM-FZ0: {PARA_GLOWNA[0]} wobec {PARA_GLOWNA[1]}",
            pb,
            f"odsetek ≥ {100 * MOC_MIN:.0f} %",
            pb >= MOC_MIN,
            _blisko(pb, spb, MOC_MIN),
        ),
    ]
    return {"kontrole": kontrole, "kryteria": kryteria, "werdykt": _werdykt(kontrole, kryteria)}


def regula_rundy(werdykt_k: str, werdykt_p: str) -> tuple[str, list[str]]:
    """(werdykt rundy, dozwolone pytania): MIERZALNA, gdy choć jedno pytanie ma TAK; WSTRZYMANA, gdy
    żadne nie ma TAK, a któreś jest WSTRZYMANE; inaczej NIEMIERZALNA."""
    dozwolone = [
        n for n, w in (("K bezwzględne", werdykt_k), ("P porównawcze", werdykt_p)) if w == "TAK"
    ]
    if dozwolone:
        return "MIERZALNA", dozwolone
    return ("WSTRZYMANA" if "WSTRZYMANE" in (werdykt_k, werdykt_p) else "NIEMIERZALNA"), []


# --- przewidywania (nie kryteria) -----------------------------------------------------------------

PRZEW_ODRZUCANE_MIN = (
    0.70  # W1: okno60_t5 i ewma94_t5 odrzucane przez test zbiorczy w ≥ 70 % paneli
)


def przewidywania(wyn: dict, oceny: dict) -> list[dict]:
    """Przewidywania z pre-rejestracji dla komórki głównej (NIE kryteria); `ok` = trafione.

    W1: test zbiorczy odrzuca okno60_t5 i ewma94_t5 w ≥ 70 % paneli (LV1: 78–98 %); W2: FZ0 ustawia
    prognozy od najgorszej do najlepszej: okno60_t5, ewma94_t5, garch_tnu (średnia strata względem
    wyroczni); W3 i W4: reguła P daje NIE (P-a i P-b nie są spełnione).
    """
    wiersze = []
    for ip, p in enumerate(POZIOMY):
        o60, ew = (_odsetek(wyn, 0, ip, f, "zb_bonf")[0] for f in ("okno60_t5", "ewma94_t5"))
        wiersze.append(
            {
                "kod": "W1",
                "p": p,
                "wartosc": min(o60, ew),
                "ok": min(o60, ew) >= PRZEW_ODRZUCANE_MIN,
                "tekst": f"test zbiorczy odrzuca okno60_t5 i ewma94_t5 w ≥ {100 * PRZEW_ODRZUCANE_MIN:.0f} % paneli",
            }
        )
        regret = [
            float(np.nanmean(wyn["dm"][:, 0, ip, POR_IDX[f"wyr_fz0_{f}"], 1]))
            for f in ("okno60_t5", "ewma94_t5", "garch_tnu")
        ]
        wiersze.append(
            {
                "kod": "W2",
                "p": p,
                "wartosc": regret[0] - regret[2],
                "ok": regret[0] > regret[1] > regret[2],
                "tekst": "średnia strata FZ0 ponad wyrocznię: okno60_t5 > ewma94_t5 > garch_tnu",
            }
        )
        wiersze.append(
            {
                "kod": "W3",
                "p": p,
                "wartosc": float("nan"),
                "ok": oceny[p]["P"]["kryteria"][0]["ok"] is False,
                "tekst": "P-a niespełnione (MDE zaniżenia σ testu DM-FZ0 > 0,10)",
            }
        )
        wiersze.append(
            {
                "kod": "W4",
                "p": p,
                "wartosc": oceny[p]["P"]["kryteria"][1]["wartosc"],
                "ok": oceny[p]["P"]["kryteria"][1]["ok"] is False,
                "tekst": "P-b niespełnione (moc DM-FZ0 pary ewma94_t5 → garch_tnu < 80 %)",
            }
        )
    return wiersze


# --- wydruk (neutralny reporter, R14) -------------------------------------------------------------

WERDYKT_TXT = {"TAK": "MIERZALNE", "NIE": "NIEMIERZALNE", "WSTRZYMANE": "WSTRZYMANE"}
OPIS_KOMORKI = ("C1 główna", "C2 populacja F2-1b")
OPIS_PROGNOZ = {
    "wyr_t5": "σ wyroczni (z generatora), ogon t5 — prawdziwa prognoza",
    **{n: f"σ wyroczni × {1 - x:.2f}, ogon t5" for n, x in ZANIZENIA.items()},
    "okno60_t5": "σ z okna 60 dni, ogon t5",
    "ewma94_t5": "σ z EWMA λ = 0,94, ogon t5",
    "garch_t5": "σ z GARCH(1,1)-t (refit co 30 dni), ogon t5",
    "garch_tnu": "σ z GARCH-t, ogon t_ν̂ (ν̂ z dopasowania) — poprawny model, estymowany",
    "garch_tnu_zan10": "garch_tnu × 0.90",
    "garch_tnu_zan20": "garch_tnu × 0.80",
    "har_t5": "σ z HAR-RV (modele.zmiennosc), ogon t5",
    "okno60_ep": "okno 60 dni, ogon empiryczny zbiorczy (reszty wszystkich monet)",
    "ewma94_ep": "EWMA 0,94, ogon empiryczny zbiorczy",
    "garch_ep": "GARCH-t, ogon empiryczny zbiorczy",
    "okno60_ec": "okno 60 dni, ogon empiryczny per moneta",
    "ewma94_ec": "EWMA 0,94, ogon empiryczny per moneta",
    "garch_ec": "GARCH-t, ogon empiryczny per moneta",
}


def _pc(v: float) -> str:
    return f"{100 * v:5.1f}"


def _wart_txt(k: dict) -> str:
    w, j = k["wartosc"], k["jednostka"]
    if j == "pct":
        return f"{100 * w:.1f} %"
    if j == "mde":
        return f"{w:.3f}" if np.isfinite(w) else f">{X_GRID[-1]:.2f}"
    return f"{w:.3f}" if j == "num3" else f"{w:.2f}"


def _wypisz_ocene(ocena: dict, tytul: str) -> None:
    print(f"  {tytul}")
    for k in (*ocena["kontrole"], *ocena["kryteria"]):
        uwaga = "  [w granicach 2 SE od progu]" if k["granica"] else ""
        if k["bramka"] != "obie":
            uwaga += f"  [bramkuje tylko wniosek {k['bramka']}]"
        print(
            f"    {k['kod']:4s} {k['grupa']:19s} {k['opis']}: {_wart_txt(k)} — {k['wymaganie']}: "
            f"{'TAK' if k['ok'] else 'NIE'}{uwaga}"
        )
    print(f"    WYNIK reguły: {WERDYKT_TXT[ocena['werdykt']]}")


def _wypisz_kryteria(wyn: dict, konfig: dict) -> dict:
    oceny: dict = {}
    for ic, (k, n) in enumerate(konfig["komorki"]):
        tytul = "KRYTERIA z pre-rejestracji" if ic == 0 else "OPIS (nie kryteria): ta sama reguła"
        print(f"\n{tytul} — komórka {OPIS_KOMORKI[ic]}: K = {k} monet, n = {n} dni, ρ = {RHO}")
        for ip, p in enumerate(POZIOMY):
            ok_k, ok_p = ocen_k(liczby_k(wyn, ic, ip)), ocen_p(liczby_p(wyn, ic, ip))
            print(f"\n p = {p:.0%}")
            _wypisz_ocene(
                ok_k, "Reguła K — pytanie bezwzględne (test zbiorczy LV1, prognoza estymowana)"
            )
            _wypisz_ocene(ok_p, "Reguła P — pytanie porównawcze (test DM na stracie FZ0)")
            runda, dozwolone = regula_rundy(ok_k["werdykt"], ok_p["werdykt"])
            print(
                f"  REGUŁA PIERWSZEJ RUNDY VaR/ES NA DANYCH, p = {p:.0%}: {runda}"
                + (f" — dozwolone pytania: {'; '.join(dozwolone)}" if dozwolone else "")
            )
            if ic == 0:
                oceny[p] = {"K": ok_k, "P": ok_p}
            for nazwa in ("wyr_t5", "garch_tnu"):
                vr, se_vr = _odsetek(wyn, ic, ip, nazwa, "vr")
                print(f"  VR dziennej sumy trafień, {nazwa}: {vr:.2f} ± {se_vr:.2f}")
    return oceny


def _wypisz_przewidywania(wyn: dict, oceny: dict) -> None:
    print("\nPRZEWIDYWANIA z pre-rejestracji (NIE kryteria), komórka główna:")
    for w in przewidywania(wyn, oceny):
        liczba = f" ({w['wartosc']:.3f})" if np.isfinite(w["wartosc"]) else ""
        print(f"  {w['kod']} p = {w['p']:.0%}: {w['tekst']}{liczba}: {'TAK' if w['ok'] else 'NIE'}")


def _wiersz_abs(wyn: dict, ic: int, ip: int, nazwa: str) -> str:
    v = {st: _odsetek(wyn, ic, ip, nazwa, st) for st in STAT if st != "niezdef"}
    return (
        f"{nazwa:16s} {100 * v['hit'][0]:6.2f} {v['u_sr'][0]:6.3f} |"
        f" {_pc(v['zb_a'][0])} {_pc(v['zb_b'][0])} {_pc(v['zb_c'][0])} |"
        f" {_pc(v['zb_bonf'][0])} ± {100 * v['zb_bonf'][1]:4.2f} | {_pc(v['zb_a_prawa'][0])} {v['vr'][0]:5.2f}"
    )


def _wypisz_abs(wyn: dict, konfig: dict) -> None:
    print("\nOPIS (nie kryteria): test zbiorczy LV1 na każdej prognozie, odsetek odrzuceń [%].")
    print(
        "A, B, C = składniki na poziomie α/3 (zbiorczy = A lub B lub C); hit = średni odsetek trafień [%];"
    )
    print(
        "U = średnia z r/(p·ES) po trafieniach, 1 przy prawdziwym ES; A>0 = A odrzuca „za dużo trafień”;"
    )
    print("VR = Var(S_t)/(K p (1 − p)); ± = SE po panelach. Opisy prognoz:")
    for nazwa in PROGNOZY:
        print(f"  {nazwa:16s} = {OPIS_PROGNOZ[nazwa]}")
    for ic, (k, n) in enumerate(konfig["komorki"]):
        for ip, p in enumerate(POZIOMY):
            print(f"\n=== {OPIS_KOMORKI[ic]}: K = {k}, n = {n}, p = {p:.0%} ===")
            print(
                f"{'prognoza':16s} {'hit':>6s} {'U':>6s} |   A     B     C  | zbiorczy ± SE |  A>0    VR"
            )
            for nazwa in PROGNOZY:
                if np.isfinite(wyn["abs"][:, ic, ip, PROG_IDX[nazwa], IDX["hit"]]).all():
                    print(_wiersz_abs(wyn, ic, ip, nazwa))
            nz = wyn["abs"][:, ic, ip, :, IDX["niezdef"]]
            print(
                f"  niezdefiniowane składniki testu (średnio na panel i prognozę): {np.nanmean(nz):.4f}"
            )


def _wiersz_dm(wyn: dict, ic: int, ip: int, por: dict) -> str | None:
    t, sr, se = (wyn["dm"][:, ic, ip, POR_IDX[por["kod"]], j] for j in range(3))
    if np.isnan(sr).all():
        return None
    prawa, lewa = (_dm_odsetek(wyn, ic, ip, por["kod"], tryb)[0] for tryb in ("prawa", "lewa"))
    return (
        f"{por['kod']:44s} {_pc(prawa)} {_pc(lewa)} | {np.nanmean(sr):+9.5f} {np.nanstd(sr, ddof=1):8.5f} |"
        f" {np.nanmean(se):8.5f} {np.nanmean(t):+6.2f}"
    )


def _wypisz_dm(wyn: dict, konfig: dict) -> None:
    print("\nOPIS (nie kryteria): test Diebolda–Mariano na różnicy dziennych średnich strat A − B.")
    print(
        "B lepsza = odsetek paneli z t > 1,96; A lepsza = t < −1,96; d̄ = średnia różnica po panelach,"
    )
    print("SD(d̄) = jej rozrzut po panelach, se = średni błąd HAC (Newey–West); t = średnie t.")
    print(
        "Role: zero = para o równych oczekiwanych stratach (rozmiar), moc = σ zaniżone wobec wyroczni,"
    )
    print(
        "wyr = prognoza estymowana wobec wyroczni (d̄ = „koszt estymacji”), real = pary realistyczne."
    )
    for ic, (k, n) in enumerate(konfig["komorki"]):
        for ip, p in enumerate(POZIOMY):
            print(f"\n=== {OPIS_KOMORKI[ic]}: K = {k}, n = {n}, p = {p:.0%} ===")
            print(f"{'porównanie A − B':44s} B>A%  A>B% |       d̄    SD(d̄) |     se     t")
            for por in POROWNANIA:
                tekst = _wiersz_dm(wyn, ic, ip, por)
                if tekst is not None:
                    print(tekst)


def _wypisz_k6(wyn: dict, konfig: dict) -> None:
    print(
        "\nOPIS (K6): rozmiar testu DM po wyśrodkowaniu na parach realistycznych [%] — |t| > 1,96, gdzie"
    )
    print(
        "t = (d̄ − średnia d̄ po panelach)/se; ≈ 5 % = błąd HAC (opóźnienie Newey–West) jest wiarygodny."
    )
    for ic, (k, n) in enumerate(konfig["komorki"]):
        for ip, p in enumerate(POZIOMY):
            wiersze = []
            for x, y in PARY_REALNE:
                v = [_dm_odsetek(wyn, ic, ip, f"real_{s}_{x}__{y}", "centr")[0] for s in STRATY]
                if np.isfinite(v).all():
                    wiersze.append(
                        f"  {x} → {y}: " + ", ".join(f"{s} {_pc(m)}" for s, m in zip(STRATY, v))
                    )
            print(f"{OPIS_KOMORKI[ic]}, p = {p:.0%}:")
            print("\n".join(wiersze))


def _wypisz_mde(wyn: dict, konfig: dict) -> None:
    print("\nMOC NA SIATCE ZANIŻENIA σ i MDE (najmniejsze x z mocą ≥ 80 %; interpolacja liniowa;")
    print(
        f"'>{X_GRID[-1]:.2f}' = nieosiągalne na siatce). Siatka x: {', '.join(f'{x:.2f}' for x in X_GRID)}"
    )
    print(
        "(x = 0: rozmiar testu zbiorczego na wyroczni; dla DM — średni rozmiar na parach zerowych)."
    )
    for ic, (k, n) in enumerate(konfig["komorki"]):
        for ip, p in enumerate(POZIOMY):
            print(f"\n{OPIS_KOMORKI[ic]}, p = {p:.0%}:")
            krzywe = [("test zbiorczy (wyrocznia × (1 − x))", *krzywa_abs(wyn, ic, ip))]
            krzywe += [
                (f"DM-{s.upper()}: wyrocznia × (1 − x) wobec wyroczni", *krzywa_dm(wyn, ic, ip, s))
                for s in STRATY
            ]
            for nazwa, krz, _ in krzywe:
                m = mde(np.asarray(X_GRID), krz, MOC_MIN)
                txt = f"{m:.3f}" if np.isfinite(m) else f">{X_GRID[-1]:.2f}"
                print(f"  {nazwa:50s} " + " ".join(_pc(v) for v in krz) + f"   MDE {txt}")
            for nazwa, x in (
                ("garch_tnu", 0.0),
                ("garch_tnu_zan10", 0.10),
                ("garch_tnu_zan20", 0.20),
            ):
                m, s = _odsetek(wyn, ic, ip, nazwa, "zb_bonf")
                print(
                    f"  test zbiorczy, GARCH-t estymowany, x = {x:.2f} ({nazwa}): {100 * m:.1f} % ± {100 * s:.2f}"
                )


def _wypisz_diag(wyn: dict) -> None:
    d = wyn["diag"]
    k7 = liczby_k7(wyn)
    print("\nDIAGNOSTYKA ESTYMATORA GARCH-t (K7), walk-forward, wszystkie monety i bloki:")
    print(f"  dopasowań na panel: {d[:, 0].mean():.0f}; średnia ν̂ {k7['nu'][0]:.3f} (prawda 5),")
    print(
        f"  średnia α̂ + β̂ {k7['pers'][0]:.4f} (prawda 0,98), bez zbieżności {100 * k7['nie_zbiezne'][0]:.2f} %,"
    )
    print(f"  przy granicy zakresu {100 * k7['brzeg'][0]:.2f} %.")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="LV2 — VaR/ES: laboratorium dla prognoz estymowanych")
    ap.add_argument("--smoke", action="store_true", help="małe panele; tylko test działania kodu")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    ap.add_argument(
        "--panele", type=int, default=None, help="PILOTAŻ: inna liczba paneli niż w rejestrze"
    )
    ap.add_argument("--ziarno", type=int, default=SEED, help="PILOTAŻ: inne ziarno niż w rejestrze")
    args = ap.parse_args(argv)
    konfig = dict(KONFIG_SMOKE if args.smoke else KONFIG)
    if args.panele is not None:
        konfig["panele"] = args.panele
    pilot = args.smoke or args.panele is not None or args.ziarno != SEED
    t0 = time.time()

    print("LV2 — VaR/ES: prognozy estymowane (zadanie 016)")
    if pilot:
        print(
            "PILOTAŻ — NIE JEST PRZEBIEGIEM REJESTROWYM: inne ziarno lub liczba paneli niż w pre-rejestracji;"
        )
        print("liczby z tego przebiegu służą wyłącznie do sprawdzenia kodu i kalibracji progów K7.")
    print(
        f"Generator: GARCH(1,1)-t, ν = {NU:.0f}, K = {konfig['k_panel']} monet, ρ = {RHO}, ziarno {args.ziarno}.\n"
        f"Panel {konfig['n_dni']} dni: historia {konfig['start']} dni, potem okres oceny; komórki (K, n) = "
        f"{konfig['komorki']} (pierwsze K monet, pierwsze n dni okresu oceny).\n"
        f"{konfig['panele']} paneli, bootstrap po dniach {konfig['boot']} replikacji, poziom testów {100 * ALFA:.0f} %,"
        f" test DM dwustronny z = {Z_KRYT}."
    )
    wyn = uruchom(konfig, args.workers, args.ziarno)
    _wypisz_diag(wyn)
    oceny = _wypisz_kryteria(wyn, konfig)
    _wypisz_przewidywania(wyn, oceny)
    _wypisz_mde(wyn, konfig)
    _wypisz_abs(wyn, konfig)
    _wypisz_dm(wyn, konfig)
    _wypisz_k6(wyn, konfig)
    if pilot:
        print("\nPILOTAŻ: powyższe wyniki reguł nie są werdyktem.")
    sek = time.time() - t0
    print(
        f"Czas przebiegu {sek:.0f} s ({args.workers} procesów, {sek * args.workers / konfig['panele']:.1f}"
        f" s na panel na rdzeń)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
