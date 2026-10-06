---
id: 014
tytul: wspólna obsługa martwych ogonów i dziur archiwum w danych 5m (dni ważne)
typ: infra
status: do_przegladu
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

2026-10-05: `dane/dni.py::dni_wazne(df5m, min_swiec=274, wyklucz_po_dziurze=False)` + `tests/test_dni.py`
(commit 014). Kolumny: `n_swiec`, `wolumen`, `rv`, `martwy`, `po_dziurze`, `niepelny`, `wazny`;
dni całkowicie bez świec są wstawiane (n_swiec = 0). Domyślne `wazny` jest równe definicji z Poprawki 1 F2-1
(n_swiec ≥ 274, rv > 0, rv nie-NaN). CLI: `python -m dane.dni`; wynik na prawdziwych danych:
`runs/2026-10-05_dq1-jakosc-binance/dni_wazne_output.txt`.

- **Zgodność z DQ1:** martwe dni 5m = dni bez obrotu z 1d, 13 452 = 13 452 (FTMUSDT 632, MATICUSDT 7), 0 dni
  tylko w jednym z archiwów.
- **Parytet z Poprawką 1 F2-1:** 20/20 monet, identyczna lista dni ważnych (suma różnic 0).
- **Do wiedzy:** (1) `martwy` nie wpływa na `wazny` (używać `wazny & ~martwy`); (2) przerwa krótsza niż dzień
  przechodząca przez północ nie jest flagowana jako `po_dziurze`, jeśli brakuje ≤ 14 świec; (3) suma wolumenu 5m
  różni się od wolumenu 1d w 600 dniach (161 symboli) — przyczyny nie badano (nie wpływa na `wazny`);
  (4) test parytetu opiera się na przepisanej masce Poprawki 1 (runda zamknięta, kod `modele/run_f21.py` bez zmian).
- Przegląd: trzech niezależnych recenzentów z mutacjami, poprawki high/medium zastosowane. F2-1b (karta 011)
  używa tej funkcji.
