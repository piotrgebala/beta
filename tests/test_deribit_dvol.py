"""Zadanie 006 bez sieci: atrapa API Deribit ze stronicowaniem od najnowszych."""

from __future__ import annotations

import json
import urllib.parse

import pandas as pd
import pytest

from dane import deribit_dvol as dv

DZIEN = dv.DZIEN_MS


def _ms(d: str) -> int:
    return int(pd.Timestamp(d, tz="UTC").value // 1_000_000)


class AtrapaAPI:
    """Oddaje najnowsze `strona` punktów z [start, end]; continuation = koniec starszej strony."""

    def __init__(self, punkty: dict[str, list[list]], strona: int = 3):
        self.punkty, self.strona, self.wywolania = punkty, strona, []

    def __call__(self, url: str):
        self.wywolania.append(url)
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
        s, e = int(q["start_timestamp"]), int(q["end_timestamp"])
        pts = [p for p in self.punkty.get(q["currency"], []) if s <= p[0] <= e]
        page = pts[-self.strona :]
        cont = page[0][0] - DZIEN if len(pts) > len(page) else None
        return json.dumps({"result": {"data": page, "continuation": cont}}).encode()


def _seria(od: str, n: int, poziom: float = 60.0) -> list[list]:
    return [
        [_ms(od) + i * DZIEN, poziom + i, poziom + i + 3, poziom + i - 2, poziom + i + 1]
        for i in range(n)
    ]


def test_url_strony():
    u = dv.url_strony("BTC", 1, 2)
    assert u.startswith(dv.API_URL) and "currency=BTC" in u and "resolution=1D" in u


def test_stronicowanie_sklada_cala_historie():
    api = AtrapaAPI({"BTC": _seria("2021-03-24", 10)}, strona=3)
    df, wpisy = dv.pobierz_dvol("BTC", _ms("2021-01-01"), _ms("2021-12-31"), api)
    assert len(df) == 10 and len(wpisy) == 4 == len(api.wywolania)
    assert df["timestamp"].is_monotonic_increasing
    assert df["timestamp"].iloc[0] == pd.Timestamp("2021-03-24", tz="UTC")
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close"]
    assert all(len(w["sha256"]) == 64 for w in wpisy)


def test_blad_api_jest_glosny():
    with pytest.raises(ValueError, match="błąd API"):
        dv.pobierz_dvol("BTC", 0, 1, lambda u: b'{"error": {"code": 10001}}')


def test_raport_bez_poprawek():
    s = _seria("2021-03-24", 6)
    s = s[:2] + s[3:] + [s[0]]  # dziura 1 dzień i duplikat
    s[1][2] = 999.0  # high poza zakresem
    df = pd.DataFrame(s, columns=["ts", *dv.KOLUMNY])
    df.insert(0, "timestamp", pd.to_datetime(df.pop("ts"), unit="ms", utc=True))
    q = dv.raport_jakosci(df)
    assert q["wiersze"] == 6 and q["duplikaty"] == 1
    assert q["dziury"] == 1 and q["brakujace_dni"] == 1
    assert q["poza_zakresem"] == 1 and q["niespojne_ohlc"] == 0


def test_kontrola_pozytywna():
    df = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2021-05-19", tz="UTC")],
            "open": [90.0],
            "high": [160.0],
            "low": [85.0],
            "close": [120.0],
        }
    )
    assert dv.kontrola_pozytywna_btc(df)["ok"] is True
    assert dv.kontrola_pozytywna_btc(df.assign(high=95.0))["ok"] is False
    assert dv.kontrola_pozytywna_btc(df.iloc[:0])["ok"] is False


def test_uruchom_tylko_pelne_dni(tmp_path):
    api = AtrapaAPI({"BTC": _seria("2021-05-10", 12, 90.0), "ETH": _seria("2021-05-10", 12)})
    m = dv.uruchom(
        ["BTC", "ETH"], pd.Timestamp("2021-05-20", tz="UTC"), tmp_path, api, lambda *_: None
    )
    q = m["jakosc"]["BTC"]
    assert q["do"] == "2021-05-19 00:00:00+00:00" and q["wiersze"] == 10  # bez dnia 2021-05-20
    assert (tmp_path / "ETH_1d.parquet").is_file() and len(q["parquet_sha256"]) == 64
    assert m["kontrola_pozytywna_btc_2021_05_19"] == {"ok": True, "high": 102.0, "close": 100.0}
    assert m["do_wylacznie"] == "2021-05-20" and m["od"] == "2021-01-01"
