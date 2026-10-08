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
- Status tego pliku: **pre-rejestracja** (commit `6787a2a`, poprzedza pilotaże formalne i przebieg rejestrowy; tekst pre-rejestracji poniżej
  nie został zmieniony) **oraz wynik**: runda zakończyła się regułą STOP 1 na kalibracji, **przebiegu rejestrowego z regułą K nie było**,
  werdykt **Revision** (sekcja „Wynik”, na końcu pliku).

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

## Wynik

Pliki wynikowe w tym katalogu: `raw_pilot_kontrola_n.txt` (K-gen-N), `raw_pilot_kalibracja.txt` + `kalibracja.json` (krok 1, STOP 1),
`raw_rejestr_odmowa.txt` (runner odmawia przebiegu rejestrowego), `druga_droga_brzeg.py` + `raw_druga_droga.txt` (weryfikacja
niezależna). Osobnego `raw_output.txt` przebiegu rejestrowego **nie ma, bo przebieg się nie odbył**; jego rolę pełnią pliki `raw_*`.
Kolejność: pre-rejestracja `6787a2a` → runner `cd4d5fd` (przed pilotażami) → pilotaże (ziarno `SeedSequence(20_261_091)`) → STOP 1 →
druga droga (ziarno 31 415 926). Żadnego odrzucenia testu zbiorczego ani odsetka trafień nie policzono.

### Co się stało, w prostych słowach

Laboratorium miało udawać cztery prawdziwe monety. Dwie rzeczy miało robić naraz: trafienia VaR mają się zbiegać w tych samych dniach
tak jak w 020 (VR 2,264) i model GARCH-t ma dochodzić do granicy trwałości (0,9999) w około połowie dopasowań (51,3 % w 020). Pierwsza
rzecz wychodzi od razu (VR 2,20–2,22, czyli w tolerancji 2,264 ± 0,14). Druga nie wychodzi: **żadne ustawienie generatora nie
doprowadziło odsetka dopasowań przy granicy do 46,3 %** (najlepsze 44,5 % ± 1,3 pp). Pre-rejestracja mówiła z góry, co wtedy: nie robię
przebiegu rejestrowego i kończę rundę werdyktem Revision. Tak zrobiłem. **Na pytanie rundy — czy reguła K jest mierzalna dla czterech
monet — ta runda nie odpowiada ani na tak, ani na nie.**

### Kontrola ujemna generatora (K-gen-N, R8)

ρ = 0, ρ_szok = 0, α + β = 0,98, 200 paneli, ziarna pilotażowe: VR 1,013 ± 0,004, ρ̂ **+0,0044 ± 0,0014**, wymaganie ρ̂ ∈ [−0,02; 0,02]
→ **ZALICZONA.** Bez zależności miara niczego nie wymyśla. (Przewidywanie „zaliczona”, 90 % → trafione.) K-gen-P (parytet z `generuj_panel`
bit w bit i parytet VR runnera z `modele.pomiar_rho_h.vr_rho`) sprawdzają testy jednostkowe w repozytorium (zielone). K-gen-D wymaga
komórki A0 z przebiegu rejestrowego, więc **nie oceniona.**

### Krok 1 kalibracji (400 paneli na punkt, ρ = 0,8, ρ_szok = 0,5, α + β = 0,9999)

| α | VR ± SE | ρ̂ | przy granicy ± SE | niezbieżne | średnia persystencja | średnie ν̂ |
|---|---|---|---|---|---|---|
| 0,08 | 2,200 ± 0,011 | 0,4000 | 36,6 % ± 1,2 pp | 0,00 % | 0,9932 | 5,32 |
| 0,12 | 2,219 ± 0,011 | 0,4065 | 41,2 % ± 1,3 pp | 0,00 % | 0,9915 | 5,33 |
| **0,16** | 2,215 ± 0,011 | 0,4051 | **44,5 % ± 1,3 pp** | 0,00 % | 0,9899 | 5,25 |
| 0,20 | 2,221 ± 0,011 | 0,4070 | 41,6 % ± 1,4 pp | 0,00 % | 0,9873 | 5,30 |
| 0,25 | 2,214 ± 0,011 | 0,4047 | 43,9 % ± 1,3 pp | 0,00 % | 0,9855 | 5,31 |
| 0,30 | 2,217 ± 0,011 | 0,4057 | 44,1 % ± 1,3 pp | 0,00 % | 0,9835 | 5,34 |

