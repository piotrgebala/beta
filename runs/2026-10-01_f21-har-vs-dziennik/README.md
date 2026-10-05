# F2-1 — HAR-RV vs prognoza zmienności dziennika alpha (QLIKE, 1 dzień, 20 monet)

> **STATUS: PRE-REJESTRACJA (zapisana 2026-10-01, PRZED pobraniem danych) + Poprawka 1 (2026-10-05, przed przebiegiem).** Przebieg na serwerze z danymi
> z zadania 002: `python -m modele.run_f21 > runs/2026-10-01_f21-har-vs-dziennik/raw_output.txt`.

## W skrócie — prostym językiem

Dziennik alpha ustala wielkość pozycji ze zmienności liczonej prostą średnią ważoną (EWMA). Pytamy, czy model
HAR, który patrzy na zmienność z 5-minutowych świec z ostatniego dnia, tygodnia i miesiąca, przewiduje
jutrzejszą zmienność lepiej. To pytanie o RYZYKO, nie o zysk — nie zużywa wspólnego budżetu odczytów
zwrotu alpha. Zanim spojrzymy na wynik, skrypt sprawdza, czy test w ogóle jest w stanie coś zobaczyć.

## Karta hipotezy (R1–R4)

- **Mechanizm (R1):** zmienność skupia się w czasie, bo rynek tworzą uczestnicy działający w różnych
  horyzontach (dzień, tydzień, miesiąc — Corsi 2009); dane 5m mierzą wczorajszą zmienność dokładniej niż
  kwadrat jednego zwrotu dziennego. „Kto traci”: nikt po drugiej stronie — to lepszy pomiar, nie transfer.
- **R2:** zbiór informacyjny = własne świece 5m (RV) i dzienne zamknięcia; formuła = HAR na log RV
  (okna 1 / 7 / 30 dni), osobno per moneta; target = RV dnia t+1 z 5m; horyzont = 1 dzień.
