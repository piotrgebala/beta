"""
podsumowanie_jakosci.py — zadanie 002: podsumowanie raportu jakości z manifestu `dane.binance_vision` oraz
„martwe ogony” — dni bez obrotu na końcu historii symbolu (archiwum Binance publikuje świece ze stałą ceną
i zerowym wolumenem także po wycofaniu kontraktu, np. FTMUSDT od 2025-01-07). Nic nie poprawia, tylko liczy.

    python -m dane.podsumowanie_jakosci > runs/2026-10-05_dq1-jakosc-binance/raw_output.txt
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from dane.binance_vision import DATA_DIR, ROOT

POLA = (
    "wiersze",
    "duplikaty",
    "dziury",
    "brakujace_interwaly",
    "swiece_zerowe",
    "niespojne_ohlc",
    "skoki_k_sigma",
)


def tabela_jakosci(manifest: dict) -> pd.DataFrame:
    """Wiersz na parę symbol/tf z polami raportu jakości."""
    rows = []
    for para, q in manifest["jakosc"].items():
        sym, tf = para.rsplit("/", 1)
        rows.append(
            {
                "symbol": sym,
                "tf": tf,
                **{k: q.get(k, 0) for k in POLA},
                "najwieksza_dziura": q.get("najwieksza_dziura", "0"),
                "od": q.get("od"),
                "do": q.get("do"),
            }
        )
    return pd.DataFrame(rows)


def martwy_ogon(df_1d: pd.DataFrame) -> dict:
    """Ciąg dni z wolumenem 0 na końcu historii: {dni, od} (0 dni → od = None) i liczba dni bez obrotu."""
    v = df_1d.sort_values("timestamp")["volume"].to_numpy()
    n = 0
    while n < len(v) and v[len(v) - 1 - n] == 0:
        n += 1
    od = str(df_1d.sort_values("timestamp")["timestamp"].iloc[len(v) - n].date()) if n else None
    return {"dni_martwe_na_koncu": n, "martwe_od": od, "dni_bez_obrotu": int((v == 0).sum())}


def tabela_martwych(dir_1d: Path) -> pd.DataFrame:
    rows = []
    for p in sorted(dir_1d.glob("*.parquet")):
        df = pd.read_parquet(p, columns=["timestamp", "volume"])
        if len(df):
            rows.append({"symbol": p.stem, **martwy_ogon(df)})
    return pd.DataFrame(rows)


def raport(manifest: dict, dir_1d: Path) -> list[str]:
    q = tabela_jakosci(manifest)
    out = [
        (
            f"Manifest: {len(manifest['pliki'])} plików źródłowych, {len(q)} par, skrypt "
            f"{manifest['wersja_skryptu'][:7]}, {manifest['od']} → {manifest['do']}"
        ),
        f"Błędy pobierania: {len(manifest.get('bledy', []))}",
        f"Kontrola pozytywna BTC 2021-05-19: {manifest.get('kontrola_pozytywna_btc_2021_05_19')}",
        "",
        "Suma po interwałach (świece zerowe = wolumen 0 albo high == low):",
    ]
    agg = q.groupby("tf")[list(POLA)].sum()
    agg.insert(0, "par", q.groupby("tf").size())
    agg.insert(1, "par_z_dziurami", q[q["dziury"] > 0].groupby("tf").size())
    out += agg.fillna(0).astype(int).to_string().splitlines()
    out += ["", "Największe braki (5m), top 10:"]
    top = q[q["tf"] == "5m"].nlargest(10, "brakujace_interwaly")
    out += (
        top[["symbol", "brakujace_interwaly", "najwieksza_dziura", "od", "do"]]
        .to_string(index=False)
        .splitlines()
    )
    m = tabela_martwych(dir_1d)
    martwe = m[m["dni_martwe_na_koncu"] > 0].sort_values("martwe_od")
    out += [
        "",
        f"Martwe ogony (dni z wolumenem 0 na końcu historii — kontrakt wycofany): {len(martwe)} z {len(m)} symboli",
    ]
    out += martwe.to_string(index=False).splitlines() if len(martwe) else ["(brak)"]
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Podsumowanie jakości danych z zadania 002.")
    ap.add_argument("--manifest", type=Path, default=ROOT / "dane" / "manifest_binance_um.json")
    ap.add_argument("--dane-1d", type=Path, default=DATA_DIR / "1d")
    a = ap.parse_args(argv)
    manifest = json.loads(a.manifest.read_text(encoding="utf-8"))
    print("\n".join(raport(manifest, a.dane_1d)))


if __name__ == "__main__":
    main()
