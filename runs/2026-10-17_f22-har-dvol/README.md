# F2-2 — HAR + log DVOL vs czysty HAR (QLIKE, 1 dzień, BTC i ETH)

> **STATUS: PRE-REJESTRACJA (przed przebiegiem).** Wynik, werdykt i „Co na plus / na minus” dopisane
> pod koniec pliku po przebiegu; pre-rejestracja zostaje bez zmian.

## W skrócie (prostym językiem)

F2-1b pokazała, że HAR (zmienność z 5-minutowych świec z ostatniego dnia, tygodnia i miesiąca) jest
lepszy od tego, czego używa dziennik, ale tylko tak sobie (11 z 15 monet przy wymaganych 12). Ta runda
pyta o następny, mały krok: czy do HAR warto dodać **DVOL**, czyli indeks zmienności oczekiwanej z opcji
na giełdzie Deribit. Opcje wyceniają przyszłą zmienność, więc DVOL może wiedzieć coś, czego nie widać w
przeszłych cenach. Test jest tylko dla BTC i ETH, bo tylko one mają ciągły DVOL.

To jest szczebel 5 drabiny F2. Dopiero po nim (i tylko jeśli przejdzie) ma sens szczebel 6, czyli
pierwszy model uczący się (boosting). Zanim runda cokolwiek porówna, skrypt sprawdza, czy test w ogóle
jest w stanie coś zobaczyć. Jeśli nie, kończy się bez testu i nic nie zużywa.

## Metadane

- Karta 025. Decyzja użytkownika 2026-10-17 („tak” na propozycję: HAR + DVOL jako pierwszy krok przed ML).
- Kod: `modele/run_f22.py`; HAR-X to `modele.zmiennosc.prognoza_har(..., dodatkowe=...)`; bramka to
  `symulacje.moc_dm.moc_kryterium_braki(..., z=...)` (nowy parametr progu, domyślnie bez zmian).
  Testy: `tests/test_f22.py` (13 przypadków, w tym kontrola pozytywna i negatywna na syntetyku).
- Dane: świece 5m BTC/ETH (`data/binance_um/5m`, obcięte na 2026-09-30 włącznie), DVOL dzienny
  (`data/deribit_dvol`, manifest `dane/manifest_deribit_dvol.json`), cecha `dvol_opozn` z rejestru
  (opóźnienie 1 dzień, test przecieku istnieje: `tests/test_cechy.py`).
- Komendy: `python -m modele.run_f22 --tylko-dni` (dni OOS, bez strat; użyta do tej pre-rejestracji),
  `python -m modele.run_f22 > runs/2026-10-17_f22-har-dvol/raw_output.txt` (pełny przebieg po commicie).
- **Hash commita pre-rejestracji:** uzupełniony w sekcji Wynik.

## Karta hipotezy (R1–R4)

- **Wnioski skumulowane, których dotyczy ta runda:** F2-1b (2026-10-06): HAR bije dziennik tylko
  brzegowo (BTC t = 2,29, ETH t = 1,46; N_eff/n 0,79, korelacja różnic strat 0,16, MDE 1 monety 0,077);
  z tego wynika, że dla pary monet liczymy MDE z nowego, ostrzejszego progu, a nie dziedziczymy 0,091.
- **Mechanizm (R1):** rynek opcji wycenia przyszłą zmienność i zawiera informację o wydarzeniach i
  pozycjonowaniu, której nie ma w przeszłych cenach. „Kto traci po drugiej stronie”: nikt, to lepsza
  informacja do prognozy, a nie transakcja. Wartość ekonomiczna mierzona byłaby osobno (PRD §11.4).
- **R2:**
  - zbiór informacyjny: świece 5m (RV) + zamknięcie DVOL z dnia poprzedniego (`dvol_opozn`);
  - formuła: regresja na log RV dnia t+1 z regresorami: stała, log RV dnia / średnia 7 dni / średnia
    30 dni (HAR) + log DVOL; osobno per moneta, walk-forward;
  - target: RV dnia t+1 z 5m; horyzont: 1 dzień.
- **Baseline (R17):** czysty HAR liczony na **dokładnie tych samych wierszach** co HAR-X (wiersze bez
  DVOL są poza próbą obu modeli). Dzięki temu różnica strat to wkład DVOL, a nie dłuższy trening.
- **Walk-forward (R6):** jak F2-1b: okno rosnące, refit co 30 dni, min. 365 dni treningu, purging
  (para wchodzi do treningu tylko gdy t+1 ≤ dzień refitu). Zero hiperparametrów do strojenia (R18).
