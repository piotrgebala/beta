"""
Pomocnik automatu (zadanie 012): kontrola, czy miesięczne pobranie Binance jest kompletne.

Po co: downloader traktuje brak pliku miesiąca (opóźniona publikacja) jak „symbolu nie było” i
kończy bez błędu — manifest „do 2026-09” mógłby powstać bez września. Tu to wychodzi na jaw.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

# Pary „kanarki”: BTC jest w top-20 cały okres, więc jej ostatnia świeca mówi, czy miesiąc jest.
PARY_KONTROLNE = ("BTCUSDT/5m", "BTCUSDT/1d")


def ostatni_dzien_miesiaca(miesiac: str) -> date:
    """Ostatni dzień miesiąca podanego jako RRRR-MM (ValueError przy złym formacie)."""
    rok, mies = (int(x) for x in miesiac.split("-"))
    date(rok, mies, 1)  # zły miesiąc (np. 13) kończy się tu ValueError
    nastepny = date(rok + (mies == 12), mies % 12 + 1, 1)
    return nastepny - timedelta(days=1)


def sprawdz_pobranie(manifest: Path, sklad: Path, miesiac: str) -> tuple[list[str], list[str]]:
    """Zwraca (błędy, ostrzeżenia): błąd = pobranie niekompletne, ostrzeżenie = stary skład."""
    bledy: list[str] = []
    ostrzezenia: list[str] = []
    koniec = ostatni_dzien_miesiaca(miesiac)
    try:
        dane = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"nie mogę odczytać manifestu {manifest}: {e}"], ostrzezenia
    if not isinstance(dane, dict) or not isinstance(dane.get("jakosc", {}), dict):
        return [f"manifest {manifest} ma nieoczekiwany układ"], ostrzezenia
    if dane.get("do") != miesiac:
        bledy.append(
            f"manifest ma do={dane.get('do')!r}, a oczekiwano {miesiac!r} (stary manifest?)"
        )
    jakosc = dane.get("jakosc", {})
    for para in PARY_KONTROLNE:
        ostatnia = (jakosc.get(para) or {}).get("do")
        if ostatnia is None:
            bledy.append(f"manifest nie ma pary kontrolnej {para}")
        elif str(ostatnia)[:10] < koniec.isoformat():
            bledy.append(
                f"{para}: ostatnia świeca {str(ostatnia)[:10]} < koniec miesiąca {koniec} "
                "(brak pliku miesiąca? opóźniona publikacja Binance)"
            )
    try:
        klucze = sorted(json.loads(sklad.read_text(encoding="utf-8")))
    except (OSError, ValueError) as e:
        ostrzezenia.append(f"nie mogę odczytać składu top-20 {sklad}: {e}")
    else:
        if not klucze or klucze[-1][:7] < miesiac:
            ostatni = klucze[-1][:7] if klucze else "(pusty)"
            ostrzezenia.append(
                f"skład top-20 kończy się na {ostatni}, a pobrano do {miesiac} "
                "(dane alpha nieodświeżone — nowe symbole nie wejdą do pobrania)"
            )
    return bledy, ostrzezenia


def kontrola_miesiaca(manifest: str, sklad: str, miesiac: str) -> int:
    """Wejście z linii poleceń automatu: drukuje wynik, zwraca kod wyjścia (0 = kompletne)."""
    try:
        bledy, ostrzezenia = sprawdz_pobranie(Path(manifest), Path(sklad), miesiac)
    except ValueError as e:
        print(f"BŁĄD: zły miesiąc {miesiac!r}: {e}")
        return 1
    for tekst in ostrzezenia:
        print(f"UWAGA: {tekst}")
    for tekst in bledy:
        print(f"BŁĄD: {tekst}")
    if not bledy:
        print(f"Pobranie do {miesiac} kompletne (kontrola: {', '.join(PARY_KONTROLNE)}).")
    return 1 if bledy else 0
