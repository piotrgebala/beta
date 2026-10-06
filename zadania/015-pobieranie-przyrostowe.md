---
id: 015
tytul: pobieranie Binance przyrostowe (tylko nowe miesiące) i aktualizacja składu top-20 po 2026-06
typ: infra
status: nowe
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

(dopisuje orkiestrator)
