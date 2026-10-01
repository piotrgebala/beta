# F2-1 — HAR-RV vs prognoza zmienności dziennika alpha (QLIKE, 1 dzień, 20 monet)

> **STATUS: PRE-REJESTRACJA (zapisana 2026-10-01, PRZED pobraniem danych).** Przebieg na serwerze z danymi
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

## Oczekiwania zapisane z góry (opis, nie kryterium)

- W świecie generatora LM1 HAR bije EWMA 60 o δ ≈ 0,09–0,12 (5 monet × 20 000 dni), N_eff/n ≈ 0,5–0,64.
- Przy danych od 2021-01 i 365 dniach treningu OOS ma ~1 600 dni (mniej niż ~2 100 ze szkicu PRD), więc
  MDE ≈ 2,8 / √(1 600 · N_eff/n) ≈ 0,09–0,12 — wynik bramki może wypaść po każdej stronie progu.
