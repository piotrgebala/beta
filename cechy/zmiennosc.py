"""
zmiennosc.py — cechy filaru F2 jako czyste funkcje `compute_<nazwa>(df) -> pd.Series` (FR-10): okna
tylko wstecz, bez dostępu do niczego po wierszu t. Każda cecha musi mieć wpis w `cechy/rejestr.yaml`
i przejść `cechy.przeciek.sprawdz_przeciek` (R7) — bez tego nie trafia do modelu.

Konwencja czasu: wiersz d ramki dziennej = informacja znana na KONIEC dnia d UTC (tak jak w
`modele.zmiennosc`: cechy z wiersza t prognozują dzień t+1). Opóźnienie publikacji to liczba dni,
o którą wartość trafia do wiersza później, niż wynika z jej własnego dnia.

RV (`rv_*`): komponenty HAR jak w `modele.zmiennosc.cechy_har` (logarytm RV, średnie z 7 i 30 dni —
tydzień krypto = 7 dni), policzone tu, bez importu z `modele/` (warstwy: dane → cechy → modele);
zgodność z `cechy_har` pilnuje test parytetu. Wejście: ramka dzienna z `dane.rv.rv_dzienna`
(kolumny `rv`, `n_swiec`), opóźnienie 0: RV dnia d jest znana o północy UTC. Dzień jest WAŻNY
(Poprawka 1 F2-1, `modele.run_f21`), gdy `n_swiec` ≥ 274 i `rv` > 0; dzień nieważny (martwe świece,
doba niepełna) daje NaN, nigdy −∞. Okna 7 i 30 dni są kalendarzowe: ramkę rozciągamy do pełnego
kalendarza dziennego, więc brakująca doba daje NaN w oknach, które ją obejmują. `cechy_har` na
ramce z brakującą dobą liczyłoby okno pozycyjne (rozciągnięte na 8 dni), więc na takich danych to
świadomie inny wariant, na danych bez dziur — ten sam co do bitu.

DVOL (`dvol_opozn`): świeca 1D ma znacznik otwarcia dnia d, a jej `close` powstaje dopiero na końcu
dnia d. Rozstrzygnięcie 010: wiersz d niesie `close` z dnia d−1, czyli opóźnienie 1 dzień (o dzień
więcej niż minimum, bo nie znamy opóźnienia publikacji API). To decyzja zachowawcza: wariant z
opóźnieniem 0 byłby osobnym wariantem (R2) i wymaga własnej pre-rejestracji. Wejście: kolumny
`timestamp` (UTC) i `close`, jak w parquet z `dane.deribit_dvol`.

Funding (`funding`): średnia dzienna stawek funding Binance z dnia d−1 w wierszu d (opóźnienie
1 dzień; moment publikacji stawki API nie podaje, więc 1 dzień jest zachowawcze). Wejście: kolumny
`timestamp` (UTC) i `funding_rate`, jak w danych alpha (`fetch_funding.FUNDING_COLUMNS`); zakładamy
siatkę 8h (00/08/16) — monety z interwałem 4h/1h mają inną liczbę stawek na dobę i taką ramkę
trzeba znormalizować przed użyciem (kod tego nie sprawdza). Dzień niepełny daje średnią z dostępnych
stawek; duplikaty znaczników to błąd. Masa punktowa: stawka bazowa to 31,4 % stawek 8h od 2021, ale
średnia dzienna ma tylko 19,8 %, więc `walidacja_progu_percentylowego` jej nie zatrzymuje — zakaz
progów percentylowych dla tej cechy zapisuje rejestr (`progi: absolutne`), a nie wynik walidacji.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from dane.rv import SWIEC_NA_DZIEN

OPOZNIENIE_DVOL_DNI = 1
OPOZNIENIE_FUNDING_DNI = 1
MIN_SWIEC_DNIA = math.ceil(0.95 * SWIEC_NA_DZIEN)  # dzień ważny: ≥ 274 z 288 świec 5m (F2-1, P1)
DZIEN = pd.Timedelta(days=1)


def _wymagaj(df: pd.DataFrame, *kolumny: str) -> None:
    for k in kolumny:
        if k not in df.columns:
            raise ValueError(f"wejście bez kolumny `{k}`")


def _log_rv_dzienny(df: pd.DataFrame) -> pd.Series:
    """log RV dni ważnych na pełnym kalendarzu dziennym (dzień nieważny lub brakujący = NaN)."""
    _wymagaj(df, "rv", "n_swiec")  # ramka dzienna z dane.rv.rv_dzienna
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex) or idx.hasnans or len(idx) == 0:
        raise ValueError("wejście RV: indeks dnia (DatetimeIndex, niepusty) jak z `rv_dzienna`")
    if not idx.is_unique or (idx != idx.floor("D")).any():
        raise ValueError("wejście RV: indeks ma być dzienny (północ UTC) i bez duplikatów")
    rv = df["rv"].astype(float)
    wazny = (df["n_swiec"] >= MIN_SWIEC_DNIA) & (rv > 0)
    kalendarz = pd.date_range(idx.min(), idx.max(), freq="D", name=idx.name)
    return np.log(rv.where(wazny)).reindex(kalendarz)


def compute_rv_dzien(df: pd.DataFrame) -> pd.Series:
    """log RV dnia d (składowa „d” HAR); dzień nieważny = NaN."""
    return _log_rv_dzienny(df).rename("rv_dzien")


def compute_rv_tydzien(df: pd.DataFrame) -> pd.Series:
    """Średnia log RV z 7 dni kalendarzowych kończących się na d (składowa „w” HAR)."""
    return _log_rv_dzienny(df).rolling(7).mean().rename("rv_tydzien")


def compute_rv_miesiac(df: pd.DataFrame) -> pd.Series:
    """Średnia log RV z 30 dni kalendarzowych kończących się na d (składowa „m” HAR)."""
    return _log_rv_dzienny(df).rolling(30).mean().rename("rv_miesiac")


def _po_dniach(df: pd.DataFrame, kolumna: str) -> pd.Series:
    """Szereg `kolumna` z indeksem = dzień UTC znacznika; duplikaty dni to błąd."""
    _wymagaj(df, "timestamp", kolumna)
    dzien = pd.DatetimeIndex(pd.to_datetime(df["timestamp"], utc=True)).floor("D")
    s = pd.Series(df[kolumna].to_numpy(dtype=float), index=dzien)
    if not s.index.is_unique:
        raise ValueError(f"duplikaty dni w `{kolumna}` — najpierw raport jakości danych")
    return s


def compute_dvol_opozn(df: pd.DataFrame) -> pd.Series:
    """`close` DVOL z dnia d−1 w wierszu d (indeks = dzień UTC znacznika, dziury zostają NaN)."""
    s = _po_dniach(df, "close")
    wynik = s.shift(freq=OPOZNIENIE_DVOL_DNI * DZIEN).reindex(s.index)
    return wynik.rename("dvol_opozn")


def compute_funding(df: pd.DataFrame) -> pd.Series:
    """Średnia stawek funding z dnia d−1 w wierszu d; kalendarz od pierwszego do ostatniego dnia."""
    _wymagaj(df, "timestamp", "funding_rate")
    if df.empty:
        raise ValueError("pusta ramka funding — nie ma z czego liczyć")
    znaczniki = pd.DatetimeIndex(pd.to_datetime(df["timestamp"], utc=True))
    if znaczniki.hasnans:
        raise ValueError("znaczniki funding z brakami (NaT)")
    if not znaczniki.is_unique:
        raise ValueError("duplikaty znaczników funding — najpierw raport jakości danych")
    stawki = pd.Series(df["funding_rate"].to_numpy(dtype=float), index=znaczniki)
    dzienna = stawki.groupby(stawki.index.floor("D")).mean()
    kalendarz = pd.date_range(dzienna.index.min(), dzienna.index.max(), freq="D")
    wynik = dzienna.reindex(kalendarz).shift(OPOZNIENIE_FUNDING_DNI)
    return wynik.rename("funding")
