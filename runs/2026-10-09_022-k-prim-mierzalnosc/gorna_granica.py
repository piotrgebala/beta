"""Karta 022, R3: górna granica mocy reguły K′ na panelach 021 (`data/lv2d_wyniki_paneli.npz`).

PYTHONPATH=. python runs/2026-10-09_022-k-prim-mierzalnosc/gorna_granica.py
"""

from __future__ import annotations

import numpy as np

from symulacje.k_prim import odrzucenia_idealne

PROGNOZY = (
    "wyr_t5", "zan30", "garch_x1.00", "garch_x0.95", "garch_x0.90",
    "garch_x0.85", "garch_x0.80", "garch_x0.70", "zan10", "zan20",
)  # fmt: skip
STAT = ("hit", "u_sr", "zb_a", "zb_b", "zb_c", "zb_bonf", "zb_a_prawa", "vr", "niezdef")
P = 0.05

z = np.load("data/lv2d_wyniki_paneli.npz")
for komorka in ("A0", "B1", "B2", "B3"):
    st = z[f"{komorka}_stat"]
    assert st.shape == (4000, len(PROGNOZY), len(STAT)), st.shape
    print(f"\n=== {komorka} (4000 paneli) ===")
    print(
        f"{'prognoza':>12} {'A':>6} {'B':>6} {'C':>6} {'razem':>7} {'bez B':>7} {'z_A śr':>7} {'z_C śr':>7}   zapisane K (zb_bonf)"
    )
    for i, f in enumerate(PROGNOZY):
        hit, u, zb_b = st[:, i, 0], st[:, i, 1], st[:, i, 3]
        w = odrzucenia_idealne(hit, u, zb_b, P)
        bez = odrzucenia_idealne(hit, u, None, P)
        print(
            f"{f:>12} {100 * w['A']:6.1f} {100 * w['B']:6.1f} {100 * w['C']:6.1f} {100 * w['razem']:7.1f} "
            f"{100 * bez['razem']:7.1f} {w['z_a_sr']:7.2f} {w['z_c_sr']:7.2f}   {100 * st[:, i, 5].mean():6.1f}"
        )
    ka = odrzucenia_idealne(st[:, 2, 0], st[:, 2, 1], st[:, 2, 3], P)["razem"]
    kb = odrzucenia_idealne(st[:, 4, 0], st[:, 4, 1], st[:, 4, 3], P)["razem"]
    werdykt = "MIERZALNA (górna granica)" if (kb >= 0.80 and ka <= 0.10) else "NIEMIERZALNA"
    print(f"  K-a* = {100 * ka:.1f} % (próg ≤ 10), K-b* = {100 * kb:.1f} % (próg ≥ 80) → {werdykt}")
