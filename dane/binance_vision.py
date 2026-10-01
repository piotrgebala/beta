"""
binance_vision.py — zadanie 002: świece perpetuali USDT-M z archiwum `data.binance.vision` (miesięczne
pliki ZIP z sumą SHA-256 w `.CHECKSUM`), zapis parquet per symbol, manifest i raport jakości.

Zasady: dane od `data.min_start` (R16; obcina `dane.ladowanie`), żadnych cichych poprawek — dziury,
duplikaty, świece zerowe i skoki raportujemy, nie naprawiamy. Moduł nie liczy żadnych statystyk zwrotów
(zakres 002: „bez statystyk zwrotów ani modeli”). Sieć wyłącznie przez wstrzykiwaną funkcję `fetch`,
więc testy działają bez internetu.

    python -m dane.binance_vision --tf 5m 1d --symbole BTCUSDT ETHUSDT --koniec 2026-08
    python -m dane.binance_vision --tf 5m 1d --uniwersum ../alpha/data/raw/universe_full --top 20
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from dane.ladowanie import min_start

BASE_URL = "https://data.binance.vision/data/futures/um/monthly/klines"
KOLUMNY = (
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "count",
    "taker_buy_volume",
    "taker_buy_quote_volume",
    "ignore",
)
INTERWAL = {"1m": "1min", "5m": "5min", "15m": "15min", "1h": "1h", "4h": "4h", "1d": "1D"}
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "binance_um"

Fetch = Callable[[str], bytes | None]  # None = brak pliku (404)


def url_pliku(symbol: str, tf: str, miesiac: str) -> str:
    return f"{BASE_URL}/{symbol}/{tf}/{symbol}-{tf}-{miesiac}.zip"


def miesiace(start: str, koniec: str) -> list[str]:
    """Miesiące 'RRRR-MM' od `start` do `koniec` włącznie."""
    return [p.strftime("%Y-%m") for p in pd.period_range(start, koniec, freq="M")]


def fetch_http(url: str, proby: int = 4) -> bytes | None:
    """GET z ponowieniem przy błędach sieci; 404 → None (symbolu nie było w tym miesiącu)."""
    for k in range(proby):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if k == proby - 1:
                raise
        except urllib.error.URLError:
            if k == proby - 1:
                raise
    return None


def parsuj_zip(blob: bytes) -> pd.DataFrame:
    """CSV z ZIP-a Binance → DataFrame; obsługuje pliki z nagłówkiem i bez (format zmieniał się w czasie)."""
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names = [n for n in z.namelist() if n.endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"oczekiwany 1 plik CSV w ZIP, jest {len(names)}")
        raw = z.read(names[0]).decode("utf-8")
    first = raw.split("\n", 1)[0]
    header = 0 if first.startswith("open_time") else None
    df = pd.read_csv(io.StringIO(raw), header=header, names=list(KOLUMNY))
    df = df.drop(columns="ignore")
    for c in ("open_time", "close_time", "count"):
        df[c] = pd.to_numeric(df[c]).astype("int64")
    for c in ("open", "high", "low", "close", "volume", "quote_volume"):
        df[c] = pd.to_numeric(df[c]).astype(float)
    for c in ("taker_buy_volume", "taker_buy_quote_volume"):
        df[c] = pd.to_numeric(df[c]).astype(float)
    # znaczniki czasu: ms (do 2024), µs w nowszych plikach spot — tu normalizujemy po długości liczby
    unit = "us" if df["open_time"].iloc[0] > 10**14 else "ms"
    df["timestamp"] = pd.to_datetime(df["open_time"], unit=unit, utc=True)
    return df.reset_index(drop=True)


def pobierz_symbol(
    symbol: str, tf: str, start: str, koniec: str, fetch: Fetch = fetch_http
) -> tuple[pd.DataFrame, list[dict]]:
    """
    Wszystkie miesiące symbolu: weryfikacja SHA-256 z `.CHECKSUM`, parsowanie, sklejenie.
    Zwraca (świece posortowane po czasie, wpisy manifestu per plik źródłowy). Rozbieżna suma = błąd.
    """
    frames, wpisy = [], []
    for m in miesiace(start, koniec):
        url = url_pliku(symbol, tf, m)
        blob = fetch(url)
        if blob is None:
            continue
        sha = hashlib.sha256(blob).hexdigest()
        chk = fetch(url + ".CHECKSUM")
        if chk is None:
            raise ValueError(f"{url}: brak pliku .CHECKSUM")
        oczekiwany = chk.decode("utf-8").split()[0].strip().lower()
        if sha != oczekiwany:
            raise ValueError(f"{url}: SHA-256 {sha} ≠ CHECKSUM {oczekiwany}")
        df = parsuj_zip(blob)
        frames.append(df)
        wpisy.append(
            {
                "symbol": symbol,
                "tf": tf,
                "miesiac": m,
                "url": url,
                "sha256": sha,
                "wiersze": len(df),
                "od": str(df["timestamp"].min()),
                "do": str(df["timestamp"].max()),
            }
        )
    if not frames:
        return pd.DataFrame(columns=[*KOLUMNY[:-1], "timestamp"]), wpisy
    out = pd.concat(frames, ignore_index=True).sort_values("timestamp", kind="stable")
    return out.reset_index(drop=True), wpisy


def raport_jakosci(df: pd.DataFrame, tf: str, k_sigma: float = 10.0) -> dict:
    """
    Kontrola jakości BEZ poprawek: dziury (brakujące interwały), duplikaty znaczników, świece zerowe
    (wolumen 0 albo high == low), niespójne OHLC, skoki |log(close/close_prev)| > k·σ (σ odporne, z MAD).
    """
    if df.empty:
        return {"wiersze": 0}
    ts = df["timestamp"]
    step = pd.Timedelta(INTERWAL[tf])
    dup = int(ts.duplicated().sum())
    u = ts.drop_duplicates().sort_values()
    diffs = u.diff().dropna()
    dziury = diffs[diffs > step]
    brak = int(((dziury / step).round() - 1).sum()) if len(dziury) else 0
    zero = int(((df["volume"] == 0) | (df["high"] == df["low"])).sum())
    zle_ohlc = int(
        (
            (df["high"] < df[["open", "close"]].max(axis=1))
            | (df["low"] > df[["open", "close"]].min(axis=1))
            | (df["low"] <= 0)
        ).sum()
    )
    lr = np.log(df["close"]).diff().dropna()
    mad = float((lr - lr.median()).abs().median()) * 1.4826
    skoki = lr[(lr - lr.median()).abs() > k_sigma * mad] if mad > 0 else lr.iloc[:0]
    return {
        "wiersze": len(df),
        "od": str(ts.min()),
        "do": str(ts.max()),
        "duplikaty": dup,
        "dziury": len(dziury),
        "brakujace_interwaly": brak,
        "najwieksza_dziura": str(dziury.max()) if len(dziury) else "0",
        "swiece_zerowe": zero,
        "niespojne_ohlc": zle_ohlc,
        "skoki_k_sigma": len(skoki),
        "k_sigma": k_sigma,
        "przyklady_skokow": [str(df["timestamp"].iloc[i]) for i in skoki.index[:5]],
    }


def kontrola_pozytywna_btc(df_1d: pd.DataFrame) -> dict:
    """
    Znany dzień: 2021-05-19 (krach maja 2021) — BTC perp miał zakres high/low ≈ 30–43 tys. USDT.
    Sprawdza, że dane pokazują ten dzień: low < 32 000 i high > 40 000.
    """
    day = df_1d.loc[df_1d["timestamp"] == pd.Timestamp("2021-05-19", tz="UTC")]
    if day.empty:
        return {"ok": False, "powod": "brak świecy 2021-05-19"}
    lo, hi = float(day["low"].iloc[0]), float(day["high"].iloc[0])
    return {"ok": lo < 32_000 and hi > 40_000, "low": lo, "high": hi}


def symbole_z_uniwersum(members: dict, od: pd.Timestamp) -> list[str]:
    """Suma składów miesięcznych od daty `od` (point-in-time skład liczy alpha; tu tylko lista do pobrania)."""
    return sorted({s for m, syms in members.items() if m >= od for s in syms})


def _uniwersum_alpha(universe_dir: Path, top_n: int, od: pd.Timestamp) -> tuple[list[str], dict]:
    """Skład top-N z plików alpha (`universe_full`) funkcjami alpha — tylko odczyt (zasada 23)."""
    import sys

    sys.dont_write_bytecode = True
    import yaml

    cfg = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    alpha = (ROOT / cfg["data"]["alpha_repo"]).resolve()
    sys.path.insert(0, str(alpha))
    from backtest.rebalance_premium import load_universe, monthly_members

    _, volume = load_universe(universe_dir)
    starts = list(pd.date_range(od, volume.index.max(), freq="MS", tz="UTC"))
    members = monthly_members(volume, starts, top_n=top_n)
    return symbole_z_uniwersum(members, od), members


def _git_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "nieznany"


def uruchom(
    symbole: list[str],
    tfs: list[str],
    koniec: str,
    out_dir: Path = DATA_DIR,
    fetch: Fetch = fetch_http,
    log=print,
) -> dict:
    """Pobiera, zapisuje parquet per (symbol, tf), zwraca manifest z raportem jakości."""
    start = min_start().strftime("%Y-%m")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "zrodlo": BASE_URL,
        "skrypt": "dane/binance_vision.py",
        "wersja_skryptu": _git_hash(),
        "utworzono": datetime.now(UTC).isoformat(timespec="seconds"),
        "od": start,
        "do": koniec,
        "pliki": [],
        "jakosc": {},
    }
    for sym in symbole:
        for tf in tfs:
            df, wpisy = pobierz_symbol(sym, tf, start, koniec, fetch)
            path = out_dir / tf / f"{sym}.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(path, index=False)
            manifest["pliki"] += wpisy
            q = raport_jakosci(df, tf) if len(df) else {"wiersze": 0}
            q["parquet"] = str(path.relative_to(out_dir))
            q["parquet_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest["jakosc"][f"{sym}/{tf}"] = q
            log(f"{sym} {tf}: {q.get('wiersze', 0)} świec, dziury {q.get('dziury', 0)}")
            if sym == "BTCUSDT" and tf == "1d" and len(df):
                manifest["kontrola_pozytywna_btc_2021_05_19"] = kontrola_pozytywna_btc(df)
    return manifest


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Zadanie 002: świece USDT-M z data.binance.vision.")
    ap.add_argument("--tf", nargs="+", default=["5m", "1d"], choices=sorted(INTERWAL))
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--symbole", nargs="+")
    g.add_argument("--uniwersum", type=Path, help="katalog alpha data/raw/universe_full")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument(
        "--koniec",
        default=(pd.Timestamp.now(tz="UTC") - pd.offsets.MonthBegin(1)).strftime("%Y-%m"),
    )
    ap.add_argument("--out", type=Path, default=DATA_DIR)
    ap.add_argument("--manifest", type=Path, default=ROOT / "dane" / "manifest_binance_um.json")
    a = ap.parse_args(argv)
    if a.symbole:
        symbole = sorted(a.symbole)
    else:
        symbole, members = _uniwersum_alpha(a.uniwersum, a.top, min_start())
        sklad = {str(k.date()): v for k, v in members.items()}
        (a.manifest.parent / f"sklad_top{a.top}.json").write_text(
            json.dumps(sklad, indent=1) + "\n", encoding="utf-8"
        )
    print(f"{len(symbole)} symboli × {a.tf}, {min_start():%Y-%m} → {a.koniec}")
    manifest = uruchom(symbole, a.tf, a.koniec, a.out)
    a.manifest.write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"manifest: {a.manifest} ({len(manifest['pliki'])} plików źródłowych)")


if __name__ == "__main__":
    main()
