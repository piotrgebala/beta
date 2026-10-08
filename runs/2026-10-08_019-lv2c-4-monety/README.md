# 019 — LV2c: czy reguła K (test bezwzględny VaR 5 %) jest mierzalna dla 4 monet przy zależności jak na prawdziwych danych

## Metadane

- Karta: `zadania/019-laboratorium-lv2c-zaleznosc-jak-na-danych.md` (przeliczona na K = 4 decyzją użytkownika z 2026-10-07 „rób tylko
  prognozy na eth btc sol, bnb”). Zlecenie wykonania: użytkownik, 2026-10-08 („019 … zaczynam od jego pre-rejestracji. wykonaj i
  wypchnij wszystko na repo”). Poprzednicy: 016 (LV2), 017, 020.
- Dane **wyłącznie syntetyczne.** Licznik: **poza licznikami.** „Ryzyko ogona (VaR/ES) 2021+” **zostaje 0**, „zmienność 2021+” zostaje 1,
  rejestr zwrotów alpha (N = 40) nietknięty. Nic tu nie czyta prawdziwych zwrotów; z prawdziwych danych wchodzą tylko liczby z karty 017
  (odsetek dopasowań przy granicy) i z karty 020 (VR, ρ̂, SE, odsetek przy granicy dla czwórki), zapisane niżej.
- Kod: generator `symulacje/garch_panel_wspolny_szok.py` + `tests/test_garch_panel_wspolny_szok.py` (commit `ad6fc17`, przed tą
  pre-rejestracją), runner `symulacje/run_lv2c.py` (po pre-rejestracji, przed pilotażami formalnymi). Pliki LV2 zamrożone od `24c8863`
  (`garch_panel.py`, `garch_t.py`, `prognozy_lv2.py`, `moc_var_es.py`, `run_lv2.py`, `porownanie_lv2.py`) i miara 017/020
  (`modele/pomiar_rho_h.py`, `modele/opis_rho_h.py`) **bez zmian**; runner je importuje.
- Status tego pliku: **pre-rejestracja** (commit pre-rejestracji poprzedza pilotaże formalne i przebieg rejestrowy; hash dopisany w sekcji
  „Wynik”). Sekcje „Wynik” i dalsze zostaną dopisane po przebiegu.

## Pre-rejestracja (zapisana przed pilotażami formalnymi i przed przebiegiem rejestrowym)

### Wnioski skumulowane, które dotyczą tej rundy

`[2026-10-07, 020]`: dla BTC, ETH, SOL, BNB VR trafień VaR 5 % = 2,264, ρ̂ = 0,421 (SE 0,091; ρ̂ ± 2 SE = [0,239; 0,604], VR
[1,717; 2,811]), 117 z 228 dopasowań GARCH-t (51,3 %) przy granicy persystencji, średnia persystencja 0,970, średnie ν̂ 4,14 → cel
kalibracji laboratorium dla K = 4; dolny koniec przedziału leży poniżej poziomu LV2 (ρ̂ 0,282), więc obowiązuje też scenariusz LV2
dla K = 4. `[2026-10-07, LV2]`: przy K = 15, n = 1 700, p = 5 % rozmiar testu zbiorczego `garch_tnu` to 5,0 % (próg 10 %), a moc wobec
σ̂ × 0,90 to 99,6 % (próg 80 %) → przy K = 4 moc **nie była mierzona** i spada z liczbą monet. `[2026-10-07, LV1]`: pojedyncza moneta
wykrywa zaniżenie σ o 10 % tylko w 10–17 % przypadków. Wynika z nich projekt: mierzymy regułę K **bez zmiany progów** w trzech
zależnościach (dół, środek, góra przedziału z 020), nie przesądzając wyniku; przewidywanie (niżej) mówi, że moc jest ryzykiem.

### R1 — mechanizm jednym zdaniem

Jeśli cztery największe monety trafiają ponad VaR w tych samych dniach, a model GARCH-t bywa na granicy trwałości, to test zbiorczy ma
mniej niezależnej informacji niż w LV2 (K = 15, zależność jak z czynnika ρ = 0,8), więc może stracić moc albo rozmiar; laboratorium
sprawdza, czy reguła K nadal rozróżnia poprawną prognozę od zaniżonej o 10 %. (Pomiar własności przyrządu, nie hipoteza o rynku; żadnej
„drugiej strony” handlowej nie zakłada.)

