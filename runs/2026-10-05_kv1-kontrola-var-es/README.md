# KV1 — kontrole R8 przyrządu VaR/ES: rozmiar i moc testów wstecznych (2026-10-05)

> **STATUS: PRE-REJESTRACJA (przed przebiegiem).** Pełny przebieg `python -m symulacje.run_kv1` nie był
> uruchomiony; kryteria poniżej są zapisane przed obejrzeniem jakiegokolwiek jego wyniku.
> Sekcje „Wynik”, „Co na plus / na minus” i werdykt (Ready/Caveats/Revision) dopisuje orkiestrator po
> pełnym przebiegu.

## W skrócie — prostym językiem

Budujemy przyrząd, który ocenia prognozy ryzyka ogona: **VaR** („strata, której dzień ma nie przekroczyć
z szansą 99 % albo 95 %”) i **ES** („jaka jest średnia strata, gdy już ją przekroczymy”). Przed użyciem na
prawdziwych danych sprawdzamy go na sztucznych, gdzie prawdę znamy (zasada R8):

1. **Gdy prognoza jest prawdziwa, przyrząd ma jej NIE odrzucać** — pomylić się powinien w ok. 5 %
   przypadków (tyle wynosi poziom testu). Tak działa kontrola negatywna.
2. **Gdy prognoza jest znanym błędem, przyrząd ma ją odrzucać** w co najmniej 80 % przypadków. To kontrole
   pozytywne: ogony za cienkie (rozkład normalny przy prawdziwym t5), zmienność stała zamiast
   zmieniającej się w czasie (grupowanie dużych strat), ES zaniżone przy dobrym VaR.

Jeśli którakolwiek z 19 kontroli nie przejdzie, przyrząd NIE idzie na prawdziwe dane, dopóki go nie
naprawimy (a progów po fakcie nie zmieniamy).

## Metadane

- **Pre-rejestracja zamrożona w commicie:** `(hash wpisze orkiestrator; commit z README, kodem
  i testami musi poprzedzić pełny przebieg, a przebieg idzie z zatwierdzonego stanu)`.
- Zadanie 008 (`zadania/008-przyrzad-var-es.md`, PRD FR-32, cel G2). Runda kalibracyjna, nie hipoteza
  rynkowa: **R1 — brak mechanizmu** (nic nie przewidujemy, kalibrujemy przyrząd).
- Kod: `miara/var_es.py` (test Kupca LR_uc, Christoffersena LR_ind i LR_cc, test ES Acerbiego–Szekelya Z2
  z p-wartością z symulacji pod H0, wzory zamknięte VaR/ES dla rozkładu normalnego i t), testy
  `tests/test_var_es.py` (142 testy: przykłady liczone ręcznie i niezależnym wzorem, w tym serie
  zaczynające i kończące się trafieniem, wzory zamknięte kontra `scipy.integrate.quad` do 1e-8,
  własności `hypothesis` z niezależnym rachunkiem pętlą po sekwencji, lekkie kontrole R8, okablowanie
  19 kryteriów KV1 z `symulacje/run_kv1.py`).
- Skrypt `symulacje/run_kv1.py`; komenda
  `python -m symulacje.run_kv1 > runs/2026-10-05_kv1-kontrola-var-es/raw_output.txt`.
  Skrót do sprawdzenia, że kod działa: `--smoke` (jego liczby NIE są wynikiem).
- Dane: WYŁĄCZNIE syntetyczne (`symulacje.garch_panel.generuj_panel`: GARCH(1,1) α 0,08 β 0,90, szok
  dzienny t z ν = 5, zmienność bezwarunkowa 4 %/dzień), ρ = 0, czyli serie niezależne. Żadnych prognoz VaR
  na prawdziwych danych (karta 008: to osobna runda z pre-rejestracją, po LV1). R16 (dane od 2021) nie
  dotyczy — nie czytamy `data/`.
