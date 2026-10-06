"""
binance_vision.py — zadanie 002: świece perpetuali USDT-M z archiwum `data.binance.vision` (miesięczne
pliki ZIP z sumą SHA-256 w `.CHECKSUM`), zapis parquet per symbol, manifest i raport jakości.

Zasady: dane od `data.min_start` (R16; obcina `dane.ladowanie`), żadnych cichych poprawek — dziury,
duplikaty, świece zerowe i skoki raportujemy, nie naprawiamy. Moduł nie liczy żadnych statystyk zwrotów
(zakres 002: „bez statystyk zwrotów ani modeli”). Sieć wyłącznie przez wstrzykiwaną funkcję `fetch`,
więc testy działają bez internetu.

Tryb przyrostowy (zadanie 015, `--przyrostowo`): czyta istniejący manifest i dla każdej pary
(symbol, tf) uznaje za gotowe miesiące z wpisami w manifeście — ale tylko wtedy, gdy parquet na
dysku ma SHA-256 równe `jakosc[para].parquet_sha256`. Inaczej para trafia do `bledy` (plik
nietknięty, bez cichej naprawy i bez pobierania całości po cichu). Pobiera tylko miesiące PO
ostatnim miesiącu pary w manifeście (para bez wpisów: wszystkie, jak w pełnym biegu), dokleja nowe
świece do parquetu; nowe świece nie później niż ostatnia istniejąca = błąd pary (bez deduplikacji).
Raport jakości liczony na całym sklejonym zbiorze. Wpisy `pliki`: stare zachowane, nowe dopisane,
kolejność jak w pełnym biegu (kolejność par, w parze miesiące); pary ze starego manifestu spoza
bieżącej listy zostają na końcu.
Wynik = pełny bieg do tego samego `--koniec` (parquet bajtowo, `pliki`, `jakosc`), o ile Binance nie
podmienił opublikowanych już plików (tego tryb przyrostowy nie wykryje — od tego jest pełny bieg) i
nie dołożył po fakcie miesiąca w środku historii pary.
Gdy bieg nic nie dodał (żadnego nowego miesiąca, żadnego błędu, stary manifest bez `bledy`), żaden
plik nie jest przepisywany — manifest bajtowo ten sam, więc automat nie ma czego commitować. Gdy coś
dodał: `do` = `--koniec`, `utworzono` i `wersja_skryptu` z bieżącego biegu. `--koniec` wcześniejszy
niż `do` manifestu albo inny `od` (zmiana `data.min_start`) = błąd: wtedy pełny bieg.
Ograniczenie: lista symboli jak w pełnym biegu — suma składów top-N z alpha `universe_full`, który
kończy się na 2026-06; nowe wejścia do top-20 po tej dacie nie są pobierane, dopóki alpha nie
odświeży `universe_full` (Poprawka w alpha, decyzja użytkownika).

Znane granice trybu przyrostowego (świadomie bez automatycznej naprawy — naprawa = pełny bieg):
- Przerwany bieg (limit kroku automatu, kill, OOM): parquety par już skończonych są podmienione, a
  manifest zapisuje się dopiero na końcu, więc następny bieg `--przyrostowo` zgłosi te pary jako
  niezgodny SHA-256. Błąd nieoczekiwany w jednej parze (np. TypeError) nie przerywa biegu — trafia
  do `bledy` jak błąd sieci.
- Świeca powtórzona na granicy miesięcy przez Binance: pełny bieg ją raportuje (`duplikaty`),
  przyrostowy zgłasza błąd pary co miesiąc, aż do pełnego biegu (automat sam tego nie rozwiąże).
- Kontrakt zdjęty z giełdy: para pyta co miesiąc o wszystkie miesiące od swojego ostatniego do
  `--koniec` (same 404) — liczba zapytań rośnie o jedno na miesiąc na taką parę; na wynik to nie
  wpływa.
- Dwa biegi naraz na tym samym `--out`: `main` bierze blokadę (flock) katalogu danych; drugi bieg
  kończy się błędem zamiast ścigać się o pliki.

Zapis parquetów, manifestu i składu jest atomowy (plik tymczasowy w tym samym katalogu, fsync,
`os.replace`, fsync katalogu; uprawnienia jak stary plik albo wg umask): wyjątek w procesie nie
zostawia uszkodzonego pliku ani pliku tymczasowego. SIGKILL/SIGTERM w trakcie zapisu może zostawić
`.<nazwa>.*.tmp` (stary plik cały) — `uruchom` usuwa takie resztki na starcie i to loguje. Parquet
zapisuje się na samym końcu pracy pary (po raporcie jakości; SHA-256 liczony z pliku tymczasowego),
więc błąd przed podmianą zostawia plik i wpis manifestu spójne.

    python -m dane.binance_vision --tf 5m 1d --symbole BTCUSDT ETHUSDT --koniec 2026-08
    python -m dane.binance_vision --tf 5m 1d --uniwersum ../alpha/data/raw/universe_full --top 20 --watki 16
    python -m dane.binance_vision --uniwersum ../alpha/data/raw/universe_full --przyrostowo
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import io
import json
import os
import stat
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
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

# umask czytany raz przy imporcie (os.umask zmienia stan procesu — nie wolno tego robić w wątkach)
_UMASK = os.umask(0)
os.umask(_UMASK)


def url_pliku(symbol: str, tf: str, miesiac: str) -> str:
    """Adres miesięcznego ZIP-a; symbol kodowany w URL (są symbole spoza ASCII, np. „币安人生USDT”)."""
    s = urllib.parse.quote(symbol)
    return f"{BASE_URL}/{s}/{tf}/{s}-{tf}-{miesiac}.zip"


def miesiace(start: str, koniec: str) -> list[str]:
    """Miesiące 'RRRR-MM' od `start` do `koniec` włącznie."""
    return [p.strftime("%Y-%m") for p in pd.period_range(start, koniec, freq="M")]


def fetch_http(url: str, proby: int = 5) -> bytes | None:
    """GET z ponowieniem (backoff 1, 2, 4… s) przy błędach sieci; 404 → None (symbolu nie było w miesiącu)."""
    for k in range(proby):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if k == proby - 1:
                raise
        except OSError:  # URLError, timeout w trakcie odczytu, zerwane połączenie
            if k == proby - 1:
                raise
        time.sleep(2**k)
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


def zapisz_atomowo(path: Path, zapisz: Callable[[Path], None]) -> str:
    """
    `zapisz(tmp)` pisze do pliku tymczasowego w katalogu `path`; potem fsync, uprawnienia jak
    stary `path` (nowy plik: 0o666 & ~umask — `mkstemp` dałby 0600), `os.replace` (atomowe
    w obrębie systemu plików) i fsync katalogu. Zwraca SHA-256 zapisanej treści (liczony z pliku
    tymczasowego przed podmianą). Wyjątek w procesie = stary `path` nietknięty, tymczasowy usunięty.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, nazwa = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    os.close(fd)
    tmp = Path(nazwa)
    try:
        zapisz(tmp)
        with open(tmp, "rb") as f:
            os.fsync(f.fileno())
        try:
            tryb = stat.S_IMODE(os.stat(path).st_mode)
        except FileNotFoundError:
            tryb = 0o666 & ~_UMASK
        os.chmod(tmp, tryb)
        sha = _sha256_pliku(tmp)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    dfd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)
    return sha


