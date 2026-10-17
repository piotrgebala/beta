"""
run_kprim.py — karta 026: laboratorium reguły K′ (bootstrap blokowy) na panelach LV2d dla K = 4 (BTC, ETH, SOL, BNB),
cel mocy σ −15 %. Neutralny reporter (R14). Pre-rejestracja: `runs/2026-10-17_026-k-prim-lab/README.md`.

    python -m symulacje.run_kprim wybor --kalibracja runs/2026-10-08_021-lv2d-regimy-wariancji/kalibracja.json
    python -m symulacje.run_kprim potwierdz --dlugosc L --kalibracja ...

Panele, prognozy i kalibracja jak w `run_lv2d` (zamrożone, importowane bez zmian). Zmienia się tylko sposób liczenia
błędu składowych A i C. Wynik nie zależy od liczby procesów (SeedSequence per panel).
"""

from __future__ import annotations

import os

for _zmienna in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_zmienna] = "1"

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

import symulacje.run_lv2c as rc
import symulacje.run_lv2d as rd
from symulacje.garch_panel_regimy import generuj_panel_lv2d
from symulacje.k_prim_blokowy import indeksy_blokowe, odrzuca, pwartosci_blokowe
from symulacje.moc_var_es import NU
from symulacje.prognozy_lv2 import zbuduj_zrodla
from symulacje.run_lv2 import _potomne, _ziarno_int

K, P = rc.K, rc.P
KONFIG = {"n_dni": 2091, "start": 400, "boot": 999}
KONFIG_SMOKE = {"n_dni": 700, "start": 400, "boot": 99}
SEED_WYBOR = 20_262_601
SEED_POTWIERDZENIE = 20_262_602
SEED_SMOKE = 20_269_998
DLUGOSCI_WYBOR = (1, 20, 60, 150)
PROGNOZY = ("wyr_t5", "zan30", "garch_x1.00", "garch_x0.90", "garch_x0.85", "garch_x0.80")
KA, KB15 = "garch_x1.00", "garch_x0.85"
SKLADOWE = ("razem", "A", "B", "C")
PANELE_WYBOR = 2000
PANELE_POTWIERDZENIE = 4000
KOMORKI = rd.NAZWY_KOMOREK
KA_MAX, KB_MIN = 0.10, 0.80


def przetworz_panel_k(arg) -> np.ndarray:
    """Panel → odrzucenia (długości × prognozy × SKLADOWE)."""
    ss, par, konfig, dlugosci = arg
    ss_gen, ss_boot = _potomne(ss, 2)
    panel = generuj_panel_lv2d(konfig["n_dni"], K, seed=_ziarno_int(ss_gen), nu=NU, **par)
    zr = zbuduj_zrodla(panel, start=konfig["start"])
    n = konfig["n_dni"] - konfig["start"]
    gen = np.random.default_rng(ss_boot)
    idx_dni = gen.integers(0, n, size=(konfig["boot"], n))
    idx_bloki = {dl: indeksy_blokowe(n, dl, konfig["boot"], gen) for dl in dlugosci}
    out = np.zeros((len(dlugosci), len(PROGNOZY), len(SKLADOWE)))
    for j, nazwa in enumerate(PROGNOZY):
        q, es = rd.prognoza_d(zr, nazwa)
        pw = pwartosci_blokowe(zr.r, q, es, P, idx_dni, idx_bloki)
        for i, dl in enumerate(dlugosci):
            out[i, j] = odrzuca(pw[dl])
    return out


def uruchom_komorke(par, ss, panele: int, pula, konfig: dict, dlugosci) -> np.ndarray:
    zadania = [(s, par, konfig, dlugosci) for s in _potomne(ss, panele)]
    return np.stack(rc._mapuj(przetworz_panel_k, zadania, pula))


def odsetek(wyn: np.ndarray, i_dl: int, nazwa: str, skl: str = "razem") -> tuple[float, float]:
    v = wyn[:, i_dl, PROGNOZY.index(nazwa), SKLADOWE.index(skl)]
    return float(v.mean()), float(v.std(ddof=1) / np.sqrt(len(v)))


