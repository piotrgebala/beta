"""
moc_dm.py — rachunek mocy przez symulację dla kryterium F2 (`docs/PRD.md` §10.4): nowy model przechodzi,
gdy DM t > 1,96 na jego korzyść w ≥ 80 % monet i żadna moneta nie ma t < −1,96.

Wzór analityczny nie istnieje (autokorelacja straty, grube ogony, korelacja monet), więc:
1. bierzemy realistyczny kształt różnicy strat D (n_src × k monet) i CENTRUJEMY go per moneta (H0: równe
   straty) — zależność w czasie, ogony i korelacja między monetami zostają;
2. losujemy próby długości n bootstrapem blokowym stacjonarnym (Politis–Romano 1994) z TYMI SAMYMI
   indeksami czasu dla wszystkich monet (zachowuje korelację przekrojową);
3. wstawiamy efekt δ (w jednostkach odchylenia D danej monety): D + δ·sd.
Wariancja HAC nie zależy od średniej, więc t(δ) = (d̄* + δ·sd) / se* liczymy dla całej siatki δ z jednego
losowania. MDE = najmniejsze δ, przy którym moc kryterium ≥ 80 %.
"""

from __future__ import annotations

import numpy as np

from miara.dm import hac_variance, newey_west_lag

Z = 1.959964


def stationary_bootstrap_indices(
    n_src: int, n_out: int, mean_block: float, rng: np.random.Generator
) -> np.ndarray:
    """Indeksy bootstrapu stacjonarnego: bloki o długości ~ Geom(1/mean_block), start losowy, zawijanie."""
    if n_src < 1 or n_out < 1 or mean_block < 1:
        raise ValueError("n_src, n_out ≥ 1 i mean_block ≥ 1")
    p = 1.0 / mean_block
    new_block = rng.uniform(size=n_out) < p
    new_block[0] = True
    starts = rng.integers(0, n_src, size=n_out)
    idx = np.empty(n_out, dtype=np.int64)
    cur = 0
    for j in range(n_out):
        cur = starts[j] if new_block[j] else (cur + 1) % n_src
        idx[j] = cur
    return idx


def moc_kryterium(
    D: np.ndarray,
    n: int,
    deltas: np.ndarray,
    reps: int,
    mean_block: float,
    seed: int = 0,
    share: float = 0.8,
    lag: int | None = None,
) -> dict:
    """
    Moc kryterium F2 i moc pojedynczej monety na siatce δ.

    Args:
        D: różnice strat baseline − kandydat (n_src × k), bez NaN; centrowane wewnątrz.
        n: długość próby OOS na monetę (dni).
        deltas: siatka efektów δ (jednostki sd różnicy strat).
        reps: liczba losowań bootstrapu.
        share: wymagany odsetek monet z t > 1,96 (F2: 80 %).

    Returns:
        {deltas, moc_kryterium, moc_moneta, alarm_gorsza (P(jakaś moneta t < −1,96)), lag}.
    """
    D = np.asarray(D, dtype=float)
    Dc = D - D.mean(axis=0)
    sd = Dc.std(axis=0)
    k = D.shape[1]
    need = int(np.ceil(share * k - 1e-12))
    L = newey_west_lag(n) if lag is None else lag
    rng = np.random.default_rng(seed)
    deltas = np.asarray(deltas, dtype=float)
    pass_c = np.zeros(len(deltas))
    pass_1 = np.zeros(len(deltas))
    worse = np.zeros(len(deltas))
    for _ in range(reps):
        idx = stationary_bootstrap_indices(len(Dc), n, mean_block, rng)
        x = Dc[idx]
        se = np.sqrt(hac_variance(x, L) / n)
        t = (x.mean(axis=0)[None, :] + deltas[:, None] * sd[None, :]) / se[None, :]
        good = (t > Z).sum(axis=1)
        bad = (t < -Z).any(axis=1)
        pass_c += (good >= need) & ~bad
        pass_1 += (t > Z).mean(axis=1)
        worse += bad
    return {
        "deltas": deltas,
        "moc_kryterium": pass_c / reps,
        "moc_moneta": pass_1 / reps,
        "alarm_gorsza": worse / reps,
        "lag": L,
    }


def moc_kryterium_braki(
    D: np.ndarray,
    deltas: np.ndarray,
    reps: int,
    mean_block: float,
    seed: int = 0,
    share: float = 0.8,
    min_n: int = 30,
) -> dict:
    """
    `moc_kryterium` dla monet o RÓŻNYCH okresach OOS (F2-1, Poprawka 1 — część wspólna 20 monet pusta).

    D to kalendarz (suma dni OOS) × k z NaN tam, gdzie monety nie ma. Losujemy indeksy kalendarza długości
    len(D) — te same dla wszystkich monet (korelacja przekrojowa zostaje tam, gdzie monety żyją razem);
    każda moneta liczy t ze SWOICH obecnych wierszy losowania (n_j ≈ jej długość OOS, lag Neweya–Westa
    z n_j). Moneta z < `min_n` wierszami w losowaniu: t = NaN (nie przechodzi, nie jest „gorsza”).
    Bez braków wynik = `moc_kryterium(D, n=len(D))` (test).
    """
    D = np.asarray(D, dtype=float)
    Dc = D - np.nanmean(D, axis=0)
    sd = np.nanstd(Dc, axis=0)
    n_cal, k = D.shape
    need = int(np.ceil(share * k - 1e-12))
    rng = np.random.default_rng(seed)
    deltas = np.asarray(deltas, dtype=float)
    pass_c = np.zeros(len(deltas))
    pass_1 = np.zeros(len(deltas))
    worse = np.zeros(len(deltas))
    for _ in range(reps):
        idx = stationary_bootstrap_indices(n_cal, n_cal, mean_block, rng)
        x = Dc[idx]
        mean = np.full(k, np.nan)
        se = np.full(k, np.nan)
        for j in range(k):
            xj = x[:, j][~np.isnan(x[:, j])]
            if len(xj) < min_n:
                continue
            mean[j] = xj.mean()
            se[j] = np.sqrt(hac_variance(xj, newey_west_lag(len(xj))) / len(xj))
        t = (mean[None, :] + deltas[:, None] * sd[None, :]) / se[None, :]
        good = (t > Z).sum(axis=1)
        bad = (t < -Z).any(axis=1)
        pass_c += (good >= need) & ~bad
        pass_1 += (t > Z).mean(axis=1)
        worse += bad
    return {
        "deltas": deltas,
        "moc_kryterium": pass_c / reps,
        "moc_moneta": pass_1 / reps,
        "alarm_gorsza": worse / reps,
    }


def mde(deltas: np.ndarray, power: np.ndarray, target: float = 0.8) -> float:
    """Najmniejsze δ z mocą ≥ target (interpolacja liniowa między węzłami); NaN gdy nieosiągalne."""
    deltas = np.asarray(deltas, dtype=float)
    power = np.maximum.accumulate(np.asarray(power, dtype=float))
    hit = np.nonzero(power >= target)[0]
    if len(hit) == 0:
        return float("nan")
    j = hit[0]
    if j == 0:
        return float(deltas[0])
    x0, x1, p0, p1 = deltas[j - 1], deltas[j], power[j - 1], power[j]
    return float(x0 + (target - p0) * (x1 - x0) / (p1 - p0)) if p1 > p0 else float(x1)
