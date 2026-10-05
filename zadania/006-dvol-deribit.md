---
id: 006
tytul: DVOL (Deribit) BTC i ETH — dzienne dane z manifestem i raportem jakości
typ: zbieranie_danych
status: w_toku
zlecil: uzytkownik
decyzja_uzytkownika: "2026-10-05: D6 — „dodaj [...] dane o oczekiwanych wahaniach z giełdy Deribit” (rekomendacja PRD: tylko DVOL)"
utworzono: 2026-10-05
zalezy_od: []
budzet: "Opus, część sesji na serwerze"
---

# 006 — DVOL z Deribit

## Po co

DVOL to indeks zmienności oczekiwanej przez rynek opcji Deribit (odpowiednik VIX dla BTC i ETH). W drabinie
modeli F2 (PRD §8, szczebel 5) to kandydat na zmienną zewnętrzną do HAR-RV. Decyzja D6: tylko DVOL,
pełne dane opcyjne dopiero, gdy F2 pokaże wartość.

## Zakres

- Publiczne API Deribit `public/get_volatility_index_data`, rozdzielczość 1D (świeca UTC 00:00–24:00,
  zgodna z dniami Binance), BTC i ETH — tylko te dwie mają ciągły DVOL (SOL był 2022-05…2022-11 i zniknął).
- Dostępność: od 2021-03-24 (start indeksu); R16 obcina i tak do 2021-01-01.
- Zapis parquet per waluta poza gitem (`data/deribit_dvol/`), manifest w repo: SHA-256 plików, zakres,
  źródło, wersja skryptu, raport jakości (dziury, duplikaty, wartości poza 0–400, niespójne OHLC) bez poprawek.
- Kontrola pozytywna: krach 2021-05-19 — DVOL BTC tego dnia powyżej 100.

## Czego NIE robić

Żadnych modeli ani statystyk przewidywania. Użycie DVOL w modelu = osobna runda z pre-rejestracją
i licznikiem „nowe źródło danych” (PRD §11.4). Bez pełnych danych opcyjnych (płatne, D6).

## Kryteria odbioru (dowody)

Testy bez sieci (atrapa API), manifest `dane/manifest_deribit_dvol.json` w repo, kontrola pozytywna w manifeście.

## Wynik

(dopisuje orkiestrator)