### R2 — zbiór informacyjny × formuła × target × horyzont

- zbiór informacyjny: syntetyczny panel 4 monet × 2 091 dni (tyle wierszy ma panel wspólny BTC/ETH/SOL/BNB z 020), 400 dni historii
  + 1 691 dni oceny; generator LV2c (niżej);
- formuła: dokładnie zamrożone `zbuduj_zrodla` / `prognoza` z LV2 (GARCH-t, refit co 30 dni, rosnące okno, ogon t_ν̂) i zamrożony test zbiorczy
  (A/B/C, Bonferroni α/3, bootstrap-t po dniach, B = 999);
- target: odrzucenie przez test zbiorczy hipotezy „prognoza VaR 5 % jest poprawnie skalibrowana” dla prognozy `garch_tnu`
  (rozmiar, K-a) i dla `garch_tnu_zan10` (moc, K-b);
- horyzont: 1 dzień; poziom p = 5 % (jedyny, jak w LV2 dla wniosku).

### R3 — mierzalność tej rundy

Runda jest eksperymentem na danych syntetycznych, więc „mierzalność” to: czy przy 4 000 paneli na komórkę (A0, A1, A2) rozmiar i moc da
się odróżnić od progów. SE odsetka przy 8 % to 0,43 pp, przy 50 % 0,79 pp, więc zapas ≥ 1 pp (2,3 SE) rozstrzyga progi 10 % i 80 %.
Rachunek na liczbach LV2 (**nie jest pomiarem K = 4**): moc 99,6 % przy K = 15 odpowiada przesunięciu statystyki o ok. 5,0 odchyleń;
przy 4 monetach jest ono mniejsze o czynnik √(4/15) ≈ 0,52, a zależność ρ̂ ≈ 0,42 zmniejsza liczbę efektywnych monet K/(1 + (K − 1)ρ̂)
z 2,17 (ρ̂ 0,28) do 1,77, czyli dodatkowo o czynnik ok. 0,90 → przesunięcie ok. 2,3–2,6 odchylenia wobec progu Bonferroniego ≈ 2,4, czyli
**moc rzędu 45–60 %**. Wynik tej rundy może więc być czysto negatywny (K-b < 80 % = reguła K niemierzalna przy K = 4). To jest
dopuszczony wynik, nie niepowodzenie rundy: runda startuje, bo odpowiedź nie jest znana, a próg mocy 80 % jest zamrożony.

### R4 — jedna zmienna, licznik, reguła STOP

- **Jedna zmienna:** siła zależności i trwałości w generatorze (komórki A0–A4 niżej). Wszystko inne jak w LV2 (ν = 5, σ̄ = 4 %, rozgrzewka
  500 dni, estymator, test, B, progi, p = 5 %).
- **Licznik:** poza licznikami (dane syntetyczne).
- **Jeden przebieg rejestrowy.** Brak powtórek po obejrzeniu wyniku. Błąd kodu znaleziony po przebiegu: poprawka + powtórka z tymi samymi
  ziarnami, jawnie opisana w README (wraz z wynikiem pierwszego przebiegu).
- **Reguły STOP:** (1) żaden α z siatki nie daje odsetka przy granicy ≥ 46,3 % przy niezbieżnych ≤ 2 % → przebiegu rejestrowego nie ma,
  runda kończy się werdyktem Revision z opisem, co się nie udało; (2) cel VR komórki A1 nieosiągalny w 2 poprawkach → STOP całej rundy;
  cel VR komórki A2 nieosiągalny → A2 raportowana jako „niedostępna”, werdykt co najwyżej Caveats; (3) NaN w wynikach panelu → STOP;
  (4) jakakolwiek chęć zmiany progów, poziomu p, komórki, estymatora albo generatora po obejrzeniu wyniku → zakazana (nowa pre-rejestracja).

### Co już widziałem (jawnie)

- z kart 017 i 020: liczby w „Wnioski skumulowane” i nic więcej z prawdziwych danych; **nie widziałem** żadnego odsetka trafień na prawdziwych
  danych;
