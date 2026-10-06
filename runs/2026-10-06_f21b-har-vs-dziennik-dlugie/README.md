# F2-1b — HAR-RV vs prognoza zmienności dziennika alpha, monety z długą historią (QLIKE, 1 dzień)

> **STATUS: PRE-REJESTRACJA (przed przebiegiem). Wyniku jeszcze nie ma.** Strat, prognoz na prawdziwym
> RV, bramki MDE ani testu DM nikt jeszcze nie liczył. Na prawdziwych danych policzono tylko dobór
> monet i liczby dni (sekcja „Co sprawdzono przed zapisem”).

## W skrócie (prostym językiem)

F2-1 pytała, czy model HAR (zmienność z 5-minutowych świec z ostatniego dnia, tygodnia i miesiąca)
przewiduje jutrzejszą zmienność lepiej niż to, czego dziś używa dziennik alpha (średnia ważona EWMA).
Odpowiedzi nie dostaliśmy: bramka mierzalności wyszła tuż nad progiem (0,103 przy progu 0,10). Główna
przyczyna: sześć monet z krótką historią, a kryterium „16 z 20” pozwalało przegrać najwyżej cztery.

F2-1b zadaje **to samo pytanie tym samym przyrządem**, ale bierze tylko monety, które mają dane przez
cały okres 2021–2026. Wyszło 15 monet z około 1 700 dniami do sprawdzenia każda. Zanim spojrzymy na
wynik, skrypt znowu sprawdza, czy test w ogóle jest w stanie coś zobaczyć. Jeśli nie jest, kończy się
bez testu. To pytanie o ryzyko, nie o zysk, więc nie zużywa wspólnego budżetu odczytów zwrotu alpha.

## Metadane

- Zadanie 011, opcja **(a)**: decyzja użytkownika 2026-10-06 („LV1: poprawiona, 011: a, E0: zamknij”).
- Poprzedniczka: `runs/2026-10-01_f21-har-vs-dziennik/` (NIEMIERZALNA, MDE 0,103; licznik bez zmian).
- Kod: `modele/run_f21b.py` (dobór monet, dni ważne, przebieg). Bez kopii logiki: importuje
  `modele.zmiennosc.prognoza_dziennik` / `prognoza_har`, `modele.run_f21.bramka_mde` / `test_dm`,
  `dane.dni.dni_wazne` (zadanie 014), `miara.dm`. Jedyna kopia: blok strat `straty()` z
  `run_f21.straty_monety` (runda F2-1 zamknięta, jej maski nie da się wydzielić); równość pilnuje
  `test_parytet_z_f21_bez_flagi`. Testy: `tests/test_f21b.py` (22 przypadki).
- Dane: `data/binance_um/5m` (manifest `dane/manifest_binance_um.json`), skład `dane/sklad_top20.json`
  (zadanie 002). Ładowanie przez `dane.ladowanie.wczytaj_swiece` (R16: od 2021-01-01). Dane **obcięte na
  2026-09-30 włącznie**, więc późniejsze pobrania automatu nie zmieniają wyniku.
- Komendy:
  - `python -m modele.run_f21b --tylko-monety`: dobór i dni OOS, bez strat (użyta do tej
    pre-rejestracji);
  - `python -m modele.run_f21b > runs/2026-10-06_f21b-har-vs-dziennik-dlugie/raw_output.txt`: pełny
    przebieg, robi go orkiestrator po commicie tej pre-rejestracji;
  - `python -m modele.run_f21b --smoke`: cały przebieg na syntetycznym panelu GARCH.
- **Hash commita pre-rejestracji:** `________` (wpisuje orkiestrator; przebieg dopiero po tym commicie).

## Karta hipotezy (R1–R4)

Jak w F2-1. Wszystkie pola R2 są **identyczne**, zmienia się tylko populacja monet (i drobny szczegół dni
ważnych, opisany niżej).

