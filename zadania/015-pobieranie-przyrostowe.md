---
id: 015
tytul: pobieranie Binance przyrostowe (tylko nowe miesiące) i aktualizacja składu top-20 po 2026-06
typ: infra
status: do_przegladu
zlecil: orkiestrator
decyzja_uzytkownika: "brak (wniosek z zadania 012: automat miesięczny pobiera całą historię od nowa)"
utworzono: 2026-10-05
zalezy_od: [002, 012]
budzet: "Sonnet, 1 sesja"
---

# 015 — pobieranie przyrostowe

## Po co

Zadanie 012 (automat) w trybie `miesiac` woła `dane.binance_vision` z `--koniec <poprzedni miesiąc>`, a pobieranie
nie jest przyrostowe: za każdym razem ściąga całą historię od 2021-01 (ok. 35 min, 4,2 GB), nadpisuje pliki
w `data/` w miejscu (zapis nieatomowy) i przepisuje manifest ~6,4 MB, który trafia do gita. Skład top-20
pochodzi z `alpha/data/raw/universe_full`, który kończy się na 2026-06-30, więc nowe wejścia po czerwcu 2026
nie zostaną wzięte.

## Zakres

- Tryb przyrostowy w `dane/binance_vision.py`: pomijaj miesiące, które są już w manifeście z zgodną sumą
  SHA-256; pobieraj tylko brakujące; zapis przez plik tymczasowy + `os.replace` (atomowo).
- Manifest przyrostowy: dopisywanie wierszy, a nie przepisywanie całości; rozważyć podział manifestu na pliki
  roczne, żeby commit miesięczny był mały.
- Skład top-20 po 2026-06: źródło listy symboli (własne zapytanie do `exchangeInfo`/rankingu wolumenu albo
  rozszerzenie `universe_full` Poprawką w alpha — decyzja użytkownika, bo alpha jest tylko do odczytu).
- `narzedzia/automat.sh miesiac`: użyć trybu przyrostowego; zachować kontrolę kompletności miesiąca.

## Czego NIE robić

Żadnych cichych poprawek danych (reguła z `kolektory/CLAUDE.md`); nie zmieniać już pobranych plików z lat
2021–2026-06 (parytet z DQ1 i F2-1).

## Kryteria odbioru (dowody)

Testy bez sieci (wstrzykiwana funkcja pobierania, jak dotychczas); drugie uruchomienie nic nie pobiera i nie
zmienia manifestu; przerwane pobieranie nie zostawia uszkodzonego pliku; na prawdziwych danych SHA-256 plików
sprzed zmiany bez różnic.

## Wynik

2026-10-06: `dane/binance_vision.py --przyrostowo` + zapis atomowy (plik tymczasowy + `os.replace`, z zachowaniem
uprawnień) także w trybie pełnym; blokada katalogu danych (drugi równoczesny bieg kończy się błędem „zajęty”);
`narzedzia/automat.sh miesiac` używa trybu przyrostowego. 19 nowych testów bez sieci; cały zestaw 851 zielonych.

- **Zasada:** miesiąc uznany za pobrany tylko wtedy, gdy parquet na dysku ma SHA-256 z manifestu. Inaczej para
  trafia do `bledy` i zostaje nietknięta (bez cichej naprawy). Pobierane są tylko miesiące po ostatnim wpisie
  danej pary. Nakładające się świece = błąd pary, bez deduplikacji. Gdy nic nowego, manifest i pliki zostają bez
  zmian, więc automat nie robi commita.
- **Dowód na prawdziwych danych:** (1) bieg przyrostowy na prawdziwym manifeście do 2026-09 trwał 25 s
  (zamiast 32 min), pobrał 0 plików, a manifest ma ten sam SHA-256. (2) Na kopiach: stan „do 2026-08”
  (3 monety, 5m+1d) uzupełniony przyrostowo o 2026-09 daje 6 parquetów **bajt w bajt identycznych** z `data/`
  oraz te same wpisy manifestu. Drugi bieg nic nie pobiera.
- Przegląd: 2 niezależnych recenzentów (eksperyment na kopiach danych, mutacje). Najpoważniejsze znalezisko:
  podmiana pliku przed policzeniem raportu i sumy. Poprawione, z testem.
- **Do wiedzy:** (1) przerwany bieg (kill, brak pamięci, limit czasu) może zostawić podmienione parquety bez
  nowego manifestu. Wtedy następny bieg zgłosi błąd SHA, a naprawą jest ręczny bieg pełny (bez
  `--przyrostowo`, ~32 min). (2) Tryb przyrostowy nie zauważy, że Binance poprawił już pobrany miesiąc; widzi
  to tylko bieg pełny. (3) **Skład top-20 nadal kończy się na 2026-06** (`alpha/.../universe_full`): monety,
  które weszły do top-20 później, nie są pobierane. Zmiana wymaga Poprawki w alpha, czyli Twojej decyzji.
  (4) Identyczność bajtowa zależy od wersji pandas/pyarrow (zablokowane w `requirements-lock.txt`).