def zapisz_tekst_atomowo(path: Path, tekst: str) -> str:
    return zapisz_atomowo(path, lambda tmp: tmp.write_text(tekst, encoding="utf-8"))


def _sha256_pliku(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for kawalek in iter(lambda: f.read(1 << 20), b""):
            h.update(kawalek)
    return h.hexdigest()


def _nastepny_miesiac(miesiac: str) -> str:
    return (pd.Period(miesiac, freq="M") + 1).strftime("%Y-%m")


def _pobierz_i_zapisz(
    sym: str,
    tf: str,
    start: str,
    koniec: str,
    out_dir: Path,
    fetch: Fetch,
    log,
    stare: tuple[list[dict], dict | None] | None = None,
) -> tuple[pd.DataFrame, list[dict], dict] | None:
    """
    Jedna para (symbol, tf): pobranie, zapis parquet (atomowo), raport jakości. `stare` = (wpisy,
    jakość) pary z poprzedniego manifestu → tryb przyrostowy; None = pełny bieg. Zwraca None, gdy
    w trybie przyrostowym nie ma nic nowego (wtedy żaden plik nie jest zapisywany).
    """
    path = out_dir / tf / f"{sym}.parquet"
    stary_df = None
    if stare is None:
        df, wpisy = pobierz_symbol(sym, tf, start, koniec, fetch)
    else:
        wpisy_stare, q_stara = stare
        if q_stara is not None:
            if not path.is_file():
                raise ValueError(f"{path}: brak pliku parquet opisanego w manifeście")
            sha = _sha256_pliku(path)
            if sha != q_stara.get("parquet_sha256"):
                raise ValueError(
                    f"{path}: SHA-256 {sha} ≠ manifest {q_stara.get('parquet_sha256')} "
                    "(przerwany poprzedni bieg albo zmiana poza skryptem; nie naprawiam — "
                    "pełny bieg)"
                )
        elif wpisy_stare:
            raise ValueError(f"{sym}/{tf}: manifest ma wpisy plików, ale brak raportu jakości")
        od = _nastepny_miesiac(max(w["miesiac"] for w in wpisy_stare)) if wpisy_stare else start
        if od > koniec:
            return None
        df_nowe, wpisy_nowe = pobierz_symbol(sym, tf, od, koniec, fetch)
        if not wpisy_nowe and q_stara is not None:
            return None
        if wpisy_stare and wpisy_nowe:
            stary_df = pd.read_parquet(path)
            if len(stary_df) and df_nowe["timestamp"].min() <= stary_df["timestamp"].max():
                raise ValueError(
                    f"{sym}/{tf}: nowe świece od {df_nowe['timestamp'].min()} nachodzą na "
                    f"istniejące (ostatnia {stary_df['timestamp'].max()}) — "
                    "nie deduplikuję po cichu"
                )
            df = pd.concat([stary_df, df_nowe], ignore_index=True)
            # zabezpieczenie, nie logika: obie części posortowane i (sprawdzone wyżej) rozłączne
            df = df.sort_values("timestamp", kind="stable").reset_index(drop=True)
        else:
            df = df_nowe
        wpisy = wpisy_stare + wpisy_nowe
    # najpierw wszystko, co może zawieść; podmiana parquetu to ostatni krok pary
    q = raport_jakosci(df, tf) if len(df) else {"wiersze": 0}
    q["parquet"] = str(path.relative_to(out_dir))
    q["parquet_sha256"] = zapisz_atomowo(path, lambda tmp: df.to_parquet(tmp, index=False))
    dopisano = "" if stary_df is None else f" (dopisano {len(df) - len(stary_df)})"
    log(f"{sym} {tf}: {q.get('wiersze', 0)} świec{dopisano}, dziury {q.get('dziury', 0)}")
    return df, wpisy, q


def _sprawdz_poprzedni(poprzedni: dict, start: str, koniec: str) -> None:
    """Tryb przyrostowy tylko dla tego samego `od` i `--koniec` nie wcześniejszego niż `do`."""
    if poprzedni.get("od", start) != start:
        raise ValueError(
            f"manifest ma od={poprzedni.get('od')!r}, a data.min_start daje {start!r} — pełny bieg"
        )
    if koniec < poprzedni.get("do", ""):
        raise ValueError(
            f"--koniec {koniec} wcześniejszy niż do={poprzedni.get('do')!r} w manifeście — "
            "tryb przyrostowy nie cofa danych; pełny bieg"
        )


def uruchom(
    symbole: list[str],
    tfs: list[str],
    koniec: str,
    out_dir: Path = DATA_DIR,
    fetch: Fetch = fetch_http,
    log=print,
    watki: int = 1,
    poprzedni: dict | None = None,
) -> dict:
    """
    Pobiera, zapisuje parquet per (symbol, tf), zwraca manifest z raportem jakości. `watki` > 1 pobiera
    pary (symbol, tf) równolegle; kolejność wpisów manifestu jest ta sama co przy pracy sekwencyjnej.

    `poprzedni` (manifest poprzedniego biegu) włącza tryb przyrostowy — zasady w docstringu modułu.
    Gdy nic nie dodano, zwraca ten sam obiekt `poprzedni` (`wynik is poprzedni` = nic do zapisania).
    """
    start = min_start().strftime("%Y-%m")
    if poprzedni is not None:
        _sprawdz_poprzedni(poprzedni, start, koniec)
    out_dir.mkdir(parents=True, exist_ok=True)
    for resztka in sorted(out_dir.glob("*/.*.parquet.*.tmp")):
        log(f"usuwam plik tymczasowy po przerwanym zapisie: {resztka}")
        resztka.unlink(missing_ok=True)
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
    pary = [(sym, tf) for sym in symbole for tf in tfs]
    stare_wpisy: dict[str, list[dict]] = {}
    stara_jakosc: dict[str, dict] = {}
    if poprzedni is not None:
        for w in poprzedni.get("pliki", []):
            stare_wpisy.setdefault(f"{w['symbol']}/{w['tf']}", []).append(w)
        stara_jakosc = poprzedni.get("jakosc", {})

    def zadanie(para: tuple[str, str]):
        klucz = f"{para[0]}/{para[1]}"
        stare = None
        if poprzedni is not None:
            stare = (stare_wpisy.get(klucz, []), stara_jakosc.get(klucz))
        try:
            return _pobierz_i_zapisz(*para, start, koniec, out_dir, fetch, log, stare)
        # błąd jednej pary (sieć, suma SHA, zły ZIP/CSV, ale też nieoczekiwany wyjątek) nie kasuje
        # reszty — trafia do manifestu; inaczej podmienione już parquety zostałyby bez manifestu
        except Exception as e:  # noqa: BLE001 — świadomie: błąd pary nie gubi manifestu
            log(f"{para[0]} {para[1]}: BŁĄD {type(e).__name__}: {e}")
            return e

    zmiany = 0
    with ThreadPoolExecutor(max_workers=max(1, watki)) as ex:
        for (sym, tf), wynik in zip(pary, ex.map(zadanie, pary), strict=True):
            klucz = f"{sym}/{tf}"
            if wynik is None or isinstance(wynik, Exception):
                if isinstance(wynik, Exception):
                    manifest.setdefault("bledy", []).append(
                        {"para": klucz, "blad": f"{type(wynik).__name__}: {wynik}"}
                    )
                # tryb przyrostowy: pliki pary nietknięte, więc jej stare wpisy zostają
                manifest["pliki"] += stare_wpisy.get(klucz, [])
                if klucz in stara_jakosc:
                    manifest["jakosc"][klucz] = stara_jakosc[klucz]
                continue
            df, wpisy, q = wynik
            zmiany += 1
            manifest["pliki"] += wpisy
            manifest["jakosc"][klucz] = q
            if sym == "BTCUSDT" and tf == "1d" and len(df):
                manifest["kontrola_pozytywna_btc_2021_05_19"] = kontrola_pozytywna_btc(df)
    if poprzedni is None:
        return manifest
    # pary ze starego manifestu spoza bieżącej listy: bez zmian, na końcu
    biezace = {f"{s}/{t}" for s, t in pary}
    for klucz in [*stara_jakosc, *(k for k in stare_wpisy if k not in stara_jakosc)]:
        if klucz not in biezace:
            manifest["pliki"] += stare_wpisy.get(klucz, [])
            if klucz in stara_jakosc:
                manifest["jakosc"][klucz] = stara_jakosc[klucz]
    kontrola = "kontrola_pozytywna_btc_2021_05_19"
    if kontrola not in manifest and kontrola in poprzedni:
        manifest[kontrola] = poprzedni[kontrola]
    if zmiany == 0 and not manifest.get("bledy") and not poprzedni.get("bledy"):
        log("Tryb przyrostowy: nic nowego — manifest i pliki bez zmian.")
        return poprzedni
    log(f"Tryb przyrostowy: zaktualizowano {zmiany} par z {len(pary)}.")
    return manifest


@contextlib.contextmanager
def _blokada(katalog: Path):
    """Wyłączna blokada (flock) katalogu danych na czas biegu; zajęta = błąd, nie czekamy."""
    katalog.mkdir(parents=True, exist_ok=True)
    fd = os.open(katalog, os.O_RDONLY)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise SystemExit(
                f"BŁĄD: {katalog} zajęty przez inny bieg (flock) — spróbuj później"
            ) from e
        yield
    finally:
        os.close(fd)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Zadanie 002: świece USDT-M z data.binance.vision.")
    ap.add_argument("--tf", nargs="+", default=["5m", "1d"], choices=sorted(INTERWAL))
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--symbole", nargs="+")
    g.add_argument("--uniwersum", type=Path, help="katalog alpha data/raw/universe_full")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument(
        "--koniec",
        default=(pd.Timestamp.now(tz="UTC").tz_localize(None).to_period("M") - 1).strftime("%Y-%m"),
    )
    ap.add_argument("--out", type=Path, default=DATA_DIR)
    ap.add_argument("--manifest", type=Path, default=ROOT / "dane" / "manifest_binance_um.json")
    ap.add_argument("--watki", type=int, default=1, help="równoległe pobieranie par (symbol, tf)")
    ap.add_argument(
        "--przyrostowo",
        action="store_true",
        help="tylko miesiące po ostatnim w manifeście (wymaga istniejącego manifestu)",
    )
    a = ap.parse_args(argv)
    with _blokada(a.out):
        _main(a)


def _main(a: argparse.Namespace) -> None:
    poprzedni = None
    if a.przyrostowo:
        try:
            poprzedni = json.loads(a.manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise SystemExit(f"--przyrostowo: nie mogę odczytać manifestu {a.manifest}: {e}") from e
    if a.symbole:
        symbole = sorted(a.symbole)
    else:
        symbole, members = _uniwersum_alpha(a.uniwersum, a.top, min_start())
        sklad = {str(k.date()): v for k, v in members.items()}
        sklad_path = a.manifest.parent / f"sklad_top{a.top}.json"
        tekst = json.dumps(sklad, indent=1) + "\n"
        if not sklad_path.is_file() or sklad_path.read_text(encoding="utf-8") != tekst:
            zapisz_tekst_atomowo(sklad_path, tekst)
    tryb = "przyrostowo" if a.przyrostowo else "pełny bieg"
    print(f"{len(symbole)} symboli × {a.tf}, {min_start():%Y-%m} → {a.koniec} ({tryb})")
    try:
        manifest = uruchom(symbole, a.tf, a.koniec, a.out, watki=a.watki, poprzedni=poprzedni)
    except ValueError as e:
        raise SystemExit(f"BŁĄD: {e}") from e
    if manifest is poprzedni:
        print(f"manifest: {a.manifest} bez zmian ({len(manifest['pliki'])} plików źródłowych)")
    else:
        zapisz_tekst_atomowo(a.manifest, json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
        print(f"manifest: {a.manifest} ({len(manifest['pliki'])} plików źródłowych)")
    if manifest.get("bledy"):
        raise SystemExit(f"BŁĘDY w {len(manifest['bledy'])} parach — lista w manifeście (`bledy`)")


if __name__ == "__main__":
    main()
