"""Diagnostyka opisowa po kroku 1 (026): błąd średniej dziennej liczby trafień — iid, bootstrap blokowy
i prawdziwy rozrzut między panelami (B2, 120 paneli, garch_x1.00). Uruchomienie: PYTHONPATH=. python <ten plik>.
"""

import json
from pathlib import Path

import numpy as np

import symulacje.run_kprim as rk
import symulacje.run_lv2d as rd
from symulacje.garch_panel_regimy import generuj_panel_lv2d
from symulacje.k_prim_blokowy import indeksy_blokowe
from symulacje.moc_var_es import NU, wklady_dzienne
from symulacje.prognozy_lv2 import zbuduj_zrodla

KAL = "runs/2026-10-08_021-lv2d-regimy-wariancji/kalibracja.json"
PANELE, BOOT, DLUGOSCI = 120, 400, (20, 60, 150)

spec = rd.zbuduj_komorki(json.loads(Path(KAL).read_bytes()), {n: PANELE for n in rk.KOMORKI})
par = spec["B2"]["par"]
kf = rk.KONFIG
n = kf["n_dni"] - kf["start"]
srednie, se_iid = [], []
se_blok = {dl: [] for dl in DLUGOSCI}
for s in rk._potomne(np.random.SeedSequence(20_269_977), PANELE):
    sg, sb = rk._potomne(s, 2)
    panel = generuj_panel_lv2d(kf["n_dni"], rk.K, seed=rk._ziarno_int(sg), nu=NU, **par)
    zr = zbuduj_zrodla(panel, start=kf["start"])
    q, es = rd.prognoza_d(zr, "garch_x1.00")
    liczba, _ = wklady_dzienne(zr.r, q, es, rk.P)
    srednie.append(liczba.mean())
    se_iid.append(liczba.std(ddof=1) / np.sqrt(n))
    gen = np.random.default_rng(sb)
    for dl, lista in se_blok.items():
        lista.append(liczba[indeksy_blokowe(n, dl, BOOT, gen)].mean(axis=1).std(ddof=1))
srednie = np.array(srednie)
print(
    f"B2, {PANELE} paneli, garch_x1.00; dzienna liczba trafień (z 4 monet), oczekiwana H0 {rk.K * rk.P:.3f}"
)
print(f"średnia po panelach {srednie.mean():.4f}")
print(f"prawdziwy rozrzut średniej między panelami {srednie.std(ddof=1):.4f}")
print(
    f"SE iid (jak w K) {np.mean(se_iid):.4f}  -> stosunek rozrzut/iid {srednie.std(ddof=1) / np.mean(se_iid):.2f}"
)
for dl, lista in se_blok.items():
    print(
        f"SE bootstrapu blokowego L={dl:<3d} {np.mean(lista):.4f}  -> stosunek do iid {np.mean(lista) / np.mean(se_iid):.2f}"
    )
