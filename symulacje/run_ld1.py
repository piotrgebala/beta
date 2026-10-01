"""
LD1 — laboratorium F3: fałszywe alarmy i moc e-procesów reportera przy CODZIENNYM zaglądaniu przez
365 dni, wobec kryterium ADR-09 (z = 2,31 na 92/182/365 dniach). Pre-rejestracja:
`runs/2026-10-01_ld1-eproces-dziennik/README.md`. Neutralny reporter (R14).

    python -m symulacje.run_ld1 > runs/2026-10-01_ld1-eproces-dziennik/raw_output.txt
"""

from __future__ import annotations

import math
import time

import numpy as np

from dowody.eproces import log_e_mieszanka, tau_dla
from dowody.nogi import DNI_ODCZYTOW, DNI_W_ROKU, NOGI, Z_ADR09

REPS = 20_000
T = 365
ALFA = 0.025
LOG_PROG = math.log(1.0 / ALFA)
MU_POTW = 0.15  # PRD F3: moc przy prawdziwym +15 %/rok
Z = 1.959964


def zwroty(rng, mu_d: float, sd_d: float, rozklad: str) -> np.ndarray:
    if rozklad == "normalny":
        e = rng.standard_normal((REPS, T))
    elif rozklad == "t3":
        e = rng.standard_t(3, size=(REPS, T)) / math.sqrt(3.0)
    elif rozklad == "t3+garch":
        z = rng.standard_t(3, size=(REPS, T)) / math.sqrt(3.0)
        e = np.empty_like(z)
        v = np.ones(REPS)
        for t in range(T):
            e[:, t] = np.sqrt(v) * z[:, t]
            v = 0.02 + 0.08 * e[:, t] ** 2 + 0.90 * v
    else:
        raise ValueError(rozklad)
    return mu_d + sd_d * e


def e_ever(x, m0, sd_d, tau, strona) -> float:
    S = np.cumsum(x - m0, axis=1)
    V = np.arange(1, T + 1)[None, :] * sd_d**2
    return float((log_e_mieszanka(S, V, tau, strona) >= LOG_PROG).any(axis=1).mean())


def adr_ever(x, m0, sd_d, strona) -> float:
    """3 odczyty: z_k = Σ (x − m0) / (σ √n_k); obalenie z < −2,31, potwierdzenie z > 2,31."""
    hit = np.zeros(len(x), dtype=bool)
    for n in DNI_ODCZYTOW:
        z = (x[:, :n] - m0).sum(axis=1) / (sd_d * math.sqrt(n))
        hit |= (strona * z) > Z_ADR09
    return float(hit.mean())


def wilson_hi(p: float, n: int = REPS) -> float:
    c = (p + Z * Z / (2 * n)) / (1 + Z * Z / n)
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / (1 + Z * Z / n)
    return c + h


def main() -> None:
    t0 = time.time()
    print(
        f"LD1 — {REPS} ścieżek × {T} dni, próg e = {1 / ALFA:.0f} (α {ALFA}), ADR-09 z {Z_ADR09}\n"
    )
    print(
        " noga | rozkład   | FAŁSZ. obal. e (ADR) | FAŁSZ. potw. e (ADR) | moc obal. μ=0 e (ADR) | "
        f"moc potw. μ=+{100 * MU_POTW:.0f} % e (ADR)"
    )
    bramka_fa, bramka_moc = True, True
    rng = np.random.default_rng(20261001)
    for noga in NOGI:
        sd_d, mu_d = noga.sigma_d, noga.mu_d
        tau = tau_dla(mu_d, sd_d)
        for rozklad in ("normalny", "t3", "t3+garch"):
            x_h0 = zwroty(rng, mu_d, sd_d, rozklad)  # prawdziwe μ = zakładane
            fa_ob = e_ever(x_h0, mu_d, sd_d, tau, -1)
            fa_ob_adr = adr_ever(x_h0, mu_d, sd_d, -1)
            x0 = zwroty(rng, 0.0, sd_d, rozklad)  # prawdziwe μ = 0
            fa_po = e_ever(x0, 0.0, sd_d, tau, +1)
            fa_po_adr = adr_ever(x0, 0.0, sd_d, +1)
            moc_ob = e_ever(x0, mu_d, sd_d, tau, -1)
            moc_ob_adr = adr_ever(x0, mu_d, sd_d, -1)
            x15 = zwroty(rng, MU_POTW / DNI_W_ROKU, sd_d, rozklad)
            moc_po = e_ever(x15, 0.0, sd_d, tau, +1)
            moc_po_adr = adr_ever(x15, 0.0, sd_d, +1)
            bramka_fa &= wilson_hi(fa_ob) <= 0.05 and wilson_hi(fa_po) <= 0.05
            if rozklad == "normalny":
                bramka_moc &= moc_po >= moc_po_adr
            print(
                f" {noga.name:<4} | {rozklad:<9} | {100 * fa_ob:5.2f} % ({100 * fa_ob_adr:5.2f} %) | "
                f"{100 * fa_po:5.2f} % ({100 * fa_po_adr:5.2f} %) | {100 * moc_ob:5.2f} % ({100 * moc_ob_adr:5.2f} %) | "
                f"{100 * moc_po:5.2f} % ({100 * moc_po_adr:5.2f} %)"
            )
    print(
        f"\nBramka 1 (fałszywe alarmy e-procesów ≤ 5 %, górna granica Wilsona, wszystkie nogi i rozkłady): "
        f"{'TAK' if bramka_fa else 'NIE'}"
    )
    print(
        f"Bramka 2 (moc potwierdzenia przy +15 %/rok ≥ trzech odczytów z 2,31, rozkład normalny): "
        f"{'TAK' if bramka_moc else 'NIE'}"
    )
    print(f"\nczas: {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
