"""
LM1 — diagnostyka DOPISANA PO przebiegu (reguła werdyktu bez zmian): generator dał różnice strat prawie
nieskorelowane między monetami (korel. D ≈ 0), więc wymiar „20 monet ≠ 20 obserwacji” (R12) nie został
sprawdzony. Tu korelację różnic strat wymuszamy wprost: D_i = √c · D_0 + √(1 − c) · D_i (po centrowaniu),
c ∈ {0; 0,3; 0,6; 0,9}, oraz skalujemy N_eff/n do wartości ze szkicu PRD (≈ 0,33).

    python -m symulacje.run_lm1_korelacja > runs/2026-09-30_lm1-moc-dm-qlike/raw_output_korelacja.txt
"""

from __future__ import annotations

import numpy as np

from miara.dm import diebold_mariano
from symulacje.garch_panel import generuj_panel
from symulacje.moc_dm import mde, moc_kryterium
from symulacje.run_lm1 import DELTAS, N_SRC, REPS, K, straty


def ar1_filtr(x: np.ndarray, phi: float) -> np.ndarray:
    """Nadaje kolumnom autokorelację AR(1) z parametrem phi, zachowując wariancję."""
    y = np.empty_like(x)
    y[0] = x[0]
    s = np.sqrt(1.0 - phi**2)
    for t in range(1, len(x)):
        y[t] = phi * y[t - 1] + s * x[t]
    return y


def main() -> None:
    p = generuj_panel(N_SRC + 30, K, seed=101, rho=0.5)
    L = straty(p)
    D = L["okno"] - L["wyrocznia"]
    D = (D - D.mean(axis=0)) / D.std(axis=0)
    print(
        "Diagnostyka po przebiegu: MDE kryterium F2 przy wymuszonej korelacji różnic strat (n = 2 100)"
    )
    print(
        " korel. D |  phi | N_eff/n | MDE kryterium | MDE 1 moneta | P(żadna gorsza) przy δ = MDE"
    )
    for phi in (0.0, 0.5):
        base = ar1_filtr(D, phi) if phi else D
        for c in (0.0, 0.3, 0.6, 0.9):
            X = np.sqrt(c) * base[:, [0]] + np.sqrt(1 - c) * base
            X[:, 0] = base[:, 0]
            cr = np.corrcoef(X.T)[np.triu_indices(K, 1)].mean()
            ne = np.mean(
                [diebold_mariano(X[:, j], np.zeros(len(X)))["n_eff"] / len(X) for j in range(K)]
            )
            out = moc_kryterium(X, 2100, DELTAS, REPS, 30 if phi == 0 else 60, seed=int(100 * c))
            m_c = mde(DELTAS, out["moc_kryterium"])
            j = int(np.argmin(np.abs(DELTAS - m_c))) if not np.isnan(m_c) else 0
            print(
                f"  {cr:6.2f}  | {phi:.1f}  | {ne:.2f}    | {m_c:13.3f} | "
                f"{mde(DELTAS, out['moc_moneta']):12.3f} | {1 - out['alarm_gorsza'][j]:.3f}"
            )


if __name__ == "__main__":
    main()
