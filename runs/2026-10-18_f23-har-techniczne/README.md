# F2-3 — HAR + pięć wskaźników technicznych vs czysty HAR (QLIKE, 1 dzień, BTC, ETH, SOL, BNB)

> **STATUS: PRE-REJESTRACJA — przebieg na stratach NIE uruchomiony.** Ten plik, kod i testy wchodzą do gita
> przed jakimkolwiek odczytem strat. Wynik i werdykt dopisze Claude pod tą linią, nie zmieniając tego, co
> powyżej sekcji „Wynik”.

## W skrócie (prostym językiem)

Pytanie użytkownika brzmiało: czy da się oprzeć uczenie maszynowe na wskaźnikach typu EMA, MACD, RSI.
**Kierunku ceny nimi nie przewidujemy** — alpha zamknęła to dowodem braku (p = 50,27 %, n = 7 687). Zostaje
pytanie o **zmienność** (jak mocno cena się ruszy jutro, nie w którą stronę). Tam wskaźniki mają jakiś sens:
zakres świecy i ATR to wprost miary rozrzutu, a odległość od średniej i RSI mówią, jak mocno cena jest
rozciągnięta.

Ta runda sprawdza jeden prosty test: czy czysty HAR (zmienność z 5-minutowych świec z ostatniego dnia, tygodnia
i miesiąca) staje się lepszy, gdy dodamy mu pięć wskaźników technicznych. Cztery monety (BTC, ETH, SOL, BNB),
zwykła regresja, żadnego boostingu. Zanim cokolwiek porównamy, skrypt sprawdza, czy test w ogóle jest w stanie
coś zobaczyć; jeśli nie, kończy się bez testu i nic nie zużywa. Moja ocena przed przebiegiem: szansa na
wynik POZYTYWNY to ok. 4 %. Robimy to, bo odpowiedź „nie” zamyka temat uczciwie, a nie bo wierzymy w „tak”.

## Metadane

- Karta 027. Decyzja użytkownika 2026-10-18 („przygotuj” w odpowiedzi na propozycję tej karty).
- Kod: `modele/run_f23.py` (bramka, test DM i werdykt wspólne z `modele/run_f22.py`), cechy w
  `cechy/techniczne.py`, agregacja doby w `dane/ohlc.py`, wpisy w `cechy/rejestr.yaml` (zbiór
  `swiece_5m_ohlc`, opóźnienie 0, `runda_definicji: F2-3`). Testy: `tests/test_f23.py`,
  `tests/test_techniczne.py`, test przecieku wszystkich pięciu cech w `tests/test_cechy.py` (czyste dane i z
  dziurami, cały łańcuch od świec 5m).
- Dane: świece 5m BTC, ETH, SOL, BNB (`data/binance_um/5m`, obcięte na 2026-09-30 włącznie).
- Komendy: `python -m modele.run_f23 --tylko-dni` (dni OOS na szeregach zastępczych, bez strat; użyta do tej
  pre-rejestracji), `python -m modele.run_f23 > runs/2026-10-18_f23-har-techniczne/raw_output.txt` (pełny
  przebieg, dopiero po decyzji o starcie).
- **Commit pre-rejestracji:** commit wprowadzający ten plik (hash w sekcji „Wynik”).
- Skille: `ta-toolkit` (lista wskaźników) niedostępny w sesji („Unknown skill”), więc listę ułożyłem ręcznie
  z klasycznego zestawu (zakres, ATR, EMA, Bollinger, RSI); `clas5-quant` / `data:statistical-analysis` przy
  wyniku.

## Karta hipotezy (R1–R4)

- **Wnioski skumulowane, których dotyczy ta runda:** F2-2 (2026-10-17): DVOL jako dodatkowy regresor nie
  poprawił HAR (t QLIKE +0,50 i −0,07), MDE 0,099 tuż pod progiem 0,10; z tego wynika, że dla K = 4 monet
  i ostrzejszego progu po 3 parach MDE liczę z góry i jest ono blisko granicy. F2-1b: HAR bije dziennik tylko
  brzegowo (11/15). Alpha: z cech wykresu kierunku nie przewidziano (p = 50,27 %) — dlatego tu tylko zmienność.