- Determinizm (R19): ziarno główne `20261005`; `SeedSequence.spawn` per zadanie, więc wynik nie zależy
  od liczby procesów (`--workers`; sprawdzone w trybie smoke na 1, 4 i 7). Na stdout (`raw_output.txt`)
  idą tylko liczby odtwarzalne; czas przebiegu idzie na stderr. Przyrząd wymaga jawnego ziarna typu
  `int` albo `SeedSequence` (`None`, bool i `Generator` są odrzucane).
- Środowisko: pandas 3.x (zablokowane w `requirements-lock.txt`: 3.0.6). Przebieg dla p = 1 %
  (200 000 dni na serię) buduje indeks dat, który w pandas 2.x wychodzi poza zakres `ns` (rok 2262).

## Pre-rejestracja (zapisana przed przebiegiem)

### Konwencja i testy

Zwrot dzienny r_t; q_t = kwantyl rzędu p (ujemny); es_t = E[r | r < q_t] ≤ q_t < 0; trafienie
I_t = 1{r_t < q_t}. Odrzucamy hipotezę zerową („prognoza jest poprawna”), gdy **p-wartość < 5 %**.
Test z niezdefiniowaną statystyką (Christoffersen ind, gdy któryś brzeg tabeli przejść 2×2 jest zerowy,
np. brak trafień, same trafienia albo jedyne trafienie na początku lub końcu serii) liczy się jako
**brak odrzucenia** i jest osobno raportowany.

- **Kupiec LR_uc** ~ χ²(1): czy odsetek trafień = p.
- **Christoffersen LR_ind** ~ χ²(1): czy trafienia są niezależne (łańcuch Markowa 1. rzędu, n − 1 przejść).
- **Christoffersen LR_cc** = LR_uc (na I₂…I_n) + LR_ind ~ χ²(2). To dokładny iloraz wiarygodności
  łańcucha Markowa (warunkowy na pierwszym dniu), więc LR_cc **nie jest** sumą Kupca z całych n i LR_ind
  (tak bywa w podręcznikach i bibliotekach): przy porównaniach z zewnętrznymi implementacjami liczby
  mogą się różnić o rząd 1/n (granica LR_cc ~ χ²(2) jest ta sama; test jednostkowy pilnuje naszej
  definicji niezależnym rachunkiem pętlą po sekwencji).
