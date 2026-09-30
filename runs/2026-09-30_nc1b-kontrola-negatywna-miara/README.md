# NC1B — kontrola negatywna przyrządu `miara` odtworzona w beta (2026-09-30)

> **STATUS: ZAMKNIĘTA — ZALICZONA.** Na danych bez informacji obie reguły dają t ≈ 0 (średnie −0,28 i
> −0,24; fałszywe alarmy 1 i 1 z 40). Celowe zajrzenie w przyszłość daje t od +6,9 do +40,4 w 40/40
> losowań. Pre-rejestracja `45c0b1b`. 0 wariantów, poza licznikami.
> Poprzednio: **PRE-REJESTRACJA (przed przebiegiem).**

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

## Wynik

`raw_output.txt` (3 s). Kolumna „t” = t_neff dziennego zwrotu brutto (N_eff ≤ n) w każdym losowaniu.

| reguła | śr. t | sd t | \|t\| > 1,96 | min / max t | śr. zwrot %/rok | kryterium |
|---|---|---|---|---|---|---|
| R-TS (trend 7 dni) | −0,28 | 0,97 | 1/40 | −2,55 / +1,58 | −4,6 | ✓ |
| R-XS (przekrój top/bottom 5) | −0,24 | 0,92 | 1/40 | −2,40 / +1,45 | −2,5 | ✓ |
| **czułość: R-TS z przyszłym tygodniem** | **+16,9** | 5,6 | **40/40** | +6,9 / +27,2 | +341 | ✓ (> 5 wszędzie) |
| **czułość: R-XS z przyszłym tygodniem** | **+20,8** | 8,0 | **40/40** | +7,6 / +40,4 | +389 | ✓ (> 5 wszędzie) |

Łącznie fałszywe alarmy: **2 z 80 = 2,5 %** [Wilson 95 %: 0,7; 8,7] — zgodne z nominalnymi 5 % i z alpha
NC1 (4/120 = 3,3 % [1,3; 8,3]); przedziały prawie się pokrywają.

Poprawka raportowa po pierwszym przebiegu (przed zapisem wyniku): nagłówek tabeli per losowanie podawał
kolumny w innej kolejności niż wydruk (R-TS, R-XS, … zamiast R-TS, R-TS peek, …). Liczby i kryteria bez
zmian — skrypt jest deterministyczny, drugi przebieg dał identyczne wartości.

## Co na plus (+) / Co na minus (−)

**(+)** Przeniesiony do beta generator i rachuba t_neff nie wymyślają zysku z szumu, także przy grubych
ogonach i grupowaniu zmienności. Kontrola czułości nie jest ślepa: zajrzenie w przyszły tydzień daje
t ≥ 6,9 w każdym losowaniu. Odsetek alarmów zgodny z alpha. Rozrzut t (sd 0,92–0,97) blisko 1, więc
t_neff jest poprawnie skalibrowany.
**(−)** Reguły referencyjne NIE są silnikami dziennika alpha (TS1 ma 7 faz, skalowanie zmiennością i
tygodniowe trzymanie; X1 dryf wag) — NC1B sprawdza przyrząd beta, a nie odtwarza liczb TS1/X1 co do
wartości. Średnie t obu reguł są lekko ujemne (−0,28, −0,24; se średniej ≈ 0,15) — w granicach
kryterium; jedno źródło to wspólny czynnik (ρ 0,5), przez który 40 losowań nie jest 80 niezależnymi
obserwacjami (R12). Bez kosztów i fundingu — ich rachuba nie jest tu sprawdzona. Parytet liczony w tym
samym środowisku (Python 3.12, pandas 3.0) dla obu stron: sprawdza tożsamość KODU, nie wersji bibliotek
alpha.

## Werdykt

**Ready.** Przyrząd `miara` w beta przechodzi kontrolę negatywną i czułości według kryteriów zapisanych
z góry; wynik zgodny z alpha NC1.

## Wniosek

**Prostym językiem:** położyliśmy na przeniesionych „wagach” pusty talerz — pokazały zero. Potem
położyliśmy talerz z oszustwem (znajomość przyszłego tygodnia) — od razu pokazały ogromny „zysk”.
Czyli przyrząd w beta działa jak w alpha: nie wymyśla przewagi z szumu i łapie zajrzenie w przyszłość.

## Użyte skille

Brak wczytanych skilli w tej sesji — procedura rundy wzorowana bezpośrednio na alpha NC1
(`runs/2026-09-24_nc1-kontrola-negatywna/README.md`) i CLAUDE.md beta (zasady 25–26).
