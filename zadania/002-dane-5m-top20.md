---
id: 002
tytul: dane OHLCV 5m i 1d dla top-20/50 od 2021 z manifestem i raportem jakości
typ: zbieranie_danych
status: czeka_na_decyzje
zlecil: orkiestrator
decyzja_uzytkownika: "brak (PRD D4)"
utworzono: 2026-09-30
zalezy_od: [001]
budzet: "Sonnet, 1 sesja"
---

# 002 — dane 5m/1d top-20/50

## Po co

HAR-RV i testy VaR/ES (filar F2) potrzebują zmienności zrealizowanej z danych 5m. Czeka na decyzję D4.

## Zakres

- Uniwersum point-in-time z pliku kompletnego alpha (`universe_full`, lekcja RU1), top-20 i top-50.
- Pobranie z archiwum `data.binance.vision` (klines 5m i 1d, perpetuale USDT-M) od 2021-01-01.
- Manifest: SHA-256 każdego pliku, zakres dat, źródło, wersja skryptu.
- Raport jakości: dziury, duplikaty, świece zerowe, skoki > k·σ — bez cichych poprawek.

## Czego NIE robić

Żadnych statystyk zwrotów ani modeli; dane poza repo (`data/` w `.gitignore`).

## Kryteria odbioru (dowody)

Manifest w repo; raport jakości w `runs/`; kontrola pozytywna: znany dzień (np. 2021-05-19) ma oczekiwany zakres ruchu BTC.

## Wynik

(dopisuje orkiestrator)