- **Mechanizm (R1):** zmienność skupia się w czasie, bo rynek tworzą uczestnicy działający w różnych
  horyzontach (dzień, tydzień, miesiąc; Corsi 2009). Dane 5m mierzą wczorajszą zmienność dokładniej niż
  kwadrat jednego zwrotu dziennego. „Kto traci”: nikt po drugiej stronie. To lepszy pomiar, nie
  przepływ pieniędzy.
- **R2:**
  - zbiór informacyjny: własne świece 5m (RV) i dzienne zamknięcia;
  - formuła: HAR na log RV (okna 1 / 7 / 30 dni), osobno dla każdej monety;
  - target: RV dnia t+1 z 5m;
  - horyzont: 1 dzień.
- **Baseline (R17):** DOKŁADNIE estymator dziennika, czyli EWMA kwadratów prostych zwrotów dziennych,
  środek masy 60, min. 30 obserwacji (`modele.zmiennosc.prognoza_dziennik`).
- **Walk-forward (R6):**
  - okno rosnące, refit co 30 dni, min. 365 dni treningu;
  - para (cechy_t, cel_t+1) wchodzi do treningu tylko gdy t+1 ≤ dzień refitu (purging);
  - okna 1/7/30 zamrożone, zero hiperparametrów do strojenia (R18).
- **Przyrząd:** QLIKE (Patton 2011) i DM z HAC Newey–West (`miara/dm.py`, kontrole w LM1). MSE log RV
  tylko opisowo.
- **Ten sam wariant (R2), inna populacja.** Zbiór informacyjny, formuła, target i horyzont się nie
  zmieniają, więc to **ten sam wariant hipotezy** co F2-1. Nie jest to nowa hipoteza ani „druga próba”
  w liczniku. F2-1 nie zużyła licznika, bo bramka zamknęła ją przed testem DM. Uczciwie trzeba dodać:
  wybór opcji (a) wynikał z liczb bramki F2-1, ale te liczby (MDE, N_eff, długości) nie mówią nic o tym,
  który model jest lepszy. Liczono je na centrowanych różnicach strat. Średniej różnicy strat w F2-1
  nikt nie widział.
- **Słownictwo.** README F2-1 i zadanie 011 nazywają F2-1b „nowym wariantem”. Chodzi tam o nową
  populację monet. W sensie R2 pola są identyczne. Licznik się nie zmienia: F2-1 zużyła 0, F2-1b
  zużywa 1 tylko przy kroku 2. F2-1c nie będzie.

## Dobór monet (jedyna zmiana merytoryczna)

**Reguła.** Progi 12 miesięcy, ≤ 2021-01-31, ≥ 2026-09-30, 95 % i K_min = 12 **pochodzą ze zlecenia**
(orkiestrator, 2026-10-06). Zostały ustalone przed danymi. Uzasadnienia niżej dopisałem sam, już po
fakcie.

1. Kandydat: symbol był w składzie top-20 point-in-time (`dane/sklad_top20.json`, miesiące 2021-01…2026-06)
   przez **≥ 12 miesięcy**.
2. Kwalifikuje się, gdy jego **dni ważne** (definicja niżej):
   - zaczynają się nie później niż **2021-01-31**;
   - trwają co najmniej do **2026-09-30**;
   - stanowią **≥ 95 %** dni kalendarza 2021-01-01…2026-09-30 (2 099 dni). Dni bez danych liczą się
     jako nieważne.
3. K = min(20, liczba kwalifikujących), wybór wg liczby miesięcy w top-20 (remis → alfabetycznie).
4. **K < 12 → runda NIEMIERZALNA z definicji** (skrypt kończy bez strat i bez testu).

Dobór korzysta wyłącznie ze składu i z maski dni ważnych: `dobierz_monety(miesiace, dostep, u)` nie
dostaje cen, zwrotów, RV ani strat. Pilnuje tego test
`test_dobor_korzysta_tylko_ze_skladu_i_dni_waznych` (inne ceny i inna skala zmienności przy tym samym
wzorze dni dają ten sam dobór).