def wypisz_komorke(nazwa: str, wyn: np.ndarray, dlugosci) -> list[dict]:
    print(f"\n=== {nazwa} ({len(wyn)} paneli) ===")
    print("  odsetek odrzuceń testu zbiorczego (%), razem; w nawiasie SE")
    print("  L     " + " ".join(f"{p:>13s}" for p in PROGNOZY) + "   K-a≤10  K-b(−15%)≥80")
    wiersze = []
    for i, dl in enumerate(dlugosci):
        v = {p: odsetek(wyn, i, p) for p in PROGNOZY}
        ka, kb = v[KA][0], v[KB15][0]
        ok = ka <= KA_MAX and kb >= KB_MIN
        print(
            f"  {dl:<4d}  "
            + " ".join(f"{100 * v[p][0]:6.1f}({100 * v[p][1]:3.1f})" for p in PROGNOZY)
            + f"   {'tak' if ka <= KA_MAX else 'NIE':>5s}  {'tak' if kb >= KB_MIN else 'NIE':>8s}"
        )
        wiersze.append(
            {"L": dl, "ka": ka, "kb15": kb, "ok": ok, "margines": min(KA_MAX - ka, kb - KB_MIN)}
        )
    print("  składowe garch_x1.00 / garch_x0.85 (A, B, C):")
    for i, dl in enumerate(dlugosci):
        s1 = [100 * odsetek(wyn, i, KA, s)[0] for s in SKLADOWE[1:]]
        s2 = [100 * odsetek(wyn, i, KB15, s)[0] for s in SKLADOWE[1:]]
        print(
            f"    L={dl:<4d} "
            + "A/B/C: "
            + "/".join(f"{x:.1f}" for x in s1)
            + "  |  "
            + "/".join(f"{x:.1f}" for x in s2)
        )
    return wiersze


def wybierz_dlugosc(wiersze_b2: list[dict]) -> int | None:
    """Reguła z pre-rejestracji: wśród L > 1 spełniających oba warunki w B2 wybierz największy margines."""
    kand = [w for w in wiersze_b2 if w["L"] > 1 and w["ok"]]
    return max(kand, key=lambda w: w["margines"])["L"] if kand else None


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="026 — K′ (bootstrap blokowy), cel σ −15 %")
    ap.add_argument("tryb", choices=("wybor", "potwierdz"))
    ap.add_argument("--kalibracja", required=True)
    ap.add_argument("--dlugosc", type=int, default=None, help="potwierdz: wybrana długość bloku")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--zapisz", default=None, help="plik .npz na surowe tablice (poza gitem)")
    a = ap.parse_args(argv)
    konfig = dict(KONFIG_SMOKE if a.smoke else KONFIG)
    if a.tryb == "potwierdz" and not a.dlugosc:
        raise SystemExit("potwierdz wymaga --dlugosc")
    dlugosci = DLUGOSCI_WYBOR if a.tryb == "wybor" else (a.dlugosc,)
    ent = SEED_SMOKE if a.smoke else (SEED_WYBOR if a.tryb == "wybor" else SEED_POTWIERDZENIE)
    panele = 4 if a.smoke else (PANELE_WYBOR if a.tryb == "wybor" else PANELE_POTWIERDZENIE)
    surowe = Path(a.kalibracja).read_bytes()
    spec = rd.zbuduj_komorki(json.loads(surowe), {n: panele for n in KOMORKI})
    t0 = time.time()
    print(f"026 — K′ (bootstrap blokowy kołowy), tryb {a.tryb}, cel mocy σ −15 % (garch_x0.85)")
    if a.smoke:
        print("SMOKE — NIE JEST PRZEBIEGIEM.")
    print(
        f"Kalibracja sha256 {hashlib.sha256(surowe).hexdigest()[:16]}; ziarno {ent}; konfig {konfig}; długości bloku {dlugosci}"
    )
    wyniki, wiersze = {}, {}
    with rc.pula_procesow(a.workers) as pula:
        for n in KOMORKI:
            if n not in spec:
                print(f"  {n}: NIEDOSTĘPNA")
                continue
            ss = np.random.SeedSequence(ent, spawn_key=(KOMORKI.index(n),))
            t1 = time.time()
            wyniki[n] = uruchom_komorke(spec[n]["par"], ss, panele, pula, konfig, dlugosci)
            print(
                f"  komórka {n}: {panele} paneli w {time.time() - t1:.0f} s",
                file=sys.stderr,
                flush=True,
            )
    for n, w in wyniki.items():
        wiersze[n] = wypisz_komorke(n, w, dlugosci)
    if a.tryb == "wybor" and "B2" in wiersze:
        wyb = wybierz_dlugosc(wiersze["B2"])
        print(
            f"\nREGUŁA WYBORU (B2, L > 1, K-a ≤ 10 % i K-b(−15 %) ≥ 80 %, największy margines): "
            f"{'L = ' + str(wyb) if wyb else 'BRAK — K′ NIEMIERZALNA dla zapisanych długości'}"
        )
    if a.zapisz:
        os.makedirs(os.path.dirname(os.path.abspath(a.zapisz)), exist_ok=True)
        np.savez_compressed(a.zapisz, **wyniki)
    print(f"Czas {time.time() - t0:.0f} s ({a.workers} procesów)", file=sys.stderr)


if __name__ == "__main__":
    main()
