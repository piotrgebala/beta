# F2-2 — HAR + log DVOL vs czysty HAR (QLIKE, 1 dzień, BTC i ETH)

> **STATUS: ZAKOŃCZONA — NIEPOZYTYWNY (Caveats).** Pre-rejestracja (commit `f12d7ff`) zostaje bez zmian;
> wynik i werdykt są w sekcji „Wynik” na końcu pliku.

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
- **Commit pre-rejestracji:** `f12d7ff` (kod, testy i ten plik, wypchnięty przed przebiegiem).

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

## Wynik (przebieg po commicie `f12d7ff`; pełny wydruk: `raw_output.txt`)

Zgodność z pre-rejestracją: tak (1 650 dni OOS na monetę, odcisk `f10ec282c39ae538`).

**Krok 1, bramka (R3):** MDE kryterium **0,099** (1 moneta 0,088) wobec progu 0,10, czyli **MIERZALNA**,
ale na samej granicy. Przewidywałem 0,098 (zakres 0,09–0,115): trafione. N_eff/n = 1,01, korelacja różnic
strat BTC/ETH **0,63** (w pre-rejestracji zakładałem ok. 0,16 z F2-1b; pomyłka w założeniu, nie w progu:
wyższa korelacja podnosi MDE dla „obu monet”, a mimo to MDE zmieściło się w 0,10, bo N_eff/n jest wyższe).

**Krok 2, DM na QLIKE (t > 0 = HAR + DVOL lepszy):**

| moneta | n | t QLIKE | δ (średnia różnica / odch. std.) | t MSE log RV (opis) |
|---|---|---|---|---|
| BTCUSDT | 1 650 | **+0,50** | +0,012 | +10,02 |
| ETHUSDT | 1 650 | **−0,07** | −0,002 | +8,36 |

Kryterium: t > 2,2414 w 0 z 2 monet (wymagane 2), t < −2,2414: 0 → **NIEPOZYTYWNY**.
Licznik „zmienność 2021+”: **1 → 2** (test DM uruchomiony).

**Przeliczenie drugą drogą (niezależne od `miara.dm`):** średnia różnicy strat QLIKE i błąd HAC liczone
w statsmodels (OLS na stałą, `cov_type=HAC`, opóźnienia 7 / 14 / 30): BTC t = 0,50 / 0,50 / 0,49,
ETH t = −0,07 / −0,07 / −0,07. Zgodne z `raw_output.txt`. Powtórny przebieg daje identyczny wydruk (R19).

## Co na plus (+) / Co na minus (−)

- (+) Runda zrobiła to, do czego służy: zamknęła pytanie jednym uczciwym testem, z bramką, progiem po
  korekcie i przewidywaniem zapisanym przed wynikiem (MDE przewidziane 0,098, wyszło 0,099).
- (+) Wynik jest wyraźnie nieistotny, nie brzegowy: t = 0,50 i −0,07 przy progu 2,24. Nie ma tu „prawie”.
- (+) Wspólna próba obu modeli: różnica strat to wkład DVOL, nie dłuższy trening.
- (−) Tylko dwie monety i jedna historia (korelacja różnic strat 0,63), więc to nie jest wniosek o rynku.
- (−) Modele zagnieżdżone: HAR-X ma jeden parametr więcej, co lekko pogarsza OOS (kontrola negatywna), więc
  test jest nieco niekorzystny dla HAR-X. Przy t bliskim zera to nie zmienia werdyktu, ale nie dowodzi,
  że DVOL jest bezwartościowy, tylko że przy tym teście i 1 650 dniach nie widać poprawy większej niż MDE 0,10.
- (−) **Rozbieżność QLIKE vs MSE log RV:** t QLIKE ok. 0, ale t MSE log RV = +10 i +8. To są dwie różne
  miary (QLIKE karze niedoszacowanie zmienności; MSE log karze błąd w skali logarytmicznej), a miara
  rozstrzygająca była zapisana przed wynikiem. MSE log liczę tylko opisowo (w F2-1b też t 6,5–9,6, więc
  duże wartości są cechą tej miary i metody, nie dowodem poprawy). Nie zmieniam kryterium po fakcie.
- (−) Opóźnienie DVOL 1 dzień i log DVOL liniowo to jedna z wielu możliwych postaci; inne postaci to
  osobne warianty z osobnym licznikiem (R2, R4).

## Wniosek

DVOL dodany do HAR nie poprawia prognozy zmienności na QLIKE ponad czysty HAR ani dla BTC, ani dla ETH
(t = +0,50 i −0,07 wobec progu 2,24). Szczebel 5 drabiny F2 nie przechodzi, więc **szczebel 6 (boosting) nie
wchodzi**: według PRD wymaga przejścia szczebli 4–5, a szczebel 4 przeszedł tylko brzegowo (11 z 15 monet).

## Rekomendacja

STOP dla toru „HAR + DVOL”: bez F2-2b (inna postać DVOL, opóźnienie 0, dodatkowe zmienne). Proces ML
na prognozie zmienności pozostaje niewystartowany i dlatego, że prosty model nie ma czego poprawiać;
bardziej obiecujące są pytania, w których prosty model realnie nie wystarcza (tor F5 likwidacji, wrzesień 2027),
oraz użycie tego, co już działa (HAR/GARCH-t do rozmiaru pozycji i dystansu do likwidacji).

## Werdykt (R14, podpisuje Claude): **Caveats**

Przyrząd, bramka i kryterium zadziałały zgodnie z pre-rejestracją, liczby zweryfikowane drugą drogą.
Caveats: dwie monety, zależne; zagnieżdżone modele bez korekty Clarka–Westa; rozbieżność QLIKE vs MSE log
opisana, nie rozstrzygnięta.

## Użyte skille

`clas5-runda` (procedura rundy), `data:statistical-analysis` (efekt + MDE zamiast samego p, wielokrotne
porównania: Holm), `data:validate-data` (przeliczenie drugą drogą, „kogo nie ma”: SOL i BNB bez ciągłego DVOL),
`engineering:code-review` (przegląd diffu przed commitem: zakres zmian `prognoza_har` i `moc_kryterium_braki`
ograniczony do nowych parametrów z domyślnymi wartościami bez zmiany zachowania).
