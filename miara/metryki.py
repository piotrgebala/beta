"""
metryki.py — trafność, przedziały Walda, próg opłacalności, moc i mierzalność (zasada R3),
statystyki zwrotu per transakcja z N_eff ≤ n (R9, R10).

Port 1:1 z alpha (parytet: `tests/test_parytet_alpha.py`, zasada 24):
- `alpha/backtest/metrics.py` — część pomiarowa: `compute_trade_returns`, `compute_t_stat`,
  `summarize_pooled_by_regime`, `break_even_hit_rate`, `compute_hit_rate`,
  `summarize_edge_by_regime`, `observed_wald_ci`, `wald_half_width`, `min_detectable_hit_rate`,
  `required_trades`, `expected_trades`, `measurability_report`;
- `alpha/backtest/checkpoint_lib.py` — `summarize_trade_returns` (bez części silnika).

Świadomie NIE przeniesione: Sharpe per fold i klasyfikacja GO/WARUNKOWY/NO-GO z Fazy 0
(`compute_fold_metrics`, `classify_checkpoint`, `summarize_by_regime`) — są związane z silnikiem
walk-forward alpha, a werdykt w obu repo stoi na dwóch warunkach R9 (t_neff zwrotu netto ORAZ
ci_low(p) > p*), które liczy `summarize_trade_returns`.

Ramka transakcji (`trades`) — kolumny wymagane jak w alpha: `kill_switch_active` (bool),
`net_pnl`, `gross_pnl`, `equity_before`, `position_size`, `entry_price`, `exit_price`, `cost`,
`regime`; opcjonalnie `exit_reason` ("tp" / "sl" / "timeout").

Konwencja: wielkość niedefiniowalna = NaN (nigdy ±inf, poza `required_trades` przy p_true == p_null).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from miara.neff import effective_sample_size

# Kwantyle rozkładu normalnego jako stałe — identyczne z alpha (parytet do ostatniej cyfry).
Z_TWO_SIDED_95 = 1.959964
Z_POWER_80 = 0.841621

MIN_TRADES_FOR_N_EFF = 10
MIN_TRADES_FOR_HIT_RATE_CI = 20


def compute_trade_returns(trades: pd.DataFrame) -> pd.Series:
    """Zwrot per transakcja = net_pnl / equity_before, bez wierszy kill_switch_active."""
    real_trades = trades.loc[~trades["kill_switch_active"]]
    return real_trades["net_pnl"] / real_trades["equity_before"]


def compute_t_stat(returns: pd.Series) -> float:
    """t = mean / (std / √n), bez annualizacji; NaN dla n < 2 albo zerowej wariancji."""
    n = len(returns)
    if n < 2:
        return float("nan")
    std = returns.std(ddof=1)
    if std == 0 or pd.isna(std):
        return float("nan")
    return float(returns.mean() / (std / np.sqrt(n)))


def summarize_pooled_by_regime(trades: pd.DataFrame) -> pd.DataFrame:
    """
    Per reżim: wszystkie realne transakcje połączone w jeden strumień zwrotów.

    Kolumny: regime, n_trades, mean_return, std_return, sharpe_per_trade, t_stat, n_eff (NaN przy
    n < MIN_TRADES_FOR_N_EFF; przycięte do n), t_stat_neff = mean / (std / √n_eff).
    """
    rows: list[dict] = []
    for regime, group in trades.groupby("regime"):
        returns = compute_trade_returns(group)
        n = len(returns)
        mean = float(returns.mean()) if n > 0 else float("nan")
        std = float(returns.std(ddof=1)) if n > 1 else float("nan")
        sharpe_per_trade = mean / std if n > 1 and std > 0 else float("nan")
        t_stat = compute_t_stat(returns)

        n_eff = float("nan")
        t_stat_neff = float("nan")
        if n >= MIN_TRADES_FOR_N_EFF:
            ess = effective_sample_size(returns.reset_index(drop=True))
            candidate_n_eff = ess["n_eff"]
            if candidate_n_eff > 0:
                n_eff = float(min(candidate_n_eff, n))
                if std and std > 0 and not pd.isna(std):
                    t_stat_neff = float(mean / (std / np.sqrt(n_eff)))

        rows.append(
            {
                "regime": regime,
                "n_trades": n,
                "mean_return": mean,
                "std_return": std,
                "sharpe_per_trade": sharpe_per_trade,
                "t_stat": t_stat,
                "n_eff": n_eff,
                "t_stat_neff": t_stat_neff,
            }
        )
    return pd.DataFrame(rows)


def break_even_hit_rate(cost_fraction: float, barrier_fraction: float) -> float:
    """
    Trafność wyjścia na zero przy symetrycznych barierach ±B i koszcie C: p = 0,5 (1 + C/B).

    Miara diagnostyczna przy wypłatach asymetrycznych (timeouty) — tam próg to p* z
    `summarize_trade_returns`. NaN dla B ≤ 0 lub brakujących argumentów.
    """
    if barrier_fraction is None or pd.isna(barrier_fraction) or barrier_fraction <= 0:
        return float("nan")
    if cost_fraction is None or pd.isna(cost_fraction):
        return float("nan")
    return float(0.5 * (1.0 + cost_fraction / barrier_fraction))


def compute_hit_rate(trades: pd.DataFrame) -> dict:
    """
    Trafność kierunku PRZED kosztami: trafienie = gross_pnl > 0 (definicja kanoniczna alpha Z18).

    Returns:
        {n_trades, hit_rate, z_stat (H0: p = 0,5), ci_low, ci_high (95 % Wald)}; z_stat i CI NaN
        przy n < MIN_TRADES_FOR_HIT_RATE_CI, wszystko NaN przy n = 0.
    """
    real_trades = trades.loc[~trades["kill_switch_active"]]
    n = len(real_trades)
    if n == 0:
        return {
            "n_trades": 0,
            "hit_rate": float("nan"),
            "z_stat": float("nan"),
            "ci_low": float("nan"),
            "ci_high": float("nan"),
        }

    hit_rate = float((real_trades["gross_pnl"] > 0).mean())
    if n < MIN_TRADES_FOR_HIT_RATE_CI:
        return {
            "n_trades": n,
            "hit_rate": hit_rate,
            "z_stat": float("nan"),
            "ci_low": float("nan"),
            "ci_high": float("nan"),
        }

    # se pod H0 (p = 0,5) dla z; se z obserwowanego p dla przedziału.
    z_stat = float((hit_rate - 0.5) / np.sqrt(0.25 / n))
    half_width = observed_wald_ci(round(hit_rate * n), n)["half_width"]
    return {
        "n_trades": n,
        "hit_rate": hit_rate,
        "z_stat": z_stat,
        "ci_low": float(hit_rate - half_width),
        "ci_high": float(hit_rate + half_width),
    }


def summarize_edge_by_regime(trades: pd.DataFrame) -> pd.DataFrame:
    """
    Rozbicie nierówności (2p − 1)·B > C na człony, per reżim.

    Kolumny: regime, n_trades, hit_rate, z_stat, ci_low, ci_high, share_timeout,
    hit_rate_barrier (tautologiczna w alpha — tp/sl odtwarzane z etykiety), hit_rate_timeout,
    barrier_pct (B), cost_pct (C), break_even_p, margin (w punktach trafności, nie zwrotu).
    """
    rows: list[dict] = []
    for regime, group in trades.groupby("regime"):
        real_trades = group.loc[~group["kill_switch_active"]]
        hit = compute_hit_rate(group)

        notional = real_trades["position_size"] * real_trades["entry_price"]
        notional = notional.replace(0.0, np.nan)
        entry_price = real_trades["entry_price"].replace(0.0, np.nan)

        barrier_pct = (
            float(
                (
                    (real_trades["exit_price"] - real_trades["entry_price"]).abs() / entry_price
                ).mean()
            )
            if len(real_trades)
            else float("nan")
        )
        cost_pct = (
            float((real_trades["cost"] / notional).mean()) if len(real_trades) else float("nan")
        )

        if "exit_reason" in real_trades.columns and len(real_trades):
            is_timeout = real_trades["exit_reason"] == "timeout"
            n_timeout = int(is_timeout.sum())
            share_timeout = n_timeout / len(real_trades)
            barrier_trades = real_trades.loc[~is_timeout]
            timeout_trades = real_trades.loc[is_timeout]
            hit_rate_barrier = (
                float((barrier_trades["gross_pnl"] > 0).mean())
                if len(barrier_trades)
                else float("nan")
            )
            hit_rate_timeout = (
                float((timeout_trades["gross_pnl"] > 0).mean()) if n_timeout else float("nan")
            )
        else:
            share_timeout = float("nan")
            hit_rate_barrier = float("nan")
            hit_rate_timeout = float("nan")

        break_even_p = break_even_hit_rate(cost_pct, barrier_pct)
        margin = (
            hit["hit_rate"] - break_even_p
            if not (pd.isna(hit["hit_rate"]) or pd.isna(break_even_p))
            else float("nan")
        )

        rows.append(
            {
                "regime": regime,
                **hit,
                "share_timeout": share_timeout,
                "hit_rate_barrier": hit_rate_barrier,
                "hit_rate_timeout": hit_rate_timeout,
                "barrier_pct": barrier_pct,
                "cost_pct": cost_pct,
                "break_even_p": break_even_p,
                "margin": margin,
            }
        )
    return pd.DataFrame(rows)


# --- moc statystyczna i mierzalność (zasada R3) ---


def observed_wald_ci(hits: int, n_trades: int, z: float = Z_TWO_SIDED_95) -> dict:
    """
    Przedział Walda EX POST wokół zaobserwowanej proporcji: p ± z √(p(1 − p)/n).

    Nie mylić z `wald_half_width` (EX ANTE, konserwatywnie przy p = 0,5).

    Returns:
        {n_trades, hit_rate, half_width, ci_low, ci_high}; NaN dla n ≤ 0.
    """
    if n_trades <= 0:
        return {
            "n_trades": 0,
            "hit_rate": float("nan"),
            "half_width": float("nan"),
            "ci_low": float("nan"),
            "ci_high": float("nan"),
        }
    p = hits / n_trades
    half = float(z * np.sqrt(p * (1.0 - p) / n_trades))
    return {
        "n_trades": int(n_trades),
        "hit_rate": float(p),
        "half_width": half,
        "ci_low": float(p - half),
        "ci_high": float(p + half),
    }


def wald_half_width(n_trades: int, z: float = Z_TWO_SIDED_95) -> float:
    """Połowa szerokości przedziału dla proporcji EX ANTE, przy p = 0,5: z √(0,25/n)."""
    if n_trades <= 0:
        return float("nan")
    return float(z * np.sqrt(0.25 / n_trades))


def min_detectable_hit_rate(break_even_p: float, n_trades: int, z: float = Z_TWO_SIDED_95) -> float:
    """Trafność, którą trzeba ZMIERZYĆ, by ci_low przekroczył próg: p_min = p_be + z √(0,25/n)."""
    if n_trades <= 0 or pd.isna(break_even_p):
        return float("nan")
    return float(break_even_p + wald_half_width(n_trades, z))


def required_trades(
    p_true: float,
    p_null: float,
    z_alpha: float = Z_TWO_SIDED_95,
    z_power: float = Z_POWER_80,
) -> float:
    """
    Liczba transakcji do odróżnienia p_true od p_null (jednopróbkowy test proporcji):

        n = (z_α √(p0(1 − p0)) + z_β √(p1(1 − p1)))² / (p1 − p0)²

    inf przy p_true == p_null; NaN dla argumentów spoza (0, 1).
    """
    for value in (p_true, p_null):
        if pd.isna(value) or not 0.0 < value < 1.0:
            return float("nan")
    delta = p_true - p_null
    if delta == 0:
        return float("inf")
    numerator = (
        z_alpha * np.sqrt(p_null * (1.0 - p_null)) + z_power * np.sqrt(p_true * (1.0 - p_true))
    ) ** 2
    return float(numerator / (delta**2))


def expected_trades(
    n_rows_oos: int,
    abstention_rate: float,
    admission_rate: float = 1.0,
) -> float:
    """
    Ile TRANSAKCJI da okno testowe (nie ile ma świec): n_rows · (1 − abstynencja) · przeżywalność.

    NaN dla argumentów spoza zakresu.
    """
    if n_rows_oos < 0 or pd.isna(abstention_rate) or pd.isna(admission_rate):
        return float("nan")
    if not 0.0 <= abstention_rate <= 1.0 or not 0.0 <= admission_rate <= 1.0:
        return float("nan")
    return float(n_rows_oos * (1.0 - abstention_rate) * admission_rate)


def measurability_report(
    assumed_hit_rate: float,
    break_even_p: float,
    n_trades_expected: float,
) -> dict:
    """
    Czy hipoteza o zakładanej trafności jest MIERZALNA przy oczekiwanej próbie (zasada R3).

    Mierzalna, gdy assumed_hit_rate > min_detectable_hit_rate(break_even_p, n).

    Returns:
        {p_detectable, band_width_pp, margin_pp, measurable, verdict};
        verdict ∈ {"MIERZALNA", "NIEMIERZALNA", "N/D"}.
    """
    n = float(n_trades_expected) if not pd.isna(n_trades_expected) else float("nan")
    invalid = (
        pd.isna(assumed_hit_rate)
        or pd.isna(break_even_p)
        or pd.isna(n)
        or n < 1
        or not 0.0 < assumed_hit_rate < 1.0
        or not 0.0 < break_even_p < 1.0
    )
    if invalid:
        return {
            "p_detectable": float("nan"),
            "band_width_pp": float("nan"),
            "margin_pp": float("nan"),
            "measurable": False,
            "verdict": "N/D",
        }

    n_int = round(n)
    p_detectable = min_detectable_hit_rate(break_even_p, n_int)
    measurable = bool(assumed_hit_rate > p_detectable)
    return {
        "p_detectable": p_detectable,
        "band_width_pp": 100.0 * wald_half_width(n_int),
        "margin_pp": 100.0 * (assumed_hit_rate - p_detectable),
        "measurable": measurable,
        "verdict": "MIERZALNA" if measurable else "NIEMIERZALNA",
    }


# --- statystyki zwrotu per transakcja (R9: dwa warunki werdyktu) ---


def build_summary(trades: pd.DataFrame, unfilled=()) -> dict:
    """
    Słownik w kształcie `checkpoint_lib.summarize_result` alpha, z samych transakcji —
    wejście `summarize_trade_returns` bez silnika alpha.
    """
    return {
        "backtest": {"trades": trades, "unfilled": list(unfilled)},
        "edge_per_regime": summarize_edge_by_regime(trades),
        "pooled_per_regime": summarize_pooled_by_regime(trades),
    }


def summarize_trade_returns(summary: dict) -> dict:
    """
    Statystyki zwrotu netto PER TRANSAKCJA (ułamek nominału wejścia) do werdyktu R9:
    r̄, se, t, t_neff (N_eff ≤ n) obok trafności p z ci_low i progu uogólnionego
    p* = (L̄ + C) / (W̄ + L̄) (przy wypłatach asymetrycznych `break_even_p` to tylko diagnostyka).

    `summary` — z `build_summary` albo z alpha `summarize_result`. Wymaga jednej grupy reżimu
    (przy dwóch reżimach liczby pooled nie mają jednego progu) — inaczej ValueError.
    """
    edge = summary["edge_per_regime"]
    if len(edge) != 1:
        raise ValueError(
            f"summarize_trade_returns oczekuje jednej grupy reżimu, dostałem {len(edge)}"
        )
    res = summary["backtest"]
    trades = res["trades"]
    real = trades.loc[~trades["kill_switch_active"]].copy()
    notional = real["position_size"] * real["entry_price"]
    real["gross_ret"] = real["gross_pnl"] / notional
    real["net_ret"] = real["net_pnl"] / notional
    real["cost_ret"] = real["cost"] / notional
    e = edge.iloc[0]
    pooled = summary["pooled_per_regime"].iloc[0]
    n = len(real)
    r = real["net_ret"]
    se = float(r.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    t = float(r.mean() / se) if se and se > 0 else float("nan")
    # N_eff ≤ n: ujemna autokorelacja dawałaby N_eff > n i |t_neff| > |t| (zasada R10).
    n_eff = min(float(effective_sample_size(r)["n_eff"]), float(n)) if n > 1 else float("nan")
    t_neff = float(t * np.sqrt(n_eff / n)) if n > 1 else float("nan")
    wins = real["gross_ret"] > 0
    w_mean = float(real.loc[wins, "gross_ret"].mean()) if wins.any() else float("nan")
    l_mean = float(-real.loc[~wins, "gross_ret"].mean()) if (~wins).any() else float("nan")
    c_mean = float(real["cost_ret"].mean()) if n else float("nan")
    p_star = (l_mean + c_mean) / (w_mean + l_mean) if n and (w_mean + l_mean) > 0 else float("nan")
    return {
        "n": n,
        "n_unfilled": len(res.get("unfilled", ())),
        "n_suppressed": int(trades["kill_switch_active"].sum()),
        "p": float(e["hit_rate"]),
        "ci_low": float(e["ci_low"]),
        "ci_high": float(e["ci_high"]),
        "be_symmetric": float(e["break_even_p"]),
        "p_star": p_star,
        "w_mean": w_mean,
        "l_mean": l_mean,
        "cost": c_mean,
        "r_mean": float(r.mean()) if n else float("nan"),
        "r_median": float(r.median()) if n else float("nan"),
        "r_std": float(r.std(ddof=1)) if n > 1 else float("nan"),
        "r_p5": float(r.quantile(0.05)) if n else float("nan"),
        "r_p95": float(r.quantile(0.95)) if n else float("nan"),
        "se": se,
        "t": t,
        "n_eff": n_eff,
        "t_neff": t_neff,
        "t_equity": float(pooled["t_stat"]),
        "t_neff_equity": float(pooled["t_stat_neff"]),
        "edge": edge,
        "pooled": summary["pooled_per_regime"],
        "classification": summary.get("classification"),
        "real": real,
    }
