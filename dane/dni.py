"""
dni.py — który dzień danych 5m nadaje się do liczenia zmienności (zadanie 014).

Prosto: dzień jest „ważny", gdy ma prawie komplet świec (274 z 288) i cena się w nim ruszała.
Dzień „martwy" to dzień bez handlu: po wycofaniu kontraktu archiwum dalej podaje świece o stałej
cenie i wolumenie 0 (tzw. martwy ogon). Dzień „po dziurze" następuje zaraz po dniu bez żadnej
świecy; jego zmienność dnia (RV, suma kwadratów zwrotów 5m) zawiera zwrot z kilku dni naraz.

Jedna funkcja zamiast kopii łatki z F2-1 (`modele/run_f21.py`, Poprawka 1). Nic nie poprawia
i nie usuwa — tylko oznacza dni; o użyciu decyduje runda (pre-rejestracja). Wejście z błędną
strefą czasu, brakami albo nieskończonościami jest odrzucane głośno (ValueError), nie naprawiane.

Domyślnie `wazny` = dokładnie dzień ważny z Poprawki 1 F2-1: `n_swiec >= 274` i `rv > 0`. Flaga
`po_dziurze` jest osobna i wyklucza dopiero na życzenie (`wyklucz_po_dziurze=True`), bo runda F2-1
jest zamknięta i jej liczby nie mogą się zmienić.

    python -m dane.dni > runs/2026-10-05_dq1-jakosc-binance/dni_wazne_output.txt
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from dane.ladowanie import wczytaj_swiece
from dane.podsumowanie_jakosci import martwy_ogon
from dane.rv import SWIEC_NA_DZIEN, rv_dzienna

MIN_SWIEC = math.ceil(0.95 * SWIEC_NA_DZIEN)  # 274 z 288 — tak samo jak w F2-1
ROOT = Path(__file__).resolve().parents[1]
KATALOG_DANYCH = ROOT / "data" / "binance_um"
SKLAD_TOP20 = ROOT / "dane" / "sklad_top20.json"
STREFY_UTC = ("UTC", "Etc/UTC")


def _sprawdz_wejscie(df5m: pd.DataFrame, min_swiec: int) -> None:
    """Odrzuca głośno wejście, które dałoby ciche błędy klasyfikacji (nic nie naprawia)."""
    ok = isinstance(min_swiec, (int, np.integer)) and not isinstance(min_swiec, bool)
    if not ok or not 1 <= min_swiec <= SWIEC_NA_DZIEN:
        raise ValueError(f"min_swiec: liczba całkowita 1..{SWIEC_NA_DZIEN}, jest {min_swiec!r}")
    if df5m.empty:
        raise ValueError("pusty df5m — nie ma czego klasyfikować")
    brak = [k for k in ("timestamp", "close", "volume") if k not in df5m.columns]
    if brak:
        raise ValueError(f"df5m bez kolumn {brak} — potrzebne `timestamp`, `close`, `volume`")
    ts = df5m["timestamp"]
    if not pd.api.types.is_datetime64_any_dtype(ts):
        raise ValueError("`timestamp` musi być czasem (datetime) w UTC")
    if str(ts.dt.tz) not in STREFY_UTC:
        raise ValueError(f"`timestamp` musi mieć strefę UTC (doba UTC), jest: {ts.dt.tz}")
    if ts.isna().any():
        raise ValueError("`timestamp` z brakami (NaT)")
    close = df5m["close"].to_numpy(dtype=float)
    if not (np.isfinite(close).all() and (close > 0).all()):
        raise ValueError("`close` musi być skończone i > 0 — najpierw raport jakości danych")
    vol = df5m["volume"].to_numpy(dtype=float)
    if not (np.isfinite(vol).all() and (vol >= 0).all()):
        raise ValueError("`volume` musi być skończone i >= 0 — najpierw raport jakości danych")


def dni_wazne(
    df5m: pd.DataFrame, min_swiec: int = MIN_SWIEC, wyklucz_po_dziurze: bool = False
) -> pd.DataFrame:
    """
    Świece 5m (`timestamp` w UTC, `close` > 0, `volume` >= 0, bez braków) → jeden wiersz na KAŻDY
    dzień kalendarzowy UTC od pierwszego do ostatniego dnia danych (indeks `day`). Dni całkowicie
    bez świec (dziura archiwum), których `rv_dzienna` nie zwraca, dostają `n_swiec = 0`,
    `wolumen = 0`, `rv = NaN`. Wejście spoza tego kontraktu (inna strefa, NaN, inf, `close <= 0`,
    `min_swiec` poza 1..288) → ValueError: cicho źle sklasyfikowany dzień byłby gorszy niż błąd.

    Kolumny:
    - `n_swiec`, `wolumen` (suma `volume` dnia), `rv` (z `rv_dzienna` bez zmian; 1. dzień NaN);
    - `martwy`: dzień ze świecami (`n_swiec > 0`), w którym `rv == 0` ALBO `wolumen == 0`
      (dokładne zera, bez tolerancji).
      `rv == 0` (kryterium F2-1): żadna świeca nie zmieniła zamknięcia, więc log RV = −∞; liczy się
      bez kolumny obrotu, może trafić dzień z obrotem > 0 i stałą ceną, nie ocenia pierwszego dnia
      historii (rv NaN). `wolumen == 0` (kryterium DQ1 na danych 1d, `dni_bez_obrotu`): brak
      jakiegokolwiek obrotu, także gdy cena skoczyła. Oba warunki łączy `OR`, bo oba znaczą „to
      nie był handel". Dzień bez świec nie jest martwy — jest brakiem danych (`n_swiec == 0`).
      Uwaga o wolumenie: o ZERZE suma 5m i świeca 1d zgadzają się, ale w niezerowych dniach nie
      zawsze (DQ1: 600 dni u 161 symboli; 549 z nich to 6 dat wspólnych dla wielu symboli, np.
      2025-01-29 u 146; różnica do ok. 2x, wszystkie te dni mają 288 świec). Przyczyna otwarta —
      rundy używające wolumenu NOMINALNIE nie powinny ufać dokładnej wartości;
    - `po_dziurze`: dzień ze świecami, którego poprzedni dzień kalendarzowy ma `n_swiec == 0`;
      `rv_dzienna` liczy jego pierwszy zwrot od ostatniego zamknięcia PRZED dziurą, więc RV
      zawiera zwrot z kilku dni. Dni bez świec flagi nie dostają (nie mają RV). Flaga łapie
      TYLKO dziury całodobowe: dziura w środku doby, po której zostaje < `min_swiec` świec,
      łapie się w `niepelny`, ale krótka dziura (domyślnie do 14 świec) albo dziura kończąca się
      o północy zostawia kolejny dzień ważnym i bez flagi (jego RV ma wtedy zwrot z kilku godzin).
      Flaga nie obejmuje
      też dnia po martwym segmencie (kilka dni stałej ceny i wolumenu 0 ZE świecami): w danych jest
      jeden taki przypadek, PUMPUSDT 2025-06-14..2025-07-09, a dzień wznowienia 2025-07-10 ma
      198 świec, więc i tak jest `niepelny`;
    - `niepelny`: `n_swiec < min_swiec`;
    - `wazny`: `n_swiec >= min_swiec` i `rv > 0` (NaN → nieważny), a przy
      `wyklucz_po_dziurze=True` także nie `po_dziurze`. Nie patrzy na `martwy`: dzień z wolumenem 0
      i `rv > 0` (w danych nie występuje) byłby martwy, a ważny jak w F2-1; kto chce go odciąć,
      bierze `wazny & ~martwy`.

    Klasyfikacja dnia zależy tylko od danych do tego dnia włącznie i od liczby świec dnia
    poprzedniego — dopisanie późniejszych dni jej nie zmienia (brak przecieku z przyszłości).
    """
    _sprawdz_wejscie(df5m, min_swiec)
    d = rv_dzienna(df5m)  # rzuca ValueError przy duplikatach
    wolumen = df5m.groupby(df5m["timestamp"].dt.floor("D"))["volume"].sum()
    kalendarz = pd.date_range(d.index.min(), d.index.max(), freq="D")
    out = pd.DataFrame({"n_swiec": d["n_swiec"], "wolumen": wolumen, "rv": d["rv"]}).reindex(
        kalendarz
    )
    out.index.name = "day"
    out["n_swiec"] = out["n_swiec"].fillna(0).astype(int)
    out["wolumen"] = out["wolumen"].fillna(0.0)
    ma_swiece = out["n_swiec"] > 0
    out["martwy"] = ma_swiece & ((out["rv"] == 0) | (out["wolumen"] == 0))
    out["po_dziurze"] = ma_swiece & (out["n_swiec"].shift(1) == 0)
    out["niepelny"] = out["n_swiec"] < min_swiec
    out["wazny"] = (out["n_swiec"] >= min_swiec) & (out["rv"] > 0)
    if wyklucz_po_dziurze:
        out["wazny"] &= ~out["po_dziurze"]
    return out[["n_swiec", "wolumen", "rv", "martwy", "po_dziurze", "niepelny", "wazny"]]


def podsumowanie_dni(dni: pd.DataFrame) -> dict[str, int]:
    """Liczby dni z wyniku `dni_wazne`: kalendarz, ważne, martwe, po dziurze, niepełne (raporty)."""
    return {
        "dni": len(dni),
        "wazne": int(dni["wazny"].sum()),
        "martwe": int(dni["martwy"].sum()),
        "po_dziurze": int(dni["po_dziurze"].sum()),
        "niepelne": int(dni["niepelny"].sum()),
        "bez_swiec": int((dni["n_swiec"] == 0).sum()),
        "wazne_po_dziurze": int((dni["wazny"] & dni["po_dziurze"]).sum()),
    }


def _dni_z_poprawki1(df5m: pd.DataFrame, min_swiec: int) -> set[pd.Timestamp]:
    """
    Lista dni ważnych wg Poprawki 1 F2-1 — kopia maski z `modele.run_f21.straty_monety`, trzymana
    tu, żeby warstwa danych nie zależała od modeli. Zgodność z oryginałem pilnuje
    `tests/test_dni.py` (wywołuje prawdziwe `straty_monety`).
    """
    d = rv_dzienna(df5m)
    rv = d["rv"].where((d["n_swiec"] >= min_swiec) & (d["rv"] > 0))
    return set(rv.index[rv.notna()])


def analiza_symbolu(symbol: str, dir_5m: Path, dir_1d: Path, min_swiec: int = MIN_SWIEC) -> dict:
    """Jeden symbol: klasyfikacja 5m, porównanie martwych dni z 1d (DQ1) i z listą Poprawki 1."""
    df = wczytaj_swiece(dir_5m / f"{symbol}.parquet")
    dni = dni_wazne(df, min_swiec)
    d1 = wczytaj_swiece(dir_1d / f"{symbol}.parquet")
    martwe_5m = set(dni.index[dni["martwy"]])
    bez_obrotu_1d = set(d1["timestamp"].dt.floor("D")[d1["volume"] == 0])
    ma = dni["n_swiec"] > 0
    v1 = d1.set_index(d1["timestamp"].dt.floor("D"))["volume"]
    wspolne = dni.index[ma].intersection(v1.index)
    wol_rozny = int(((dni.loc[wspolne, "wolumen"] - v1[wspolne]).abs() > 1e-6 * v1[wspolne]).sum())
    ostatni = dni.iloc[-1]
    p1 = _dni_z_poprawki1(df, min_swiec)
    return {
        "symbol": symbol,
        **podsumowanie_dni(dni),
        "wolumen0": int((ma & (dni["wolumen"] == 0)).sum()),
        "rv0": int((ma & (dni["rv"] == 0)).sum()),
        "oba": int((ma & (dni["wolumen"] == 0) & (dni["rv"] == 0)).sum()),
        "bez_obrotu_1d": martwy_ogon(d1)["dni_bez_obrotu"],
        "tylko_5m": len(martwe_5m - bez_obrotu_1d),
        "tylko_1d": len(bez_obrotu_1d - martwe_5m),
        "dni_tylko_w_1d": len(set(d1["timestamp"].dt.floor("D")) - set(dni.index[ma])),
        "wol_rozny": wol_rozny,
        "ostatni_dzien": str(dni.index[-1].date()),
        "ostatni_n_swiec": int(ostatni["n_swiec"]),
        "p1_wazne": len(p1),
        "p1_roznice": len(p1 ^ set(dni.index[dni["wazny"]])),
    }


def raport(dir_5m: Path, dir_1d: Path, monety_f21: list[str]) -> list[str]:
    """Wydruk neutralny (same liczby): martwe dni vs DQ1, parytet z Poprawką 1, tabela symboli."""
    symbole = sorted(p.stem for p in dir_5m.glob("*.parquet"))
    wyniki = pd.DataFrame([analiza_symbolu(s, dir_5m, dir_1d) for s in symbole]).set_index("symbol")
    f21 = wyniki.loc[monety_f21]
    out = [
        f"Dni ważne w danych 5m (zadanie 014): min_swiec = {MIN_SWIEC}, wyklucz_po_dziurze = False",
        f"Symboli w danych: {len(wyniki)}; monet F2-1: {len(f21)}",
        "",
        "(a) Martwe dni 5m (`martwy`) a DQ1 (`dni_bez_obrotu` z 1d)",
        "    wolumen0 / rv0 / oba: dni ze świecami z samym wolumenem = 0 / samym rv = 0 / z oboma;",
        "    tylko_5m / tylko_1d: dni martwe tylko wg 5m / tylko wg 1d; dni_tylko_w_1d: dni z",
        "    wierszem 1d bez świec 5m; wol_rozny: dni, w których suma wolumenu 5m różni się od",
        "    wolumenu 1d o > 1e-6 (względnie); ostatni_*: ostatni dzień danych i jego liczba świec",
    ]
    kol_a = ["martwe", "wolumen0", "rv0", "oba", "bez_obrotu_1d", "tylko_5m", "tylko_1d"]
    kol_a += ["dni_tylko_w_1d", "wol_rozny", "ostatni_dzien", "ostatni_n_swiec"]
    a = wyniki.loc[[s for s in ("FTMUSDT", "MATICUSDT") if s in wyniki.index], kol_a]
    out += a.to_string().splitlines()
    w = wyniki
    z_roznica = int(((w["tylko_5m"] + w["tylko_1d"]) > 0).sum())
    out.append(
        f"Wszystkie {len(w)} symboli: martwe 5m {w['martwe'].sum()}, dni_bez_obrotu 1d "
        f"{w['bez_obrotu_1d'].sum()}; dni tylko w 5m {w['tylko_5m'].sum()}, tylko w 1d "
        f"{w['tylko_1d'].sum()} (symboli z różnicą: {z_roznica})"
    )
    out.append(
        f"  dni obecne tylko w archiwum 1d: {w['dni_tylko_w_1d'].sum()}; dni z samym wolumen = 0 "
        f"(rv > 0): {(w['wolumen0'] - w['oba']).sum()}; z samym rv = 0 (wolumen > 0): "
        f"{(w['rv0'] - w['oba']).sum()}; dni z różnym wolumenem 5m vs 1d: "
        f"{w['wol_rozny'].sum()} (symboli: {int((w['wol_rozny'] > 0).sum())})"
    )
    out += [
        "",
        "(b) Zgodność z Poprawką 1 F2-1 (dzień ważny = co najmniej 274 świece i rv > 0)",
        f"    {len(f21)} monet F2-1: liczba dni ważnych (wazne), liczba wg listy Poprawki 1",
        "    (p1_wazne) i liczba dni, w których obie listy się różnią (p1_roznice)",
    ]
    b = f21[["wazne", "p1_wazne", "p1_roznice"]]
    out += b.to_string().splitlines()
    out.append(
        f"Parytet: {int((f21['p1_roznice'] == 0).sum())}/{len(f21)} symboli z identyczną listą "
        f"dni, suma różnic {int(f21['p1_roznice'].sum())}"
    )
    kol_c = ["dni", "wazne", "martwe", "po_dziurze", "niepelne", "bez_swiec", "wazne_po_dziurze"]
    out += ["", "(c) Dni na symbol (monety F2-1); niepelne zawiera dni bez świec (bez_swiec),"]
    out += ["    wazne_po_dziurze = dni ważne, które wyklucza wyklucz_po_dziurze=True"]
    c = pd.concat([f21[kol_c], f21[kol_c].sum().rename("RAZEM").to_frame().T.astype(int)])
    out += c.to_string().splitlines()
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Dni ważne w danych 5m — sprawdzenie na danych.")
    ap.add_argument("--dane", type=Path, default=KATALOG_DANYCH)
    ap.add_argument("--sklad", type=Path, default=SKLAD_TOP20)
    a = ap.parse_args(argv)
    from modele.run_f21 import wybierz_monety  # tylko do wyboru 20 monet F2-1 (parytet)

    monety = wybierz_monety(json.loads(a.sklad.read_text(encoding="utf-8")))
    print("\n".join(raport(a.dane / "5m", a.dane / "1d", monety)))


if __name__ == "__main__":
    main()