**Uzasadnienie progów (dopisane przeze mnie, po fakcie):**
- **12 miesięcy.** Rok w top-20 oddziela monety „głównego rynku” od krótkich epizodów (spekulacyjne
  wejścia na kilka miesięcy). **Ten próg decyduje o K.** Przegląd sprawdził to tylko na składzie i
  `dni_wazne`: przy progu 10 miesięcy K = 19 (doszłyby SAND, XLM, UNI, AXS), przy 8 miesiącach K = 20.
  Czyli K = 15 wynika z tego progu, a nie z długości danych. Progu nie zmieniam, bo zmiana po
  zobaczeniu tych liczb byłaby ścieżką rozwidlenia (forking path).
- **≤ 2021-01-31 i ≥ 2026-09-30.** Pełny okres OOS (~1 700 dni) dla każdej monety, czyli to, czego
  zabrakło w F2-1. Miesiąc luzu na starcie, bo pierwszy dzień danych nie ma RV.
- **95 %.** Ten sam ułamek co próg świec w dniu (274 z 288). Dopuszcza wspólne dziury archiwum
  (2022-02-26…28, 2022-04-01…02; DQ1), odcina monety z długimi przerwami.
- **K_min = 12** (ze zlecenia). Przy K < 12 kryterium ⌈0,8 K⌉ zostawia za mało monet, żeby wynik
  mówił o czymś szerszym niż „kilka największych monet”.

**Wynik doboru** (`--tylko-monety`, policzony przed zapisem; zawiera tylko dostępność danych):

| | |
|---|---|
| kandydaci (≥ 12 mies. w top-20) | 25 |
| kwalifikujące się | 15 |
| **K** | **15** |
| kryterium | t > 1,96 w **≥ 12 z 15** monet i 0 monet z t < −1,96 |

| moneta | mies. top-20 | dni ważne / 2 099 | dni OOS | OOS |
|---|---|---|---|---|
| BNBUSDT | 66 | 2 098 | 1 703 | 2022-02-01 … 2026-09-30 |
| BTCUSDT | 66 | 2 098 | 1 703 | 〃 |
| ETHUSDT | 66 | 2 098 | 1 703 | 〃 |
| XRPUSDT | 66 | 2 091 | 1 636 | 〃 |
| SOLUSDT | 62 | 2 091 | 1 636 | 〃 |
| DOGEUSDT | 61 | 2 098 | 1 703 | 〃 |
| ADAUSDT | 55 | 2 098 | 1 703 | 〃 |
| LINKUSDT | 45 | 2 098 | 1 703 | 〃 |
| AVAXUSDT | 40 | 2 098 | 1 703 | 〃 |
| LTCUSDT | 34 | 2 091 | 1 636 | 〃 |
| BCHUSDT | 20 | 2 098 | 1 703 | 〃 |
| DOTUSDT | 20 | 2 098 | 1 703 | 〃 |
| FILUSDT | 17 | 2 091 | 1 636 | 〃 |
| ETCUSDT | 16 | 2 098 | 1 703 | 〃 |
| NEARUSDT | 15 | 2 091 | 1 636 | 〃 |

n (mediana) = 1 703, min 1 636, kalendarz (suma dni OOS) 1 703.

**Odpadły (10):**
- za późny start: 1000PEPE, SUI, WIF, WLD, OP, ENA;
- za wczesny koniec: MATIC (2024-09-04), FTM (2025-01-06), EOS (2025-05-20);
- za mało dni ważnych: 1000SHIB (start 2021-05-11, 93,8 %).

Względem F2-1: 14 z 15 monet jest wspólnych. Odpadło sześć krótkich (PEPE, MATIC, SUI, SHIB, FTM, WIF),
doszedł NEAR.

## Dni ważne (zadanie 014)

- Dzień ważny = `wazny & ~martwy` z `dane.dni.dni_wazne(df5m, wyklucz_po_dziurze=True)`, czyli
  ≥ 274 z 288 świec, RV > 0, wolumen dnia > 0 i dzień nie następuje po dobie bez żadnej świecy.
