---
id: 002
tytul: dane OHLCV 5m i 1d dla top-20/50 od 2021 z manifestem i raportem jakości
typ: zbieranie_danych
status: w_toku
zlecil: orkiestrator
decyzja_uzytkownika: "2026-09-30: „Rób co chcesz, ma działać” — zgoda na rekomendację D4"
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

2026-09-30: zablokowane w chmurze — polityka sieci środowiska odrzuca `data.binance.vision` (CONNECT 403),
a użytkownik nie ma w ustawieniach opcji Network access.

2026-10-01: kod gotowy i przetestowany bez sieci — `dane/binance_vision.py` (pobranie miesięcznych ZIP-ów
USDT-M, weryfikacja SHA-256 z `.CHECKSUM`, parquet per symbol, manifest, raport jakości bez poprawek,
kontrola pozytywna BTC 2021-05-19), 9 testów w `tests/test_binance_vision.py`. Brakuje uruchomienia
na maszynie z internetem.

### Jak uruchomić (maszyna z internetem, beta i alpha obok siebie)

```
git clone https://github.com/piotrgebala/beta && cd beta
git checkout claude/fervent-fermi-vfctk6        # do czasu scalenia PR #1
python -m pip install -r requirements-lock.txt
# wariant A — skład top-20 point-in-time z plików alpha (zalecany, jak RU1):
python -m dane.binance_vision --tf 5m 1d --uniwersum ../alpha/data/raw/universe_full --top 20
# wariant B — tylko podana lista (np. na próbę):
python -m dane.binance_vision --tf 5m 1d --symbole BTCUSDT ETHUSDT
```

Wynik: świece w `data/binance_um/` (poza gitem, kilka GB dla 5m), `dane/manifest_binance_um.json`
(SHA-256 każdego pliku, zakresy, raport jakości) i przy wariancie A `dane/sklad_top20.json`.
Do repo wracają manifest i skład (commit), nie świece.