- z LV2: wyniki reguły K dla K = 15 (K-a, K-b, K1, K2, K7);
- **rozpoznanie wykonalności generatora LV2c (przed tą pre-rejestracją, ziarna 9001+, 112 paneli na konfigurację, K = 4, n = 2 091):**
  drukowałem wyłącznie VR, odsetek dopasowań przy granicy, odsetek niezbieżnych, średnią persystencję i średnie ν̂ — **żadnego odrzucenia
  testu zbiorczego, K-a, K-b, K1, K2 ani odsetka trafień w LV2c**. Co z tego wiem: (a) przy α = 0,08 i α + β = 0,9999 odsetek przy granicy
  to tylko ≈ 34–40 % (poniżej celu), przy α = 0,20 ≈ 47 %, przy α = 0,30 ≈ 48,5 % (nasycenie ≈ 49–50 %); (b) przy α = 0,20, ρ = 0,8
  VR rośnie z ρ_szok: 0,5 → 2,24; 0,8 → 2,49; 0,95 → 2,64; 1,0 → 2,69; przy ρ_szok = 1 i ρ = 0,9 → 3,11; (c) niezbieżnych 0–2 %.
  Z (a) i (b) wynika projekt kalibracji (niżej): pokrętłem odsetka przy granicy jest α, pokrętłem VR jest ρ_szok, a dla góry przedziału
  dodatkowo ρ. Te liczby **nie są** wynikiem rundy; kalibracja formalna jest powtarzana na ziarnach rozłącznych.

### Generator LV2c (zbudowany i przetestowany przed pre-rejestracją)

`generuj_panel_lv2c(n_days, n_coins, seed, nu, rho, rho_szok, persystencja, alpha, …)`:

1. **Wspólny szok zmienności.** Mnożnik skali dnia m_it = (ν − 2)/χ²_ν jest brany z kopuły gaussowskiej o parametrze `rho_szok`, więc
   brzeg każdej monety zostaje dokładnie t_ν (wariancja 1), a dni dużej zmienności padają na kilka monet naraz.
2. **Trwałość przy granicy.** `persystencja` (α + β) do 0,9999 (jedna wartość dla wszystkich monet albo wektor); `alpha` (ARCH) jest
   drugim pokrętłem odsetka dopasowań przy granicy.
3. **Własność używana w kalibracji:** rozkład szeregu pojedynczej monety nie zależy od `rho` ani `rho_szok` (testy), więc odsetek przy
   granicy, ν̂ i persystencja zależą tylko od `alpha` i `persystencja`, a VR od `rho` i `rho_szok`; kalibracje rozdzielają się.
4. **Parytet z LV2:** `rho_szok = 0`, `persystencja = None`, `alpha = 0,08` → identyczny wynik bit w bit z `generuj_panel`.

### Komórki (K = 4, n = 2 091, 400 historii + 1 691 oceny)

| komórka | rola | ρ | ρ_szok | α | α + β | cel kalibracji | paneli |
|---|---|---|---|---|---|---|---|
| **A0** | scenariusz LV2 dla K = 4 (dół przedziału z 020) | 0,8 | 0 | 0,08 | 0,98 | brak (ρ̂ LV2 0,282 → VR 1,846) | 4 000 |
| **A1** | **środek przedziału z 020** (komórka główna) | 0,8 | z kalibracji | α\* | 0,9999 | VR 2,264 ± 0,14; przy granicy 51,3 % ± 5 pp | 4 000 |
| **A2** | **góra przedziału z 020** (ρ̂ + 2 SE) | z kalibracji | z kalibracji | α\* | 0,9999 | VR 2,811 ± 0,14; przy granicy 51,3 % ± 5 pp | 4 000 |
| A3 | tylko trwałość (opis dekompozycji) | 0,8 | 0 | α\* | 0,9999 | przy granicy 51,3 % ± 5 pp | 2 000 |
| A4 | tylko wspólny szok (opis dekompozycji) | ρ z A1 | ρ_szok z A1 | 0,08 | 0,98 | brak | 2 000 |

A0, A1, A2 współtworzą werdykt; A3 i A4 tylko opisują, **co** psuje test, jeśli się psuje (nie wchodzą do werdyktu).

### Kalibracja (formalne pilotaże na ziarnach rozłącznych od rejestrowych)

