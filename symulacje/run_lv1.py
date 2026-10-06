"""
LV1 — laboratorium VaR/ES: czy testy wsteczne odróżniają dobrą prognozę ryzyka od złej przy NASZEJ
długości historii (n = 600–2 100 dni, 20 monet, ρ = 0,5 i 0,8). Zadanie 009, PRD FR-32 / cel G2.
Pre-rejestracja: `runs/2026-10-05_lv1-moc-var-es/README.md`. Neutralny reporter (R14).

    python -m symulacje.run_lv1 > runs/2026-10-05_lv1-moc-var-es/raw_output.txt
    python -m symulacje.run_lv1 --smoke      # małe B, n: TYLKO sprawdzenie, że kod działa

Wynik nie zależy od liczby procesów (`--workers`): ziarna rozdziela SeedSequence.spawn per zadanie.
Na stdout (raw_output.txt) idą tylko liczby odtwarzalne; czas przebiegu idzie na stderr.
Panele generujemy RAZ na ρ na największe n; mniejsze n to początkowy fragment tego samego panelu.
Progi i reguła zmienione po przeglądzie, przed pełnym przebiegiem (README rundy, „Zmiany po
przeglądzie”).
"""

from __future__ import annotations

import argparse
import math
import multiprocessing as mp
import os
import sys
import time

import numpy as np

from miara.var_es import (
    as_z2,
    as_z2_h0_polozenie_skala,
    as_z2_pwartosc,
    christoffersen_cc,
    czy_polozenie_skala,
    kupiec_uc,
)
from symulacje.garch_panel import generuj_panel
from symulacje.moc_var_es import (
    IDX,
    NU,
    OPIS_PROGNOZ,
    PROGNOZY,
    STAT,
    WARM,
    ZANIZENIA,
    mde,
    odrzuca_zbiorczo,
    prognoza_q_es,
    rodzina_prognozy,
    sigmy_prognoz,
    testy_zbiorcze,
)

SEED = 20_261_009
K = 20
POZIOMY = (0.01, 0.05)
RHOS = (0.5, 0.8)
ALFA = 0.05  # odrzucamy, gdy p-wartość < ALFA (dla testów jednostronnych też 5 %)

KONFIG = {
    "ns": (600, 1000, 1600, 2100),
    "panele": 5000,  # na ρ; SE odsetka ≤ 0,71 pp dla dowolnej mocy (0,57 pp przy mocy 80 %)
    "boot": 999,
    "h0": 20_000,
    "glowne_n": 1600,
}
KONFIG_SMOKE = {"ns": (150, 250), "panele": 6, "boot": 99, "h0": 400, "glowne_n": 250}
CHUNK_H0 = 1000
RHO_GLOWNE = 0.8

# Progi pre-rejestracji (README rundy, „Kryteria”). Zapisane przed pełnym przebiegiem.
ROZMIAR = (0.025, 0.075)  # (i) i K1: rozmiar testu na prawdziwej prognozie
MOC_MIN = 0.80  # (ii) i (iii): wymagana moc
MOC_KONTROLA = 0.95  # K2: moc wobec σ zaniżonego o 30 %
NAIWNY_MIN = 0.10  # K3: naiwny Kupiec na 20·n trafieniach ma rozmiar powyżej tego (ρ = 0,8)
X_MAX = {0.01: 0.10, 0.05: 0.10}  # (iii): największe dopuszczalne MDE zaniżenia σ, per p
II_A_POZIOMY = (0.01,)  # ii-a jest kryterium tylko tu; przy 5 % „normalna” jest ostrożna (opis)
X_MAX_PIERWOTNE = {0.01: 0.10, 0.05: 0.05}  # reguła sprzed przeglądu — drukowana tylko jako opis
II_A_PIERWOTNE = (0.01, 0.05)
GRID = ("prawdziwa", *ZANIZENIA)  # prognozy na osi x zaniżenia σ; pierwsza = x 0 (rozmiar)
X_GRID = (0.0, *ZANIZENIA.values())
TESTY_MONETA = (("kupiec", "Kupiec"), ("cc", "Christoff. cc"), ("z2_rej", "Z2"))
TESTY_ZBIORCZE = (
    ("zb_a", "A pokrycie"),
    ("zb_b", "B niezależn."),
    ("zb_c", "C ogon"),
    ("zb_bonf", "zbiorczy"),
)