Wymagane: ≥ 46,3 % **i** niezbieżne ≤ 2 %. Niezbieżnych jest ≈ 0, więc warunek zawodzi wyłącznie na odsetku przy granicy: maksimum
44,5 % leży 1,8 pp (ok. 1,4 SE) pod progiem, a od α = 0,12 odsetek leży na płaskowyżu 41–45 % (nie rośnie z α). → **STOP 1.** VR (cel
2,264 ± 0,14) leży w tolerancji przy ρ_szok = 0,5 w każdym wierszu, czyli kalibracja VR byłaby osiągalna; zawodzi tylko drugi cel.
Wynik z pliku `kalibracja.json` (klucze `krok1`, `stop`; `krok2a` puste, `alfa_star` null, bo kroki 2–3 nie ruszały).

### Odmowa runnera

`python -m symulacje.run_lv2c rejestr --kalibracja kalibracja.json` kończy się natychmiast komunikatem „STOP: kalibracja A1 nie powiodła
się — przebiegu rejestrowego nie ma”, kod wyjścia 1 (`raw_rejestr_odmowa.txt`). Reguła nie jest tylko zapisem w README, runner jej pilnuje.

### Weryfikacja niezależna (druga droga)

`druga_droga_brzeg.py` liczy odsetek przy granicy **wprost z `dopasuj_garch_t`** na świeżych panelach (ziarno 31 415 926, rozłączne z pilotażowym
i rejestrowym), z tym samym harmonogramem dopasowań (co 30 dni, okno rosnące od 400), ale bez `run_lv2c`, bez `prognoza_garch_tnu` i bez agregacji
runnera. To **opis po STOP 1**, nie kalibracja i nie przebieg rejestrowy. 100 paneli × 4 monety × 57 dopasowań = 22 800 dopasowań na punkt.

| punkt (α, ρ_szok) | druga droga | pilotaż (400 paneli) | różnica / SE różnicy |
|---|---|---|---|
| 0,16; 0,5 | 41,1 % ± 2,5 pp | 44,5 % ± 1,3 pp | 3,4 / 2,8 = 1,2 |
| 0,30; 0,5 | 43,6 % ± 2,5 pp | 44,1 % ± 1,3 pp | 0,5 / 2,8 = 0,2 |
| 0,20; 1,0 | 36,6 % ± 2,9 pp | 41,6 % ± 1,4 pp (przy ρ_szok = 0,5) | 5,0 / 3,2 = 1,6 |

Wniosek z porównania: **druga droga potwierdza poziom 37–44 % i brak dojścia do 46,3 %.** Różnice mieszczą się w 1,6 SE; trzeci punkt jest
najniższy, bo przy ρ_szok = 1 cztery monety dzielą tę samą ścieżkę zmienności, więc 100 paneli niesie mniej niezależnej informacji (stąd
większe SE). Własność „rozkład pojedynczej monety nie zależy od ρ_szok” stoi w testach generatora; rozbieżność trzeciego punktu o 1,6 SE
traktuję jako szum, nie jako jej złamanie. Rozbicie po parametrach: **100 % przypadków „przy granicy” to granica persystencji**; ω, udział α
i ν nigdy nie stoją na swoich granicach. Zależność od długości okna uczącego jest słaba i niejednolita (α = 0,16: 42,0 / 42,0 / 39,8 % dla okien
400–800 / 800–1 400 / 1 400–2 100 dni; α = 0,30: 41,9 / 44,2 / 44,1 %), więc dłuższe okno nie dowozi brakujących 2–7 pp. Średnia
persystencja dopasowań 0,976–0,992 (nie 0,9999): estymator zaniża prawdziwą, ledwie stacjonarną trwałość.

### Sprzeczność z rozpoznaniem (jawnie)