Ziarna pilotaży: `SeedSequence(20_261_091)` (rejestrowe: `SeedSequence(20_261_019)`; rozpoznanie wykonalności używało ziaren 9001+).
Pilotaż drukuje **wyłącznie** VR, odsetek dopasowań przy granicy, odsetek niezbieżnych, średnią persystencję, średnie ν̂ (test jednostkowy
pilnuje, że funkcja pilotażowa nie liczy żadnych statystyk testu zbiorczego ani odsetka trafień).

- **Krok 1 (α\*).** Siatka α ∈ {0,08; 0,12; 0,16; 0,20; 0,25; 0,30}, α + β = 0,9999, ρ = 0,8, ρ_szok = 0,5, **400 paneli** na punkt.
  α\* = **najmniejsze α**, dla którego średni odsetek przy granicy ≥ 46,3 % **i** odsetek niezbieżnych ≤ 2 %. Gdy żadne: STOP (1).
- **Krok 2a (ρ_szok dla A1 i A2).** Przy α\*: ρ_szok ∈ {0; 0,25; 0,5; 0,75; 1,0}, ρ = 0,8, **300 paneli** na punkt; średnie VR wygładzone
  maksimum narastającym; ρ_szok dla celu T to rozwiązanie interpolacji liniowej po siatce.
- **Krok 2b (tylko gdy T > VR(ρ_szok = 1,0), czyli prawdopodobnie dla A2).** ρ_szok = 1,0, ρ ∈ {0,80; 0,85; 0,90; 0,95}, 300 paneli na
  punkt; ρ dla celu T z interpolacji liniowej.
- **Potwierdzenie.** Parametry z interpolacji, **400 nowych paneli** (świeże ziarna pilotażowe). Przyjęte, gdy |średnie VR − T| ≤ 0,14 i odsetek
  przy granicy w [46,3; 56,3] %. Gdy nie: korekta metodą siecznej na punktach siatki i potwierdzeniu, ponownie 400 paneli; najwyżej 2 korekty,
  potem STOP (2). Parametry zaokrąglam do 3 miejsc po przecinku.
- Wyniki kalibracji i wartości parametrów dopisuję **dodatkiem do pre-rejestracji w osobnym commicie przed przebiegiem rejestrowym**.

**Kontrole generatora (R8), na ziarnach pilotażowych:**

- **Ujemna (K-gen-N):** ρ = 0, ρ_szok = 0, α + β = 0,98 (LV2 bez wspólnego czynnika), 200 paneli: średnie ρ̂ ∈ [−0,02; 0,02]
  (VR ≈ 1). Zawiedzenie = generator albo miara zepsute, runda Revision.
- **Parytet (K-gen-P):** test jednostkowy bit w bit z `generuj_panel`, plus parytet wartości VR runnera z `modele.pomiar_rho_h.vr_rho` na tych
  samych trafieniach.
- **Dodatnia (K-gen-D):** średnie VR komórki A0 w przebiegu rejestrowym ∈ 1,846 ± 0,09 (LV2 C2, ρ̂ 0,282 × 3 + 1; tolerancja 3 × 0,03,
  jak w 020). Zawiedzenie = silnik niewiarygodny, werdykt Revision.

### Reguła K (bez zmian względem LV2) i kontrole

Test zbiorczy z `symulacje.moc_var_es` (A: poziom trafień, B: niezależność w czasie, C: ES; Bonferroni α/3 = 1,667 %; bootstrap-t po dniach,
B = 999). Wszystko na p = 5 % i komórce 4 × 1 691. Wartości wierszy i werdykt komórki liczą zamrożone `_wiersz` i `_werdykt` z `run_lv2`.

