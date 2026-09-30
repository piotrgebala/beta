# NC1B — kontrola negatywna przyrządu `miara` odtworzona w beta (2026-09-30)

> **STATUS: PRE-REJESTRACJA (przed przebiegiem).**

## W skrócie — prostym językiem

Sprawdzamy nie strategię, tylko **przeniesione do beta narzędzia pomiarowe**. Generator sztucznych cen
(przeniesiony z alpha) daje ceny podobne do krypto, ale z definicji bez przewidywalnego kierunku. Dwie
proste reguły (trend tygodniowy i momentum przekrojowe) muszą na nich pokazać „zero w granicach szumu”,
a ta sama reguła celowo oszukująca (zna przyszły tydzień) — ogromny „zysk”. Jeśli tak — przyrząd w beta
liczy t tak jak w alpha i umie złapać zajrzenie w przyszłość.

## Metadane

- Zadanie 001 (etap E0, `docs/PRD.md` §12: „kontrola negatywna NC1 odtworzona w nowym repo”).
- Moduł `miara/kontrola_negatywna.py` (generator = port 1:1 alpha, parytet w `tests/test_parytet_alpha.py`;
  reguły `regula_trendu`, `regula_przekrojowa` — nowe w beta, test leakage w `tests/test_miara.py`).
- Skrypt `miara/run_nc1b.py`; komenda `python -m miara.run_nc1b` → `raw_output.txt`.
- Dane: WYŁĄCZNIE syntetyczne (R16 nie dotyczy). 40 losowań (ziarna 0–39) × 20 monet × 2 000 dni,
  parametry jak alpha NC1: t-Student df 3, GARCH(1,1) α 0,08 β 0,90, ρ 0,5, zmienność 4 %/dzień.
- Wzorzec: alpha `runs/2026-09-24_nc1-kontrola-negatywna` (wniosek 79): fałszywe alarmy brutto 4/120 =
  3,3 % [Wilson 1,3; 8,3], czułość t +13…+30 w 40/40.

## Pre-rejestracja (zapisana przed przebiegiem)

- **Mechanizm (R1):** brak — to kalibracja przyrządu; po drugiej stronie nikt nie traci, bo nie ma
  informacji do wykorzystania.
- **Mierzone:** t_neff (`miara.neff.summarize_pnl`, N_eff ∈ [1, n], 365 okresów/rok, kapitał 1)
  dziennego zwrotu BRUTTO każdej reguły na każdym losowaniu.
- **Reguły:** R-TS = `regula_trendu` (znak zwrotu 7 dni, równe wagi, pozycja od następnego dnia);
  R-XS = `regula_przekrojowa` (long top 5 / short bottom 5 z 20 po zwrocie 7 dni, po 0,5 kapitału na nogę).
  Obie bez kosztów (kontrola dotyczy przecieku i rachuby zwrotu, koszty tylko odejmują).
- **Kryterium ZALICZENIA (każda reguła):** |średnia t_neff z 40 losowań| < 0,5 ORAZ liczba losowań
  z |t_neff| > 1,96 ≤ 5 z 40 (dwumian n = 40, p = 0,05: P(X ≥ 6) ≈ 4 %) — te same progi co alpha NC1.
- **Zgodność z alpha:** łączny odsetek fałszywych alarmów (80 losowań) z przedziałem Wilsona 95 %;
  raportowany obok alpha 3,3 % [1,3; 8,3] (opis, nie kryterium).
- **Kontrola CZUŁOŚCI:** obie reguły z `peek=True` (znak / ranking po zwrocie NASTĘPNYCH 7 dni) —
  zaliczenie, gdy t_neff > 5 na każdym z 40 losowań. Jeśli nie — kontrola jest ślepa.
- **Niezaliczenie** = błąd przyrządu `miara` do znalezienia przed jakąkolwiek rundą w beta.
- **Liczniki (zasada 22):** 0 wariantów, POZA licznikami — dane syntetyczne, żaden odczyt historii;
  rejestr alpha `odczyty_historii.csv` NIE jest podbijany (i nie jest zmieniany — zasada 23).