- **Różnice względem F2-1 (Poprawka 1: ≥ 274 świec i RV > 0):**
  - `~martwy` dodatkowo odcina dzień z wolumenem 0 przy RV > 0. W danych taki dzień nie występuje
    (DQ1 / zadanie 014), więc praktycznie bez zmian.
  - `wyklucz_po_dziurze=True` odcina dzień zaraz po dziurze archiwum. Jego RV zawiera zwrot z kilku dni.
    W danych to 2 dni (2022-03-01, 2022-04-03) w 5 monetach (XRP, SOL, LTC, FIL, NEAR). Przy
  wyłączonej fladze straty F2-1b są identyczne ze stratami F2-1 (test `test_parytet_z_f21_bez_flagi`).
- **Koszt tej decyzji (zauważony przy liczeniu dni, opisany jawnie):** wyłączony dzień zostawia w
  szeregu RV lukę. Średnie HAR 7- i 30-dniowe liczone są po wierszach, więc przez kolejne ~30 dni nie ma
  prognozy. Te 5 monet ma przez to **1 636 zamiast 1 703 dni OOS (−67, ok. 4 %)**. W F2-1, bez tej
  flagi, traciły 5 dni. Decyzję zostawiam: wolę stracić 4 % dni niż wpuścić do treningu i do strat dwa
  dni z RV zawyżonym z definicji. Wpływ na MDE szacuję na ok. +2 % w 5 monetach.
- **Pytanie zamknięte.** `wyklucz_po_dziurze=True` było w kodzie przed pierwszym `--tylko-monety` i
  zostaje. Nie wracam do tej decyzji po zobaczeniu liczby dni. Przegląd proponował też wariant
  „usuń wiersz zamiast NaN” (~1 dzień straty na dziurę). Nie przyjmuję go: NaN to dokładnie sposób, w
  jaki F2-1 traktuje każdy dzień nieważny. Dzień niepełny (< 274 świec) w F2-1 też kosztuje ~31 dni
  OOS (sprawdzone na danych syntetycznych: 449 → 418 dni). Usunięcie wiersza zmieniłoby definicję
  względem F2-1 i dawałoby więcej dni tylko po to, żeby bramka łatwiej przeszła.
- Wiersze szeregu to dni ze świecami, tak jak w F2-1 (`rv_dzienna`). Dni ważne wstawiają tylko NaN w
  RV. Baseline dziennika liczy się z tych samych dziennych zwrotów co w F2-1, bez maski: dziennik też
  jej nie ma.

## Krok 1 — bramka mierzalności (R3)

- Tak samo jak F2-1 (`run_f21.bramka_mde`, Poprawka 1 P2):
  - MDE kryterium liczone bootstrapem stacjonarnym (blok 30, **1 000 losowań, ziarno 2101**) na
    **centrowanej** różnicy strat QLIKE (dziennik − HAR), po kalendarzu sumy dni OOS z brakami;
  - n = mediana dni OOS;
  - udział kryterium = 0,8 (⌈0,8 · 15⌉ = 12).
- **MIERZALNA ⇔ MDE kryterium ≤ 0,10.** To ten sam próg co w F2-1 i LM1.
- **NIEMIERZALNA → skrypt kończy bez testu DM, licznik bez zmian.** Ziarno jest jedno, zapisane z góry.
  Nie powtarzamy losowania „do skutku”, także gdy wynik wypadnie tuż przy progu.
- Centrowanie usuwa średnią różnicy strat, więc bramka nie zdradza, który model jest lepszy.

## Krok 2 — test DM i kryterium (tylko gdy MIERZALNA)

- DM na QLIKE per moneta (HAC Newey–West, lag ⌊4 (n/100)^{2/9}⌋; `run_f21.test_dm`); t > 0 = HAR lepszy.
- Wydruk neutralny (R14): t per moneta, δ, t MSE log (opisowo), skala RV / prognoza dziennika, liczba
  t > 1,96, liczba t < −1,96.
- **Kryterium POZYTYWNY:** t > 1,96 w **≥ 12 z 15** monet **i** żadna moneta z t < −1,96. Inaczej
  NIEPOZYTYWNY. Jedna para modeli, więc bez korekty Holma.