| kod | rola | co | wymaganie | bramkuje |
|---|---|---|---|---|
| K1 | kontrola negatywna (R8) | rozmiar testu na `wyr_t5` (σ wyroczni, ogon t5) | ∈ [2,5; 7,5] % | każdy wniosek |
| K2 | kontrola pozytywna (R8) | moc wobec `zan30` (σ wyroczni − 30 %) | ≥ 95 % | każdy wniosek |
| K7a | estymator | średnia ν̂ (prawda 5) | ∈ [4,0; 6,5] | każdy wniosek |
| K7c | estymator | odsetek dopasowań bez zbieżności | ≤ 2 % | każdy wniosek |
| K7b, K7d | estymator | średnia α̂ + β̂ ∈ [0,95; 0,995]; odsetek przy granicy ≤ 5 % | **bramkują tylko w komórkach z trwałością LV2 (A0, A4)**; w A1–A3 zastępuje je KAL | jw. |
| KAL | zgodność kalibracji | w A1 i A2: VR komórki w przebiegu rejestrowym ∈ cel ± 0,14; w A1, A2, A3: odsetek przy granicy ∈ [46,3; 56,3] % | każdy wniosek |
| **K-a** | kryterium | rozmiar na `garch_tnu` | ≤ **10 %** | — |
| **K-b** | kryterium | moc na `garch_tnu_zan10` (σ̂ × 0,90) | ≥ **80 %** | — |

Werdykt komórki: zamrożony `_werdykt` (TAK ⇔ wszystkie kryteria i kontrole; NIE ⇔ kryterium niespełnione przy kontrolach w porządku; w
przeciwnym razie WSTRZYMANE). **Opis, nie kryterium:** krzywa mocy `garch_tnu` przy mnożniku σ̂ ∈ {1; 0,95; 0,90; 0,85; 0,80; 0,70}
(punkty 0,90 i 0,80 liczy zamrożone `prognoza`; pozostałe własna funkcja z testem parytetu), MDE(80 %) metodą zamrożonego `mde`, VR, ρ̂,
odsetek trafień `garch_tnu` w laboratorium, odsetek przy granicy, persystencja i ν̂. Raport (R14) jest neutralnym reporterem: werdykt
podpisuje Claude w sekcji „Wynik”.

### Przewidywania (zapisane przed jakimkolwiek odczytem reguły K w LV2c)

Ze skalowania z LV2 (R3), nie z pomiaru; to ma być zgadywanie do sprawdzenia, nie cel.

| wielkość | przewidywanie | pewność |
|---|---|---|
| kalibracja możliwa (nie STOP 1) | α\* = 0,20 (60 %), 0,16 (25 %), 0,25 (15 %) | 90 % że istnieje |
| A2 wymaga kroku 2b (ρ > 0,8) | tak | 80 % |
| K-gen-N, K-gen-D | zaliczone | 90 % |
| K1 w A0, A1, A2 | zaliczone (∈ [2,5; 7,5] %) | 85 % |
| K2 (zan30) w A0, A1, A2 | zaliczone (≥ 95 %) | 85 % |
| K7c (niezbieżne ≤ 2 %) w A1, A2 | zaliczone, ale blisko progu (0–2 %) | 70 % |
| K-a w A0 / A1 / A2 | 5–8 % / 6–10 % / 6–11 % | P(K-a ≤ 10 % w A1) = 65 % |
| **K-b w A0 / A1 / A2** | **ok. 58 % (40–75) / ok. 48 % (30–65) / ok. 42 % (25–60)** | **P(K-b ≥ 80 % w A1) = 10 %** |
| werdykt A1 | **NIE** (K-b < 80 %) | 70 %; TAK 8 %; WSTRZYMANE 22 % |
| konsekwencja | reguła K niemierzalna przy K = 4 (moc zbyt mała na zaniżenie σ o 10 %) | 70 % |

Gdyby wyszło TAK w A1 i A2 (K-b ≥ 80 % przy czterech monetach przy zależności ρ̂ ≈ 0,42–0,60), byłoby to **zaskoczenie** (prawdopodobieństwo
poniżej 10 %), które każe sprawdzić, czy zależność nie jest za słaba w laboratorium (K-gen-D i VR komórek).

### Co wynika z którego wyniku (zapisane z góry)

Werdykty trzech komórek: T0 (A0), T1 (A1), T2 (A2).

