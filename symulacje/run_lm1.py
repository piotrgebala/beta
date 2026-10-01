"""
LM1 — laboratorium F1: moc testu DM na stracie QLIKE dla kryterium rundy F2-1 (HAR-RV vs okno wstecz).
Pre-rejestracja: `runs/2026-09-30_lm1-moc-dm-qlike/README.md`. Neutralny reporter (R14).

    python -m symulacje.run_lm1 > runs/2026-09-30_lm1-moc-dm-qlike/raw_output.txt
"""

from __future__ import annotations

import math
import time

import numpy as np

from miara.dm import diebold_mariano, dm_t, newey_west_lag, qlike
from symulacje.garch_panel import generuj_panel, momenty, prognoza_ewma, prognoza_okno
from symulacje.moc_dm import mde, moc_kryterium

Z = 1.959964
K = 20
N_SRC = 20_000
RHOS = (0.0, 0.5, 0.8)
NS = (500, 1000, 2100)
DELTAS = np.round(np.arange(0.0, 0.3001, 0.005), 3)
REPS = 1000
BLOK = 30
BLOKI_WRAZLIWOSC = (10, 60)
N_KONTROLA_SEEDS = 50
ETA_SD = 0.25
DELTA_ZAKLADANE = 0.10  # szkic PRD §7 F2: t ≈ 0,1 × √700 ≈ 2,6
GLOWNA = (2100, 0.8)


def wilson(k: int, n: int, z: float = Z) -> tuple[float, float]:
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def straty(p: dict) -> dict:
    rv = p["rv"]
    f = {
        "okno": prognoza_okno(p["r"], 30),
        "ewma": prognoza_ewma(p["r"], 0.94),
        "wyrocznia": p["sigma2"],
        "stala": p["sigma2"] * 0 + 0.04**2,
    }
    return {k: qlike(rv.iloc[30:], v.iloc[30:]) for k, v in f.items()}


def acf1(x: np.ndarray) -> float:
    c = x - x.mean(axis=0)
    return float(((c[1:] * c[:-1]).sum(axis=0) / (c * c).sum(axis=0)).mean())


