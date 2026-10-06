"""
deribit_dvol.py — zadanie 006: DVOL (indeks zmienności oczekiwanej z opcji Deribit) dla BTC i ETH, świece
dzienne UTC z publicznego API `public/get_volatility_index_data`, zapis parquet per waluta, manifest
i raport jakości.

Zasady jak w `dane.binance_vision`: dane od `data.min_start` (R16; obcina `dane.ladowanie`), żadnych cichych
poprawek — dziury, duplikaty i wartości poza zakresem raportujemy, nie naprawiamy. Bez statystyk i modeli
(zakres 006). Sieć wyłącznie przez wstrzykiwaną funkcję `fetch`, więc testy działają bez internetu.

    python -m dane.deribit_dvol                  # BTC i ETH do wczoraj (pełne dni UTC)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from dane.binance_vision import Fetch, _git_hash, fetch_http
from dane.ladowanie import min_start

API_URL = "https://www.deribit.com/api/v2/public/get_volatility_index_data"
WALUTY = ("BTC", "ETH")  # jedyne z ciągłym DVOL (SOL istniał 2022-05…2022-11)
KOLUMNY = ("open", "high", "low", "close")
ZAKRES = (0.0, 400.0)  # DVOL w punktach zmienności rocznej (%); poza zakresem = podejrzane
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "deribit_dvol"
DZIEN_MS = 86_400_000


def url_strony(waluta: str, start_ms: int, koniec_ms: int) -> str:
    q = {
        "currency": waluta,
        "start_timestamp": start_ms,
        "end_timestamp": koniec_ms,
        "resolution": "1D",
    }
    return f"{API_URL}?{urllib.parse.urlencode(q)}"


def pobierz_dvol(
    waluta: str, start_ms: int, koniec_ms: int, fetch: Fetch = fetch_http
) -> tuple[pd.DataFrame, list[dict]]:
    """
    Wszystkie świece 1D z [start_ms, koniec_ms]. API oddaje strony od najnowszych; `continuation` to koniec
    następnej (starszej) strony, None = koniec historii. Zwraca (świece posortowane po czasie, wpisy
    manifestu per strona z SHA-256 odpowiedzi).
    """
    rows, wpisy = [], []
    koniec = koniec_ms
    while True:
        url = url_strony(waluta, start_ms, koniec)
        blob = fetch(url)
        if blob is None:
            raise ValueError(f"{url}: brak odpowiedzi")
        res = json.loads(blob)
        if "result" not in res:
            raise ValueError(f"{url}: błąd API {res.get('error')}")
        data = res["result"]["data"]
        rows += data
        wpisy.append(
            {
                "waluta": waluta,
                "url": url,
                "sha256": hashlib.sha256(blob).hexdigest(),
                "wiersze": len(data),
            }
        )
        cont = res["result"].get("continuation")
        if not cont or not data or cont >= koniec:
            break
        koniec = int(cont)
    df = pd.DataFrame(rows, columns=["ts_ms", *KOLUMNY])
    df["timestamp"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
    df = df.drop(columns="ts_ms").astype({c: float for c in KOLUMNY})
    df = df.sort_values("timestamp", kind="stable").reset_index(drop=True)
    return df[["timestamp", *KOLUMNY]], wpisy


def raport_jakosci(df: pd.DataFrame) -> dict:
    """Kontrola BEZ poprawek: dziury (brakujące dni), duplikaty, wartości poza ZAKRES, niespójne OHLC."""
    if df.empty:
        return {"wiersze": 0}
    ts = df["timestamp"]
    u = ts.drop_duplicates().sort_values()
    diffs = u.diff().dropna()
    dzien = pd.Timedelta("1D")
    dziury = diffs[diffs > dzien]
    lo, hi = ZAKRES
    v = df[list(KOLUMNY)]
    return {
        "wiersze": len(df),
        "od": str(ts.min()),
        "do": str(ts.max()),
        "duplikaty": int(ts.duplicated().sum()),
        "dziury": len(dziury),
        "brakujace_dni": int(((dziury / dzien).round() - 1).sum()) if len(dziury) else 0,
        "najwieksza_dziura": str(dziury.max()) if len(dziury) else "0",
        "poza_zakresem": int(((v <= lo) | (v > hi)).any(axis=1).sum()),
        "niespojne_ohlc": int(
            (
                (df["high"] < df[["open", "close"]].max(axis=1))
                | (df["low"] > df[["open", "close"]].min(axis=1))
            ).sum()
        ),
    }


def kontrola_pozytywna_btc(df: pd.DataFrame) -> dict:
    """Znany dzień: krach 2021-05-19 — zmienność oczekiwana BTC skoczyła powyżej 100 (high DVOL > 100)."""
    day = df.loc[df["timestamp"] == pd.Timestamp("2021-05-19", tz="UTC")]
    if day.empty:
        return {"ok": False, "powod": "brak świecy 2021-05-19"}
    hi = float(day["high"].iloc[0])
    return {"ok": hi > 100.0, "high": hi, "close": float(day["close"].iloc[0])}


def uruchom(
    waluty: list[str],
    koniec: pd.Timestamp,
    out_dir: Path = DATA_DIR,
    fetch: Fetch = fetch_http,
    log=print,
) -> dict:
    """
    Pobiera świece 1D od `data.min_start` do dnia przed `koniec` (tylko pełne dni UTC), zapisuje parquet
    per waluta, zwraca manifest z raportem jakości.
    """
    start = min_start()
    start_ms = int(start.value // 1_000_000)
    koniec_ms = int(koniec.value // 1_000_000) - 1
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "zrodlo": API_URL,
        "rozdzielczosc": "1D",
        "skrypt": "dane/deribit_dvol.py",
        "wersja_skryptu": _git_hash(),
        "utworzono": datetime.now(UTC).isoformat(timespec="seconds"),
        "od": str(start.date()),
        "do_wylacznie": str(koniec.date()),
        "strony": [],
        "jakosc": {},
    }
    for w in waluty:
        df, wpisy = pobierz_dvol(w, start_ms, koniec_ms, fetch)
        df = df[df["timestamp"] < koniec].reset_index(drop=True)
        path = out_dir / f"{w}_1d.parquet"
        df.to_parquet(path, index=False)
        manifest["strony"] += wpisy
        q = raport_jakosci(df)
        q["parquet"] = path.name
        q["parquet_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest["jakosc"][w] = q
        log(
            f"DVOL {w}: {q.get('wiersze', 0)} dni, {q.get('od')} → {q.get('do')}, dziury {q.get('dziury', 0)}"
        )
        if w == "BTC" and len(df):
            manifest["kontrola_pozytywna_btc_2021_05_19"] = kontrola_pozytywna_btc(df)
    return manifest


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Zadanie 006: DVOL (Deribit) 1D.")
    ap.add_argument("--waluty", nargs="+", default=list(WALUTY))
    ap.add_argument(
        "--koniec",
        default=pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"),
        help="pierwszy dzień NIEpobierany (domyślnie dziś → ostatni pełny dzień to wczoraj)",
    )
    ap.add_argument("--out", type=Path, default=DATA_DIR)
    ap.add_argument("--manifest", type=Path, default=ROOT / "dane" / "manifest_deribit_dvol.json")
    a = ap.parse_args(argv)
    manifest = uruchom(a.waluty, pd.Timestamp(a.koniec, tz="UTC"), a.out)
    a.manifest.write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"manifest: {a.manifest} ({len(manifest['strony'])} stron API)")


if __name__ == "__main__":
    main()
