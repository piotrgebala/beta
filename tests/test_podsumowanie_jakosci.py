"""Podsumowanie jakości (002) na małym manifeście i plikach testowych."""

from __future__ import annotations

import pandas as pd

from dane import podsumowanie_jakosci as pj


def _df(vols: list[float]) -> pd.DataFrame:
    ts = pd.date_range("2024-01-01", periods=len(vols), freq="1D", tz="UTC")
    return pd.DataFrame({"timestamp": ts, "volume": vols})


def test_martwy_ogon():
    assert pj.martwy_ogon(_df([5, 0, 3, 0, 0])) == {
        "dni_martwe_na_koncu": 2,
        "martwe_od": "2024-01-04",
        "dni_bez_obrotu": 3,
    }
    assert pj.martwy_ogon(_df([5, 6]))["martwe_od"] is None
    assert pj.martwy_ogon(_df([0, 0]))["dni_martwe_na_koncu"] == 2


def test_raport(tmp_path):
    (tmp_path / "1d").mkdir()
    _df([1, 1, 0]).to_parquet(tmp_path / "1d" / "AAAUSDT.parquet")
    _df([1, 1, 1]).to_parquet(tmp_path / "1d" / "BBBUSDT.parquet")
    q = {
        "wiersze": 3,
        "dziury": 1,
        "brakujace_interwaly": 2,
        "najwieksza_dziura": "0 days 00:15:00",
    }
    manifest = {
        "pliki": [{}, {}],
        "wersja_skryptu": "abcdef123",
        "od": "2021-01",
        "do": "2026-09",
        "kontrola_pozytywna_btc_2021_05_19": {"ok": True},
        "jakosc": {"AAAUSDT/5m": q, "AAAUSDT/1d": {"wiersze": 3}, "BBBUSDT/1d": {"wiersze": 3}},
    }
    txt = "\n".join(pj.raport(manifest, tmp_path / "1d"))
    assert "Błędy pobierania: 0" in txt and "abcdef1" in txt
    assert "1 z 2 symboli" in txt and "AAAUSDT" in txt