- **Dni ważne:** jak F2-1b (`dni_wazne(..., wyklucz_po_dziurze=True)`), okres do 2026-09-30.
- **Przyrząd:** QLIKE (Patton 2011) i test Diebolda–Mariano z HAC Newey–West (`miara/dm.py`). MSE log RV
  tylko opisowo.

## Ustalone przed danymi (zamrożone)

| co | wartość | skąd |
|---|---|---|
| monety | BTCUSDT, ETHUSDT | jedyne z ciągłym DVOL (SOL: 2022-05…11) |
| dni OOS | 1 650 na monetę, 2022-03-26 … 2026-09-30, odcisk `f10ec282c39ae538` | `--tylko-dni`, bez strat |
| próg \|t\| | **Z_HOLM = 2,2414** (α = 0,05 / 2 pary modeli) | PRD §11.4: licznik „zmienność 2021+” ma 2 pary (HAR vs dziennik, HAR+DVOL vs HAR); Bonferroni to górna granica Holma, wybór zachowawczy |
| kryterium | POZYTYWNY ⇔ t > 2,2414 w obu monetach i żadna z t < −2,2414 | PRD §10.4: ≥ 80 % monet, K = 2 → ⌈1,6⌉ = 2 |
| bramka | MDE kryterium (centrowana różnica strat, bootstrap blokowy 30 dni, 1 000 powtórzeń, ziarno 2201) ≤ 0,10 | jak F2-1 / F2-1b |
| dopasowanie bramki | ten sam próg Z_HOLM w bramce i w kryterium | R3: bramka mierzy to, co kryterium |

## Reguła STOP i licznik

- Bramka NIEMIERZALNA (MDE > 0,10): test DM nie jest uruchamiany, licznik „zmienność 2021+” bez zmian
  (1), runda zamknięta. Tor HAR+DVOL na dwóch monetach zostaje zamknięty do przedłużenia danych; nie
  robimy wersji „z mniejszym progiem po fakcie”.
- Bramka MIERZALNA: test DM, licznik „zmienność 2021+” 1 → 2.
- NIEPOZYTYWNY: STOP. Szczebel 6 (boosting) nie wchodzi (PRD F2: „tylko jeśli 4–5 przejdą bramkę”),
  bez F2-2b.
- POZYTYWNY: dopiero wtedy pytanie, czy boosting ma pojemność ponad HAR-X na tych samych cechach
  (osobna pre-rejestracja; wynik z dwóch monet nie uprawnia do wniosku o koszyku).
- Nie zużywa rejestru zwrotów alpha (pytanie o prognozę zmienności, nie o zwrot strategii).

## Przewidywania (zapisane przed przebiegiem, po rachunku z N_eff)

- Z F2-1b: pojedyncza moneta MDE 0,077 przy Z = 1,96 i n = 1 703; przy Z = 2,24 to ok. 0,086 (×1,10),
  a dla warunku „obie monety” ok. 0,098 (×√(3,49/3,08) przy korelacji różnic ok. 0,16).
  **Przewidywane MDE kryterium: 0,098 (zakres 0,09–0,115). P(MIERZALNA) ≈ 50 %.**
- Jeśli MIERZALNA: **P(POZYTYWNY) ≈ 30 %**. Literatura (wskaźniki zmienności implikowanej w HAR-X) mówi
  o skromnej poprawie QLIKE; przy teście odporności na dwie monety i ostrym progu spodziewam się
  wyniku brzegowego.

## Ograniczenia (znane z góry)

- **Dwie monety, jedna historia (R12).** Korelacja różnic strat ok. 0,16 nie robi z nich 2 niezależnych
  prób dla wniosku o rynku; K = 2 nie jest koszykiem z F2-1b.
- **Modele zagnieżdżone.** HAR jest szczególnym przypadkiem HAR-X, a DM nie koryguje szumu estymacji
  dodatkowego parametru: zbędny regresor *pogarsza* wynik poza próbą (kontrola negatywna: średnie t ≈ −1).
  Test jest więc zachowawczy wobec „lepszy” i czulszy na „gorszy”. Nie stosujemy poprawki Clarka–Westa
  (zmiana przyrządu po fakcie).
- **Opóźnienie DVOL 1 dzień** jest zachowawcze (rejestr cech). Wariant z opóźnieniem 0 to osobny wariant
  (R2) i wymaga własnej pre-rejestracji.
- Log DVOL wchodzi liniowo; brak interakcji i brak funding / OI (każda dodatkowa zmienna = osobna runda, R4).
- Dane syntetyczne w testach to kontrola mechaniki, nie dowód o rynku.
