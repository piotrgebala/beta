---
id: 010
tytul: rejestr cech + automatyczny test przecieku (FR-10…13)
typ: infra
status: nowe
zlecil: uzytkownik
decyzja_uzytkownika: "2026-10-05: „rozpisz sobie kolejne taski, zaplanuj i zacznij realizować” + akceptacja planu (007–012)"
utworzono: 2026-10-05
zalezy_od: []
budzet: "Opus, 1 sesja"
---

# 010 — rejestr cech i test przecieku

## Po co

R7 i FR-11: cecha bez testu przecieku nie trafia do modelu. Potrzebne przed HAR-X (DVOL, funding) i torem F5.

## Zakres

- `cechy/rejestr.yaml`: nazwa, zbiór informacyjny, opóźnienie publikacji, data dodania, runda.
- `cechy/zmiennosc.py`: czyste funkcje `compute_<nazwa>(df) -> pd.Series` (RV dzień/tydzień/miesiąc, DVOL
  z opóźnieniem, funding), okna tylko wstecz.
- Jeden test przechodzący po CAŁYM rejestrze: zmiana danych po t nie zmienia wartości cechy w t (FR-11);
  test masy punktowej (FR-12).

## Czego NIE robić

Żadnych modeli ani odczytów.

## Kryteria odbioru (dowody)

Test rejestru zielony; cecha z celowym przeciekiem (kontrola pozytywna) jest przez test złapana.

## Wynik

(dopisuje orkiestrator)
