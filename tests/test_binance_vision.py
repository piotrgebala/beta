"""Zadanie 002 bez sieci: atrapa `fetch` z ZIP-ami w pamięci."""

from __future__ import annotations

import hashlib
import io
import zipfile

import pandas as pd
import pytest

from dane import binance_vision as bv


def _zip(rows: list[list], header: bool) -> bytes:
    lines = [",".join(bv.KOLUMNY)] if header else []
    lines += [",".join(str(x) for x in r) for r in rows]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("x.csv", "\n".join(lines) + "\n")
    return buf.getvalue()


def _swiece(start: str, n: int, tf: str = "1d", price: float = 100.0) -> list[list]:
    ts = pd.date_range(start, periods=n, freq=bv.INTERWAL[tf], tz="UTC")
    out = []
    for i, t in enumerate(ts):
        ms = int(t.value // 1_000_000)
        p = price + i
        out.append([ms, p, p + 2, p - 2, p + 1, 10.0, ms + 1, 1000.0, 5, 4.0, 400.0, 0])
    return out


class Atrapa:
    def __init__(self):
        self.pliki: dict[str, bytes] = {}

    def dodaj(self, url: str, blob: bytes, zla_suma: bool = False):
        self.pliki[url] = blob
        sha = "0" * 64 if zla_suma else hashlib.sha256(blob).hexdigest()
        self.pliki[url + ".CHECKSUM"] = f"{sha}  plik.zip\n".encode()

    def __call__(self, url: str):
        return self.pliki.get(url)


def test_url_i_miesiace():
    assert bv.url_pliku("BTCUSDT", "5m", "2021-01").endswith("BTCUSDT/5m/BTCUSDT-5m-2021-01.zip")
    assert bv.miesiace("2021-11", "2022-02") == ["2021-11", "2021-12", "2022-01", "2022-02"]


@pytest.mark.parametrize("header", [True, False])
def test_parsuj_zip_z_naglowkiem_i_bez(header):
    df = bv.parsuj_zip(_zip(_swiece("2021-01-01", 3), header))
    assert len(df) == 3
    assert df["timestamp"].iloc[0] == pd.Timestamp("2021-01-01", tz="UTC")
    assert df["close"].dtype == float and "ignore" not in df.columns


def test_pobierz_weryfikuje_sume_i_pomija_404():
    f = Atrapa()
    f.dodaj(bv.url_pliku("BTCUSDT", "1d", "2021-01"), _zip(_swiece("2021-01-01", 31), True))
    f.dodaj(bv.url_pliku("BTCUSDT", "1d", "2021-03"), _zip(_swiece("2021-03-01", 31), False))
    df, wpisy = bv.pobierz_symbol("BTCUSDT", "1d", "2021-01", "2021-03", f)
    assert len(df) == 62 and len(wpisy) == 2
    assert df["timestamp"].is_monotonic_increasing
    zla = Atrapa()
    zla.dodaj(bv.url_pliku("BTCUSDT", "1d", "2021-01"), _zip(_swiece("2021-01-01", 3), True), True)
    with pytest.raises(ValueError, match="SHA-256"):
        bv.pobierz_symbol("BTCUSDT", "1d", "2021-01", "2021-01", zla)


def test_raport_jakosci_bez_poprawek():
    rows = _swiece("2021-01-01", 10, tf="5m")
    rows = rows[:3] + rows[5:]  # dziura: 2 brakujące świece
    rows.append(rows[-1])  # duplikat
    rows[0][5] = 0.0  # świeca zerowa (wolumen 0)
    df = bv.parsuj_zip(_zip(rows, False))
    q = bv.raport_jakosci(df, "5m")
    assert q["duplikaty"] == 1
    assert q["dziury"] == 1 and q["brakujace_interwaly"] == 2
    assert q["swiece_zerowe"] == 1
    assert q["wiersze"] == len(rows)  # nic nie usunięto


def test_raport_skok():
    rows = _swiece("2021-01-01", 200)
    for i, r in enumerate(rows):  # szum ±0,1 %, jeden skok ×3
        c = 100.0 * (1.001 if i % 2 else 0.999) * (3.0 if i == 150 else 1.0)
        r[1], r[2], r[3], r[4] = c, c * 1.01, c * 0.99, c
    q = bv.raport_jakosci(bv.parsuj_zip(_zip(rows, False)), "1d")
    assert q["skoki_k_sigma"] == 2  # wejście i wyjście z wartości odstającej
    assert q["niespojne_ohlc"] == 0


def test_kontrola_pozytywna_btc():
    ok = pd.DataFrame(
        {"timestamp": [pd.Timestamp("2021-05-19", tz="UTC")], "low": [30_000.0], "high": [43_000.0]}
    )
    assert bv.kontrola_pozytywna_btc(ok)["ok"]
    assert not bv.kontrola_pozytywna_btc(ok.assign(low=37_000.0))["ok"]
    assert not bv.kontrola_pozytywna_btc(ok.iloc[:0])["ok"]


def test_symbole_z_uniwersum():
    t = pd.Timestamp
    m = {
        t("2020-12-01", tz="UTC"): ["XUSDT"],
        t("2021-01-01", tz="UTC"): ["BTCUSDT", "ETHUSDT"],
        t("2021-02-01", tz="UTC"): ["BTCUSDT", "SOLUSDT"],
    }
    assert bv.symbole_z_uniwersum(m, t("2021-01-01", tz="UTC")) == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def test_uruchom_zapisuje_parquet_i_manifest(tmp_path):
    f = Atrapa()
    rows = _swiece("2020-12-01", 31 + 31)
    f.dodaj(bv.url_pliku("BTCUSDT", "1d", "2021-01"), _zip(rows[31:], True))
    m = bv.uruchom(["BTCUSDT"], ["1d"], "2021-01", tmp_path, f, log=lambda *_: None)
    assert m["od"] == "2021-01"
    assert len(m["pliki"]) == 1 and len(m["pliki"][0]["sha256"]) == 64
    q = m["jakosc"]["BTCUSDT/1d"]
    assert q["wiersze"] == 31 and len(q["parquet_sha256"]) == 64
    assert (tmp_path / "1d" / "BTCUSDT.parquet").is_file()
    assert m["kontrola_pozytywna_btc_2021_05_19"]["ok"] is False  # brak maja w atrapie


def test_uruchom_rownolegle_daje_ten_sam_manifest(tmp_path):
    f = Atrapa()
    for i, sym in enumerate(["BTCUSDT", "ETHUSDT", "SOLUSDT"]):
        for tf in ("1d", "1h"):
            for m, start, n in (("2021-01", "2021-01-01", 31), ("2021-02", "2021-02-01", 28)):
                k = n * (24 if tf == "1h" else 1)
                f.dodaj(
                    bv.url_pliku(sym, tf, m), _zip(_swiece(start, k, tf, 100.0 * (i + 1)), True)
                )
    cisza = lambda *_: None
    sek = bv.uruchom(
        ["BTCUSDT", "ETHUSDT", "SOLUSDT"], ["1d", "1h"], "2021-02", tmp_path / "a", f, cisza
    )
    row = bv.uruchom(
        ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        ["1d", "1h"],
        "2021-02",
        tmp_path / "b",
        f,
        cisza,
        watki=4,
    )
    for m in (sek, row):
        m.pop("utworzono")
    assert sek == row
    assert [(w["symbol"], w["tf"], w["miesiac"]) for w in row["pliki"]][:3] == [
        ("BTCUSDT", "1d", "2021-01"),
        ("BTCUSDT", "1d", "2021-02"),
        ("BTCUSDT", "1h", "2021-01"),
    ]


def test_fetch_http_ponawia_i_404_to_none(monkeypatch):
    import urllib.error

    wywolania = []

    class Odp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"ok"

    def urlopen(url, timeout):
        wywolania.append(url)
        if url.endswith("404"):
            raise urllib.error.HTTPError(url, 404, "nie ma", None, None)
        if len(wywolania) < 3:
            raise TimeoutError("timeout w trakcie odczytu")
        return Odp()

    monkeypatch.setattr(bv.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(bv.time, "sleep", lambda s: None)
    assert bv.fetch_http("https://x/plik.zip") == b"ok" and len(wywolania) == 3
    assert bv.fetch_http("https://x/404") is None
    wywolania.clear()
    monkeypatch.setattr(
        bv.urllib.request,
        "urlopen",
        lambda u, timeout: (_ for _ in ()).throw(ConnectionResetError()),
    )
    with pytest.raises(ConnectionResetError):
        bv.fetch_http("https://x/zawsze-zle", proby=3)