- **Acerbi–Szekely Z2** = 1 − Σ r_t I_t / (n p es_t); E[Z2] = 0 pod H0, Z2 < 0 = ogon niedoszacowany.
  Rozkład pod H0 z symulacji (20 000 losowań); p-wartość lewostronna (1 + #{Z2* ≤ z}) / (1 + B).
  Dla prognoz typu położenie–skala σ się skraca, więc rozkład zerowy zależy tylko od (n, p, rodziny
  rozkładu); test jednostkowy sprawdza, że skrót i wersja ogólna dają to samo **dla takich prognoz**.
  Dwa interfejsy NIE są równoważne dla prognozy spoza rodziny (np. es za niskie przy dobrym q, czyli
  POZYTYWNA 3): skrót liczy rozkład zerowy ze wzorów zamkniętych rodziny (a, b), a Z2 danych z
  raportowanym es, więc ma moc; wersja ogólna liczy rozkład zerowy z raportowanym es i samplerem, więc
  przy es niespójnym z samplerem rozkład zerowy przesuwa się razem z błędem (E ≈ −0,14) i mocy nie ma.
  Ogólna wersja jest więc do prognoz, w których sampler i (q, es) są jednym modelem; `czy_polozenie_skala`
  sprawdza, czy prognoza jest typu σ_t (a, b), a skrypt KV1 kończy się błędem, gdy prognoza z rodziny
  (`prawdziwa`, `normalna`, `stala`) tej cechy nie ma. **Kryteria Z2 w KV1 (#4, #8, #13, #16, #17) dotyczą
  skrótu**; ścieżkę ogólną (potrzebną na danych) pokrywają kontrole R8 w `tests/test_var_es.py`
  (prawdziwy model nie jest odrzucany, zła prognoza tak, p-wartość ma właściwy kierunek).

### Projekt

| poziom p | dni na serię n | paneli × monet | serii | oczekiwane trafienia | przejścia 1→1 (n·p²) |
|---|---|---|---|---|---|
| 1 % | 200 000 | 200 × 25 | 5 000 | 2 000 | 20 |
| 5 % | 20 000 | 100 × 50 | 5 000 | 1 000 | 50 |

Cztery prognozy na każdej serii (σ_t — wyrocznia generatora, znana w t − 1):

| nazwa | q, es | prawda w generatorze | rodzina rozkładu zerowego Z2 |
|---|---|---|---|
| prawdziwa | σ_t, kwantyl i ES znormalizowanego t5 | to samo | t |
| normalna | σ_t, kwantyl i ES normalny | t5 (grubsze ogony) | normal |
| stała | σ = 4 % (t5), bez zmian w czasie | GARCH (σ_t zmienne) | t |
| es_za_niski | q prawdziwe, es = q · (ES/q rozkładu normalnego) | q prawdziwe, ES ok. 13 % za niskie | t |

**Dlaczego tak długie serie przy p = 1 % (R3 w wersji dla przyrządu).** Przybliżenie χ² dla LR_ind
psuje się, gdy n·p² jest małe (rozkład liczby przejść 1→1 jest dyskretny). W szybkiej symulacji ciągów 0/1
o stałym p (niezależnej od generatora; wartości orientacyjne) rozmiar testu ind przy p = 1 % skakał
od ok. 1,8 % do ok. 8,8 % dla n między 5 000 a 50 000, a przy n = 200 000 (n·p² = 20) wyszedł
ok. 4,9 % (Kupiec ok. 5,0 %, cc ok. 5,2 %); przy p = 5 % i n = 20 000 (n·p² = 50) Kupiec ok. 4,8 %,
ind ok. 5,4 %, cc ok. 5,0 %. Stąd reguła n·p² ≳ 20 i wybór n powyżej. Ograniczenie jest opisane
w docstringu modułu: na prawdziwych 5-minutowych/dziennych próbach o małym n·p² (np. 2 100 dni przy
p = 1 %, czyli 0,2) wynik LR_ind trzeba czytać ostrożnie.

### Kryteria (19; werdykt ZALICZONA ⇔ spełnione WSZYSTKIE)

Odsetek odrzuceń liczony na 5 000 serii; raportujemy przedział Wilsona (95 %), ale decyduje sam odsetek.
Numeracja #1–19 jest taka sama w tej tabeli, w kodzie (`_kryteria`) i w wydruku `raw_output.txt`.

**NEGATYWNA** — prognoza „prawdziwa”, odsetek odrzuceń ∈ [2,5 %; 7,5 %] (ta sama reguła co w LM1):

| # | poziom | test |
|---|---|---|
| 1–4 | p = 1 % | Kupiec, Christoffersen ind, Christoffersen cc, Z2 |
| 5–8 | p = 5 % | Kupiec, Christoffersen ind, Christoffersen cc, Z2 |
| 9–10 | p = 1 %, 5 % | udział serii z niezdefiniowanym Christoffersen ind ≤ 1 % |

**POZYTYWNA 1** — prognoza „normalna” przy prawdziwym t5, odsetek odrzuceń ≥ 80 %:

| # | poziom | test |
|---|---|---|
| 11 | p = 1 % | Kupiec |
| 12 | p = 5 % | Kupiec |
| 13 | p = 1 % | Z2 |

**POZYTYWNA 2** — prognoza „stała” przy prawdziwym GARCH, odsetek odrzuceń ≥ 80 %:

| # | poziom | test |
|---|---|---|
| 14 | p = 1 % | Christoffersen ind |
| 15 | p = 5 % | Christoffersen ind |

**POZYTYWNA 3** — prognoza „es_za_niski” (VaR dobry, ES o ok. 13 % za niskie), odsetek odrzuceń ≥ 80 %:

| # | poziom | test |
|---|---|---|
| 16 | p = 1 % | Z2 |
| 17 | p = 5 % | Z2 |

**POZYTYWNA 4** — prognoza „normalna” przy prawdziwym t5, Christoffersen cc (R8: pozytywna kontrola
silnika cc, którego składnik pokrycia inaczej nie byłby sprawdzony), odsetek odrzuceń ≥ 80 %:

| # | poziom | test |
|---|---|---|
| 18 | p = 1 % | Christoffersen cc |
| 19 | p = 5 % | Christoffersen cc |

Skład kryteriów mocy: składnik niezależności cc sprawdza POZYTYWNA 2 (#14–15, test ind), składnik
pokrycia POZYTYWNA 4 (#18–19); wzór LR_cc jako całość pilnują testy jednostkowe.

**Czułość kontroli negatywnej.** Pasmo [2,5 %; 7,5 %] to ok. ±8 błędów standardowych przy 5 000 seriach
(SE = 0,31 pp): kontrola negatywna wykrywa tylko duże odchylenia rozmiaru testu (np. rozmiar 3 % albo 7 %
by przeszedł). Poprawność wzorów pilnują testy jednostkowe (wartości do 1e-9 względem niezależnych
rachunków), a KV1 sprawdza, że przyrząd działa na generatorze i ma moc.

**Odstępstwo od karty 008.** Karta mówi „odsetek odrzuceń ≈ poziom testu (przedział Wilsona)”; decyduje
stałe pasmo [2,5 %; 7,5 %] (ta sama reguła co w LM1), a przedział Wilsona jest tylko raportowany.

### Odstępstwo od pierwotnego szkicu: komórka „Z2, normalna vs t5, p = 5 %” jest tylko opisem

Szkic karty żądał, by przy normalnym VaR/ES i prawdziwym t5 odrzucały i Kupiec, i Z2. Rachunek zamknięty
(całka `quad`, przed przebiegiem) pokazuje, że **przy p = 5 % Z2 nie ma tu mocy z konstrukcji**: błąd
kwantyla (normalny jest za płytki, trafień 4,36 % zamiast 5 %) i błąd ES kasują się prawie dokładnie,
E[Z2] = +0,015 (przy p = 1 %: E[Z2] = −0,754, trafień 1,50 %). Żądanie mocy ≥ 80 % tej komórki byłoby
kryterium nie do spełnienia przez żaden poprawny test, więc jest tylko **opisem** (tabela „OPIS” w wyniku).
W jego miejsce dodajemy POZYTYWNĄ 3 (#16–17), która sprawdza moc Z2 tam, gdzie powinien ją mieć — przy
dobrym VaR i zaniżonym ES (E[Z2] ≈ −0,155 przy p = 1 % i −0,144 przy p = 5 %). Wniosek dla użytkownika
przyrządu, niezależnie od wyniku: **Z2 sam nie wystarczy do oceny prognozy; trzeba go czytać razem
z Kupcem.**

### Co NIE jest kryterium (opis)

Odsetek odrzuceń na poziomie 5 % we wszystkich komórkach (cztery testy × cztery prognozy × dwa poziomy),
średni odsetek trafień, średnie Z2 z błędem standardowym, liczba niezdefiniowanych LR_ind, rozkłady
zerowe Z2 (średnia, sd, 5. percentyl).

### Reguła decyzji (R4 / reguła STOP)

- **ZALICZONA** ⇔ wszystkie 19 kryteriów spełnionych. Wtedy `miara/var_es.py` jest dopuszczony do rundy
  z pre-rejestracją na danych (po LV1; osobna karta).
- **NIEZALICZONA** ⇔ co najmniej jedno kryterium nie spełnione → przyrząd NIE wchodzi na dane. Najpierw
  diagnoza (błąd w kodzie vs ograniczenie przyrządu, np. rozmiar LR_ind przy małym n·p²). Naprawa kodu
  to nowa runda (KV1b) z tymi samymi progami; progów ani liczby serii nie zmieniamy po obejrzeniu wyniku.
- Skrypt jest neutralnym reporterem (R14): drukuje liczby i regułę; werdykt podpisuje Claude w README po
  przebiegu.

### Co sprawdzono PRZED zapisem kryteriów (pełna jawność)

- Rachunki zamknięte (całki `quad`) na E[Z2] i odsetek trafień dla prognoz „normalna” i „es_za_niski”
  (liczby powyżej) oraz szybkie symulacje ciągów 0/1 o stałym p do wyboru n (tabela wyżej).
- Rachunek mierzalności (R3) dla kryteriów mocy. Trafienia normalnej prognozy przy prawdziwym t5 są
  niezależne (σ_t się skraca), więc LR_uc i LR_cc mają rozkład nieśrodkowy χ² z parametrem
  ncp = 2·n·KL(π ‖ p): p = 5 % (trafień 4,356 % zamiast 5 %, n = 20 000): ncp ≈ 18,2, moc Kupca
  ≈ 99,0 %, moc cc (χ²(2)) ≈ 97,6 %; p = 1 % (trafień 1,499 % zamiast 1 %, n = 200 000): ncp ≈ 437,
  moc ≈ 100 % obu. Z2, POZYTYWNA 3: odchylenie Z2 pod H0 wynosi ok. 0,033 (p = 5 %, n = 20 000) i
  0,023 (p = 1 %, n = 200 000), przy przesunięciu średniej −0,144 i −0,155: moc ≈ 99,6 % i ≈ 100 %.
  POZYTYWNA 2 (ind, stałe σ = 4 % vs GARCH): pilotaż 40 serii na poziom (ziarna inne niż rejestrowe)
  dał 40/40 odrzuceń, największa p-wartość 1e-5 (p = 5 %) i 1e-36 (p = 1 %). Wszystkie kryteria mocy są
  więc mierzalne z zapasem względem progu 80 % (to nie jest wynik rundy).
- **Zmiany po przeglądzie, przed pełnym przebiegiem** (pełna jawność): trzej niezależni recenzenci
  przejrzeli kod i pre-rejestrację. Recenzent uruchomił wersję ze zepsutym cc (tylko składnik niezależności,
  χ²(1)) w skali pre-rejestracji z innym ziarnem (999, nie rejestrowym) i zobaczył, że 17 pierwotnych
  kryteriów go nie wykrywa (cc ze składnikiem pokrycia dałoby przy „normalna vs t5” moc z rachunku ncp
  wyżej). W odpowiedzi dopisano POZYTYWNĄ 4 (#18–19; próg 80 % taki sam jak w pozostałych kryteriach mocy, nie dobrany do tej repliki),
  ponumerowano kryteria jak w tabelach i dodano straż w skrypcie (rodzina położenie–skala). Replika
  nie jest wynikiem rundy; wynik rundy powstanie wyłącznie z ziarna `20261005`.
- Lekkie kontrole R8 w `tests/test_var_es.py` (n = 10 000, 300 serii; ścieżka ogólna Z2: n = 5 000,
  30 serii): te same mechanizmy w mniejszej skali, w tym kontrola pozytywna cc; progi testów
  jednostkowych dobrane do tej skali i **nie są** progami KV1.
- Tryb `--smoke` (n = 2 000–4 000, 10 serii na poziom): sprawdza tylko, że kod działa i że wynik nie
  zależy od liczby procesów. Jego liczb nie użyto do wyboru progów ani projektu.
- Pełnego przebiegu nie uruchamiano. Pojedyncze zadania (jedna partia 500 losowań rozkładu zerowego,
  jeden panel) wzięły 0,3–1 s, co przy 32 rdzeniach daje szacunek całego przebiegu rzędu minuty
  (orientacyjnie).

### Liczniki

- **0 wariantów**, POZA licznikami: dane syntetyczne, kalibracja przyrządu.
- Wspólny rejestr odczytów alpha (`odczyty_historii.csv`, N = 40): **bez zmian** — żaden zwrot strategii
  nie jest odczytywany na historii.
- Licznik „ryzyko 2021+” (PRD §11.4): **bez zmian (0)** — nie testujemy żadnej prognozy VaR/ES na prawdziwych
  danych.
- R15: LLM nie występuje w żadnej ścieżce decyzyjnej; przyrząd i skrypt są deterministyczne (R19).
- Użyte skille: brak (kod i rachunki własne; żaden skill nie był ładowany).