- Reguła jest w czystej funkcji `werdykt` (testy na stałych wektorach: 12/15 → POZYTYWNY, 11/15 →
  NIE, 12 dobrych + 1 z t = −2 → NIE, t = dokładnie 1,96 nie jest „dobre”).
- **Kontrole spójności z twardym STOP (licznik bez zmian, potrzebna Poprawka):**
  - **przed stratami:** lista monet, liczba dni OOS i odcisk SHA-256 dni OOS
    (`80001c5c1ca5686c`) muszą być równe tym z pre-rejestracji (`OCZEKIWANE` w kodzie). Chroni to
    przed sytuacją, w której dane zostaną pobrane ponownie i zmienią się dni. Inaczej: STOP bez
    strat, bez bramki i bez testu;
  - **przed Krokiem 1:** dni strat muszą być równe dniom OOS z wzoru braków. Inaczej: STOP bez bramki
    i bez testu.

## Kontrole (R7, R8, R19)

- **Leakage (R7):** `test_bez_przecieku_zaklocenie_i_obciecie` (5m → dni ważne → prognozy obu modeli).
  - Zakłócenie świec po końcu dnia k (ceny i wolumen) nie zmienia prognoz dni ≤ k+1.
  - Obcięcie danych na dniu k daje te same prognozy.
  - W danych testowych jest dziura archiwum.
  - Test złapał wstrzyknięty przeciek o 1 dzień (sprawdzone mutacją przed zapisem).
- **Kontrola pozytywna (R8):**
  - `test_kontrola_pozytywna_garch`: 2 100 dni GARCH, pipeline 5m F2-1b, DM t > 1,96 na korzyść HAR;
  - `--smoke` (też jako test `test_smoke_kontrola_pozytywna`): 5 monet × 2 100 dni GARCH, cały
    przebieg; wynik MIERZALNA (MDE 0,087), POZYTYWNY 5/5, t 2,9–5,0. To tylko kontrola, że pipeline
    działa. **Jego MDE nie przewiduje prawdziwego.** Świece monet są losowane niezależnie, więc
    korelacja różnic strat wynosi 0,00 (w F2-1 było 0,19). Prawdziwe MDE będzie wyższe.
- **Kontrola negatywna DM:** LM1 (rozmiar 3,8 / 4,9 %), przyrząd bez zmian.
- **Dobór monet:** test, że dobór zależy tylko od składu i dni ważnych (wyżej), oraz testy progów
  (także granic włącznie: start 2021-01-31, udział 95 %), kolejności wg miesięcy, remisu, limitu K,
  dnia martwego i K < 12 → NIEMIERZALNA.
- **Gałęzie przebiegu:** MDE 0,101 → test DM nie jest wywoływany; MDE 0,10 → krok 2 rusza; dni
  strat ≠ dni OOS → STOP; inne monety, dni lub odcisk niż w pre-rejestracji → STOP przed stratami.
- **Stałe pre-rejestracji:** test `test_ustawienia_i_oczekiwane_z_pre_rejestracji` przypina progi,
  walk-forward (365 / co 30), reps 1 000 i to, że udział kryterium = udział w bramce (0,8).
- **Determinizm (R19):** brak losowości poza bootstrapem (ziarno 2101) i szeregiem zastępczym do liczenia
  dni OOS (ziarno 2102). `--tylko-monety` dwa razy dało identyczny wydruk.

## Licznik (zasada 22, PRD §11.4)

- „Prognoza zmienności 2021+”: **0 → 1 przy kroku 2** (gdy bramka przepuści). Przy NIEMIERZALNEJ bez
  zmian.
- Wspólny rejestr zwrotów alpha (`odczyty_historii.csv`): **bez zmian**. To pytanie o prognozę
  zmienności, nie o zwrot strategii.

## STOP (jak F2-1)

- **NIEPOZYTYWNY (albo NIEMIERZALNA)** → F2 idzie dalej przez ES/likwidacje (PRD E1, zadania 008–009).
  HAR odkładamy. Nie robimy F2-1c z kolejną populacją.
