# DQ1 — jakość świec Binance USDT-M 5m i 1d, top-20 od 2021 (zadanie 002)

> **Opis danych, nie hipoteza.** Licznik: **0 — POZA licznikami** (żadnych statystyk zwrotów ani modeli).
> Dane: `dane/manifest_binance_um.json` (skrypt `f1b0e58`, 17 380 plików źródłowych z sumą SHA-256 zgodną
> z `.CHECKSUM` Binance), skład `dane/sklad_top20.json`. Liczby: `raw_output.txt`
> (`python -m dane.podsumowanie_jakosci`).

## W skrócie — prostym językiem

Pobraliśmy ceny wszystkich 196 kontraktów, które od 2021 roku choć przez miesiąc były w top-20 Binance
(skład liczony na każdy miesiąc osobno, z kontraktami już wycofanymi — lekcja RU1). Dane są czyste: nie
ma duplikatów ani świec z niemożliwymi cenami, a BTC w dniu krachu 2021-05-19 pokazuje dokładnie znany
zakres (28 688 – 43 616). Są dwie rzeczy, o których każda runda musi wiedzieć:

1. **Martwe ogony.** Po wycofaniu kontraktu archiwum Binance dalej publikuje świece, ale z zerowym obrotem
   i stałą ceną. Dotyczy 33 z 196 symboli (np. FTT od 2022-11-15, FTM od 2025-01-07, MATIC od 2024-09-05).
   Kto weźmie je za handel, zobaczy „dni bez żadnych wahań” — to fałsz. Takie dni trzeba traktować jak brak
   danych (runda F2-1 robi to Poprawką 1).
2. **Wspólne dziury archiwum.** Dla wielu altcoinów brakuje dni 2022-02-26…28 i 2022-04-01…02 (BTC ma
   komplet). BNX ma dodatkowo 21 dni przerwy od 2023-02-01.

## Wynik

| | 1d | 5m |
|---|---|---|
| pary (symbol × interwał) | 196 | 196 |
| świece | 261 929 | 75 415 849 |
| duplikaty / niespójne OHLC | 0 / 0 | 0 / 0 |
| pary z dziurami | 36 | 37 |
| brakujące interwały | 198 dni | 57 291 świec |
| świece zerowe (wolumen 0 albo high = low) | 13 452 | 3 900 031 |
| skoki > 10 σ (σ odporne z MAD) | 1 221 | 299 192 |

- Świece zerowe to prawie w całości martwe ogony (np. FTT: 1 416 dni). W żywym handlu są rzadkie
  (BTC 5m: < 0,1 % w kwartale — przerwy techniczne).
- Skoki > 10 σ na 5m są częste, bo zwroty 5m mają bardzo grube ogony, a σ z MAD jest mała. To raport,
  nie filtr — nic nie usuwaliśmy.
- Błędy pobierania: 0 (pierwszy przebieg padł na symbolu „币安人生USDT” — poprawka `f1b0e58`, pełny drugi przebieg).

## Co na plus / na minus

- **+** Komplet 392 par, sumy SHA-256 każdego pliku źródłowego zgodne z Binance, kontrola pozytywna BTC ✓.
- **+** Uniwersum point-in-time z kontraktami wycofanymi — bez obciążenia „tylko ocalałe”.
- **−** Martwe ogony i wspólne dziury nie są oznaczone w samych plikach — każdy odczyt musi je obsłużyć
  jawnie (kandydat na wspólną funkcję w `dane/`, gdy pojawi się druga runda, która tego potrzebuje).
- **−** Top-50 (FR-01) jeszcze niepobrane — zrobimy, gdy runda będzie tego potrzebować (`--top 50`).

## Werdykt

**Ready** — dane nadają się do rund F2, pod warunkiem jawnej obsługi martwych ogonów i dziur.

Użyte skille: brak (opis danych; kontrole w kodzie i testach `tests/test_binance_vision.py`,
`tests/test_podsumowanie_jakosci.py`).