def main() -> None:
    t0 = time.time()
    print("LM1 — moc DM (QLIKE, HAC Newey–West) dla kryterium F2: t > 1,96 w ≥ 80 % z 20 monet,")
    print(
        "żadna t < −1,96. Źródło kształtu różnicy strat: okno 30 dni − wyrocznia σ², centrowane.\n"
    )

    # --- 1. panele źródłowe
    src = {}
    print("1. Panele źródłowe (20 monet × 20 000 dni) — momenty i efekty w świecie generatora")
    print(
        " rho | vol   | kurt | acf r² | korel. zwr. | δ wyrocznia | δ EWMA | acf1 D | korel. D | N_eff/n"
    )
    for i, rho in enumerate(RHOS):
        p = generuj_panel(N_SRC + 30, K, seed=100 + i, rho=rho)
        L = straty(p)
        D = L["okno"] - L["wyrocznia"]
        D_ewma = L["okno"] - L["ewma"]
        m = momenty(p["r"])
        d_or = float((D.mean(axis=0) / D.std(axis=0)).mean())
        d_ew = float((D_ewma.mean(axis=0) / D_ewma.std(axis=0)).mean())
        cD = np.corrcoef(D.T)[np.triu_indices(K, 1)].mean()
        neff = np.mean(
            [diebold_mariano(L["okno"][:, j], L["wyrocznia"][:, j])["n_eff"] for j in range(K)]
        )
        src[rho] = D
        print(
            f" {rho:.1f} | {m['vol']:.4f} | {m['excess_kurtosis']:4.1f} | {m['acf_r2_lag1']:.3f}  | "
            f"{m['corr']:.2f}        | {d_or:.3f}       | {d_ew:.3f}  | {acf1(D):.3f}  | {cD:.2f}     | "
            f"{neff / D.shape[0]:.3f}"
        )

    # --- 2. kontrola negatywna i pozytywna DM na niezależnych panelach
    print(f"\n2. Kontrole przyrządu DM ({N_KONTROLA_SEEDS} paneli × {K} monet, rho = 0)")
    for n in (2100, 500):
        t_neg, t_pos, t_or = [], [], []
        for s in range(N_KONTROLA_SEEDS):
            p = generuj_panel(n + 30, K, seed=10_000 + 1000 * (n == 500) + s, rho=0.0)
            rng = np.random.default_rng(20_000 + s + 1000 * (n == 500))
            sig = p["sigma2"].iloc[30:].to_numpy()
            rv = p["rv"].iloc[30:].to_numpy()
            fa = sig * np.exp(rng.normal(0, ETA_SD, sig.shape))
            fb = sig * np.exp(rng.normal(0, ETA_SD, sig.shape))
            L = straty(p)
            lag = newey_west_lag(n)
            t_neg += list(dm_t(qlike(rv, fa) - qlike(rv, fb), lag))
            t_pos += list(dm_t(L["stala"] - L["wyrocznia"], lag))
            t_or += list(dm_t(L["okno"] - L["wyrocznia"], lag))
        t_neg, t_pos, t_or = map(np.array, (t_neg, t_pos, t_or))
        k = int((np.abs(t_neg) > Z).sum())
        lo, hi = wilson(k, len(t_neg))
        ok = 0.025 <= k / len(t_neg) <= 0.075
        print(
            f" n = {n}: NEGATYWNA (bliźniacze prognozy) |t| > 1,96: {k}/{len(t_neg)} = "
            f"{100 * k / len(t_neg):.1f} % [Wilson {100 * lo:.1f}; {100 * hi:.1f}] "
            f"(śr. t {t_neg.mean():+.3f}, sd {t_neg.std(ddof=1):.3f}) — w [2,5; 7,5] %: {'TAK' if ok else 'NIE'}"
        )
        if n == 2100:
            kp = int((t_pos > Z).sum())
            print(
                f"           POZYTYWNA (wyrocznia vs stała) t > 1,96: {kp}/{len(t_pos)} = "
                f"{100 * kp / len(t_pos):.1f} % (mediana t {np.median(t_pos):.1f}) — ≥ 95 %: "
                f"{'TAK' if kp / len(t_pos) >= 0.95 else 'NIE'}"
            )
        ko = int((t_or > Z).sum())
        print(
            f"           opis: wyrocznia vs okno 30 t > 1,96: {ko}/{len(t_or)} = {100 * ko / len(t_or):.1f} % "
            f"(mediana t {np.median(t_or):.2f})"
        )

    # --- 3. moc i MDE
    print(f"\n3. Moc i MDE (bootstrap stacjonarny, blok {BLOK}, {REPS} losowań, siatka δ co 0,005)")
    print(
        " rho |    n | MDE kryterium | MDE 1 moneta | moc kryt. przy δ 0,10 | moc 1 monety przy δ 0,10 | P(kryt.) przy δ 0"
    )
    wyniki = {}
    for rho in RHOS:
        for n in NS:
            out = moc_kryterium(src[rho], n, DELTAS, REPS, BLOK, seed=int(1000 * rho) + n)
            j = int(np.nonzero(DELTAS == DELTA_ZAKLADANE)[0][0])
            m_c, m_1 = mde(DELTAS, out["moc_kryterium"]), mde(DELTAS, out["moc_moneta"])
            wyniki[(n, rho)] = m_c
            print(
                f" {rho:.1f} | {n:4d} | {m_c:13.3f} | {m_1:12.3f} | {out['moc_kryterium'][j]:21.3f} | "
                f"{out['moc_moneta'][j]:24.3f} | {out['moc_kryterium'][0]:.3f}"
            )
    print(f"\n   wrażliwość na długość bloku (n = {GLOWNA[0]}, rho = {GLOWNA[1]}):")
    for b in BLOKI_WRAZLIWOSC:
        out = moc_kryterium(src[GLOWNA[1]], GLOWNA[0], DELTAS, REPS, b, seed=7 + b)
        print(f"   blok {b:2d}: MDE kryterium {mde(DELTAS, out['moc_kryterium']):.3f}")

    # --- 4. werdykt według reguły z pre-rejestracji
    m = wyniki[GLOWNA]
    print(
        f"\n4. Reguła z pre-rejestracji: MDE kryterium (n = {GLOWNA[0]}, rho = {GLOWNA[1]}) = {m:.3f} "
        f"{'≤' if m <= DELTA_ZAKLADANE else '>'} {DELTA_ZAKLADANE} → "
        f"{'MIERZALNA' if m <= DELTA_ZAKLADANE else 'NIEMIERZALNA'}"
    )
    print(f"\nczas: {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
