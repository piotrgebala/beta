"""Zadanie 002 bez sieci: atrapa `fetch` z ZIP-ami w pamięci."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

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


def test_url_koduje_symbol_spoza_ascii():
    u = bv.url_pliku("币安人生USDT", "1d", "2025-11")
    assert u.isascii() and "%E5%B8%81" in u and u.endswith("USDT-1d-2025-11.zip")
    assert bv.url_pliku("BTCUSDT", "1d", "2021-01").endswith("BTCUSDT/1d/BTCUSDT-1d-2021-01.zip")


def test_blad_jednej_pary_trafia_do_manifestu_a_reszta_sie_pobiera(tmp_path):
    f = Atrapa()
    f.dodaj(bv.url_pliku("BTCUSDT", "1d", "2021-01"), _zip(_swiece("2021-01-01", 31), True))
    f.dodaj(bv.url_pliku("ETHUSDT", "1d", "2021-01"), _zip(_swiece("2021-01-01", 31), True), True)
    m = bv.uruchom(["BTCUSDT", "ETHUSDT"], ["1d"], "2021-01", tmp_path, f, lambda *_: None, watki=2)
    assert m["jakosc"]["BTCUSDT/1d"]["wiersze"] == 31 and "ETHUSDT/1d" not in m["jakosc"]
    assert m["bledy"] == [{"para": "ETHUSDT/1d", "blad": m["bledy"][0]["blad"]}]
    assert "SHA-256" in m["bledy"][0]["blad"]


# --- zadanie 015: tryb przyrostowy i zapis atomowy ---

SYMBOLE = ["BTCUSDT", "ETHUSDT"]
TFS = ["1d", "1h"]
MIESIACE = ["2021-01", "2021-02", "2021-03"]


def _cisza(*_):
    return None


class Licznik(Atrapa):
    """Atrapa, która liczy pobrania ZIP-ów (bez .CHECKSUM)."""

    def __init__(self):
        super().__init__()
        self.zipy: list[str] = []

    def __call__(self, url: str):
        if url.endswith(".zip"):
            self.zipy.append(url)
        return super().__call__(url)


def _archiwum(symbole=SYMBOLE, tfs=TFS, miesiace=MIESIACE, pomin=()) -> Licznik:
    f = Licznik()
    for i, sym in enumerate(symbole):
        for tf in tfs:
            for m in miesiace:
                if (sym, m) in pomin:
                    continue
                okres = pd.Period(m, freq="M")
                n = okres.days_in_month * (24 if tf == "1h" else 1)
                rows = _swiece(f"{m}-01", n, tf, 100.0 * (i + 1) + okres.month)
                f.dodaj(bv.url_pliku(sym, tf, m), _zip(rows, True))
    return f


def _pliki(katalog) -> dict[str, tuple[bytes, int]]:
    return {
        str(p.relative_to(katalog)): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in sorted(katalog.rglob("*"))
        if p.is_file()
    }


def test_drugi_bieg_przyrostowy_nic_nie_pobiera_i_nic_nie_zmienia(tmp_path):
    f = _archiwum()
    pelny = bv.uruchom(SYMBOLE, TFS, "2021-03", tmp_path, f, _cisza)
    przed = _pliki(tmp_path)
    f.zipy.clear()
    m = bv.uruchom(SYMBOLE, TFS, "2021-03", tmp_path, f, _cisza, poprzedni=pelny)
    assert m is pelny  # nic nowego = ten sam obiekt, main nie przepisuje manifestu
    assert f.zipy == []  # wszystkie pary kończą się na --koniec: zero pobrań
    assert _pliki(tmp_path) == przed  # bajty i mtime parquetów bez zmian
    # nowy miesiąc jeszcze nieopublikowany (404) — jedno zapytanie na parę, nadal bez zmian
    m = bv.uruchom(SYMBOLE, TFS, "2021-04", tmp_path, f, _cisza, poprzedni=pelny)
    assert m is pelny and len(f.zipy) == len(SYMBOLE) * len(TFS)
    assert all(u.endswith("-2021-04.zip") for u in f.zipy)
    assert _pliki(tmp_path) == przed


def test_main_przyrostowo_nie_przepisuje_manifestu_gdy_nic_nowego(tmp_path, monkeypatch):
    f = _archiwum()
    pelny = bv.uruchom(SYMBOLE, TFS, "2021-03", tmp_path / "d", f, _cisza)
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(pelny, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    przed = (mpath.read_bytes(), mpath.stat().st_mtime_ns)
    oryginalny = bv.uruchom
    monkeypatch.setattr(bv, "uruchom", lambda *a, **k: oryginalny(*a, fetch=f, log=_cisza, **k))
    argv = ["--tf", *TFS, "--symbole", *SYMBOLE, "--koniec", "2021-03", "--przyrostowo"]
    bv.main([*argv, "--out", str(tmp_path / "d"), "--manifest", str(mpath)])
    assert (mpath.read_bytes(), mpath.stat().st_mtime_ns) == przed
    with pytest.raises(SystemExit, match="nie mogę odczytać manifestu"):
        bv.main([*argv, "--out", str(tmp_path / "d"), "--manifest", str(tmp_path / "brak.json")])


def test_pelny_do_m_minus_1_plus_przyrostowy_do_m_rowna_sie_pelnemu_do_m(tmp_path):
    f = _archiwum(pomin={("ETHUSDT", "2021-01")})  # ETH wchodzi w lutym
    ref = bv.uruchom(SYMBOLE, TFS, "2021-03", tmp_path / "ref", f, _cisza)
    stary = bv.uruchom(SYMBOLE, TFS, "2021-02", tmp_path / "inc", f, _cisza)
    f.zipy.clear()
    inc = bv.uruchom(SYMBOLE, TFS, "2021-03", tmp_path / "inc", f, _cisza, watki=3, poprzedni=stary)
    assert sorted(f.zipy) == sorted(bv.url_pliku(s, t, "2021-03") for s in SYMBOLE for t in TFS)
    assert inc["pliki"] == ref["pliki"]
    assert inc["jakosc"] == ref["jakosc"]  # w tym parquet_sha256: to_parquet jest deterministyczny
    assert inc["do"] == "2021-03" and "bledy" not in inc
    for tf in TFS:
        for sym in SYMBOLE:
            a = (tmp_path / "ref" / tf / f"{sym}.parquet").read_bytes()
            b = (tmp_path / "inc" / tf / f"{sym}.parquet").read_bytes()
            assert a == b
    assert not list((tmp_path / "inc").rglob("*.tmp"))


def test_niezgodny_sha_parquetu_to_blad_pary_a_plik_nietkniety(tmp_path):
    f = _archiwum()
    stary = bv.uruchom(SYMBOLE, TFS, "2021-02", tmp_path, f, _cisza)
    zly = tmp_path / "1d" / "BTCUSDT.parquet"
    zly.write_bytes(zly.read_bytes() + b"x")
    przed = zly.read_bytes()
    f.zipy.clear()
    m = bv.uruchom(SYMBOLE, TFS, "2021-03", tmp_path, f, _cisza, poprzedni=stary)
    assert [b["para"] for b in m["bledy"]] == ["BTCUSDT/1d"]
    assert "SHA-256" in m["bledy"][0]["blad"]
    assert zly.read_bytes() == przed
    assert not any("BTCUSDT/1d/" in u for u in f.zipy)  # nic nie pobrano po cichu
    # stare wpisy i jakość pary zostają, pozostałe pary dostały marzec
    assert m["jakosc"]["BTCUSDT/1d"] == stary["jakosc"]["BTCUSDT/1d"]
    btc = [w["miesiac"] for w in m["pliki"] if w["symbol"] == "BTCUSDT" and w["tf"] == "1d"]
    assert btc == ["2021-01", "2021-02"]
    assert m["jakosc"]["ETHUSDT/1d"]["do"].startswith("2021-03-31")
    kontrola = "kontrola_pozytywna_btc_2021_05_19"  # BTC/1d bez zmian: kontrola przeniesiona
    assert m[kontrola] == stary[kontrola]
    # brak pliku opisanego w manifeście — też błąd pary
    zly.unlink()
    m = bv.uruchom(["BTCUSDT"], ["1d"], "2021-03", tmp_path, f, _cisza, poprzedni=stary)
    assert "brak pliku parquet" in m["bledy"][0]["blad"] and not zly.exists()


def test_nachodzace_znaczniki_czasu_to_blad_pary(tmp_path):
    f = _archiwum(symbole=["BTCUSDT"], tfs=["1d"])
    stary = bv.uruchom(["BTCUSDT"], ["1d"], "2021-02", tmp_path, f, _cisza)
    sciezka = tmp_path / "1d" / "BTCUSDT.parquet"
    przed = sciezka.read_bytes()
    # marcowy plik zaczyna się od 2021-02-28 (nachodzi na ostatnią istniejącą świecę)
    f.dodaj(bv.url_pliku("BTCUSDT", "1d", "2021-03"), _zip(_swiece("2021-02-28", 32), True))
    m = bv.uruchom(["BTCUSDT"], ["1d"], "2021-03", tmp_path, f, _cisza, poprzedni=stary)
    assert m["bledy"][0]["para"] == "BTCUSDT/1d" and "nachodzą" in m["bledy"][0]["blad"]
    assert sciezka.read_bytes() == przed
    assert m["pliki"] == stary["pliki"]


def test_wyjatek_w_trakcie_zapisu_zostawia_stary_plik(tmp_path, monkeypatch):
    f = _archiwum(symbole=["BTCUSDT"], tfs=["1d"])
    stary = bv.uruchom(["BTCUSDT"], ["1d"], "2021-02", tmp_path, f, _cisza)
    sciezka = tmp_path / "1d" / "BTCUSDT.parquet"
    przed = sciezka.read_bytes()
    oryginalny = pd.DataFrame.to_parquet

    def polowa(self, path, *a, **k):
        oryginalny(self, path, *a, **k)
        dane = Path(path).read_bytes()
        Path(path).write_bytes(dane[: len(dane) // 2])
        raise OSError("dysk pełny (symulacja)")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", polowa)
    for poprzedni in (stary, None):  # przyrostowo i pełny bieg
        m = bv.uruchom(["BTCUSDT"], ["1d"], "2021-03", tmp_path, f, _cisza, poprzedni=poprzedni)
        assert "dysk pełny" in m["bledy"][0]["blad"]
        assert sciezka.read_bytes() == przed
        assert sorted(p.name for p in (tmp_path / "1d").iterdir()) == ["BTCUSDT.parquet"]


def test_zapisz_atomowo_przy_przerwaniu_usuwa_plik_tymczasowy(tmp_path):
    cel = tmp_path / "m.json"
    bv.zapisz_tekst_atomowo(cel, "stary\n")

    def przerwany(tmp):
        tmp.write_text("pół", encoding="utf-8")
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        bv.zapisz_atomowo(cel, przerwany)
    assert cel.read_text(encoding="utf-8") == "stary\n"
    assert [p.name for p in tmp_path.iterdir()] == ["m.json"]


def test_para_bez_wpisow_pobiera_wszystko(tmp_path):
    f = _archiwum()
    stary = bv.uruchom(["BTCUSDT"], TFS, "2021-02", tmp_path / "inc", f, _cisza)
    f.zipy.clear()
    m = bv.uruchom(SYMBOLE, TFS, "2021-02", tmp_path / "inc", f, _cisza, poprzedni=stary)
    assert sorted(f.zipy) == sorted(
        bv.url_pliku("ETHUSDT", t, mm) for t in TFS for mm in ("2021-01", "2021-02")
    )
    ref = bv.uruchom(SYMBOLE, TFS, "2021-02", tmp_path / "ref", f, _cisza)
    assert m["pliki"] == ref["pliki"] and m["jakosc"] == ref["jakosc"]
    # para bez danych w ogóle (same 404): pusty parquet i jakość jak w pełnym biegu
    m2 = bv.uruchom(
        [*SYMBOLE, "XUSDT"], ["1d"], "2021-02", tmp_path / "inc", f, _cisza, poprzedni=m
    )
    assert m2 is not m and m2["jakosc"]["XUSDT/1d"]["wiersze"] == 0
    assert (
        bv.uruchom(
            [*SYMBOLE, "XUSDT"], ["1d"], "2021-02", tmp_path / "inc", f, _cisza, poprzedni=m2
        )
        is m2
    )


def test_przyrostowo_odrzuca_cofniecie_konca_i_inny_start(tmp_path):
    f = _archiwum(symbole=["BTCUSDT"], tfs=["1d"])
    stary = bv.uruchom(["BTCUSDT"], ["1d"], "2021-02", tmp_path, f, _cisza)
    with pytest.raises(ValueError, match="wcześniejszy"):
        bv.uruchom(["BTCUSDT"], ["1d"], "2021-01", tmp_path, f, _cisza, poprzedni=stary)
    with pytest.raises(ValueError, match="min_start"):
        bv.uruchom(
            ["BTCUSDT"],
            ["1d"],
            "2021-02",
            tmp_path,
            f,
            _cisza,
            poprzedni={**stary, "od": "2020-01"},
        )


def test_przyrostowo_zachowuje_pary_spoza_listy_i_czysci_stare_bledy(tmp_path):
    f = _archiwum()
    stary = bv.uruchom(SYMBOLE, ["1d"], "2021-02", tmp_path, f, _cisza)
    stary["bledy"] = [{"para": "ETHUSDT/1h", "blad": "OSError: stary"}]
    m = bv.uruchom(["BTCUSDT"], ["1d"], "2021-02", tmp_path, f, _cisza, poprzedni=stary)
    assert m is not stary and "bledy" not in m  # stare błędy nie przeżywają biegu bez błędów
    assert list(m["jakosc"]) == ["BTCUSDT/1d", "ETHUSDT/1d"]
    assert m["pliki"] == stary["pliki"]


def test_para_z_wpisami_bez_raportu_jakosci_to_blad(tmp_path):
    f = _archiwum(symbole=["BTCUSDT"], tfs=["1d"])
    stary = bv.uruchom(["BTCUSDT"], ["1d"], "2021-02", tmp_path, f, _cisza)
    sciezka = tmp_path / "1d" / "BTCUSDT.parquet"
    przed = sciezka.read_bytes()
    stary["jakosc"] = {}
    m = bv.uruchom(["BTCUSDT"], ["1d"], "2021-03", tmp_path, f, _cisza, poprzedni=stary)
    assert "brak raportu jakości" in m["bledy"][0]["blad"]
    assert sciezka.read_bytes() == przed and m["pliki"] == stary["pliki"]


def test_blad_po_pobraniu_a_przed_podmiana_zostawia_plik_i_manifest_spojne(tmp_path, monkeypatch):
    f = _archiwum(symbole=["BTCUSDT"], tfs=["1d"])
    stary = bv.uruchom(["BTCUSDT"], ["1d"], "2021-02", tmp_path, f, _cisza)
    sciezka = tmp_path / "1d" / "BTCUSDT.parquet"
    przed = sciezka.read_bytes()
    oryginalny = bv.raport_jakosci

    def zepsuty(*a, **k):
        raise ValueError("raport (symulacja)")

    monkeypatch.setattr(bv, "raport_jakosci", zepsuty)
    m = bv.uruchom(["BTCUSDT"], ["1d"], "2021-03", tmp_path, f, _cisza, poprzedni=stary)
    assert "raport (symulacja)" in m["bledy"][0]["blad"]
    assert sciezka.read_bytes() == przed  # parquet nie podmieniony przed raportem
    assert hashlib.sha256(przed).hexdigest() == m["jakosc"]["BTCUSDT/1d"]["parquet_sha256"]
    monkeypatch.setattr(bv, "raport_jakosci", oryginalny)
    m2 = bv.uruchom(["BTCUSDT"], ["1d"], "2021-03", tmp_path, f, _cisza, poprzedni=m)
    assert "bledy" not in m2 and m2["jakosc"]["BTCUSDT/1d"]["do"].startswith("2021-03-31")


def test_nieoczekiwany_wyjatek_jednej_pary_nie_zostawia_reszty_bez_manifestu(tmp_path, monkeypatch):
    f = _archiwum()
    stary = bv.uruchom(SYMBOLE, ["1d"], "2021-02", tmp_path, f, _cisza)
    oryginalny = bv.pobierz_symbol

    def czasem_zepsuty(sym, *a, **k):
        if sym == "ETHUSDT":
            raise TypeError("niespodzianka (symulacja)")
        return oryginalny(sym, *a, **k)

    monkeypatch.setattr(bv, "pobierz_symbol", czasem_zepsuty)
    m = bv.uruchom(SYMBOLE, ["1d"], "2021-03", tmp_path, f, _cisza, watki=2, poprzedni=stary)
    assert m["bledy"] == [{"para": "ETHUSDT/1d", "blad": "TypeError: niespodzianka (symulacja)"}]
    sciezka = tmp_path / "1d" / "BTCUSDT.parquet"
    assert (
        hashlib.sha256(sciezka.read_bytes()).hexdigest()
        == m["jakosc"]["BTCUSDT/1d"]["parquet_sha256"]
    )
    monkeypatch.setattr(bv, "pobierz_symbol", oryginalny)
    m2 = bv.uruchom(SYMBOLE, ["1d"], "2021-03", tmp_path, f, _cisza, poprzedni=m)
    assert "bledy" not in m2  # BTC spójny z manifestem, ETH dociągnięty


def test_zapisz_atomowo_zachowuje_uprawnienia_i_zwraca_sha(tmp_path):
    cel = tmp_path / "m.json"
    sha = bv.zapisz_tekst_atomowo(cel, "a\n")
    assert sha == hashlib.sha256(b"a\n").hexdigest()
    assert (cel.stat().st_mode & 0o777) == 0o666 & ~bv._UMASK  # nie 0600 z mkstemp
    cel.chmod(0o640)
    bv.zapisz_tekst_atomowo(cel, "b\n")
    assert (cel.stat().st_mode & 0o777) == 0o640 and cel.read_text(encoding="utf-8") == "b\n"


def test_uruchom_usuwa_resztki_plikow_tymczasowych(tmp_path):
    f = _archiwum(symbole=["BTCUSDT"], tfs=["1d"])
    stary = bv.uruchom(["BTCUSDT"], ["1d"], "2021-02", tmp_path, f, _cisza)
    resztka = tmp_path / "1d" / ".BTCUSDT.parquet.abc123.tmp"
    resztka.write_bytes(b"pol")
    log: list[str] = []
    m = bv.uruchom(["BTCUSDT"], ["1d"], "2021-02", tmp_path, f, log.append, poprzedni=stary)
    assert m is stary and not resztka.exists() and "plik tymczasowy" in log[0]


def test_main_blokada_katalogu_danych(tmp_path):
    import fcntl
    import os

    fd = os.open(tmp_path, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(SystemExit, match="zajęty"):
            bv.main(["--symbole", "BTCUSDT", "--out", str(tmp_path), "--manifest", "x.json"])
    finally:
        os.close(fd)


def test_main_uniwersum_nie_przepisuje_skladu_bez_zmian(tmp_path, monkeypatch):
    f = _archiwum(symbole=["BTCUSDT"], tfs=["1d"])
    members = {pd.Timestamp("2021-01-01", tz="UTC"): ["BTCUSDT"]}
    monkeypatch.setattr(bv, "_uniwersum_alpha", lambda *a: (["BTCUSDT"], members))
    oryginalny = bv.uruchom
    monkeypatch.setattr(bv, "uruchom", lambda *a, **k: oryginalny(*a, fetch=f, log=_cisza, **k))
    mpath = tmp_path / "manifest.json"
    argv = ["--tf", "1d", "--uniwersum", str(tmp_path), "--top", "1", "--koniec", "2021-02"]
    argv += ["--out", str(tmp_path / "d"), "--manifest", str(mpath)]
    bv.main(argv)
    sklad = tmp_path / "sklad_top1.json"
    assert json.loads(sklad.read_text(encoding="utf-8")) == {"2021-01-01": ["BTCUSDT"]}
    przed = (sklad.read_bytes(), sklad.stat().st_mtime_ns, mpath.stat().st_mtime_ns)
    bv.main([*argv, "--przyrostowo"])
    assert (sklad.read_bytes(), sklad.stat().st_mtime_ns, mpath.stat().st_mtime_ns) == przed
