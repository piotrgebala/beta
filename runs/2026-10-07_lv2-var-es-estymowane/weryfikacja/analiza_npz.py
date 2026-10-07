"""Kontrola NaN / nieokreśloności na zapisanych wynikach paneli (krok 4, punkt ii)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from symulacje import run_lv2 as R

plik = sys.argv[1]
z = np.load(plik)
abs_, dm, diag = z["abs"], z["dm"], z["diag"]
print(f"plik {plik}: abs {abs_.shape}, dm {dm.shape}, diag {diag.shape}")
B = abs_.shape[0]
print(f"paneli: {B}")

print("\n## NaN w tablicy abs (komórka × p × prognoza × STAT) — tylko pola, które NIE są niezdef")
for ic in range(abs_.shape[1]):
    for ip, p in enumerate(R.POZIOMY):
        zle = []
        for j, nazwa in enumerate(R.PROGNOZY):
            blok = abs_[:, ic, ip, j, :]
            if np.isnan(blok).all():
                continue  # prognozy nieobecne w tej komórce (podpanel bez ogonów ep/ec itd.)
            n_nan = int(np.isnan(blok[:, [R.IDX[s] for s in R.STAT if s != "niezdef"]]).sum())
            if n_nan:
                zle.append((nazwa, n_nan))
        print(f"  komórka {ic}, p = {p}: prognozy z NaN w statystykach: {zle if zle else 'brak'}")

print(
    "\n## niezdef (liczba nieokreślonych p-wartości testu zbiorczego na panel), średnia po panelach"
)
for ic in range(abs_.shape[1]):
    for ip, p in enumerate(R.POZIOMY):
        wiersze = []
        for j, nazwa in enumerate(R.PROGNOZY):
            v = abs_[:, ic, ip, j, R.IDX["niezdef"]]
            if np.isnan(v).all():
                continue
            if np.nansum(v) > 0:
                wiersze.append((nazwa, float(np.nanmean(v)), int(np.nansum(v > 0))))
        print(
            f"  komórka {ic}, p = {p}: {wiersze if wiersze else 'wszystkie p-wartości określone we wszystkich panelach'}"
        )

print(
    "\n## DM: porównania z NaN lub nieskończonymi t/średnia/se (tylko tam, gdzie porównanie istnieje)"
)
for ic in range(dm.shape[1]):
    for ip, p in enumerate(R.POZIOMY):
        zle = []
        istnieje = 0
        for j, por in enumerate(R.POROWNANIA):
            blok = dm[:, ic, ip, j, :]
            if np.isnan(blok[:, 1]).all():
                continue
            istnieje += 1
            n_zle = int((~np.isfinite(blok)).any(axis=1).sum())
            if n_zle:
                zle.append((por["kod"], n_zle))
        print(
            f"  komórka {ic}, p = {p}: istniejących porównań {istnieje}; z nieskończonościami/NaN: {zle if zle else 'brak'}"
        )

print("\n## DIAG GARCH (po panelach): " + ", ".join(R.DIAG))
for k, nazwa in enumerate(R.DIAG):
    v = diag[:, k]
    print(
        f"  {nazwa:<14} średnia {np.mean(v):.5f}  min {np.min(v):.5f}  max {np.max(v):.5f}  NaN {int(np.isnan(v).sum())}"
    )
