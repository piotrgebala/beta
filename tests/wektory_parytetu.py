"""
Wektory testowe parytetu przyrządu beta ↔ alpha (zasada 24).

Każdy przypadek: (klucz, nazwa funkcji, budowniczy argumentów). Budowniczy dostaje `lib(nazwa)` —
funkcję z TEJ strony, po której liczymy (alpha albo beta) — żeby wejścia złożone (np. `summary`
dla `summarize_trade_returns`) były budowane kodem tej samej strony. Wartości oczekiwane liczy kod
alpha: `python -m tests.generuj_parytet_alpha` → `tests/fixtures/parytet_alpha.json`.
"""

from __future__ import annotations

import contextlib
import io
import math
import tempfile
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

# funkcja → (moduł alpha, moduł beta)
FUNKCJE: dict[str, tuple[str, str]] = {
    "effective_sample_size": ("agents.labeling", "miara.neff"),
    "summarize_pnl": ("backtest.carry_hedged", "miara.neff"),
    "compute_trade_returns": ("backtest.metrics", "miara.metryki"),
    "compute_t_stat": ("backtest.metrics", "miara.metryki"),
    "summarize_pooled_by_regime": ("backtest.metrics", "miara.metryki"),
    "break_even_hit_rate": ("backtest.metrics", "miara.metryki"),
    "compute_hit_rate": ("backtest.metrics", "miara.metryki"),
    "summarize_edge_by_regime": ("backtest.metrics", "miara.metryki"),
    "observed_wald_ci": ("backtest.metrics", "miara.metryki"),
    "wald_half_width": ("backtest.metrics", "miara.metryki"),
    "min_detectable_hit_rate": ("backtest.metrics", "miara.metryki"),
    "required_trades": ("backtest.metrics", "miara.metryki"),
    "expected_trades": ("backtest.metrics", "miara.metryki"),
    "measurability_report": ("backtest.metrics", "miara.metryki"),
    "summarize_trade_returns": ("backtest.checkpoint_lib", "miara.metryki"),
    "expected_max_t": ("backtest.dsr", "miara.dsr"),
    "expected_max_sr": ("backtest.dsr", "miara.dsr"),
    "deflated_sharpe": ("backtest.dsr", "miara.dsr"),
    "required_t": ("backtest.dsr", "miara.dsr"),
    "min_annual_sr": ("backtest.dsr", "miara.dsr"),
    "load_registry": ("backtest.dsr", "miara.dsr"),
    "n_program": ("backtest.dsr", "miara.dsr"),
    "n_warianty": ("backtest.dsr", "miara.dsr"),
    "registry_errors": ("backtest.dsr", "miara.dsr"),
    "threshold_rows": ("backtest.dsr", "miara.dsr"),
    "report": ("backtest.dsr", "miara.dsr"),
    "main": ("backtest.dsr", "miara.dsr"),
    "synthetic_returns": ("backtest.negative_control", "miara.kontrola_negatywna"),
    "synthetic_ohlc": ("backtest.negative_control", "miara.kontrola_negatywna"),
    "all_members": ("backtest.negative_control", "miara.kontrola_negatywna"),
    "autocorr": ("backtest.negative_control", "miara.kontrola_negatywna"),
    "excess_kurtosis": ("backtest.negative_control", "miara.kontrola_negatywna"),
}

# funkcje, których wynik porównujemy po wydruku (stdout), a nie po wartości zwracanej
PO_WYDRUKU = {"main"}

NAN = float("nan")


