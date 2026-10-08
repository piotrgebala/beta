"""Druga droga dla STOP 1 (karta 019): odsetek dopasowań GARCH-t przy granicy liczony bez `run_lv2c`
i bez `prognoza_garch_tnu` — wprost z `dopasuj_garch_t` na świeżych panelach (ziarno 31_415_926, rozłączne
z pilotażowym 20_261_091 i rejestrowym 20_261_019). Rozbija granicę na parametry. To OPIS po STOP 1,
nie kalibracja i nie przebieg rejestrowy; reguły K nie dotyka.

    PYTHONPATH=. python runs/2026-10-08_019-lv2c-4-monety/druga_droga_brzeg.py > .../raw_druga_droga.txt
"""

from __future__ import annotations

import os

for _zmienna in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_zmienna] = (
        "1"  # 32 procesów × wątki BLAS = przeciążenie; musi być przed importem numpy
    )

import multiprocessing as mp

import numpy as np

from symulacje.garch_panel_wspolny_szok import generuj_panel_lv2c
from symulacje.garch_t import _GRANICE, _theta, dopasuj_garch_t

N_DNI, START, KROK, K = 2091, 400, 30, 4
PANELE = 100
ZIARNO = 31_415_926
PARAMETRY = ("log omega", "persystencja", "udział alfa", "nu")
PUNKTY = ((0.16, 0.5), (0.30, 0.5), (0.20, 1.0))  # (alfa, rho_szok), persystencja 0,9999, rho 0,8


def panel(arg) -> np.ndarray:
    """Dla panelu: macierz (dopasowania × 4 parametry) 0/1 — który parametr jest przy granicy — i persystencja."""
    ss, alfa, rho_szok = arg
    seed = int(ss.generate_state(1, dtype=np.uint64)[0])
    r = generuj_panel_lv2c(
        N_DNI, K, seed=seed, rho=0.8, rho_szok=rho_szok, persystencja=0.9999, alpha=alfa
    )["r"].to_numpy()
    wiersze = []
    for j in range(K):
        f = None
        for b in range(START, N_DNI, KROK):
            f = dopasuj_garch_t(r[:b, j], start=f)
            theta = _theta(f.omega / f.backcast, f.alpha, f.beta, f.nu)
            przy = [abs(t - g[0]) < 1e-3 or abs(t - g[1]) < 1e-3 for t, g in zip(theta, _GRANICE)]
            wiersze.append([*przy, f.brzeg, f.alpha + f.beta, b])
    return np.array(wiersze, dtype=float)


def main() -> None:
    print("Druga droga STOP 1: dopasowania wprost z dopasuj_garch_t, ziarno", ZIARNO)
    with mp.get_context("forkserver").Pool(os.cpu_count() or 1) as pula:
        for i, (alfa, rs) in enumerate(PUNKTY):
            ss = np.random.SeedSequence(ZIARNO, spawn_key=(i,)).spawn(PANELE)
            m = np.vstack(pula.map(panel, [(s, alfa, rs) for s in ss]))
            n = len(m)
            per_panel = m[:, 4].reshape(PANELE, -1).mean(axis=1)
            se = per_panel.std(ddof=1) / np.sqrt(PANELE)
            print(
                f"\nα = {alfa:.2f}, ρ_szok = {rs:.2f}, α + β = 0,9999, ρ = 0,8; {PANELE} paneli, {n} dopasowań"
            )
            print(
                f"  przy granicy (flaga `brzeg`): {100 * m[:, 4].mean():.1f} % ± {100 * se:.1f} pp"
            )
            for p, nazwa in enumerate(PARAMETRY):
                print(f"    z tego parametr „{nazwa}”: {100 * m[:, p].mean():.1f} % dopasowań")
            for lo, hi in ((400, 800), (800, 1400), (1400, 2100)):
                w = (m[:, 6] >= lo) & (m[:, 6] < hi)
                print(
                    f"    okno uczące {lo}–{hi}: przy granicy {100 * m[w, 4].mean():.1f} %, "
                    f"średnia persystencja {m[w, 5].mean():.4f}"
                )


if __name__ == "__main__":
    main()