- **Mechanizm (R1):** zmienność jest uporczywa i reaguje asymetrycznie (spadki ceny podnoszą ją bardziej niż
  wzrosty). Wskaźniki z zakresu świec (high/low) używają informacji, której nie ma w zamknięciach 5m
  (ekstrema wewnątrz doby), a odległość od średniej i RSI niosą ślad ruchu cen z ostatnich tygodni. „Kto traci
  po drugiej stronie”: nikt; to lepsza informacja do prognozy, a nie transakcja. Wartość ekonomiczna byłaby
  mierzona osobno (PRD §11.4). **Zastrzeżenie uczciwości:** RV z 5m jest już bardzo efektywnym estymatorem,
  a ATR, zakres i szerokość Bollingera są jego bliskimi krewnymi, więc oczekiwany dodatkowy wkład jest mały.
- **R2:**
  - zbiór informacyjny: świece 5m (high, low, close; RV) do końca doby t (opóźnienie 0);
  - formuła: regresja na log RV dnia t+1 z regresorami: stała, log RV dnia / średnia 7 dni / średnia 30 dni
    (HAR) + **pięć cech zamrożonych** poniżej; osobno per moneta, zwykła OLS, walk-forward;
  - target: RV dnia t+1 z 5m; horyzont: 1 dzień.
- **Baseline (R17):** czysty HAR liczony na **dokładnie tych samych wierszach** co HAR + cechy (wiersze bez
  któregokolwiek wskaźnika są poza próbą obu modeli).
- **Walk-forward (R6):** jak F2-1b/F2-2: okno rosnące, refit co 30 dni, min. 365 dni treningu, purging.
  Zero hiperparametrów do strojenia (R18): bez regularyzacji, bez wyboru podzbioru cech.
- **Dni ważne:** jak F2-1b (`dni_wazne(..., wyklucz_po_dziurze=True)`), okres do 2026-09-30.
- **Przyrząd:** QLIKE (Patton 2011) i test Diebolda–Mariano z HAC Newey–West (`miara/dm.py`). MSE log RV
  tylko opisowo.

### Zamrożona lista cech (wszystkie liczone z doby UTC, opóźnienie 0, dzień ważny: ≥ 274 świec 5m i high > low > 0)

| cecha | formuła | po co |
|---|---|---|
| `zakres_dzien` | log(ln(high/low)) doby | zakres wewnątrzdobowy (estymator typu Parkinsona) |
| `atr14` | log(średnia prosta z 14 dni true range / close) | zakres z uwzględnieniem luk między dobami |
| `ema20_odl` | log(close / EMA20), ewm span 20, adjust | rozciągnięcie ceny względem średniej (znak = kierunek odchylenia) |
| `bb20_szer` | log(4 · std20(close) / średnia20(close)) | szerokość wstęgi Bollingera |
| `rsi14` | (RSI14 − 50)/50, RSI Cutlera (średnie proste) | napięcie zysków i strat z 14 dni |

Pominięte świadomie: MACD (to różnica dwóch EMA, silnie współliniowa z `ema20_odl`; jako osobny wariant
wymaga własnej pre-rejestracji), wolumen, funding, OI, DVOL (osobne rundy, R4). RSI i EMA wchodzą **ze znakiem,
liniowo** — efekty nieliniowe i interakcje to zadanie dla modelu bogatszego i wolno je badać dopiero po
sukcesie tej rundy (R17, R21).

## Ustalone przed danymi (zamrożone)

| co | wartość | skąd |
|---|---|---|
| monety | BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT | koszyk 4 monet (decyzja użytkownika 2026-10-07) |
| dni OOS | BTC, ETH, BNB 1 703; SOL 1 636; 2022-02-01 … 2026-09-30; odcisk `8c22047ed61fb1b6` | `--tylko-dni`, bez strat (jak F2-1b: cechy nie zmniejszają próby ponad HAR) |
| próg \|t\| | **Z_HOLM = 2,3940** (α = 0,05 / 3 pary modeli) | PRD §11.4: licznik „zmienność 2021+” będzie miał 3 pary (HAR vs dziennik, HAR+DVOL vs HAR, HAR+techniczne vs HAR); Bonferroni to górna granica Holma, wybór zachowawczy |
| kryterium | POZYTYWNY ⇔ t > 2,3940 w ≥ ⌈0,8 · 4⌉ = **4** monetach i żadna z t < −2,3940 | PRD §10.4 |
| bramka | MDE kryterium (centrowana różnica strat, bootstrap blokowy 30 dni, 1 000 powtórzeń, ziarno 2201) ≤ 0,10 | jak F2-1 / F2-1b / F2-2; próg zamrożony przez użytkownika |
| dopasowanie bramki | ten sam próg Z_HOLM w bramce i w kryterium | R3 |
| model | OLS, deterministyczny (R19) | R17, R18 |

