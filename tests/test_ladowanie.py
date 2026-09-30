"""Jedna funkcja ładująca z filtrem `data.min_start` (zasada R16)."""

from __future__ import annotations

import pandas as pd
import pytest

from dane.ladowanie import min_start, wczytaj_swiece


def _plik(tmp_path, suffix: str):
    ts = pd.date_range("2020-12-30", periods=6, freq="D", tz="UTC")
    df = pd.DataFrame({"timestamp": ts[::-1], "close": range(6)})
    p = tmp_path / f"x{suffix}"
    df.to_parquet(p) if suffix == ".parquet" else df.to_csv(p, index=False)
    return p


def test_min_start_z_konfiguracji():
    assert min_start() == pd.Timestamp("2021-01-01", tz="UTC")


@pytest.mark.parametrize("suffix", [".parquet", ".csv"])
def test_obcina_przed_2021_i_sortuje(tmp_path, suffix):
    df = wczytaj_swiece(_plik(tmp_path, suffix))
    assert df["timestamp"].min() == pd.Timestamp("2021-01-01", tz="UTC")
    assert df["timestamp"].is_monotonic_increasing
    assert len(df) == 4
    assert list(df.index) == [0, 1, 2, 3]


def test_brak_min_start_to_blad(tmp_path):
    cfg = tmp_path / "settings.yaml"
    cfg.write_text("data:\n  alpha_repo: '../alpha'\n", encoding="utf-8")
    with pytest.raises(ValueError, match="min_start"):
        wczytaj_swiece(_plik(tmp_path, ".csv"), settings_path=cfg)


def test_zly_format_i_brak_kolumny(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("a")
    with pytest.raises(ValueError):
        wczytaj_swiece(p)
    q = tmp_path / "y.csv"
    pd.DataFrame({"t": [1]}).to_csv(q, index=False)
    with pytest.raises(ValueError, match="timestamp"):
        wczytaj_swiece(q)
