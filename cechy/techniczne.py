"""
techniczne.py — pięć wskaźników technicznych jako cechy PROGNOZY ZMIENNOŚCI (nie kierunku), F2-3.
Czyste funkcje `compute_<nazwa>(df) -> pd.Series`, okna tylko wstecz; wejście to ramka dzienna z
`dane.ohlc.ohlc_dzienne` (kolumny `high`, `low`, `close`, `n_swiec`), opóźnienie 0: wiersz d niesie
informację znaną o północy UTC po dobie d (konwencja jak w `cechy.zmiennosc`).

Dzień jest WAŻNY, gdy `n_swiec` ≥ 274 (jak RV) i `high` > `low` > 0; dzień nieważny lub brakujący = NaN
(nigdy ±∞). Okna są kalendarzowe (ramka rozciągnięta do pełnego kalendarza) i wymagają PEŁNEGO okna
(`min_periods` = długość): dziura w oknie daje NaN, bez interpolacji i bez wypełniania w przód.

- `zakres_dzien`  log(ln(high_d / low_d)) — logarytm zakresu doby (skala jak log RV w HAR; estymator typu
                  Parkinsona).
- `atr14`         log(ATR14 / close_d); ATR14 = średnia PROSTA z 14 dni true range, TR_d = max(high−low,
                  |high−close_{d−1}|, |low−close_{d−1}|) (nie rekurencja Wildera: nie zależy od startu próby).
- `ema20_odl`     log(close_d / EMA20_d); EMA20 = ewm(span=20, adjust=True), min. 20 ważnych dni, dziura
                  liczy się jako upływ czasu (ignore_na=False).
- `bb20_szer`     log(4 · std20(close) / średnia20(close)) — szerokość wstęgi Bollingera (std z ddof=1; std = 0 daje NaN).
- `rsi14`         (RSI14 − 50) / 50 ∈ [−1, 1]; RSI14 wg Cutlera (średnie PROSTE zysków i strat z 14 zmian
                  zamknięcia), bez rekurencji Wildera; brak ruchu (zyski = straty = 0) = NaN.

Pominięty świadomie: MACD (różnica dwóch EMA, silnie współliniowa z `ema20_odl`; jako osobny wariant
wymaga własnej pre-rejestracji, R2).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from cechy.zmiennosc import MIN_SWIEC_DNIA, _wymagaj


def _dzienne(df: pd.DataFrame) -> pd.DataFrame:
    """high, low, close dni ważnych na pełnym kalendarzu dziennym (nieważny/brakujący = NaN)."""
    _wymagaj(df, "high", "low", "close", "n_swiec")
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex) or idx.hasnans or len(idx) == 0:
        raise ValueError("wejście OHLC: indeks dnia (DatetimeIndex, niepusty) jak z `ohlc_dzienne`")
    if not idx.is_unique or (idx != idx.floor("D")).any():
        raise ValueError("wejście OHLC: indeks ma być dzienny (północ UTC) i bez duplikatów")
    h, lo, c = (df[k].astype(float) for k in ("high", "low", "close"))
    wazny = (df["n_swiec"] >= MIN_SWIEC_DNIA) & (lo > 0) & (h > lo) & (c >= lo) & (c <= h)
    kalendarz = pd.date_range(idx.min(), idx.max(), freq="D", name=idx.name)
    return pd.DataFrame({"high": h, "low": lo, "close": c}).where(wazny).reindex(kalendarz)


def compute_zakres_dzien(df: pd.DataFrame) -> pd.Series:
    d = _dzienne(df)
    return np.log(np.log(d["high"] / d["low"])).rename("zakres_dzien")


def compute_atr14(df: pd.DataFrame) -> pd.Series:
    d = _dzienne(df)
    poprz = d["close"].shift(1)
    tr = pd.concat(
        [d["high"] - d["low"], (d["high"] - poprz).abs(), (d["low"] - poprz).abs()], axis=1
    ).max(axis=1, skipna=False)
    return np.log(tr.rolling(14).mean() / d["close"]).rename("atr14")


def compute_ema20_odl(df: pd.DataFrame) -> pd.Series:
    c = _dzienne(df)["close"]
    ema = c.ewm(span=20, adjust=True, min_periods=20, ignore_na=False).mean()
    return np.log(c / ema).rename("ema20_odl")


def compute_bb20_szer(df: pd.DataFrame) -> pd.Series:
    r = _dzienne(df)["close"].rolling(20)
    std = r.std()
    return np.log(4.0 * std.where(std > 0) / r.mean()).rename("bb20_szer")


def compute_rsi14(df: pd.DataFrame) -> pd.Series:
    zm = _dzienne(df)["close"].diff()
    zysk = zm.clip(lower=0.0).rolling(14).mean()
    strata = (-zm).clip(lower=0.0).rolling(14).mean()
    suma = zysk + strata
    rsi = 100.0 * zysk / suma.where(suma > 0)
    return ((rsi - 50.0) / 50.0).rename("rsi14")