- **POZYTYWNY** → **nie zmienia dziennika alpha.** Wpięcie HAR do dziennika = Poprawka w alpha + decyzja
  użytkownika (zasada 23). Wartość ekonomiczna tylko prospektywnie.

## Ograniczenia (zapisane z góry)

- **Selekcja ocalałych.** Wymóg życia kontraktu przez cały okres 2021–2026 wyklucza monety, które
  wypadły z rynku (MATIC → POL, FTM, EOS), i nowe (PEPE, SUI, WIF). Wniosek dotyczy tylko **„monet z
  długą historią w top-20”**, nie całego top-20.
- **Kierunek biasu (ostrożnie).** Pytamy o prognozę zmienności, nie o zwrot, więc klasyczny bias
  ocalałych (zawyżony zwrot) nie przenosi się wprost. Monety, które zbankrutowały lub zostały wycofane,
  zwykle mają w końcówce skoki zmienności i zmiany reżimu, a potem martwe ogony. Na takich odcinkach
  trwałość zmienności (na niej opiera się HAR) może być słabsza albo silniejsza. Nowe monety (memy,
  2023+) odpadły. To inny reżim zmienności (listing, moda). Nie wiemy, czy trwałość jest tam słabsza,
  czy silniejsza. Wniosek ich nie obejmuje. Nie zakładamy kierunku.
- Populacja jest prawie podzbiorem F2-1 (14 z 15 monet). Gdyby F2-1 była MIERZALNA, wyniki obu rund
  dla wspólnych monet byłyby identyczne poza 67 dniami po dziurach i NEAR.
- Okres OOS 2022-02 … 2026-09 to jeden zestaw reżimów rynku. Monety są skorelowane, więc 15 monet
  ≠ 15 niezależnych obserwacji (R12). Kryterium „≥ 12 z 15” to reguła decyzji, nie liczba niezależnych
  dowodów.

## Oczekiwania zapisane z góry (opis, nie kryterium)

- MDE pojedynczej monety w F2-1 (`walidacja_output.txt`, 500 losowań, informacja ślepa) dla 14 monet
  wspólnych z F2-1b: **0,055–0,089** (NEAR nie był liczony).
- Kryterium 12/15 dopuszcza najwyżej 3 monety bez t > 1,96. Żadna nie ma krótkiego OOS. Spodziewam
  się **MDE kryterium ≈ 0,085–0,10**, czyli wyraźnie lepiej niż 0,103 w F2-1, ale **znowu możliwie
  blisko progu**. Wymóg „żadna moneta t < −1,96” i 5 monet z 1 636 dniami podnoszą MDE. Wynik
  NIEMIERZALNA jest realny i byłby uczciwą odpowiedzią.
- Gdyby test ruszył: w świecie generatora LM1 i w `--smoke` HAR bije EWMA 60 o δ ≈ 0,08–0,17. Na
  prawdziwych danych nie zakładamy kierunku.

## Co sprawdzono przed zapisem (pełna jawność)

Na **prawdziwych danych** policzono wyłącznie (komenda `--tylko-monety`):
- skład top-20 i liczbę miesięcy na symbol;
- `dni_wazne` na świecach 5m (dni ważne, pierwszy i ostatni dzień, udział w okresie);
- dni OOS każdej monety. Liczone z **wzoru braków** (`dni_oos`): ten sam przebieg na szeregu
  zastępczym z losowych liczb (ziarno 2102) w miejscach, gdzie RV i zwrot są znane. Prognozy na
  szumie istnieją dokładnie w tych dniach co prawdziwe (test `test_dni_oos_zgodne_ze_stratami`),
  ale nie niosą żadnej informacji o danych poza tym, które dni są ważne.

Na prawdziwych danych **NIE** policzono: prognoz HAR ani EWMA na prawdziwym RV i zwrotach, strat QLIKE
ani MSE, różnic strat, N_eff, korelacji strat, bramki MDE, statystyk DM.

Kolejność decyzji:
1. Progi (12 mies., ≤ 2021-01-31, ≥ 2026-09-30, 95 %, K_min 12) dało zlecenie. `wyklucz_po_dziurze=True`
   rekomendowało zlecenie, a ja przyjąłem. Obcięcie na 2026-09-30 dodałem sam. Wszystko to było w
   `modele/run_f21b.py` przed pierwszym uruchomieniem `--tylko-monety`.
