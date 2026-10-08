"""Druga droga dla karty 021: VR, ρ̂, odsetek dopasowań przy granicy i niezbieżnych liczone bez `run_lv2d`,
bez `prognoza_garch_tnu`, bez `filtr_sigma2`, bez `vr_rho` i bez `var_es_t` — wprost z `dopasuj_garch_t`,
własnej rekurencji σ² w pętli i `scipy.stats.t`. Świeże panele (ziarno 27_182_818, rozłączne z pilotażowym,
rejestrowym i dymnym). To OPIS (100 paneli na komórkę), nie kalibracja i nie przebieg rejestrowy; reguły K
nie dotyka i odsetka trafień na prawdziwych danych nie liczy.

    PYTHONPATH=. python runs/2026-10-08_021-lv2d-regimy-wariancji/druga_droga.py \
        runs/2026-10-08_021-lv2d-regimy-wariancji/kalibracja.json > .../raw_druga_droga.txt
"""

from __future__ import annotations

import json
import os
import sys

for _zmienna in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_zmienna] = "1"  # musi być przed importem numpy

import multiprocessing as mp

import numpy as np
from scipy.stats import t as student_t

from symulacje.garch_panel_regimy import generuj_panel_lv2d
from symulacje.garch_t import dopasuj_garch_t

N_DNI, START, KROK, K, P = 2091, 400, 30, 4, 0.05
PANELE = 100
ZIARNO = 27_182_818
A0 = {
    "rho": 0.8,
    "rho_szok": 0.0,
    "persystencja": None,
    "alpha": 0.08,
    "amplituda": 0.0,
    "dlugosc": 300.0,
}


def sigma2_wprost(x: np.ndarray, omega: float, alpha: float, beta: float, s0: float, ile: int):
    """σ²_0 … σ²_{ile−1}: σ²_{t+1} = ω + α x_t² + β σ²_t, pętla bez `lfilter`."""
    s2 = np.empty(ile)
    s2[0] = s0
    for t in range(ile - 1):
        s2[t + 1] = omega + alpha * x[t] ** 2 + beta * s2[t]
    return s2


def panel(arg) -> np.ndarray:
    """[VR, ρ̂, przy granicy, niezbieżne, persystencja, ν̂] jednego panelu."""
    ss, par = arg
    seed = int(ss.generate_state(1, dtype=np.uint64)[0])
    r = generuj_panel_lv2d(N_DNI, K, seed=seed, **par)["r"].to_numpy()
    hit = np.zeros((N_DNI - START, K))
    brzeg = nz = n_fit = 0
    pers, nus = [], []
    for j in range(K):
        f = None
        for b in range(START, N_DNI, KROK):
            e = min(b + KROK, N_DNI)
            f = dopasuj_garch_t(r[:b, j], start=f)
            s2 = sigma2_wprost(r[:, j], f.omega, f.alpha, f.beta, f.backcast, e)[b:e]
            q = np.sqrt(s2) * np.sqrt((f.nu - 2.0) / f.nu) * student_t.ppf(P, f.nu)
            hit[b - START : e - START, j] = r[b:e, j] < q
            brzeg += bool(f.brzeg)
            nz += not f.zbiezny
            n_fit += 1
            pers.append(f.alpha + f.beta)
            nus.append(f.nu)
    s = hit.sum(axis=1)
    n = len(s)
    vr = (((s - s.mean()) ** 2).sum() / (n - 1)) / (K * P * (1 - P))
    return np.array(
        [vr, (vr - 1) / (K - 1), brzeg / n_fit, nz / n_fit, np.mean(pers), np.mean(nus)]
    )


def main() -> None:
    with open(sys.argv[1], encoding="utf-8") as plik:
        kal = json.load(plik)
    komorki = {"A0": A0} | {
        nr: k["par"] for nr, k in kal.get("komorki", {}).items() if k.get("status") == "ok"
    }
    print(f"Druga droga 021: ziarno {ZIARNO}, {PANELE} paneli na komórkę, K = {K}, p = {P}")
    with mp.get_context("forkserver").Pool(os.cpu_count() or 1) as pula:
        for i, (nazwa, par) in enumerate(komorki.items()):
            ss = np.random.SeedSequence(ZIARNO, spawn_key=(i,)).spawn(PANELE)
            m = np.array(pula.map(panel, [(s, par) for s in ss]))
            if not np.isfinite(m).all():
                raise SystemExit(f"STOP: NaN w drugiej drodze, komórka {nazwa}")
            se = m.std(axis=0, ddof=1) / np.sqrt(PANELE)
            opis = ", ".join(f"{k}={v}" for k, v in par.items())
            print(f"\n{nazwa}: {opis}")
            for kol, nm, mn in (
                (0, "VR", 1.0),
                (1, "ρ̂", 1.0),
                (2, "przy granicy", 100.0),
                (3, "niezbieżne", 100.0),
                (4, "persystencja", 1.0),
                (5, "ν̂", 1.0),
            ):
                dod = " %" if mn == 100.0 else ""
                print(
                    f"  {nm}: {m[:, kol].mean() * mn:.4f}{dod} ± {se[kol] * mn:.4f}"
                    if mn == 1.0
                    else f"  {nm}: {m[:, kol].mean() * mn:.1f}{dod} ± {se[kol] * mn:.1f} pp"
                )


if __name__ == "__main__":
    main()