| wynik | praktyczna konsekwencja |
|---|---|
| T0, T1, T2 = TAK | **Reguła K mierzalna przy K = 4 w całym przedziale z 020.** Warunek przeniesienia nr 2 z LV2 zastąpiony wynikiem LV2c; 018 może być zlecona po danych za październik 2026 i powtórce 020 (kryterium niżej). |
| T0, T1 = TAK; T2 ≠ TAK | **Caveats:** mierzalna w środku, nie w górze przedziału. 018 tylko, gdy powtórka 020 da ρ̂ ≤ ρ̂ środka + 1 SE (do ustalenia w pre-rejestracji 018); decyzja użytkownika. |
| T1 = NIE (K-a > 10 % lub K-b < 80 % przy kontrolach w porządku) | **NIEMIERZALNA przy K = 4 w warunkach z danych** (R3: runda VaR/ES na danych nie startuje w tej postaci). Opcje dla użytkownika: (a) reguła K′ (inne kryterium, np. MDE ≤ 0,20, albo test na wielu dniach z osobną pre-rejestracją), (b) zamknięcie rundy VaR/ES na danych, (c) szerszy koszyk — wymaga **zmiany decyzji użytkownika** o czterech monetach, więc tylko za jego zgodą. |
| T1 = WSTRZYMANE | brak wniosku; naprawa kontroli (Revision). Jeśli niezaliczoną kontrolą jest tylko K2 (moc wobec zan30 < 95 %), praktycznie to samo co NIE (test głuchy przy K = 4), formalnie WSTRZYMANE wg zamrożonej `_werdykt`. |
| T0 = NIE, T1 = TAK (lub odwrotnie) | wynik jest nietypowy; opisać i nie wyciągać wniosku bez sprawdzenia kalibracji (KAL, K-gen-D). |
| A3 albo A4 ≠ A1 w K-a lub K-b o > 3 SE | opis: wskazuje, czy wspólny szok, czy trwałość przy granicy bardziej psuje test (bez wpływu na werdykt) |

### Propozycja kryterium zgodności dla powtórki 020 (karta 018; ostateczne zapisze pre-rejestracja 018)

Stara bramka 017 (ρ̂ + 2 SE ≤ 0,282) nie przechodzi nawet w LV2. Zapisuję z góry kryterium, które **MOŻE przejść**: powtórka 020 na danych
do 2026-10-31 jest zgodna z laboratorium, gdy ρ̂_powtórki ≤ ρ̂ komórki A2 (≈ 0,60, o ile A2 wyszła TAK) **oraz** odsetek dopasowań
przy granicy ∈ [41; 61] %. Jeśli A2 nie wyszła TAK, kryterium dotyczy najwyższej komórki z werdyktem TAK.

### Czego NIE robię

- Nie uruchamiam karty 018 ani nie liczę odsetka trafień na prawdziwych danych.
- Nie zmieniam plików zamrożonych, progów 10 % i 80 %, poziomu p, komórki, `dopasuj_garch_t` ani granicy persystencji 0,9999.
- Nie stroję generatora na odrzuceniach testu zbiorczego (kalibracja wyłącznie na VR i odsetku przy granicy); nie dobieram ziaren.
- Nie dotykam alpha, nie wkładam `data/` do gita, nie scalam do `main`.

### Decyzje projektowe podjęte na delegację (2026-10-08; zapis także w `STATUS.md`)

1. **α jako pokrętło odsetka przy granicy** (karta mówiła tylko „α + β do 0,9999”): przy α = 0,08 odsetek nasyca się na ≈ 40 %, poniżej
   tolerancji celu 46,3 %. Ścieżka odwrotu: pozostać przy α = 0,08 i uznać cel odsetka przy granicy za nieosiągalny (raport z tym zastrzeżeniem).
2. **Trzy scenariusze zależności (A0, A1, A2) i dwie komórki dekompozycji (A3, A4)** zamiast jednego punktu: 020 dała SE ρ̂ = 0,091 i dolny
   koniec poniżej LV2, a tabela decyzji z 020 wymaga scenariusza LV2 dla K = 4. Ścieżka odwrotu: werdykt tylko z A1.
3. **K7b i K7d nie bramkują w komórkach z trwałością przy granicy:** są sprzeczne z celem kalibracji z karty (27 → 51 % przy granicy),
   a ich funkcję (kontrola estymatora) pełni KAL oraz K7a/K7c. Ścieżka odwrotu: raportować je jako opis (robię to i tak).
4. **Krzywa mocy `garch_tnu` jako opis** (MDE dla ewentualnej reguły K′): bez wpływu na werdykt.

### Użyte skille

(do uzupełnienia po przebiegu)