Rozpoznanie przed pre-rejestracją (ziarna 9001+, 112 paneli) dało przy α = 0,20 ≈ 47 % i przy α = 0,30 ≈ 48,5 %, więc uznałem próg 46,3 % za
osiągalny. Formalny pilotaż (400 paneli, ziarna rozłączne) dał 41,6 % i 44,1 %, a druga droga przy α = 0,30 43,6 %. Rozpoznanie miało SE rzędu
2,5 pp (112 paneli), więc różnica wobec pilotażu to ok. 2 SE: albo szczęśliwy szum, albo coś, czego nie umiem rozstrzygnąć (ta sama wielkość,
ten sam kod, inne ziarna). **Liczy się pilotaż formalny**, bo tylko on był zapisany z góry. Moja pre-rejestrowa pewność 90 %, że kalibracja jest
możliwa, była zawyżona (przewidywanie **chybione**).

### Dlaczego tak wychodzi (hipoteza, nie wynik)

Przy prawdziwej wartości α + β dokładnie na granicy jednostronnej estymator ląduje na niej asymptotycznie w ok. 50 % przypadków (typowy
efekt „piętrzenia się” estymatora na brzegu przestrzeni parametrów; **z pamięci, nie sprawdzone tu w źródle**), a w skończonej próbie mniej: tu 37–45 %. Dane (51,3 %) leżą powyżej tego pułapu, co
sugeruje, że w prawdziwych szeregach trwałość jest „poza granicą” (przesunięcia poziomu wariancji, reżimy), czego stacjonarny GARCH z
α + β ≤ 0,9999 nie wytworzy. **Tego tu nie zmierzyłem** (nie badałem prawdziwych szeregów; rozbicie po oknach jest zgodne, nie dowodzi). To jest
treść karty 021.

### Przewidywania z pre-rejestracji — rozliczenie

| wielkość | przewidywanie | wynik |
|---|---|---|
| kalibracja możliwa (nie STOP 1) | istnieje, 90 % | **chybione** (STOP 1) |
| K-gen-N | zaliczone, 90 % | trafione (ρ̂ +0,0044) |
| pozostałe (K-gen-D, K1, K2, K7c, K-a, K-b, werdykty A1, konieczność kroku 2b) | — | **nieocenione** — przebiegu rejestrowego nie było |

### Co na plus (+) / Co na minus (−)

**+** STOP 1 zadziałał tak, jak zapisano z góry: nie dobierałem ziaren ani progów, nie zmieniłem generatora po obejrzeniu wyniku, runner
odmawia przebiegu. **+** Pilotaż nie pokazał żadnego odrzucenia testu K, więc rundę da się powtórzyć w nowej pre-rejestracji bez skażenia
generatora. **+** VR (cel z 020) jest osiągalny bez korekty, więc w kolejnej rundzie zostaje jedno pokrętło do znalezienia, nie dwa. **+** Druga
droga (inne ziarna, inny kod) zgadza się co do poziomu 37–44 %. **+** Granica to w 100 % persystencja, więc brakujący mechanizm dotyczy
persystencji, nie ν ani ω.

**−** **Pytanie rundy bez odpowiedzi:** mierzalność reguły K przy K = 4 nadal nieznana; 018 nadal stoi. **−** Próg 46,3 % i tolerancja ± 5 pp
wzięły się z rozpoznania, które okazało się zawyżone; STOP 1 zadziałał na progu, który sam ustaliłem, więc przy innym progu (np. 40 %) kalibracja
by przeszła, i nie wolno tego robić po fakcie. **−** Pułap ok. 44 % jest hipotezą o brzegu parametru, nie zmierzonym faktem. **−** Laboratorium to
ν = 5 (w 020 ν̂ = 4,14), jednakowa persystencja dla czterech monet (w 020 SOL ma 0 dopasowań przy granicy), bez dźwigni i skoków, kopuła
gaussowska; nawet udana kalibracja VR i granicy zostawiłaby te uproszczenia. **−** Druga droga ma 100 paneli (SE 2,5 pp), więc tylko
potwierdza poziom, nie ostrzy go.

### Kogo NIE ma w zbiorze

