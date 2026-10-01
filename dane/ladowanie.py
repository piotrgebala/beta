"""
ladowanie.py — JEDNA funkcja ładująca dane rynkowe (zasada R16): każdy odczyt świec w beta przechodzi
przez `wczytaj_swiece`, która obcina wszystko sprzed `data.min_start` z `config/settings.yaml`.

Wzór: `alpha/backtest/checkpoint_lib.fetch_window` (zasada 20 alpha) — brak `min_start` w konfiguracji
to błąd głośny, nie ciche „całe dane”. Funkcja nie pobiera niczego z sieci: czyta plik lokalny
(parquet albo csv) z kolumną `timestamp`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / "config" / "settings.yaml"


def min_start(settings_path: Path = SETTINGS) -> pd.Timestamp:
    """Data graniczna `data.min_start` jako Timestamp UTC; brak klucza → ValueError."""
    cfg = yaml.safe_load(Path(settings_path).read_text(encoding="utf-8")) or {}
    data_cfg = cfg.get("data") or {}
    if "min_start" not in data_cfg:
        raise ValueError("config bez `data.min_start` — zasada R16 wymaga jawnej daty granicznej")
    ts = pd.Timestamp(data_cfg["min_start"])
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def wczytaj_swiece(path: str | Path, settings_path: Path = SETTINGS) -> pd.DataFrame:
    """
    Świece z pliku `path` (.parquet / .csv) od `data.min_start` włącznie, posortowane po czasie,
    z `timestamp` w UTC i indeksem 0..n−1. Duplikatów ani dziur NIE poprawia (raport jakości
    danych jest osobnym krokiem — bez cichych poprawek).
    """
    path = Path(path)
    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    elif path.suffix == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(f"nieobsługiwany format pliku: {path.suffix!r} (parquet albo csv)")
    if "timestamp" not in df.columns:
        raise ValueError(f"{path.name}: brak kolumny `timestamp`")
    ts = pd.to_datetime(df["timestamp"], utc=True)
    out = df.assign(timestamp=ts).loc[ts >= min_start(settings_path)]
    return out.sort_values("timestamp", kind="stable").reset_index(drop=True)