2. Potem smoke i testy na danych syntetycznych.
3. Potem `--tylko-monety` na prawdziwych danych.
4. Po zobaczeniu liczby dni żaden próg nie został zmieniony. Koszt `wyklucz_po_dziurze` (−67 dni)
   opisałem wyżej, decyzji nie zmieniłem.

**Tej kolejności nie da się sprawdzić w gicie.** Kod nie był zacommitowany przed pierwszym
`--tylko-monety`. Plik z kodem ma późniejszą datę zmiany niż pierwszy wydruk, bo po nim poprawiałem
drobiazgi. Progi się nie zmieniły. Wydruk powtórzony po tych poprawkach i po przeglądzie jest
identyczny (monety, dni, a teraz też odcisk dni OOS).

Po pre-rejestracji, przy przeglądzie, policzono na prawdziwych danych jeszcze tylko skład i
`dni_wazne` monet tuż pod progiem 12 miesięcy (wrażliwość K na próg, opisana w „Uzasadnieniu
progów”). Strat, prognoz ani bramki nadal nikt nie liczył.

Wcześniej (z F2-1) znane były: MDE kryterium 0,103, MDE pojedynczych monet, N_eff/n 0,78 i korelacja
różnic strat 0,19. Wszystko to liczono na centrowanych różnicach, bez informacji o kierunku.

## Zmiany po przeglądzie, przed przebiegiem

Dwa niezależne przeglądy (2026-10-06). Żadna zmiana nie dotyka R2, progów doboru, bramki ani
kryterium. Zmienia się tylko to, kiedy skrypt się zatrzymuje, oraz opis.

1. **STOP przy niezgodności dni** (oba przeglądy). Wcześniej „NIE” w kontroli „dni strat = dni OOS”
   tylko się drukowało, a skrypt szedł dalej. Teraz zatrzymuje się przed Krokiem 1, licznik się nie
   zmienia. Dodatkowo, **przed liczeniem strat**, skrypt porównuje monety, dni OOS i odcisk
   SHA-256 z tą pre-rejestracją (`OCZEKIWANE`). Każda różnica → STOP.
2. **Reguła kroku 2 w czystej funkcji `werdykt`** z testami na stałych wektorach. Gałęzie
   NIEMIERZALNA / MIERZALNA są przetestowane podmianą bramki. Kod był poprawny, ale wcześniej żaden
   test tego nie pilnował (20 mutantów przeżywało).
3. **Udział kryterium = udział bramki.** `udzial_kryterium` jest teraz brany z domyślnego `share`
   w `moc_kryterium_braki` (0,8), a przebieg sprawdza, że oba są równe. Wcześniej zgadzały się
   przypadkiem.
4. **Testy:** parytet z F2-1 bez flagi, stałe pre-rejestracji, kolejność wg miesięcy, granice
   włącznie, dzień martwy, smoke jako test. Razem 22 przypadki testowe zamiast 12.
5. **Opis:** progi pochodzą ze zlecenia, a próg 12 miesięcy decyduje o K. Wycofany argument
   „25/2” przy K_min. Jawnie: kolejność decyzji nie była zacommitowana. Dodane zdanie o słowie „nowy
   wariant”. Poprawiony akapit o kierunku biasu. Dopisane, że MDE smoke jest optymistyczne.
6. **Odrzucone:** zamiana NaN na usunięcie wiersza dnia po dziurze (uzasadnienie w „Dni ważne”).
   Zmiana progu 12 miesięcy po zobaczeniu wrażliwości K: odrzucona jako ścieżka rozwidlenia.

## Wynik

*(do uzupełnienia po przebiegu: `raw_output.txt`, tabela, „Co na plus / na minus”, werdykt
Ready / Caveats / Revision, użyte skille)*

Użyte skille (pre-rejestracja): brak. Metodologia wg CLAUDE.md (R2–R8, zasada 22).