- **Baseline (R17):** DOKŁADNIE estymator dziennika — EWMA kwadratów prostych zwrotów dziennych, środek
  masy 60, min. 30 obserwacji (`alpha/backtest/ts_momentum.ewma_vol`); `modele/zmiennosc.prognoza_dziennik`.
  (Uwaga: PRD pisze „okno wstecz” — dziennik faktycznie używa EWMA 60, więc to ona jest baseline'em.)
- **Walk-forward (R6):** rosnące okno, refit co 30 dni, min. 365 dni treningu, para (cechy_t, cel_t+1)
  w treningu tylko gdy t+1 ≤ dzień refitu (purging horyzontu 1 dnia). Bez strojenia: okna 1/7/30 zamrożone
  (R18, 0 hiperparametrów do przeszukania).
- **Monety:** 20 symboli z największą liczbą miesięcy w składzie top-20 point-in-time od 2021-01
  (`dane/sklad_top20.json` z zadania 002; remis → alfabetycznie). Dzień ważny: ≥ 274 z 288 świec 5m.
  Dane od 2021-01-01 (R16, `dane.ladowanie.wczytaj_swiece`).
- **Przyrząd:** QLIKE (Patton 2011), DM z HAC Newey–West (`miara/dm.py`, kontrole w LM1: rozmiar 3,8 / 4,9 %).
  MSE log RV — opisowo.
- **Krok 1 — bramka mierzalności (R3):** MDE kryterium bootstrapem stacjonarnym (blok 30, 1 000 losowań)
  na CENTROWANEJ różnicy strat wspólnych dni, n = mediana dni OOS. MIERZALNA ⇔ MDE ≤ 0,10. Inaczej skrypt
  kończy bez testu DM i licznik się nie zmienia.
- **Krok 2 — kryterium POZYTYWNE (PRD §10.4):** DM t > 1,96 na korzyść HAR w ≥ 80 % monet (16 z 20) i żadna
  moneta z t < −1,96. Jedna para modeli → bez korekty Holma.
- **Kontrole:** leakage HAR i baseline (`tests/test_zmiennosc.py::test_bez_przecieku`), kontrola pozytywna
  na GARCH (`test_har_bije_dziennik_na_garch`), negatywna DM — LM1.
- **Licznik (zasada 22, PRD §11.4):** „zmienność 2021+”: 0 → 1 przy kroku 2; wspólny rejestr zwrotów alpha —
  bez zmian (pytanie o prognozę zmienności, nie o zwrot strategii).
- **STOP:** wynik niepozytywny → F2 wraca do ES/likwidacji (PRD E1); wynik pozytywny NIE zmienia dziennika —
  wpięcie = Poprawka w alpha + decyzja użytkownika (zasada 23); wartość ekonomiczna tylko prospektywnie.

## Poprawka 1 — 2026-10-05, PRZED przebiegiem (bez wglądu w straty)

Po pobraniu danych (zadanie 002, DQ1) i przed jakimkolwiek liczeniem strat wyszły dwie rzeczy, których
pre-rejestracja nie przewidziała. Sprawdzone były tylko daty i liczba ważnych dni — żadna strata ani różnica
strat nie była liczona ani oglądana.

- **P1 — martwe dni.** Po wycofaniu kontraktu archiwum Binance publikuje świece ze stałą ceną i wolumenem 0.
  Wśród 20 monet: FTMUSDT 632 takie dni od 2025-01-07, MATICUSDT 7 dni od 2024-09-05 (zamiana na POL). Taka
  doba ma pełne 288 świec, ale RV = 0 → log RV = −∞ psuje dopasowanie HAR. **Zmiana:** doba z RV = 0 jest
  nieważna, tak jak doba z < 274 świecami (`straty_monety`). Zestaw 20 monet bez zmian — FTM i MATIC mają po
  prostu krótszy OOS (do 2025-01-06 i 2024-09-04).
- **P2 — brak wspólnych dni.** Okresy OOS 20 monet nie mają części wspólnej: WIFUSDT zaczyna OOS 2025-02-17,
  MATICUSDT kończy 2024-09-04 (PEPE i SUI od 2024-06). Bramka „na różnicy strat wspólnych dni” nie ma więc na
  czym liczyć. **Zmiana:** bootstrap stacjonarny (blok 30, 1 000 losowań, ziarno 2101) idzie po kalendarzu
  SUMY dni OOS z brakami (`symulacje.moc_dm.moc_kryterium_braki`): te same indeksy dni dla wszystkich monet
  (korelacja zostaje tam, gdzie monety żyją razem), każda moneta liczy t ze swoich obecnych dni (n_j ≈ jej
  długość OOS, lag Neweya–Westa z n_j). Bez braków funkcja daje to samo co `moc_kryterium` (test
  `test_moc_braki_bez_brakow_rowna_sie_moc_kryterium`). N_eff/n i korelacja różnic — per moneta / parami.
  Próg MDE ≤ 0,10, krok 2 (DM per moneta na jej dniach) i kryterium 16/20 — **bez zmian**.

Kod poprawki: `modele/run_f21.py`, `symulacje/moc_dm.py`, testy `tests/test_zmiennosc.py`
(`test_f21_poprawka1_martwe_dni_i_rozlaczne_okresy`), `tests/test_dm_symulacje.py`. Hash commita poprawki:
w historii gita (commit „F2-1 Poprawka 1”) — przebieg dopiero po nim.

## Oczekiwania zapisane z góry (opis, nie kryterium)

- W świecie generatora LM1 HAR bije EWMA 60 o δ ≈ 0,09–0,12 (5 monet × 20 000 dni), N_eff/n ≈ 0,5–0,64.
- Przy danych od 2021-01 i 365 dniach treningu OOS ma ~1 600 dni (mniej niż ~2 100 ze szkicu PRD), więc
  MDE ≈ 2,8 / √(1 600 · N_eff/n) ≈ 0,09–0,12 — wynik bramki może wypaść po każdej stronie progu.