_H0: dict = {}


def _init(h0: dict) -> None:
    _H0.update(h0)


def _ziarno_int(ss: np.random.SeedSequence) -> int:
    return int(ss.generate_state(1, dtype=np.uint64)[0])


def _chunk_h0(arg):
    n, p, rodzina, reps, ss = arg
    return as_z2_h0_polozenie_skala(n, p, rodzina, NU if rodzina == "t" else None, reps, seed=ss)


def statystyki_komorki(r, q, es, p: float, h0: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """Wektor STAT dla jednej komórki (p, n, prognoza): testy per moneta, zbiorcze i naiwny."""
    k = r.shape[1]
    hit = r < q
    kup = np.array([kupiec_uc(hit[:, j], p)["p_wartosc"] for j in range(k)])
    cc = np.array([christoffersen_cc(hit[:, j], p)["p_wartosc"] for j in range(k)])
    z2 = np.array([as_z2(r[:, j], q[:, j], es[:, j], p) for j in range(k)])
    z2p = np.array([as_z2_pwartosc(z, h0) for z in z2])
    zb = testy_zbiorcze(r, q, es, p, idx)
    naiwny = kupiec_uc(hit.ravel(), p)["p_wartosc"]
    pz = np.array([zb["p_a"], zb["p_b"], zb["p_c"]])
    s = hit.sum(axis=1)
    wynik = np.empty(len(STAT))
    wynik[IDX["hit"]] = hit.mean()
    wynik[IDX["z2"]] = z2.mean()
    wynik[IDX["kupiec"]] = (kup < ALFA).mean()
    wynik[IDX["cc"]] = (cc < ALFA).mean()  # NaN w cc = brak odrzucenia (porównanie fałszywe)
    wynik[IDX["z2_rej"]] = (z2p < ALFA).mean()
    wynik[IDX["zb_a"]], wynik[IDX["zb_b"]], wynik[IDX["zb_c"]] = (pz < ALFA).astype(float)
    wynik[IDX["zb_bonf"]] = float(odrzuca_zbiorczo(pz, ALFA))
    wynik[IDX["zb_a_prawa"]] = float(zb["p_a"] < ALFA / 3 and zb["t_a"] > 0)
    wynik[IDX["zb_ac"]] = float(odrzuca_zbiorczo(pz[[0, 2]], ALFA))
    wynik[IDX["vr"]] = s.var(ddof=1) / (k * p * (1 - p))
    wynik[IDX["naiwny"]] = float(naiwny < ALFA)
    wynik[IDX["niezdef"]] = float(np.isnan(pz).sum())
    return wynik


def przetworz_panel(arg) -> np.ndarray:
    """Jeden panel: wynik (poziomy × n × prognozy × STAT). Deterministyczny dla danego `ss`."""
    rho, ns, boot, ss = arg
    ss_gen, ss_boot = ss.spawn(2)
    n_max = max(ns)
    panel = generuj_panel(n_max + WARM, K, seed=_ziarno_int(ss_gen), nu=NU, rho=rho)
    r = panel["r"].to_numpy()[WARM:]
    sigmy = sigmy_prognoz(panel)
    gen = np.random.default_rng(ss_boot)
    idx = {n: gen.integers(0, n, size=(boot, n)) for n in ns}  # wspólne dla komórek tego n
    wyn = np.full((len(POZIOMY), len(ns), len(PROGNOZY), len(STAT)), np.nan)
    for ip, p in enumerate(POZIOMY):
        for jf, nazwa in enumerate(PROGNOZY):
            q, es = prognoza_q_es(sigmy[nazwa], nazwa, p)
            rodzina = rodzina_prognozy(nazwa)
            if nazwa != "es_za_niski" and not czy_polozenie_skala(
                q[:, 0], es[:, 0], p, rodzina, NU if rodzina == "t" else None
            ):  # skrót rozkładu zerowego Z2 wymaga prognozy σ_t (a, b); es_za_niski jest poza nią
                raise ValueError(f"prognoza {nazwa} nie jest typu położenie–skala")
            for jn, n in enumerate(ns):
                wyn[ip, jn, jf] = statystyki_komorki(
                    r[:n], q[:n], es[:n], p, _H0[(n, p, rodzina)], idx[n]
                )
    return wyn


def zadania_h0(ns, reps: int, ss_h0) -> tuple[list, list]:
    """Zadania symulacji rozkładów zerowych Z2: jeden rozkład na (n, p, rodzina), w partiach."""
    kombinacje = [(n, p, rod) for n in ns for p in POZIOMY for rod in ("t", "normal")]
    zadania, klucze = [], []
    for (n, p, rodzina), ss_k in zip(kombinacje, ss_h0.spawn(len(kombinacje)), strict=True):
        n_chunk = math.ceil(reps / CHUNK_H0)
        for j, ss in enumerate(ss_k.spawn(n_chunk)):
            zadania.append((n, p, rodzina, min(CHUNK_H0, reps - j * CHUNK_H0), ss))
            klucze.append((n, p, rodzina))
    return zadania, klucze


def uruchom(konfig: dict, workers: int) -> tuple[dict, dict]:
    """Cały przebieg: rozkłady zerowe Z2, potem panele.

    Zwraca ({rho: tablica B × p × n × prognoza × STAT}, rozkłady zerowe Z2 po (n, p, rodzina)).
    Procesy startują przez forkserver, więc skrypt wołający musi mieć `if __name__ == "__main__"`.
    """
    ns = konfig["ns"]
    ss_h0, ss_panele = np.random.SeedSequence(SEED).spawn(2)
    zad_h0, klucze = zadania_h0(ns, konfig["h0"], ss_h0)
    panele_rho = ss_panele.spawn(len(RHOS))
    zad_panele = [
        (rho, ns, konfig["boot"], ss)
        for rho, ss_rho in zip(RHOS, panele_rho, strict=True)
        for ss in ss_rho.spawn(konfig["panele"])
    ]
    kontekst = mp.get_context("forkserver")  # fork w procesie z wątkami grozi zakleszczeniem
    with kontekst.Pool(workers) as pool:
        czesci = pool.map(_chunk_h0, zad_h0, chunksize=1)
    h0: dict = {}
    for k, z in zip(klucze, czesci, strict=True):
        h0.setdefault(k, []).append(z)
    h0 = {k: np.concatenate(v) for k, v in h0.items()}
    with kontekst.Pool(workers, initializer=_init, initargs=(h0,)) as pool:
        wyniki = pool.map(przetworz_panel, zad_panele, chunksize=1)
    out = {}
    for rho in RHOS:
        out[rho] = np.stack([w for w, z in zip(wyniki, zad_panele, strict=True) if z[0] == rho])
    return out, h0


# --- reguła MIERZALNA / NIEMIERZALNA --------------------------------------------------------------


def _blisko(wartosc: float, se: float, *progi: float) -> bool:
    """Wynik w odległości < 2 SE od któregoś progu: werdykt może zależeć od losowości przebiegu."""
    return any(abs(wartosc - prog) < 2 * se for prog in progi)


def _wiersz(kod, grupa, opis, wartosc, wymaganie, ok, granica=False):
    return {
        "kod": kod,
        "grupa": grupa,
        "opis": opis,
        "wartosc": wartosc,
        "wymaganie": wymaganie,
        "ok": bool(ok),
        "granica": bool(granica),
    }


def ocen(
    liczby: dict, p: float, z_k3: bool = True, x_max: dict = X_MAX, ii_a_poziomy=II_A_POZIOMY
) -> dict:
    """Reguła z pre-rejestracji dla jednej komórki (ρ, n) i poziomu p; wejście = liczby z symulacji.

    `liczby`: rozmiar, moc_normalna, moc_stala, kontrola30, naiwny — pary (wartość, SE) —
    oraz krzywa i krzywa_se = moc testu zbiorczego na siatce X_GRID (x = 0 to rozmiar) i jej SE.
    Werdykt: WSTRZYMANE, gdy któraś kontrola (K1–K3) zawodzi; inaczej TAK wtedy i tylko wtedy, gdy
    spełnione są kryteria (ii-a tylko przy p z `ii_a_poziomy`, ii-b, iii); inaczej NIE.
    Wiersze „opis” są drukowane, ale nie wchodzą do werdyktu. `z_k3=False` (mapa przy ρ ≠ 0,8):
    K3 jest opisem, bo przy słabszej korelacji naiwny test nie musi być mocno zawyżony.
    """
    lo, hi = ROZMIAR
    (roz, se_roz), (kon, se_kon), (nai, se_nai) = (
        liczby["rozmiar"],
        liczby["kontrola30"],
        liczby["naiwny"],
    )
    (mn, se_mn), (ms, se_ms) = liczby["moc_normalna"], liczby["moc_stala"]
    pr_moc = f"odsetek ≥ {100 * MOC_MIN:.0f} %"
    kontrole = [
        _wiersz(
            "K1",
            "KONTROLA NEGATYWNA",
            "rozmiar testu zbiorczego, prawdziwa prognoza",
            roz,
            f"odsetek ∈ [{100 * lo:.1f}; {100 * hi:.1f}] %",
            lo <= roz <= hi,
            _blisko(roz, se_roz, lo, hi),
        ),
        _wiersz(
            "K2",
            "KONTROLA POZYTYWNA",
            "moc testu zbiorczego wobec σ zaniżonego o 30 %",
            kon,
            f"odsetek ≥ {100 * MOC_KONTROLA:.0f} %",
            kon >= MOC_KONTROLA,
            _blisko(kon, se_kon, MOC_KONTROLA),
        ),
    ]
    k3 = _wiersz(
        "K3",
        "KONTROLA LABORATORIUM",
        "rozmiar naiwnego Kupca (20·n trafień jak niezależne)",
        nai,
        f"odsetek > {100 * NAIWNY_MIN:.0f} %",
        nai > NAIWNY_MIN,
        _blisko(nai, se_nai, NAIWNY_MIN),
    )
    opis = []
    if z_k3:
        kontrole.append(k3)
    else:
        k3["grupa"] = "OPIS"
        opis.append(k3)
    m = mde(np.asarray(X_GRID), np.asarray(liczby["krzywa"], dtype=float), MOC_MIN)
    jx = X_GRID.index(x_max[p])  # x* leży na siatce, więc (iii) ⇔ moc przy x* ≥ MOC_MIN
    ii_a = _wiersz(
        "ii-a",
        "MIERZALNOŚĆ",
        "moc testu zbiorczego wobec prognozy normalnej",
        mn,
        pr_moc,
        mn >= MOC_MIN,
        _blisko(mn, se_mn, MOC_MIN),
    )
    kryteria = [ii_a] if p in ii_a_poziomy else []
    if p not in ii_a_poziomy:
        ii_a["grupa"] = "OPIS"
        opis.append(ii_a)
    kryteria += [
        _wiersz(
            "ii-b",
            "MIERZALNOŚĆ",
            "moc testu zbiorczego wobec prognozy stałej",
            ms,
            pr_moc,
            ms >= MOC_MIN,
            _blisko(ms, se_ms, MOC_MIN),
        ),
        _wiersz(
            "iii",
            "MIERZALNOŚĆ",
            "MDE zaniżenia σ (moc 80 %, siatka X_GRID)",
            m,
            f"MDE ≤ {x_max[p]:.2f}",
            bool(np.isfinite(m) and m <= x_max[p]),
            _blisko(liczby["krzywa"][jx], liczby["krzywa_se"][jx], MOC_MIN),
        ),
    ]
    if all(k["ok"] for k in kontrole):
        werdykt = "TAK" if all(k["ok"] for k in kryteria) else "NIE"
    else:
        werdykt = "WSTRZYMANE"
    return {"kontrole": kontrole, "kryteria": kryteria, "opis": opis, "werdykt": werdykt}


def _odsetek(w: np.ndarray, ip: int, jn: int, nazwa: str, stat: str) -> tuple[float, float]:
    """(średnia, SE) statystyki STAT dla prognozy `nazwa` w komórce (p, n) po B panelach."""
    v = w[:, ip, jn, PROGNOZY.index(nazwa), IDX[stat]]
    return float(v.mean()), float(v.std(ddof=1) / math.sqrt(len(v)))


def krzywa_mocy(w: np.ndarray, ip: int, jn: int, stat: str, se: bool = False) -> np.ndarray:
    """Moc statystyki `stat` na siatce X_GRID (x = 0: rozmiar prawdziwej prognozy); se: jej SE."""
    return np.array([_odsetek(w, ip, jn, f, stat)[int(se)] for f in GRID])


def liczby_komorki(w: np.ndarray, ip: int, jn: int) -> dict:
    """Wejście reguły `ocen` z tablicy wyników jednego ρ."""
    return {
        "rozmiar": _odsetek(w, ip, jn, "prawdziwa", "zb_bonf"),
        "moc_normalna": _odsetek(w, ip, jn, "normalna", "zb_bonf"),
        "moc_stala": _odsetek(w, ip, jn, "stala", "zb_bonf"),
        "kontrola30": _odsetek(w, ip, jn, "zanizenie_30", "zb_bonf"),
        "naiwny": _odsetek(w, ip, jn, "prawdziwa", "naiwny"),
        "krzywa": krzywa_mocy(w, ip, jn, "zb_bonf"),
        "krzywa_se": krzywa_mocy(w, ip, jn, "zb_bonf", se=True),
    }


P1C_Z2_NORMALNA = (0.60, 0.95)  # P1c: przedział mocy Z2 per moneta wobec normalnej (z pilotażu)


def przewidywanie_per_moneta(w: np.ndarray, ip: int, jn: int) -> list[dict]:
    """P1 rozpisane per test: Kupiec i cc < MOC_MIN wobec obu; Z2 < MOC_MIN wobec stałej
    i w przedziale P1C_Z2_NORMALNA wobec normalnej. `sprawdza` = przewidywanie trafione."""
    wiersze = []
    lo, hi = P1C_Z2_NORMALNA
    for stat, nazwa in TESTY_MONETA:
        mn = _odsetek(w, ip, jn, "normalna", stat)[0]
        ms = _odsetek(w, ip, jn, "stala", stat)[0]
        if stat == "z2_rej":
            ok, tekst = (
                ms < MOC_MIN and lo <= mn <= hi,
                f"stała < 80 %, normalna ∈ [{lo:.0%}; {hi:.0%}]",
            )
        else:
            ok, tekst = max(mn, ms) < MOC_MIN, "normalna i stała < 80 %"
        wiersze.append(
            {"test": nazwa, "normalna": mn, "stala": ms, "przewidywanie": tekst, "sprawdza": ok}
        )
    return wiersze


# --- wydruk (neutralny reporter, R14) -------------------------------------------------------------

WERDYKT_TXT = {"TAK": "MIERZALNA", "NIE": "NIEMIERZALNA", "WSTRZYMANE": "WSTRZYMANY"}


def _pc(v: float) -> str:
    return f"{100 * v:5.1f}"


def _mde_txt(m: float) -> str:
    return f"{m:.3f}" if np.isfinite(m) else f">{X_GRID[-1]:.2f}"


def _wypisz_ocene(ocena: dict, p: float) -> None:
    for k in (*ocena["kontrole"], *ocena["kryteria"], *ocena["opis"]):
        w = k["wartosc"]
        wart = _mde_txt(w) if k["kod"] == "iii" else f"{100 * w:.1f} %"
        uwaga = "  [w granicach 2 SE od progu]" if k["granica"] else ""
        if k in ocena["opis"]:
            uwaga += "  (opis, poza regułą)"
        print(
            f"  {k['kod']:4s} {k['grupa']:21s} {k['opis']}: {wart} — {k['wymaganie']}: "
            f"{'TAK' if k['ok'] else 'NIE'}{uwaga}"
        )
    print(f"  WYNIK REGUŁY dla p = {p:.0%}: {WERDYKT_TXT[ocena['werdykt']]}")


def _wypisz_kryteria(w: np.ndarray, ns, glowne_n: int) -> dict:
    jn = ns.index(glowne_n)
    print(f"\nKRYTERIA z pre-rejestracji — komórka główna: ρ = {RHO_GLOWNE}, n = {glowne_n}")
    wyniki = {}
    for ip, p in enumerate(POZIOMY):
        print(f"\n p = {p:.0%}")
        wyniki[p] = ocen(liczby_komorki(w, ip, jn), p)
        _wypisz_ocene(wyniki[p], p)
        vr, se_vr = _odsetek(w, ip, jn, "prawdziwa", "vr")
        print(
            f"  VR dziennej sumy trafień (prawdziwa prognoza): {vr:.2f} ± {se_vr:.2f} — warunek"
            f" przeniesienia: VR na danych ≤ {vr:.2f}"
        )
    print(
        "\nOPIS (nie werdykt): reguła PIERWOTNA sprzed przeglądu (x* = 0,05 przy 5 %, ii-a przy obu p)"
    )
    for ip, p in enumerate(POZIOMY):
        stara = ocen(liczby_komorki(w, ip, jn), p, True, X_MAX_PIERWOTNE, II_A_PIERWOTNE)
        print(f"  p = {p:.0%}: {WERDYKT_TXT[stara['werdykt']]}")
    print("\nPRZEWIDYWANIE P1 (nie kryterium), testy per moneta wobec normalnej / stałej")
    print(f"(p = 1 %, n = {glowne_n}, ρ = {RHO_GLOWNE}):")
    wiersze = przewidywanie_per_moneta(w, POZIOMY.index(0.01), jn)
    for v in wiersze:
        print(
            f"  {v['test']:14s} normalna {_pc(v['normalna'])} %, stała {_pc(v['stala'])} % — "
            f"przewidywanie: {v['przewidywanie']}: {'TAK' if v['sprawdza'] else 'NIE'}"
        )
    p1 = all(v["sprawdza"] for v in wiersze)
    print(f"  P1 {'sprawdziło się' if p1 else 'NIE sprawdziło się'}")
    return wyniki


def mapa_regul(wyn: dict, ns) -> dict:
    """Wynik reguły w każdej komórce (ρ, p, n); K3 jest kontrolą tylko przy ρ = RHO_GLOWNE."""
    return {
        (rho, p, n): ocen(liczby_komorki(w, ip, jn), p, rho == RHO_GLOWNE)["werdykt"]
        for rho, w in wyn.items()
        for ip, p in enumerate(POZIOMY)
        for jn, n in enumerate(ns)
    }


def _wypisz_mape(wyn: dict, ns) -> None:
    print("\nMAPA (opis do planowania, nie werdykt): wynik reguły w komórkach ρ × p × n;")
    print(f"K3 działa jako kontrola tylko przy ρ = {RHO_GLOWNE}, przy innym ρ jest opisem.")
    print(" rho  | p    | " + " | ".join(f"n = {n:4d}    " for n in ns))
    mapa = mapa_regul(wyn, ns)
    for rho in wyn:
        for p in POZIOMY:
            kom = [WERDYKT_TXT[mapa[(rho, p, n)]] for n in ns]
            print(f" {rho:.1f}  | {p:.0%}   | " + " | ".join(f"{k:12s}" for k in kom))


def _wiersz_opisu(w: np.ndarray, ip: int, jn: int, nazwa: str) -> str:
    v = {st: _odsetek(w, ip, jn, nazwa, st) for st in STAT if st != "niezdef"}
    return (
        f"{nazwa:13s} {100 * v['hit'][0]:6.2f} {v['z2'][0]:+8.3f} |"
        f" {_pc(v['kupiec'][0])} {_pc(v['cc'][0])} {_pc(v['z2_rej'][0])} |"
        f" {_pc(v['zb_a'][0])} {_pc(v['zb_b'][0])} {_pc(v['zb_c'][0])} |"
        f" {_pc(v['zb_bonf'][0])} ± {100 * v['zb_bonf'][1]:4.2f} | {_pc(v['naiwny'][0])} |"
        f" {_pc(v['zb_a_prawa'][0])} {_pc(v['zb_ac'][0])} {v['vr'][0]:5.2f}"
    )


def _wypisz_opis(wyn: dict, ns) -> None:
    print("\nOPIS (nie kryteria): odsetek odrzuceń na poziomie 5 % [%]; zbiorczy = A lub B lub C")
    print(
        "na poziomie α/3. Per moneta = średnia po 20 monetach; naiwny = Kupiec na 20·n trafieniach"
    )
    print(
        "jak na niezależnych; hit = średni odsetek trafień [%]; Z2 = średnie Z2; ± = SE (panele)."
    )
    print("Prognozy okno10/okno60/ewma94: opis (H0 dla nich fałszywa, odrzucenie = moc).")
    print("A>0 = A na α/3 odrzuca po stronie „za dużo trafień”; A|C = zbiorczy bez B (α/2);")
    print("VR = wariancja S_t / (K p (1 − p)).")
    for nazwa in PROGNOZY:
        print(f"  {nazwa:13s} = {OPIS_PROGNOZ[nazwa]}")
    naglowek = f"{'prognoza':13s} {'hit':>6s} {'Z2':>8s} | kupiec   cc   Z2 |   A    B    C | "
    for rho, w in wyn.items():
        for ip, p in enumerate(POZIOMY):
            for jn, n in enumerate(ns):
                print(f"\n=== ρ = {rho}, p = {p:.0%}, n = {n} ===")
                print(naglowek + "zbiorczy ± SE | naiwny |   A>0  A|C    VR")
                for nazwa in PROGNOZY:
                    print(_wiersz_opisu(w, ip, jn, nazwa))


def _wypisz_mde(wyn: dict, ns) -> None:
    print("\nMDE zaniżenia σ (najmniejsze x z mocą ≥ 80 %, x ∈ {0; 0,05; 0,10; 0,15; 0,20; 0,30},")
    print("interpolacja liniowa;", end=" ")
    print(f"'>{X_GRID[-1]:.2f}' = nieosiągalne na siatce)")
    testy = (*TESTY_MONETA, *TESTY_ZBIORCZE, ("zb_a_prawa", "A za dużo"), ("zb_ac", "A|C bez B"))
    print(" rho  | p    | n    | " + " | ".join(f"{nazwa:13s}" for _, nazwa in testy))
    for rho, w in wyn.items():
        for ip, p in enumerate(POZIOMY):
            for jn, n in enumerate(ns):
                m = [_mde_txt(mde(np.asarray(X_GRID), krzywa_mocy(w, ip, jn, s))) for s, _ in testy]
                print(f" {rho:.1f}  | {p:.0%}   | {n:4d} | " + " | ".join(f"{x:13s}" for x in m))


def _wypisz_h0(h0: dict) -> None:
    print("\nRozkłady zerowe Z2 (symulacja prognozy dokładnie trafnej):")
    for (n, p, rodzina), z in sorted(h0.items()):
        print(
            f"  n = {n:4d}, p = {p:.0%}, {rodzina:6s}: średnia {z.mean():+.4f}, "
            f"sd {z.std(ddof=1):.4f}, 5. percentyl {np.quantile(z, 0.05):+.4f}"
        )


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(
        description="LV1 — moc testów VaR/ES przy naszej długości historii"
    )
    ap.add_argument("--smoke", action="store_true", help="male B i n; tylko test dzialania kodu")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    args = ap.parse_args(argv)
    konfig = KONFIG_SMOKE if args.smoke else KONFIG
    ns = konfig["ns"]
    t0 = time.time()

    print("LV1 — moc testów wstecznych VaR/ES przy naszej długości historii (zadanie 009)")
    if args.smoke:
        print("TRYB SMOKE: małe B i n, TYLKO sprawdzenie działania kodu — brak werdyktu,")
        print("liczb z tego trybu nie wolno używać do wyboru progów.")
    print(
        f"Generator: GARCH(1,1)-t, ν = {NU:.0f}, K = {K} monet, ρ ∈ {RHOS}, ziarno główne {SEED}."
        f"\nn ∈ {ns} (panel generowany raz na ρ na największe n + {WARM} dni rozgrzewki;"
        f" mniejsze n = początkowy fragment),"
        f"\n{konfig['panele']} paneli na ρ, bootstrap po dniach {konfig['boot']} replikacji,"
        f" rozkład zerowy Z2: {konfig['h0']} symulacji, poziom testów {100 * ALFA:.0f} %."
    )
    wyn, h0 = uruchom(konfig, args.workers)
    _wypisz_h0(h0)
    _wypisz_kryteria(wyn[RHO_GLOWNE], ns, konfig["glowne_n"])
    if args.smoke:
        print("\nTRYB SMOKE: powyższe wyniki reguły nie są werdyktem.")
    _wypisz_mape(wyn, ns)
    _wypisz_opis(wyn, ns)
    _wypisz_mde(wyn, ns)
    sek = time.time() - t0
    n_paneli = len(RHOS) * konfig["panele"]
    print(
        f"Czas przebiegu {sek:.0f} s ({args.workers} procesów, {sek * args.workers / n_paneli:.2f}"
        f" s na panel na rdzeń)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
