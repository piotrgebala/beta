---
id: 014
tytul: wspólna obsługa martwych ogonów i dziur archiwum w danych 5m (dni ważne)
typ: infra
status: nowe
zlecil: orkiestrator
decyzja_uzytkownika: "2026-10-05: akceptacja zaktualizowanej listy zadań (plan „sprawdź, co jest zrobione, i zaktualizuj listę”)"
utworzono: 2026-10-05
zalezy_od: [002]
budzet: "Opus, część sesji"
---

# 014 — dni ważne w danych 5m

## Po co

DQ1: 33 z 196 symboli ma „martwy ogon” (świece po wycofaniu kontraktu, wolumen 0, stała cena), a wiele altcoinów
ma wspólne dziury archiwum (2022-02-26…28, 2022-04-01…02). F2-1 obsłużyła to łatką w `modele/run_f21.py`
(Poprawka 1: RV = 0 → dzień nieważny). Każda kolejna runda na danych 5m potrzebuje tego samego — jedna funkcja
zamiast kopii (wniosek z DQ1).

## Zakres

- Funkcja w `dane/` (np. `dane/dni.py::dni_wazne(df5m, min_swiec=274)`) zwracająca dla każdego dnia UTC:
  liczbę świec, wolumen, flagę „martwy” (wolumen 0 / brak zmiany ceny) i flagę „po dziurze” (pierwszy dzień
  po brakującym dniu — RV zawiera kilkudniowy zwrot).
- Testy: martwy ogon, dziura, pełny dzień, dzień niepełny; zgodność z wynikiem Poprawki 1 F2-1 na tych samych
  danych (ta sama lista ważnych dni → te same liczby rundy).
- `modele/run_f21.py` zostaje bez zmian (runda zamknięta) — nowe rundy używają funkcji z `dane/`.

## Czego NIE robić

Żadnych poprawek danych (bez cichych napraw) — tylko jawna klasyfikacja dni; decyzję o użyciu podejmuje runda.

## Kryteria odbioru (dowody)

Testy zielone; na prawdziwych danych liczba martwych dni zgodna z DQ1 (np. FTMUSDT 632, MATICUSDT 7).

## Wynik

(dopisuje orkiestrator)
