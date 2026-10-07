"""
zwroty_dzienne.py — dzienne log-zwroty ze świec 1d i panel wspólny kilku monet (karty 017 i 018).

Zwrot dnia D = log(close_D / close_{D−1}) i tylko wtedy, gdy w pliku są świece obu kolejnych dni kalendarzowych
(dziura w źródle daje NaN, nie zwrot wielodniowy). Panel wspólny zostawia daty, w których zwrot jest poprawny
dla wszystkich monet. Dane czyta `wczytaj_swiece` (R16: od `data.min_start`); nic nie jest pobierane z sieci.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from dane.ladowanie import ROOT, wczytaj_swiece

KATALOG_1D = ROOT / "data" / "binance_um" / "1d"
# lista i kolejność z F2-1b (`python -m modele.run_f21b --tylko-monety`)
MONETY_F21B = (
    "BNBUSDT",
    "BTCUSDT",
    "ETHUSDT",
    "XRPUSDT",
    "SOLUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "LINKUSDT",
    "AVAXUSDT",
    "LTCUSDT",
    "BCHUSDT",
    "DOTUSDT",
    "FILUSDT",
    "ETCUSDT",
    "NEARUSDT",
)


@dataclass(frozen=True)
class InwentarzMonety:
    symbol: str
    swiec: int
    pierwsza: pd.Timestamp
    ostatnia: pd.Timestamp
    brakujace_dni: tuple[pd.Timestamp, ...]  # dni kalendarzowe bez świecy między pierwszą a `do`
    zwroty_wazne: int


def log_zwroty_1d(swiece: pd.DataFrame, do: pd.Timestamp) -> pd.Series:
    """Log-zwroty dzienne na kalendarzu od pierwszej świecy do `do` (włącznie); NaN przy dziurze."""
    dzien = pd.DatetimeIndex(pd.to_datetime(swiece["timestamp"], utc=True)).normalize()
    close = pd.Series(swiece["close"].to_numpy(dtype=float), index=dzien).sort_index()
    if close.index.has_duplicates:
        raise ValueError("duplikaty dni w świecach 1d")
    if not (np.isfinite(close) & (close > 0)).all():
        raise ValueError("cena zamknięcia nieskończona albo ≤ 0")
    close = close.loc[:do]
    if close.empty:
        raise ValueError("brak świec przed datą `do`")
    kalendarz = pd.date_range(close.index.min(), do, freq="D")
    return np.log(close.reindex(kalendarz)).diff().rename("r")


def inwentarz_monety(symbol: str, swiece: pd.DataFrame, do: pd.Timestamp) -> InwentarzMonety:
    r = log_zwroty_1d(swiece, do)
    dni = pd.DatetimeIndex(pd.to_datetime(swiece["timestamp"], utc=True)).normalize()
    dni = dni[(dni >= r.index.min()) & (dni <= do)]
    brak = r.index.difference(dni)
    return InwentarzMonety(
        symbol=symbol,
        swiec=len(dni),
        pierwsza=dni.min(),
        ostatnia=dni.max(),
        brakujace_dni=tuple(brak),
        zwroty_wazne=int(r.notna().sum()),
    )


def panel_wspolny(
    monety: tuple[str, ...] | list[str],
    katalog: str | Path = KATALOG_1D,
    do: str = "2026-09-30",
) -> tuple[pd.DataFrame, list[InwentarzMonety], list[pd.Timestamp]]:
    """
    (panel, inwentarz, wyciete): panel dni × monety (kolejność `monety`) z poprawnym zwrotem u wszystkich;
    `wyciete` = daty z kalendarza, które odpadły przez dziurę u którejś monety (bez pierwszego dnia,
    który nie ma poprzednika u nikogo).
    """
    if len(monety) < 2 or len(set(monety)) != len(monety):
        raise ValueError("potrzeba ≥ 2 różnych monet")
    do_ts = pd.Timestamp(do)
    do_ts = do_ts.tz_localize("UTC") if do_ts.tzinfo is None else do_ts.tz_convert("UTC")
    szereg, inw = {}, []
    for m in monety:
        sw = wczytaj_swiece(Path(katalog) / f"{m}.parquet")
        szereg[m] = log_zwroty_1d(sw, do_ts)
        inw.append(inwentarz_monety(m, sw, do_ts))
    wszystkie = pd.concat(szereg, axis=1)[list(monety)]
    ma_nan = wszystkie.isna().any(axis=1)
    wyciete = [d for d in wszystkie.index[ma_nan] if d != wszystkie.index[0]]
    return wszystkie.loc[~ma_nan], inw, wyciete


def ostatnie_wiersze(panel: pd.DataFrame, n: int) -> pd.DataFrame:
    """Ostatnie `n` wierszy panelu (0 = cały); n większe od panelu to błąd, nie ciche obcięcie."""
    if n == 0:
        return panel
    if n > len(panel):
        raise ValueError(f"panel ma {len(panel)} wierszy, potrzeba {n}")
    return panel.iloc[-n:]