def _szereg(kind: str) -> pd.Series:
    rng = np.random.default_rng(12345)
    if kind == "iid":
        return pd.Series(rng.standard_normal(400) * 0.01 + 0.0005)
    if kind == "ar_dodatni":
        x = np.zeros(400)
        e = rng.standard_normal(400) * 0.01
        for t in range(1, 400):
            x[t] = 0.6 * x[t - 1] + e[t]
        return pd.Series(x + 0.0003)
    if kind == "ar_ujemny":  # suma autokorelacji < −0,5 → mianownik ≤ 0
        return pd.Series(np.tile([0.01, -0.01], 100) + rng.standard_normal(200) * 1e-4)
    if kind == "z_nan":
        x = pd.Series(rng.standard_normal(60) * 0.02)
        x.iloc[[0, 5, 17]] = np.nan
        return x
    if kind == "krotki":
        return pd.Series([0.01, -0.02, 0.005, 0.0, 0.03])
    if kind == "stala":
        return pd.Series([0.01] * 12)
    if kind == "jeden":
        return pd.Series([0.01])
    raise ValueError(kind)


def _transakcje(n: int, regimes=("trend", "range"), seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    entry = 100.0 * np.exp(rng.standard_normal(n) * 0.1)
    direction = rng.choice([-1.0, 1.0], n)
    move = rng.standard_normal(n) * 0.02 + 0.001
    exit_price = entry * (1.0 + move)
    size = rng.uniform(0.5, 2.0, n)
    gross = direction * (exit_price - entry) * size
    cost = 0.0009 * entry * size
    kill = rng.uniform(size=n) < 0.05
    gross = np.where(kill, 0.0, gross)
    cost = np.where(kill, 0.0, cost)
    size = np.where(kill, 0.0, size)
    net = gross - cost
    equity = 10_000.0 + np.cumsum(net) - net  # kapitał PRZED transakcją
    reason = rng.choice(["tp", "sl", "timeout"], n, p=[0.25, 0.25, 0.5])
    return pd.DataFrame(
        {
            "regime": np.array(regimes)[np.arange(n) % len(regimes)],
            "kill_switch_active": kill,
            "entry_price": entry,
            "exit_price": exit_price,
            "position_size": size,
            "gross_pnl": gross,
            "cost": cost,
            "net_pnl": gross - cost,
            "equity_before": equity,
            "exit_reason": reason,
        }
    )


def _summary(lib, trades: pd.DataFrame) -> dict:
    return {
        "backtest": {"trades": trades, "unfilled": [1, 2, 3]},
        "edge_per_regime": lib("summarize_edge_by_regime")(trades),
        "pooled_per_regime": lib("summarize_pooled_by_regime")(trades),
        "classification": None,
    }


REJESTR_CSV = (
    "nr,data,runda,katalog,baza,rodzaj,odczyt_programu,wariantow,uwagi\n"
    '1,2026-09-23,A1,2026-09-23_a1-x,krypto-2021-2026,werdykt,tak,3,"opis"\n'
    '2,2026-09-24,B1,2026-09-24_b1-y,krypto-2021-2026,opis-z-wynikiem,tak,0,"opis, z przecinkiem"\n'
    "3,2026-09-24,C1,2026-09-24_c1-z,inna,bez-wyniku,nie,0,opis\n"
    "4,2026-09-25,D1,2026-09-25_d1-w,tradfi-1990-2026,werdykt,tak,5,opis\n"
)

REJESTR_BLEDNY = [
    # nr nieciągły, data malejąca, katalog bez daty, baza/rodzaj spoza słownika, warianty nie-liczba
    {
        "nr": "1",
        "data": "2026-09-25",
        "runda": "X",
        "katalog": "2026-09-25_x",
        "baza": "krypto-2021-2026",
        "rodzaj": "werdykt",
        "odczyt_programu": "tak",
        "wariantow": "2",
        "uwagi": "ok",
    },
    {
        "nr": "3",
        "data": "2026-09-24",
        "runda": " ",
        "katalog": "zly-katalog",
        "baza": "marsjańska",
        "rodzaj": "bez-wyniku",
        "odczyt_programu": "tak",
        "wariantow": "1",
        "uwagi": "",
    },
    {
        "nr": "3",
        "data": "2026-09-26",
        "runda": "Y",
        "katalog": "2026-09-26_y",
        "baza": "krypto-2021-2026",
        "rodzaj": "werdykt",
        "odczyt_programu": "nie",
        "wariantow": "4",
        "uwagi": "ok",
    },
    {
        "nr": "4",
        "data": "2026-09-26",
        "runda": "Z",
        "katalog": "2026-09-26_y",
        "baza": "inna",
        "rodzaj": "cos",
        "odczyt_programu": "moze",
        "wariantow": "x",
        "uwagi": "ok",
    },
]


def _rejestr_plik() -> str:
    d = Path(tempfile.mkdtemp())
    p = d / "odczyty_historii.csv"
    p.write_text("﻿" + REJESTR_CSV, encoding="utf-8")  # z BOM, jak z Excela
    return str(p)


def _rejestr_wiersze(lib) -> list[dict]:
    return lib("load_registry")(Path(_rejestr_plik()))


def przypadki():
    """Lista (klucz, funkcja, budowniczy(lib) → (args, kwargs))."""
    P = []

    def add(key, fn, build):
        P.append((key, fn, build))

    for kind in ("iid", "ar_dodatni", "ar_ujemny", "z_nan", "krotki", "stala", "jeden"):
        add(f"ess_{kind}", "effective_sample_size", lambda lib, k=kind: ((_szereg(k),), {}))
        add(f"pnl_{kind}", "summarize_pnl", lambda lib, k=kind: ((_szereg(k),), {}))
        add(f"t_{kind}", "compute_t_stat", lambda lib, k=kind: ((_szereg(k),), {}))
    add("ess_lag5", "effective_sample_size", lambda lib: ((_szereg("ar_dodatni"),), {"max_lag": 5}))
    add(
        "pnl_dzienny",
        "summarize_pnl",
        lambda lib: ((_szereg("iid"),), {"periods_per_year": 365, "capital_per_notional": 1.0}),
    )

    add("ret_mix", "compute_trade_returns", lambda lib: ((_transakcje(50),), {}))
    for n in (0, 10, 500):
        add(f"hit_{n}", "compute_hit_rate", lambda lib, n=n: ((_transakcje(n),), {}))
        add(f"pooled_{n}", "summarize_pooled_by_regime", lambda lib, n=n: ((_transakcje(n),), {}))
        add(f"edge_{n}", "summarize_edge_by_regime", lambda lib, n=n: ((_transakcje(n),), {}))
    add(
        "edge_bez_exit_reason",
        "summarize_edge_by_regime",
        lambda lib: ((_transakcje(80).drop(columns="exit_reason"),), {}),
    )
    for n in (30, 700):
        add(
            f"str_{n}",
            "summarize_trade_returns",
            lambda lib, n=n: ((_summary(lib, _transakcje(n, regimes=("all",))),), {}),
        )

    for c, b in (
        (0.001, 0.02),
        (0.0, 0.01),
        (0.001, 0.0),
        (0.001, -1.0),
        (None, 0.01),
        (NAN, 0.01),
    ):
        add(f"be_{c}_{b}", "break_even_hit_rate", lambda lib, c=c, b=b: ((c, b), {}))
    for h, n in ((0, 0), (5, 10), (523, 1000), (1000, 1000), (0, 7)):
        add(f"owci_{h}_{n}", "observed_wald_ci", lambda lib, h=h, n=n: ((h, n), {}))
    add("owci_z", "observed_wald_ci", lambda lib: ((60, 100), {"z": 2.575829}))
    for n in (-1, 0, 1, 98, 345, 1037, 7687):
        add(f"whw_{n}", "wald_half_width", lambda lib, n=n: ((n,), {}))
        add(f"mdh_{n}", "min_detectable_hit_rate", lambda lib, n=n: ((0.5225, n), {}))
    add("mdh_nan", "min_detectable_hit_rate", lambda lib: ((NAN, 100), {}))
    for p1, p0 in ((0.55, 0.5), (0.5, 0.5), (0.45, 0.5), (0.6, 0.52), (1.0, 0.5), (0.5, NAN)):
        add(f"rt_{p1}_{p0}", "required_trades", lambda lib, a=p1, b=p0: ((a, b), {}))
    add(
        "rt_z",
        "required_trades",
        lambda lib: ((0.56, 0.5), {"z_alpha": 2.575829, "z_power": 1.2816}),
    )
    for args in (
        (10_000, 0.6648),
        (10_000, 0.6648, 0.5),
        (0, 0.1),
        (-1, 0.1),
        (100, 1.2),
        (100, NAN),
    ):
        add(f"et_{args}", "expected_trades", lambda lib, a=args: (a, {}))
    for args in (
        (0.58, 0.5225, 345),
        (0.53, 0.5225, 345),
        (0.56, 0.5, 7687.4),
        (0.56, 0.5, 0.4),
        (1.0, 0.5, 100),
        (0.56, NAN, 100),
        (0.56, 0.5, NAN),
    ):
        add(f"mr_{args}", "measurability_report", lambda lib, a=args: (a, {}))

    for n in (0, 1, 2, 10, 28, 41, 53, 1000):
        add(f"emt_{n}", "expected_max_t", lambda lib, n=n: ((n,), {}))
    add("emsr", "expected_max_sr", lambda lib: ((41, 1.0 / 2000), {}))
    add("dsr_norm", "deflated_sharpe", lambda lib: ((0.08, 0.05, 2000, 0.0, 3.0), {}))
    add("dsr_ogony", "deflated_sharpe", lambda lib: ((0.08, 0.05, 2000, -0.5, 9.0), {}))
    for n in (1, 28, 41, 53):
        for d in (0.5, 0.8, 0.95):
            add(f"rqt_{n}_{d}", "required_t", lambda lib, n=n, d=d: ((n, d), {}))
    add("rqt_nobs", "required_t", lambda lib: ((41, 0.95), {"n_obs": 2000}))
    add(
        "rqt_nobs_ogony",
        "required_t",
        lambda lib: ((41, 0.95), {"n_obs": 2000, "g3": -0.3, "g4": 8.0}),
    )
    add("rqt_nobs_niski", "required_t", lambda lib: ((41, 0.2), {"n_obs": 500}))
    for t in (1.96, 3.84):
        add(f"mas_{t}", "min_annual_sr", lambda lib, t=t: ((t,), {}))
    add("mas_lata", "min_annual_sr", lambda lib: ((3.84, 3.0), {}))

    add("lr", "load_registry", lambda lib: ((Path(_rejestr_plik()),), {}))
    add("np", "n_program", lambda lib: ((_rejestr_wiersze(lib),), {}))
    add("np_do", "n_program", lambda lib: ((_rejestr_wiersze(lib),), {"do_nr": 2}))
    add("nw", "n_warianty", lambda lib: ((_rejestr_wiersze(lib),), {}))
    add("nw_do", "n_warianty", lambda lib: ((_rejestr_wiersze(lib),), {"do_nr": 1}))
    add("re_ok", "registry_errors", lambda lib: ((_rejestr_wiersze(lib),), {}))
    add("re_zle", "registry_errors", lambda lib: ((REJESTR_BLEDNY,), {}))
    add("tr", "threshold_rows", lambda lib: (([1, 41, 53],), {}))
    add("tr_lata", "threshold_rows", lambda lib: (([41],), {"lata": 3.0}))
    add("rep", "report", lambda lib: ((_rejestr_wiersze(lib),), {}))
    add("rep_k", "report", lambda lib: ((_rejestr_wiersze(lib),), {"k": 5, "lata": 4.0}))
    add("main_n", "main", lambda lib: ((["--n", "41", "53"],), {}))
    add("main_rej", "main", lambda lib: ((["--rejestr", _rejestr_plik(), "--k", "3"],), {}))

    add("sr_mala", "synthetic_returns", lambda lib: ((300, 5), {"seed": 1}))
    add(
        "sr_param",
        "synthetic_returns",
        lambda lib: (
            (200, 3),
            {"seed": 9, "df": 5.0, "rho": 0.2, "daily_vol": 0.03, "garch": (0.1, 0.8)},
        ),
    )
    add(
        "ohlc",
        "synthetic_ohlc",
        lambda lib: ((lib("synthetic_returns")(120, 4, seed=5),), {"seed": 5}),
    )

    def _members(lib):
        idx = pd.date_range("2021-01-01", periods=100, freq="D", tz="UTC")
        close = pd.DataFrame(1.0, index=idx, columns=["A", "B"])
        return (close, idx[10], idx[-1]), {}

    add("am", "all_members", _members)
    x = np.sin(np.arange(200) / 3.0) + np.linspace(0, 1, 200)
    for lag in (1, 7):
        add(f"ac_{lag}", "autocorr", lambda lib, lag=lag: ((x,), {"lag": lag}))
    add("ek", "excess_kurtosis", lambda lib: ((np.r_[x, 25.0],), {}))
    return P


# --- serializacja i porównanie ---


def do_json(v):
    """Wynik funkcji → struktura JSON (liczby jako float/int, NaN i inf dozwolone)."""
    if isinstance(v, pd.DataFrame):
        return {
            "__df__": True,
            "columns": [str(c) for c in v.columns],
            "index": [str(i) for i in v.index],
            "data": [[do_json(x) for x in row] for row in v.itertuples(index=False, name=None)],
        }
    if isinstance(v, pd.Series):
        return {
            "__s__": True,
            "index": [str(i) for i in v.index],
            "values": [do_json(x) for x in v],
        }
    if isinstance(v, dict):
        return {str(k): do_json(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, np.ndarray)):
        return [do_json(x) for x in v]
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return float(v)
    if v is None or isinstance(v, str):
        return v
    if isinstance(v, pd.Timestamp):
        return str(v)
    raise TypeError(f"nieobsługiwany typ wyniku: {type(v)}")


def roznice(a, b, tol: float = 1e-12, path: str = "") -> list[str]:
    """Lista rozbieżności między dwiema strukturami JSON (float: |a − b| ≤ tol·max(1, |a|))."""
    if isinstance(a, float) or isinstance(b, float):
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            return [f"{path}: {a!r} vs {b!r}"]
        fa, fb = float(a), float(b)
        if math.isnan(fa) and math.isnan(fb):
            return []
        if math.isinf(fa) or math.isinf(fb):
            return [] if fa == fb else [f"{path}: {fa!r} vs {fb!r}"]
        return [] if abs(fa - fb) <= tol * max(1.0, abs(fa)) else [f"{path}: {fa!r} vs {fb!r}"]
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return [f"{path}: klucze {sorted(set(a) ^ set(b))}"]
        out = []
        for k in a:
            out += roznice(a[k], b[k], tol, f"{path}.{k}")
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: długość {len(a)} vs {len(b)}"]
        out = []
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            out += roznice(x, y, tol, f"{path}[{i}]")
        return out
    return [] if a == b else [f"{path}: {a!r} vs {b!r}"]


def _jeden(lib, fn: str, args, kwargs) -> dict:
    try:
        if fn in PO_WYDRUKU:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                lib(fn)(*args, **kwargs)
            return {"fn": fn, "out": buf.getvalue()}
        return {"fn": fn, "out": do_json(lib(fn)(*args, **kwargs))}
    except Exception as exc:  # noqa: BLE001 — parytet obejmuje też typ błędu
        return {"fn": fn, "out": {"__error__": type(exc).__name__}}


def wykonaj(lib) -> dict:
    """Liczy wszystkie przypadki funkcjami `lib(nazwa)`; wyjątek zapisuje jako {"__error__": typ}."""
    wyniki = {}
    for key, fn, build in przypadki():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            args, kwargs = build(lib)
            wyniki[key] = _jeden(lib, fn, args, kwargs)
    return wyniki