## Reguła STOP i licznik

- Bramka NIEMIERZALNA (MDE > 0,10): test DM nie jest uruchamiany, licznik „zmienność 2021+” zostaje 2,
  runda zamknięta. Nie robimy wersji „z mniejszym progiem”, „z mniejszą liczbą monet” ani „z podzbiorem
  cech” po fakcie.
- Bramka MIERZALNA: test DM, licznik „zmienność 2021+” 2 → 3.
- NIEPOZYTYWNY: STOP. Szczebel 6 (boosting) nie wchodzi, bez F2-3b (ridge, podzbiory cech, inne okna wskaźników,
  inne monety są nowymi wariantami i wymagają nowej decyzji).
- POZYTYWNY: dopiero wtedy osobna pre-rejestracja pytania, czy boosting ma pojemność ponad HAR + cechy; wynik
  z czterech monet jednej historii nie uprawnia do wniosków o koszyku (R12).
- Nie zużywa rejestru zwrotów alpha (pytanie o prognozę zmienności, nie o zwrot strategii).
- Pytanie o **kierunek** (czy EMA/RSI/MACD przewidują zwrot) nie należy do tej rundy: byłoby odczytem zwrotu
  na historii 2021–2026, podbiłoby wspólny rejestr alpha (N = 40, próg t ≈ 3,84) i wymaga osobnej decyzji.

## Przewidywania (zapisane przed przebiegiem, bez oglądania strat)

- **Bramka:** z F2-1b (1 moneta MDE 0,077 przy Z = 1,96, n = 1 703) i F2-2 (1 moneta 0,088 przy Z = 2,24)
  wynika 1 moneta ≈ 0,090 przy Z = 2,39. Warunek „wszystkie 4 monety” podnosi MDE ponad pojedynczą monetę,
  a korelacja różnic strat między monetami (F2-1b 0,16; F2-2 BTC/ETH 0,63) jest nieznana dla tej pary
  modeli. **Przewidywane MDE kryterium: 0,10 (zakres 0,09–0,12). P(MIERZALNA) ≈ 45 %.**
- Jeśli MIERZALNA: **P(POZYTYWNY) ≈ 8 %** (wymagane t > 2,39 w każdej z czterech monet, a pięć zbędnych
  regresorów kosztuje dokładność poza próbą). Łącznie P(POZYTYWNY) ≈ 4 %.
- Jeśli test DM się odbędzie: spodziewam się t QLIKE w przedziale od −2,5 do +1,5 w każdej monecie;
  P(któraś moneta z t < −2,39, czyli istotnie gorszy) ≈ 15 %. MSE log RV (opisowo) jak w F2-1b i F2-2
  prawdopodobnie duże dodatnie (t rzędu +5…+10) mimo t QLIKE bliskiego zera; to miara pomocnicza i nie
  rozstrzyga.

## Ograniczenia (znane z góry)

- **Cztery monety, jedna historia (R12).** Korelacja różnic strat nie robi z nich czterech niezależnych prób.
- **Modele zagnieżdżone.** HAR jest szczególnym przypadkiem HAR + cechy, a DM nie koryguje szumu estymacji
  dodatkowych parametrów: zbędne regresory *pogarszają* wynik poza próbą (kontrola negatywna: średnie t < 0,5).
  Test jest zachowawczy wobec „lepszy” i czulszy na „gorszy”. Nie stosujemy poprawki Clarka–Westa (zmiana
  przyrządu po fakcie).
- **Cechy są wzajemnie silnie skorelowane** (zakres, ATR, szerokość Bollingera to krewni RV), więc współliniowość
  podnosi wariancję estymacji OLS; zamrożona lista nie jest strojona, żeby ten efekt zmniejszyć.
- **Liniowość i znak** (patrz wyżej) — jeśli wskaźniki mają wartość tylko nieliniowo, ta runda tego nie zobaczy.
- **Dane syntetyczne w testach to kontrola mechaniki,** nie dowód o rynku.
- **Wnioski o zmienności nie przenoszą się na kierunek** ani na zysk strategii.

## Użyte skille

`clas5-runda` (procedura), `data:statistical-analysis` i `data:validate-data` (bramki przy wyniku),
`engineering:code-review` (przed scaleniem). `ta-toolkit` niedostępny w sesji.
