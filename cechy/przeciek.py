"""
przeciek.py — bramka R7 / FR-11 / FR-12 dla cech: test przecieku przyszłości i test masy punktowej.

`sprawdz_przeciek` ma dwa tryby, oba w każdym punkcie cięcia T:
- ZAKŁÓCENIE: cechę liczymy na całych danych i na danych, w których WSZYSTKO po T (wszystkie
  kolumny, także tekst, bool i daty) zastąpiono śmieciami (losowe, odwrócone, przeskalowane,
  brak). Wynik dla etykiet ≤ T musi być identyczny co do bitu (NaN = NaN, także w jedną stronę:
  czysty NaN, a po zakłóceniu liczba, to różnica). Przy deklarowanym opóźnieniu L śmiecimy już
  od chwili T − L, więc test sprawdza też, że cecha nie pobiera danych świeższych, niż deklaruje
  rejestr.
- OBCIĘCIE: cechę liczymy na danych urwanych w T (`df` do T włącznie) i porównujemy z wynikiem na
  całości dla etykiet ≤ T. Łapie to, czego zakłócanie wartości nie widzi: zależność od długości
  próby, od końca próby, od przyszłych znaczników czasu i wypełnianie dziur do przodu (bfill,
  interpolate).
  Gdy T leży w dziurze, porównujemy etykiety tylko do ostatniego wiersza, jaki obcięte dane mają:
  cecha z kalendarzem sięgającym do końca danych nie ma czego liczyć za nim (to nie przeciek).

Konwencje:
- Oś czasu danych to kolumna `timestamp` (jeśli jest), inaczej indeks; musi rosnąć bez duplikatów.
  Punkt cięcia to POZYCJA wiersza (int) albo CHWILA (Timestamp, także w dziurze — brakujący wiersz
  nie jest pozycją, a przeciek przez wypełnianie siedzi właśnie tam; `ciecia` wylicza i wiersze, i
  dziury). Wynik cechy musi mieć indeks czasowy zgodny z osią danych (można grubszy: dzienny z 8h).
- Dla ramek dziennych wiersz d = informacja znana na koniec dnia d; dla siatek drobniejszych punkty
  cięcia wybieramy na ostatnim slocie pełnej doby (`ciecia(..., koniec_doby=True)`). Cięcie w środku
  doby ma sens tylko dla OBCIĘCIA cechy z opóźnieniem ≥ 1 doby (`punkty_obciecia`).
- Opóźnienie jest w jednostkach osi czasu: dni dla osi czasowej, wiersze dla osi liczbowej.
- Oś czasu nie jest zakłócana (cecha nie ma jej „zgadywać”); jej przyszłość widzi tylko OBCIĘCIE.
  Przeciek przez znaczniki czasu tej samej doby przy cięciu na końcu doby pozostaje poza zasięgiem.
- Cecha ma być czystą funkcją: nie zmienia wejścia i daje ten sam wynik przy ponownym wywołaniu.

`masa_punktowa` i `walidacja_progu_percentylowego`: progi percentylowe są zabronione, gdy jedna
wartość ma > 20 % obserwacji. Funding BTC: stawka bazowa to 31,4 % stawek 8h od 2021 (R16;
35,85 % od 2019 — liczba z PRD). Średnia dzienna dziedziczy ten atom, ale ma od 2021 tylko 19,8 %,
więc ta walidacja jej NIE zatrzymuje; zakaz dla takiej cechy zapisuje rejestr (`progi: absolutne`).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd

ZAKLOCENIA = ("losowe", "odwrocone", "skalowane", "nan")
OBCIECIE = "obciecie"
PROG_MASY = 0.20
DZIEN = pd.Timedelta(days=1)


@dataclass(frozen=True)
class Naruszenie:
    """Pierwsze naruszenie: wynik dla etykiety ≤ t zmienił się po zakłóceniu lub obcięciu po t."""

    punkt_ciecia: object
    czas_ciecia: object
    indeks: object
    zaklocenie: str
    wartosc_czysta: float
    wartosc_zaklocona: float

    def __str__(self) -> str:
        co = (
            "obcięcie danych po t"
            if self.zaklocenie == OBCIECIE
            else f"zakłócenie {self.zaklocenie!r}"
        )
        return (
            f"PRZECIEK: cięcie t={self.punkt_ciecia} ({self.czas_ciecia}), {co}: wynik w "
            f"{self.indeks} zmienił się {self.wartosc_czysta!r} → {self.wartosc_zaklocona!r}"
        )


class MasaPunktowaBlad(ValueError):
    """Próg percentylowy na szeregu z masą punktową powyżej limitu (FR-12)."""


def _os_czasu(df: pd.DataFrame) -> pd.Index:
    if "timestamp" in df.columns:
        osc = pd.Index(pd.to_datetime(df["timestamp"], utc=True))
    else:
        osc = df.index
    if osc.hasnans:
        raise ValueError("oś czasu danych ma braki (NaT/NaN)")
    if not (osc.is_unique and osc.is_monotonic_increasing):
        raise ValueError("oś czasu danych musi rosnąć bez duplikatów — posortuj wejście")
    return osc


def _odejmij(czas, opoznienie: float):
    """czas − opóźnienie; dni dla osi czasowej, jednostki indeksu dla liczbowej."""
    if isinstance(czas, pd.Timestamp):
        return czas - pd.Timedelta(days=opoznienie)
    return czas - opoznienie


def _czas_ciecia(osc: pd.Index, t):
    """Chwila cięcia: int = pozycja wiersza; Timestamp (oś czasowa) lub liczba (oś liczbowa)."""
    if isinstance(t, (int, np.integer)) and not isinstance(t, bool):
        if not 0 <= t < len(osc):
            raise ValueError(f"punkt cięcia {t} spoza [0, {len(osc) - 1}]")
        return osc[t]
    if isinstance(osc, pd.DatetimeIndex):
        czas = pd.Timestamp(t)
        if osc.tz is not None and czas.tzinfo is None:
            czas = czas.tz_localize(osc.tz)
        elif osc.tz is None and czas.tzinfo is not None:
            raise ValueError(f"punkt cięcia {t!r} ma strefę czasową, a oś danych nie")
    elif isinstance(t, (float, np.floating)):
        czas = float(t)
    else:
        raise TypeError(f"punkt cięcia {t!r}: oś liczbowa przyjmuje pozycję (int) lub liczbę")
    if czas < osc[0]:
        raise ValueError(f"punkt cięcia {t!r} przed pierwszym wierszem danych")
    return czas


def _zaklocona_kolumna(s: pd.Series, maska: np.ndarray, rodzaj: str, rng) -> pd.Series:
    """Kopia kolumny `s`, w której wiersze `maska` zastąpiono śmieciami danego rodzaju."""
    poz = np.flatnonzero(maska)
    if isinstance(s.dtype, pd.CategoricalDtype):
        s = s.astype(object)
    dt = s.dtype
    tyl = s.iloc[poz[::-1]]
    if pd.api.types.is_bool_dtype(dt):
        if rodzaj == "nan":
            s = s.astype("boolean")
        nowe = {
            "losowe": lambda: rng.random(len(poz)) < 0.5,
            "odwrocone": lambda: tyl.array,
            "skalowane": lambda: (~s.iloc[poz]).array,
            "nan": lambda: pd.NA,
        }[rodzaj]()
    elif pd.api.types.is_numeric_dtype(dt):
        x = s.to_numpy(dtype=float, na_value=np.nan, copy=True)
        przyszlosc = x[poz]
        if rodzaj == "losowe":
            baza = x[np.isfinite(x)]
            if len(baza) == 0:
                baza = np.ones(1)
            nowe = rng.choice(baza, size=len(poz)) * rng.uniform(0.1, 10.0, len(poz))
        elif rodzaj == "odwrocone":
            nowe = przyszlosc[::-1]
        elif rodzaj == "skalowane":
            nowe = przyszlosc * 7.3
        else:
            nowe = np.nan
        x[poz] = nowe
        return pd.Series(x, index=s.index, name=s.name)
    elif pd.api.types.is_datetime64_any_dtype(dt) or pd.api.types.is_timedelta64_dtype(dt):
        przesuniecie = pd.Timedelta(days=7) if pd.api.types.is_datetime64_any_dtype(dt) else 7.3
        nowe = {
            "losowe": lambda: _losowe_z_kolumny(s, poz, rng),
            "odwrocone": lambda: tyl.array,
            "skalowane": lambda: (
                (s.iloc[poz] + przesuniecie)
                if pd.api.types.is_datetime64_any_dtype(dt)
                else (s.iloc[poz] * przesuniecie)
            ).array,
            "nan": lambda: pd.NaT,
        }[rodzaj]()
    elif dt == object or pd.api.types.is_string_dtype(dt):
        nowe = {
            "losowe": lambda: _losowe_z_kolumny(s, poz, rng),
            "odwrocone": lambda: tyl.array,
            "skalowane": lambda: s.iloc[poz].astype(object).map(_dopisz_gwiazdke).array,
            "nan": lambda: None,
        }[rodzaj]()
    else:
        raise TypeError(f"kolumna {s.name!r} typu {dt}: brak zakłócenia — usuń ją z wejścia testu")
    out = s.copy()
    out.iloc[poz] = nowe
    return out


def _dopisz_gwiazdke(v):
    return v if pd.isna(v) else f"{v}*"


def _losowe_z_kolumny(s: pd.Series, poz: np.ndarray, rng):
    """Wartości wylosowane (ze zwracaniem) spośród niepustych wartości kolumny."""
    obserwowane = np.flatnonzero(s.notna().to_numpy())
    if len(obserwowane) == 0:
        return s.iloc[poz].array
    return s.iloc[rng.choice(obserwowane, size=len(poz))].array


def _zaklocony(df: pd.DataFrame, maska: np.ndarray, rodzaj: str, rng) -> pd.DataFrame:
    """Kopia `df`; w wierszach `maska` WSZYSTKIE kolumny (poza osią `timestamp`) to śmieci."""
    if rodzaj not in ZAKLOCENIA:
        raise ValueError(f"nieznany rodzaj zakłócenia {rodzaj!r}; dozwolone: {ZAKLOCENIA}")
    out = df.copy()
    for kol in df.columns:
        if kol != "timestamp":
            out[kol] = _zaklocona_kolumna(df[kol], maska, rodzaj, rng)
    return out


def _wynik(compute: Callable[[pd.DataFrame], pd.Series], df: pd.DataFrame, osc: pd.Index):
    """compute(df) z kontrolą kontraktu FR-10: Series liczbowa z indeksem czasu zgodnym z osią."""
    kopia = df.copy()
    s = compute(kopia)
    if not kopia.equals(df):
        raise ValueError("cecha zmienia swoje wejście — to nie jest czysta funkcja (FR-10)")
    if not isinstance(s, pd.Series):
        raise TypeError("cecha musi zwracać pd.Series (compute_<nazwa>(df) -> pd.Series)")
    if not pd.api.types.is_numeric_dtype(s):
        raise TypeError("cecha musi zwracać wartości liczbowe")
    if not s.index.is_unique:
        raise ValueError("wynik cechy ma zduplikowane etykiety indeksu — nie da się porównać")
    if isinstance(osc, pd.DatetimeIndex):
        if not isinstance(s.index, pd.DatetimeIndex) or (s.index.tz is None) != (osc.tz is None):
            raise TypeError(
                "oś czasu wyniku niezgodna z osią danych: cecha musi zwracać Series z indeksem "
                f"czasowym tej samej strefy (dane: {osc.dtype}, wynik: {s.index.dtype})"
            )
    elif isinstance(s.index, pd.DatetimeIndex):
        raise TypeError("wynik cechy ma indeks czasowy, a oś danych jest liczbowa")
    return s


def _pierwsza_roznica(a: pd.Series, b: pd.Series, rtol: float):
    """(pozycja, wartość a, wartość b) pierwszej różnicy na etykietach `a` albo None."""
    va = a.to_numpy(dtype=float)
    vb = b.reindex(a.index).to_numpy(dtype=float)
    zgodne = (np.isnan(va) & np.isnan(vb)) | (va == vb)
    if rtol:
        zgodne |= np.isclose(va, vb, rtol=rtol, atol=0.0)
    if zgodne.all():
        return None
    i = int(np.argmin(zgodne))  # pierwszy False = najwcześniejsza etykieta
    return a.index[i], float(va[i]), float(vb[i])


def _waliduj(punkty, opoznienie, zaklocenia, rtol) -> list:
    if opoznienie < 0:
        raise ValueError(f"opóźnienie ujemne ({opoznienie}) osłabia test do zera — dozwolone ≥ 0")
    if rtol < 0:
        raise ValueError("rtol ujemne")
    if isinstance(zaklocenia, str):
        raise TypeError(f"zaklocenia to krotka rodzajów, nie napis: {zaklocenia!r}")
    zaklocenia = tuple(zaklocenia)
    if not zaklocenia:
        raise ValueError("puste `zaklocenia` — test nic by nie sprawdził (użyj obciecie=True)")
    for rodzaj in zaklocenia:
        if rodzaj not in ZAKLOCENIA:
            raise ValueError(f"nieznany rodzaj zakłócenia {rodzaj!r}; dozwolone: {ZAKLOCENIA}")
    return list(punkty)


def sprawdz_przeciek(
    compute: Callable[[pd.DataFrame], pd.Series],
    df: pd.DataFrame,
    punkty_ciecia: Iterable,
    *,
    opoznienie: float = 0,
    zaklocenia=ZAKLOCENIA,
    ziarno: int = 0,
    rtol: float = 0.0,
    obciecie: bool = True,
    punkty_obciecia: Iterable | None = None,
) -> Naruszenie | None:
    """
    None, gdy cecha przeszła; inaczej pierwsze `Naruszenie` (najwcześniejsza różniąca się etykieta).
    Wartości mają być identyczne co do bitu (`rtol=0`). `punkty_obciecia` (domyślnie jak punkty
    cięcia) pozwala dla OBCIĘCIA użyć innych chwil, np. w środku doby. ValueError, gdy test byłby
    pusty (punkt cięcia bez niczego do zakłócenia, brak policzalnych wartości do porównania)
    albo argumenty go osłabiają (puste zakłócenia, ujemne opóźnienie, wejście nie jest czyste).
    """
    punkty = _waliduj(punkty_ciecia, opoznienie, zaklocenia, rtol)
    if not punkty:
        raise ValueError("brak punktów cięcia — test pusty")
    if not df.columns.is_unique:
        raise ValueError("kolumny wejścia muszą mieć unikalne nazwy")
    osc = _os_czasu(df)
    czyste = _wynik(compute, df, osc)
    if not czyste.equals(_wynik(compute, df, osc)):
        raise ValueError("cecha nie jest deterministyczna: dwa wywołania dały różne wyniki")
    porownan = 0
    for t in punkty:
        czas = _czas_ciecia(osc, t)
        maska = np.asarray(osc > _odejmij(czas, opoznienie))
        if not maska.any():
            raise ValueError(f"punkt cięcia {t}: nic po t − opóźnienie do zakłócenia (test pusty)")
        a = czyste[czyste.index <= czas]
        porownan += int(np.isfinite(a.to_numpy(dtype=float)).sum())
        poz = int(osc.searchsorted(czas))
        for k, rodzaj in enumerate(zaklocenia):
            rng = np.random.default_rng([ziarno, poz, int(czas not in osc), k])
            b = _wynik(compute, _zaklocony(df, maska, rodzaj, rng), osc)
            roznica = _pierwsza_roznica(a, b, rtol)
            if roznica is not None:
                return Naruszenie(t, czas, roznica[0], rodzaj, roznica[1], roznica[2])
    if obciecie:
        for t in punkty if punkty_obciecia is None else punkty_obciecia:
            czas = _czas_ciecia(osc, t)
            do_t = np.asarray(osc <= czas)
            czesc = df[do_t]
            b = _wynik(compute, czesc, osc[do_t])
            a = czyste[czyste.index <= osc[do_t][-1]]  # w dziurze: do ostatniego wiersza obciętych
            porownan += int(np.isfinite(a.to_numpy(dtype=float)).sum())
            roznica = _pierwsza_roznica(a, b, rtol)
            if roznica is not None:
                return Naruszenie(t, czas, roznica[0], OBCIECIE, roznica[1], roznica[2])
    if porownan == 0:
        raise ValueError("brak policzalnych wartości przed punktami cięcia — test pusty")
    return None


def ciecia(
    df: pd.DataFrame, *, ile: int | None = None, ziarno: int = 0, koniec_doby: bool = False
) -> list:
    """
    Punkty cięcia pokrywające całą próbę: każdy wiersz oprócz ostatniego ORAZ każdy slot dziury
    (brakujący wiersz — tam siedzi przeciek przez bfill/interpolate). `ile` ogranicza wiersze do
    losowej próbki o jawnym `ziarno` (dziury zostają wszystkie). `koniec_doby`: tylko ostatni slot
    każdej doby kalendarza, czyli cięcia dla siatek drobniejszych niż doba; doba bez żadnego
    wiersza jest dziurą i zostaje zawsze. Oś czasowa daje Timestampy, liczbowa — pozycje wierszy.
    """
    osc = _os_czasu(df)
    if len(osc) < 2:
        raise ValueError("za mało wierszy na punkty cięcia")
    rng = np.random.default_rng(ziarno)
    if not isinstance(osc, pd.DatetimeIndex):
        wiersze = list(range(len(osc) - 1))
        dziury: list = []
    else:
        krok = pd.Series(osc).diff().dropna().median()
        if koniec_doby:
            if krok > DZIEN:
                raise ValueError("koniec_doby wymaga siatki nie rzadszej niż doba")
            dni = pd.date_range(osc[0].floor("D"), osc[-1].floor("D"), freq="D")
            konce = dni + (DZIEN - krok)
            w_probie = np.asarray((osc[0] <= konce) & (konce < osc[-1]))
            ma_wiersze = np.asarray(dni.isin(osc.floor("D")))
            wiersze = list(konce[w_probie & ma_wiersze])
            # doba bez żadnego wiersza = dziura, zawsze w próbie
            dziury = list(konce[w_probie & ~ma_wiersze])
        else:
            wiersze = list(osc[:-1])
            odstepy = osc[1:] - osc[:-1]
            dziury = [
                osc[i] + j * krok
                for i in np.flatnonzero(odstepy > 1.5 * krok)
                for j in range(1, round(odstepy[i] / krok))
            ]
    if ile is not None and len(wiersze) > ile:
        wybrane = np.sort(rng.choice(len(wiersze), size=ile, replace=False))
        wiersze = [wiersze[i] for i in wybrane]
    return sorted({*wiersze, *dziury}) if dziury else wiersze


def _najczestsza(serie, miejsca: int | None) -> tuple[float, float]:
    x = pd.Series(np.asarray(serie, dtype=float)).dropna()
    if x.empty:
        raise ValueError("pusty szereg — masa punktowa nieokreślona")
    if miejsca is not None:
        x = x.round(miejsca)
    liczby = x.value_counts()
    return float(liczby.index[0]), float(liczby.iloc[0] / len(x))


def masa_punktowa(serie, miejsca: int | None = None) -> float:
    """
    Udział najczęstszej wartości wśród obserwacji niebędących NaN. `miejsca` zaokrągla przed
    zliczaniem (średnia kilku identycznych stawek bywa różna o ułamek ULP, a to jedna wartość).
    """
    return _najczestsza(serie, miejsca)[1]


def walidacja_progu_percentylowego(
    serie, prog_masy: float = PROG_MASY, miejsca: int | None = None
) -> float:
    """
    FR-12: zwraca masę punktową, gdy ≤ `prog_masy`; inaczej MasaPunktowaBlad — progu percentylowego
    na takim szeregu nie wolno używać (granica tkwi w atomie, nie w rozkładzie).
    """
    wartosc, masa = _najczestsza(serie, miejsca)
    if masa > prog_masy:
        raise MasaPunktowaBlad(
            f"progi percentylowe zabronione: {masa:.2%} obserwacji = {wartosc!r} "
            f"(limit {prog_masy:.0%}); użyj progu bezwzględnego"
        )
    return masa
