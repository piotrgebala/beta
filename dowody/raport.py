"""
raport.py — REPORTER F3 dla dziennika alpha: e-procesy obalenia i potwierdzenia oraz rozkład a posteriori,
per noga. Czyta `alpha/dziennik/*.csv` (tylko odczyt, zasada 23). NIE WIĄŻE — o nodze decyduje kryterium
ADR-09 (z = 2,31 na odczytach 92/182/365 dni); rola F3 = decyzja D3 użytkownika.

    python -m dowody.raport                      # stan dziennika z katalogu alpha
    python -m dowody.raport --dziennik ŚCIEŻKA
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from dowody.bayes import posterior
from dowody.eproces import obalenie, potwierdzenie
from dowody.nogi import DNI_W_ROKU, NOGI, Z_ADR09

ROOT = Path(__file__).resolve().parents[1]
ALFA = 0.025  # jak łączna jednostronna szansa fałszywego obalenia w ADR-09
PROG_E = 1.0 / ALFA


def _dziennik_alpha() -> Path:
    cfg = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    return (ROOT / cfg["data"]["alpha_repo"] / "dziennik").resolve()


def raport_nogi(x: pd.Series, noga) -> dict:
    v = x.to_numpy(dtype=float)
    v = v[~np.isnan(v)]
    n = len(v)
    out = {"noga": noga.name, "n": n}
    if n == 0:
        return out
    e_ob = obalenie(v, noga.mu_d, noga.sigma_d)
    e_po = potwierdzenie(v, noga.mu_d, noga.sigma_d)
    se = noga.sigma / math.sqrt(n / DNI_W_ROKU)
    post = posterior(v, noga.sigma, 0.0, noga.mu)
    out.update(
        {
            "srednia_rok": float(v.mean()) * DNI_W_ROKU,
            "prog_adr09_opisowo": noga.mu - Z_ADR09 * se,
            "e_obalenie": float(e_ob[-1]),
            "e_obalenie_max": float(e_ob.max()),
            "e_potwierdzenie": float(e_po[-1]),
            "e_potwierdzenie_max": float(e_po.max()),
            "post": post,
        }
    )
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Reporter F3 (e-procesy, Bayes) dla dziennika alpha.")
    ap.add_argument("--dziennik", type=Path, default=None)
    a = ap.parse_args(argv)
    d = a.dziennik or _dziennik_alpha()
    print("REPORTER F3 — NIE WIĄŻE. Obowiązuje kryterium ADR-09 (z = 2,31 na 92/182/365 dniach).")
    print(f"Dziennik: {d}. Próg e-wartości: {PROG_E:.0f} (α = {ALFA}).\n")
    print(
        " noga | dni | średnia %/rok | próg ADR-09 przy tym n | E obal. (max) | E potw. (max) | "
        "a posteriori %/rok [95 %] | P(μ>0)"
    )
    cache: dict[str, pd.DataFrame] = {}
    for noga in NOGI:
        path = d / noga.plik
        if not path.is_file():
            print(f" {noga.name:<4} | brak pliku {noga.plik}")
            continue
        df = cache.setdefault(noga.plik, pd.read_csv(path))
        if noga.kolumna not in df.columns:
            print(f" {noga.name:<4} | brak kolumny {noga.kolumna}")
            continue
        r = raport_nogi(df[noga.kolumna], noga)
        if r["n"] == 0:
            print(f" {noga.name:<4} |   0 | —")
            continue
        p = r["post"]
        flag = " ← E ≥ próg" if max(r["e_obalenie_max"], r["e_potwierdzenie_max"]) >= PROG_E else ""
        print(
            f" {noga.name:<4} | {r['n']:3d} | {100 * r['srednia_rok']:+13.1f} | "
            f"{100 * r['prog_adr09_opisowo']:+22.1f} | {r['e_obalenie']:5.2f} ({r['e_obalenie_max']:5.2f}) | "
            f"{r['e_potwierdzenie']:5.2f} ({r['e_potwierdzenie_max']:5.2f}) | "
            f"{100 * p['mean']:+6.1f} [{100 * p['ci_low']:+.0f}; {100 * p['ci_high']:+.0f}] | "
            f"{p['p_dodatnia']:.2f}{flag}"
        )


if __name__ == "__main__":
    main()