Panele, w których estymator nie dochodzi do granicy, są w zbiorze (to ok. 55–63 % dopasowań), niezbieżnych praktycznie nie ma (< 0,01 %), więc
wynik nie powstaje z odfiltrowania. Nie ma natomiast: (1) komórek A0–A4 w ogóle (ani jednego odrzucenia testu K), (2) kroków 2a, 2b i
potwierdzenia, (3) żadnych prawdziwych szeregów (poziom wariancji w czasie nie był badany), (4) kombinacji α > 0,30, ρ_szok ≠ 0,5 w pilotażu
(druga droga zajrzała w ρ_szok = 1 na jednym punkcie), (5) generatora z reżimami wariancji (karta 021).

### Weryfikacja i przegląd kodu

- **Liczba przeliczona drugą drogą:** odsetek przy granicy (tabela wyżej), z niezależnym kodem i ziarnem; zgodność w 1,6 SE.
- **K-gen-N** zaliczona; **kontrole generatora** w testach: 11 testów generatora (parytet z LV2 bit w bit, niezależność brzegu pojedynczej
  monety od ρ i ρ_szok, determinizm, `hypothesis`), 43 testy runnera (m.in. że pilotaż nie liczy statystyk reguły K); pełny zestaw 1 237 przeszedł.
- **Błąd kodu znaleziony w rundzie:** `roznica_se` dzieliło przez zero przy SE = 0 (wykryte przy próbie dymnej, naprawione i opisane testem).
  Nie dotyczy liczb STOP 1 (funkcja służy porównaniu komórek A3/A4 w przebiegu rejestrowym, którego nie było).
- **Przegląd diffu (`engineering:code-review`):** wynik w sekcji „Przegląd kodu” poniżej.
- **Przeoczenie wykonawcze:** pierwsza wersja drugiej drogi nie ustawiała jednowątkowego BLAS i przeciążyła maszynę (obciążenie 180); poprawiona
  (te same punkty, 39 s). Nie wpływa na liczby, wpływa na czas.

### Wniosek

Reguła K dla czterech monet pozostaje **niezmierzona**. Generator LV2c nie potrafi odtworzyć granicy persystencji w 51 % dopasowań, najwyżej
w ok. 44 %. To nie jest wynik o rynku ani o regule K, tylko o ograniczeniu laboratorium. Nie wolno z tego wyciągać, że reguła K jest dobra
albo zła.

### Rekomendacja

Otwieram kartę **021** (nowa pre-rejestracja): generator z przesunięciami poziomu wariancji, komórka A0 (scenariusz LV2 dla K = 4)
w tej samej rundzie, bez zmiany progów i reguły K. Poluzowanie celu odsetka przy granicy odradzam jako samodzielne rozwiązanie (przesunięcie
słupków po fakcie). Kartę 018 trzymam wstrzymaną.

### Werdykt (podpisuje Claude, 2026-10-08, R14)

**Revision.** Powód wprost z pre-rejestracji (STOP 1): kalibracja generatora nie osiągnęła zapisanego celu, przebiegu rejestrowego nie ma.
Skrypt był neutralnym reporterem; ocena i werdykt są moje.

### Użyte skille

- `data:statistical-analysis` — SE różnicy dwóch odsetków, porównanie pilotażu z drugą drogą w jednostkach SE, wnioski ostrożne wobec małej próby
  drugiej drogi (100 paneli).
- `data:validate-data` — lista kontrolna: źródło liczby, niezależne przeliczenie, „kogo nie ma w zbiorze”, ostrzeżenie o wyniku idealnie
  potwierdzającym hipotezę (tu wynik jej NIE potwierdza).
- `engineering:code-review` — przegląd diffu runnera i generatora (sekcja „Przegląd kodu”).
- `clas5-runda` — procedura rundy: pre-rejestracja przed wynikiem, wpis w pamięci projektu (`runs/INDEX.md`), rejestr STOP.
  (Rejestr `runs/skille/` z alpha nie istnieje w beta; użycia wpisane ręcznie.)

### Przegląd kodu

(przegląd niezależnego recenzenta był w toku w chwili tego commitu; jego wynik jest dopisany w następnym commicie)
