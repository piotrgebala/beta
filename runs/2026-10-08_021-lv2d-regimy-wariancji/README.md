# 021 — LV2d: czy reguła K (test bezwzględny VaR 5 %) jest mierzalna dla 4 monet, gdy poziom zmienności przesuwa się skokami

## Metadane

- Karta: `zadania/021-lv2d-przesuniecia-poziomu-wariancji.md` (otwarta po STOP 1 w karcie 019). Zlecenie wykonania: użytkownik, 2026-10-08
  („Wykonaj i realizuj kolejne kroki”). Poprzednicy: 016 (LV2), 017, 020, 019 (STOP 1).
- Dane **wyłącznie syntetyczne.** Licznik: **poza licznikami.** „Ryzyko ogona (VaR/ES) 2021+” **zostaje 0**, „zmienność 2021+” zostaje 1,
  rejestr zwrotów alpha (N = 40) nietknięty. Nic tu nie czyta prawdziwych zwrotów; z prawdziwych danych wchodzą tylko liczby z kart 017 i 020
  (VR, ρ̂, SE, odsetek dopasowań przy granicy), zapisane niżej.
- Kod: generator `symulacje/garch_panel_regimy.py` + `tests/test_garch_panel_regimy.py` (commit `1d1f90c`, przed tą pre-rejestracją).
  Runner `symulacje/run_lv2d.py` powstaje **po** tej pre-rejestracji, przed pilotażami formalnymi. Pliki zamrożone, importowane bez zmian:
  LV2 (`garch_panel.py`, `garch_t.py`, `prognozy_lv2.py`, `moc_var_es.py`, `run_lv2.py`, `porownanie_lv2.py`), generator LV2c
  (`garch_panel_wspolny_szok.py`), runner 019 (`run_lv2c.py`) i miara 017/020 (`modele/pomiar_rho_h.py`, `modele/opis_rho_h.py`).
- Status tego pliku: **pre-rejestracja** (zapisana i zacommitowana przed jakimkolwiek pilotażem formalnym i przed przebiegiem rejestrowym; hash
  commitu dopisuję w dodatku po kalibracji). Wynik, werdykt i przegląd kodu dojdą w osobnych sekcjach poniżej, bez zmiany tego tekstu.

## Pre-rejestracja

### Wnioski skumulowane, które dotyczą tej rundy

`[2026-10-08, 019]`: laboratorium LV2c doszło do celu VR (2,20–2,22 wobec 2,264 ± 0,14), ale nie do odsetka dopasowań GARCH-t przy granicy
persystencji: maksimum 44,5 % ± 1,3 pp (płaskowyż 41–45 % od α = 0,12) wobec progu 46,3 % (cel z 020: 51,3 %), 100 % trafień w granicę to
granica persystencji, niezbieżnych ≈ 0 %; druga droga zgodna (37–44 %); przebiegu rejestrowego nie było, mierzalność reguły K dla czterech monet
**niezmierzona**. `[2026-10-07, 020]`: VR 2,264, ρ̂ 0,421 (SE 0,091; ρ̂ ± 2 SE = [0,239; 0,604], VR [1,717; 2,811]), 117 z 228 dopasowań
(51,3 %) przy granicy, persystencja 0,970, ν̂ 4,14. `[2026-10-07, LV2]`: przy K = 15 rozmiar testu zbiorczego `garch_tnu` 5,0 % (próg 10 %), moc wobec
σ̂ × 0,90 99,6 % (próg 80 %); przy K = 4 moc nie była mierzona. Wynika z nich projekt: (i) generator ma dostać mechanizm, którego LV2c
nie miał (przesunięcia poziomu wariancji wspólne dla monet), a nie kolejne pokrętło trwałości; (ii) próg i reguła K zostają bez zmian;
(iii) komórka A0 (scenariusz LV2 dla K = 4) wchodzi do tej rundy niezależnie od kalibracji, bo odpowiada na pytanie, które w 019 pozostało
bez wyniku.

### R1 — mechanizm jednym zdaniem

Jeśli poziom zmienności całego rynku zmienia się skokami w skali setek dni, której GARCH(1,1) nie opisze swoją krótką pamięcią, to
estymator dopasowuje trwałość do jej granicy (jak w około połowie dopasowań na prawdziwych danych) i cztery monety wychodzą ponad VaR razem,
w tych samych reżimach; laboratorium z takim mechanizmem sprawdza, czy reguła K nadal rozróżnia poprawną prognozę od zaniżonej o 10 %.
(Pomiar własności przyrządu, nie hipoteza o rynku; żadnej „drugiej strony” handlowej nie zakłada.) **Uczciwe zastrzeżenie:** mechanizm wybrałem
po obejrzeniu STOP 1 w 019, więc to wyjaśnienie po fakcie, a nie przewidywanie; nie sprawdzałem go na prawdziwych szeregach.

### R2 — zbiór informacyjny × formuła × target × horyzont

- zbiór informacyjny: syntetyczny panel 4 monet × 2 091 dni (tyle wierszy ma panel wspólny BTC/ETH/SOL/BNB z 020), 400 dni historii + 1 691 dni
  oceny; generator LV2d (niżej);
- formuła: dokładnie zamrożone `zbuduj_zrodla` / `prognoza` z LV2 (GARCH-t, refit co 30 dni, rosnące okno od 400, ogon t_ν̂) i zamrożony test
  zbiorczy (A/B/C, Bonferroni α/3, bootstrap-t po dniach, B = 999), tak jak w `run_lv2c.py`;
- target: odrzucenie przez test zbiorczy hipotezy „prognoza VaR 5 % jest poprawnie skalibrowana” dla `garch_tnu` (rozmiar, K-a) i dla
  `garch_tnu_zan10` (moc, K-b);
- horyzont: 1 dzień; poziom p = 5 % (jedyny).

### R3 — mierzalność tej rundy

Runda jest eksperymentem na danych syntetycznych, więc „mierzalność” to: czy przy 4 000 paneli na komórkę rozmiar i moc da się odróżnić od progów
10 % i 80 %. SE odsetka przy 8 % to 0,43 pp, przy 50 % 0,79 pp, więc zapas ≥ 1 pp (2,3 SE) rozstrzyga oba progi. Kalibracja ma 1 000 paneli na
punkt (SE odsetka dopasowań przy granicy ≈ 26 pp / √1000 ≈ 0,8 pp; SD pojedynczego panelu ≈ 26 pp z przeglądu 019). Koszt: jeden panel pilotażowy
ok. 0,5 s, jeden panel rejestrowy (wszystkie prognozy + bootstrap, B = 999) ok. 1,2 s, 32 procesory → cały plan to rzędu kilkudziesięciu minut.
**Wynik czysto negatywny jest dopuszczony** (K-b < 80 % = reguła K niemierzalna przy K = 4): to odpowiedź na pytanie rundy, nie jej porażka.

### R4 — jedna zmienna, licznik, reguły STOP

- **Jedna zmienna:** wspólny poziom wariancji w reżimach (amplituda *s*, średnia długość reżimu *D*) jako mechanizm brakujący w LV2c; baza
  to LV2 bez zmian (ν = 5, σ̄ = 4 %, α = 0,08, α + β = 0,98, rozgrzewka 500 dni, estymator, test, B, progi, p = 5 %). Zależność między monetami
  (ρ, ρ_szok) jest drugim, **kalibrowanym** pokrętłem (cel VR z 020), nie zmienną rundy.
- **Licznik:** poza licznikami (dane syntetyczne).
- **Jeden przebieg rejestrowy.** Brak powtórek po obejrzeniu wyniku. Błąd kodu znaleziony po przebiegu: poprawka + powtórka z tymi samymi
  ziarnami, jawnie opisana w README (wraz z wynikiem pierwszego przebiegu).
- **Reguły STOP:**
  1. **STOP 1 (generator):** żadna amplituda *s* z siatki nie daje wygładzonego odsetka przy granicy ≥ **41,3 %** ani dla *D* = 300, ani dla
     *D* = 150 → komórki B1–B3 są „niedostępne”, mechanizm uznajemy za niewystarczający; komórka A0 i tak idzie w przebiegu rejestrowym
     (nie wymaga kalibracji); werdykt rundy co najwyżej Revision.
  2. **STOP 2 (potwierdzenie):** potwierdzenie amplitudy (odsetek przy granicy ∈ [41,3; 61,3] % i niezbieżne ≤ 2 %) nie udaje się po 2 korektach →
     jak STOP 1. Potwierdzenie VR komórki B2 nie udaje się po 2 korektach → B2 „niedostępna”, werdykt rundy Revision. Dla B1 albo B3 → ta
     komórka „niedostępna”, werdykt co najwyżej Caveats.
  3. **NaN** w wynikach panelu (pilotaż, kalibracja, przebieg rejestrowy) → STOP (nie „niedostępna”, nie „zaliczone”).
  4. Jakakolwiek chęć zmiany progów, poziomu p, estymatora, generatora, okna celu, komórki albo ziaren po obejrzeniu wyniku → zakazana
     (nowa pre-rejestracja).

### Co już widziałem (jawnie)

- z kart 017 i 020: liczby w „Wnioski skumulowane” i nic więcej z prawdziwych danych; **nie widziałem** odsetka trafień na prawdziwych danych;
- z LV2: wyniki reguły K dla K = 15; z 019: pilotaż kroku 1 i druga droga (odsetek przy granicy, VR, ρ̂, niezbieżne, persystencja, ν̂ — tylko
  pilotaż, **żadnego** odrzucenia testu zbiorczego z przebiegu rejestrowego), przegląd kodu 019;
- **próba dymna 019** (`rejestr --smoke`, 4 panele po 700 dni, ziarno rejestrowe 19) wydrukowała szum odrzuceń testu K na maleńkich panelach,
  patrz README 019, „Ujawnienie”; dlatego 021 ma **nowe ziarna** (niżej) i próby dymne na ziarnie spoza wszystkich pilotażowych i rejestrowych;
- **generator LV2d** zbudowałem i przetestowałem jednostkowo przed tą pre-rejestracją (commit `1d1f90c`): testy sprawdzają własności
  konstrukcji (bit w bit z LV2c przy *s* = 0, niezależność standaryzowanej innowacji od poziomu, wspólny poziom dla monet, kurtoza rośnie
  z amplitudą). **Nie uruchamiałem** na LV2d żadnego estymatora GARCH-t, pilotażu, VR ani testu zbiorczego. Zmierzyłem czas pełnego potoku
  na jednym panelu (ziarno 9 999 021, wykluczone z pilotaży i przebiegu), czytałem tylko czas, nie odrzucenia testu;
- **nie widziałem** żadnej wartości odsetka przy granicy, VR ani ν̂ dla LV2d. Hipoteza, że poziom wariancji podnosi odsetek przy granicy,
  jest niezmierzona.

### Generator LV2d

`generuj_panel_lv2d(n_days, n_coins, seed, nu, rho, rho_szok, persystencja, alpha, amplituda, dlugosc)`:

1. **Baza = LV2c** (wspólny szok zmienności `rho_szok`, zależność `rho`, trwałość `persystencja`, `alpha`); brzeg każdej monety to t_ν o wariancji 1.
2. **Wspólny poziom wariancji L_t.** Każdy dzień zaczyna nowy reżim z prawdopodobieństwem 1/*D* (dzień 0 zawsze). W reżimie L jest stałe i takie samo
   dla wszystkich monet; log L = x − *s*²/2, x ~ N(0, *s*²), niezależnie między reżimami (pełny powrót do średniej), więc E[L] = 1.
   Zwrot r = √L · r(LV2c); `sigma2` wyroczni = L · σ²(LV2c). L **nie wchodzi** do rekurencji GARCH, więc standaryzowana innowacja r/√σ² jest
   dokładnie jak w LV2c; wyrocznia zna L (to prawdziwy warunkowy rozkład), a estymowany GARCH-t go nie zna i musi go „odgadnąć” trwałością.
3. **Osobny strumień losowań** (`[seed, 21]`): losowania LV2c są nietknięte. **Parytet:** *s* = 0 daje wynik identyczny bit w bit z `generuj_panel_lv2c`
   (a przy `rho_szok = 0`, `persystencja = None`, `alpha = 0,08` także z `generuj_panel` z LV2).
4. **Własność używana w kalibracji (testy):** poziom L zależy tylko od (ziarno, *s*, *D*), więc rozkład szeregu **pojedynczej monety** nie zależy od
   `rho` ani `rho_szok`. Odsetek dopasowań przy granicy zależy więc tylko od (*s*, *D*) — i kalibruję go **osobno** od VR; VR zależy od `rho`, `rho_szok`
   i (przez skupianie trafień przy skokach poziomu) od *s*.
5. *s* = 0,5 znaczy: odchylenie standardowe log-wariancji 0,5, czyli zmienność ±25 % przy 1 odchyleniu; *s* = 1,5 to zmienność ±2,1× przy 1 odchyleniu.

### Komórki (K = 4, n = 2 091, 400 historii + 1 691 oceny)

| komórka | rola | ρ | ρ_szok | poziom wariancji | α, α + β | cel kalibracji | paneli |
|---|---|---|---|---|---|---|---|
| **A0** | scenariusz LV2 dla K = 4 (karta, pkt 2); bez kalibracji | 0,8 | 0 | brak (*s* = 0) | 0,08; 0,98 | brak (VR 1,846 ± 0,09 jako K-gen-D) | 4 000 |
| **B1** | dół przedziału z 020 | z kalibracji | z kalibracji | *s*\*, *D*\* | 0,08; 0,98 | VR 1,717 ± 0,14 | 4 000 |
| **B2** | **środek przedziału z 020 (komórka główna)** | z kalibracji | z kalibracji | *s*\*, *D*\* | 0,08; 0,98 | VR 2,264 ± 0,14 | 4 000 |
| **B3** | góra przedziału z 020 (ρ̂ + 2 SE) | z kalibracji | z kalibracji | *s*\*, *D*\* | 0,08; 0,98 | VR 2,811 ± 0,14 | 4 000 |

Odsetek dopasowań przy granicy w B1–B3 jest wspólny (jedno *s*\*, *D*\*) i musi leżeć w oknie [41,3; 61,3] %. A0, B1, B2, B3 współtworzą werdykt
rundy; komórka główna to B2. Specjalnie nie ma tu komórek rozbijających winę na „trwałość” i „wspólny szok” (A3, A4 z 019): rozbicie daje kolumna
wyroczni (niżej) i porównanie B-komórek z A0.

### Kalibracja (pilotaże formalne, ziarno `SeedSequence(20_262_101)`, rozłączne z rejestrowym)

Pilotaż drukuje **wyłącznie** VR, ρ̂, odsetek dopasowań przy granicy, odsetek niezbieżnych, średnią persystencję i średnie ν̂ oraz opisowy rozrzut
zmienności (stosunek 90. do 10. percentyla 60-dniowego odchylenia standardowego monety 0, średnio po panelach — „rozsądek skali”, bez progu).
Test jednostkowy pilnuje, że funkcja pilotażowa nie liczy żadnych statystyk testu zbiorczego ani odsetka trafień.

**Okno celu odsetka przy granicy: [41,3; 61,3] % (cel środka 51,3 %).** To **jest** poluzowanie względem 019 ([46,3; 56,3] %) i jest ono
**po fakcie**: powód to wniosek z przeglądu 019 (pkt 4): SD pojedynczego panelu ≈ 26 pp, więc 51,3 % z jednego prawdziwego panelu nie wyznacza
średniej z dokładnością ± 5 pp. Konsekwencja, której nie ukrywam: najlepszy punkt 019 (44,5 %) wpadłby w nowe okno. Dlatego (a) cel kalibracji to wciąż
środek 51,3 %, nie dolna krawędź; (b) raportuję osobno, czy odsetek mieści się w starym oknie [46,3; 56,3] %; (c) jeśli B2 przejdzie tylko dzięki dolnej
części nowego okna [41,3; 46,3) %, wniosek brzmi „poziom wariancji nic nie dodał do tego, co sięgał LV2c” (tabela konsekwencji).

- **Krok 1 (amplituda *s*\*, *D*\*).** *D* = 300. Siatka *s* ∈ {0; 0,25; 0,5; 0,75; 1,0; 1,25; 1,5}, `rho = 0,8`, `rho_szok = 0,5`, α = 0,08, α + β = 0,98,
  **1 000 paneli** na punkt. Wygładzenie: maksimum narastające po siatce. Gdy wygładzone maksimum < 41,3 % → powtórka kroku 1 z *D* = 150
  (świeże ziarna, ta sama siatka); gdy też < 41,3 % → **STOP 1**. *s*\*: (i) jeśli wygładzony odsetek przekracza 51,3 %, rozwiązanie interpolacji
  liniowej na pierwszym przejściu (cel poniżej wartości na początku siatki → początek siatki); (ii) w przeciwnym razie (płaskowyż albo wzrost,
  który nie sięga środka) **dolna mediana** punktów siatki, których surowy odsetek ≥ 41,3 % i ≥ (maksimum surowe − 2 SE) — środek płaskowyża, nie
  zwycięzca (przekleństwo zwycięzcy z przeglądu 019). *s*\* zaokrąglam do 3 miejsc.
- **Potwierdzenie amplitudy.** **1 000 nowych paneli** (świeże ziarna) przy (*s*\*, *D*\*): przyjęte, gdy odsetek przy granicy ∈ [41,3; 61,3] %
  **i** niezbieżne ≤ 2 %. Gdy nie: korekta *s* metodą siecznej na punkcie potwierdzenia i najbliższym punkcie siatki po stronie celu, ze strażą znaku
  nachylenia (nachylenie ≤ 0 albo brak sąsiada → środek między *s*\* a następnym punktem siatki w kierunku celu); najwyżej 2 korekty, potem **STOP 2**.
- **Krok 2 (VR, przy zamrożonych *s*\*, *D*\*).** Trzy ścieżki liczone zawsze, po **500 paneli** na punkt:
  ścieżka **S**: `rho = 0,8`, `rho_szok` ∈ {0; 0,25; 0,5; 0,75; 1,0}; ścieżka **R↑**: `rho_szok = 1,0`, `rho` ∈ {0,80; 0,85; 0,90; 0,95};
  ścieżka **R↓**: `rho_szok = 0`, `rho` ∈ {0,20; 0,35; 0,50; 0,65; 0,80}. Średnie VR wygładzone maksimum narastającym wzdłuż `rho_szok` albo `rho`.
  Cel *T* komórki: *T* < VR(S, 0) → ścieżka R↓; VR(S, 0) ≤ *T* ≤ VR(S, 1) → S; *T* > VR(S, 1) → R↑. Parametr = rozwiązanie interpolacji liniowej,
  zaokrąglone do 3 miejsc. Cel poza zakresem ścieżki (np. *T* poniżej VR przy `rho = 0,20`) → komórka „niedostępna” (to wynik: poziom wariancji sam
  daje VR wyższe od celu), nie STOP.
- **Potwierdzenie VR komórki.** **1 000 nowych paneli**: przyjęte, gdy |średnie VR − *T*| ≤ **0,14** i niezbieżne ≤ 2 %. Gdy nie: korekta sieczna wzdłuż tej
  samej ścieżki (ze strażą znaku), najwyżej 2 korekty, potem komórka „niedostępna” (STOP 2 dla B2). Odsetek przy granicy **nie jest tu bramką** (jest
  ustalony w kroku 1, a jego rozkład nie zależy od `rho`, `rho_szok`); zostaje bramką KAL w przebiegu rejestrowym, więc korekty nie są marnowane.
- Wyniki kalibracji i wartości parametrów dopisuję **dodatkiem do pre-rejestracji w osobnym commicie przed przebiegiem rejestrowym**.

**Kontrole generatora i kalibracji (R8), na ziarnach pilotażowych:**

- **Ujemna (K-gen-N):** `rho = 0`, `rho_szok = 0`, *s* = 0, α + β = 0,98 (LV2 bez wspólnego czynnika), **400 paneli**: średnie ρ̂ ∈ [−0,02; 0,02]
  (VR ≈ 1). Zawiedzenie = generator albo miara zepsute, Revision.
- **Parytet (K-gen-P):** testy jednostkowe: *s* = 0 daje bit w bit panel LV2c; wartości VR runnera zgodne z `modele.pomiar_rho_h.vr_rho` na tych samych
  trafieniach; `pilot_panel` przypięty do niezależnego obliczenia.
- **Dodatnia (K-gen-D):** średnie VR komórki A0 w przebiegu rejestrowym ∈ 1,846 ± 0,09 (LV2 C2, ρ̂ 0,282 × 3 + 1). Zawiedzenie = silnik niewiarygodny, Revision.
- **Opisowa (N2):** `rho = 0`, `rho_szok = 0`, (*s*\*, *D*\*), 500 paneli: ile VR wytwarza **sam** poziom wariancji (bez zależności `rho`, `rho_szok`).
  Bez progu; ma powiedzieć, czy poziom wariancji sam tłumaczy VR z 020.
- **Punkt zerowy siatki** (*s* = 0) odtwarza A0: odsetek przy granicy rzędu LV2 (K7d: 2,2 % przy K = 15). Gdyby był > 10 %, generator albo miara są zepsute (Revision).

### Reguła K (bez zmian względem LV2) i kontrole

Test zbiorczy z `symulacje.moc_var_es` (A: poziom trafień, B: niezależność w czasie, C: ES; Bonferroni α/3 = 1,667 %; bootstrap-t po dniach, B = 999).
Wszystko na p = 5 % i komórce 4 × 1 691. Wartości wierszy i werdykt komórki liczą zamrożone `_wiersz` i `_werdykt` z `run_lv2`.

| kod | rola | co | wymaganie | bramkuje |
|---|---|---|---|---|
| K1 | kontrola negatywna (R8) | rozmiar testu na `wyr_t5` (σ wyroczni **z poziomem L**, ogon t5) | ∈ [2,5; 7,5] % | każdy wniosek |
| K2 | kontrola pozytywna (R8) | moc wobec `zan30` (σ wyroczni − 30 %) | ≥ 95 % | każdy wniosek |
| K7c | estymator | odsetek dopasowań bez zbieżności | ≤ 2 % | każdy wniosek |
| K7a | estymator | średnia ν̂ (prawda 5) | ∈ [4,0; 6,5] | **tylko w A0**; w B opis (przy przesunięciach poziomu „prawdziwe” ν dopasowania nie jest 5; 020: ν̂ 4,14) |
| K7b, K7d | estymator | średnia α̂ + β̂ ∈ [0,95; 0,995]; odsetek przy granicy ≤ 5 % | **tylko w A0**; w B zastępuje je KAL |
| KAL | zgodność kalibracji | w B1–B3: VR komórki ∈ *T* ± 0,14; odsetek przy granicy ∈ [41,3; 61,3] % | każdy wniosek w tej komórce |
| **K-a** | kryterium | rozmiar na `garch_tnu` | ≤ **10 %** | — |
| **K-b** | kryterium | moc na `garch_tnu_zan10` (σ̂ × 0,90) | ≥ **80 %** | — |

**Uwaga o K-a w komórkach B.** W B prognoza `garch_tnu` jest *błędnie wyspecyfikowana* względem procesu z poziomem L, więc K-a mierzy nie „rozmiar
testu pod prawdziwą H0”, lecz jak często test odrzuca GARCH-t, który poziomu nie widzi. To nadal poprawne pytanie dla reguły K na prawdziwych danych,
ale czystą miarą samego testu są kolumny wyroczni (K1 dla rozmiaru, `zan10`/`zan20` dla mocy). Dlatego **opis (nie kryterium)** obejmuje:
moc wyroczni wobec σ × 0,90 (`zan10`) i σ × 0,80 (`zan20`) oraz krzywą mocy `garch_tnu` przy mnożniku σ̂ ∈ {1; 0,95; 0,90; 0,85; 0,80; 0,70}
(zamrożone `krzywa_mocy` z `run_lv2c`), MDE(80 %) zamrożoną `mde`, VR, ρ̂, odsetek trafień `garch_tnu`, odsetek przy granicy, persystencję i ν̂.
Werdykt komórki: zamrożony `_werdykt` (TAK ⇔ wszystkie kryteria i kontrole; NIE ⇔ kryterium niespełnione przy kontrolach w porządku; w przeciwnym
razie WSTRZYMANE). Raport (R14) jest neutralnym reporterem: werdykt podpisuje Claude w sekcji „Wynik”.

### Ziarna

Pilotaż: `SeedSequence(20_262_101)` (kroki po `spawn_key`). Rejestr: `SeedSequence(20_262_021, spawn_key=(i,))` dla komórek A0, B1, B2, B3.
Próby dymne: `SeedSequence(20_269_999)`. Druga droga: 27 182 818. Wszystkie rozłączne z użytymi dotąd: 20_261_016 (LV2), 20_261_019, 20_261_091,
31_415_926, 9001+ (rozpoznanie 019), 9_999_021 (pomiar czasu). Test jednostkowy sprawdza rozłączność faktycznie wyliczonych ziaren paneli.

### Przewidywania (zapisane przed jakimkolwiek odczytem LV2d)

Zgadywanie do sprawdzenia, nie cel; rząd wielkości z LV2 i wyniku 019, nie z pomiaru LV2d.

| wielkość | przewidywanie | pewność |
|---|---|---|
| kalibracja odsetka możliwa (nie STOP 1) | tak: *D* = 300 (75 %), dopiero *D* = 150 (10 %), STOP 1 (15 %) | 85 % że istnieje |
| *s*\* (gdy istnieje) | 0,5–1,25 (mediana ok. 0,9) | 60 % |
| odsetek przy granicy w ogóle sięga 51,3 % | tak | 60 % |
| B2 przechodzi potwierdzenie VR (nie STOP 2) | tak | 85 % |
| B1 osiągalna (poziom sam nie daje VR > 1,717) | tak | 65 % |
| B3 wymaga ścieżki R↑ (`rho` > 0,8) | tak | 55 % |
| N2: sam poziom wytwarza VR | 1,3–1,9 (nie całe 2,26) | 60 % |
| K-gen-N, K-gen-D | zaliczone | 95 % / 90 % |
| K1 w A0, B1, B2, B3 | zaliczone (∈ [2,5; 7,5] %) | 80 % wszystkie cztery |
| K2 (zan30) w A0, B1, B2, B3 | zaliczone (≥ 95 %) | 75 % wszystkie cztery |
| K7c (niezbieżne ≤ 2 %) w B | zaliczone | 85 % |
| K-a w A0 / B1 / B2 / B3 | 5–8 % / 7–14 % / 8–16 % / 9–18 % | P(K-a ≤ 10 % w B2) = 40 % |
| **K-b w A0 / B1 / B2 / B3** | **ok. 58 % (40–75) / ok. 55 % (35–72) / ok. 50 % (30–68) / ok. 45 % (25–62)** | **P(K-b ≥ 80 % w B2) = 7 %** |
| moc wyroczni `zan10` w B2 | ok. 52 % (35–68) | P(≥ 80 %) = 5 % |
| werdykt A0 | **NIE** | 70 %; TAK 10 %; WSTRZYMANE 20 % |
| werdykt B2 | **NIE** 62 %; WSTRZYMANE 25 %; TAK 5 %; niedostępna 8 % | — |
| konsekwencja | reguła K niemierzalna przy K = 4 już w A0 (moc zbyt mała na zaniżenie σ o 10 %) | 70 % |

TAK w B2 byłoby **zaskoczeniem** (ok. 5 %) i kazałoby sprawdzić, czy zależność nie jest za słaba w laboratorium (K-gen-D, KAL-VR, N2).

### Co wynika z którego wyniku (zapisane z góry)

Werdykty komórek: T0 (A0), T1, T2, T3 (B1, B2, B3). „Moc wyroczni” = `zan10`.

| wynik | praktyczna konsekwencja |
|---|---|
| T0 = NIE (K-b < 80 % przy kontrolach w porządku) | **NIEMIERZALNA przy K = 4 już w najłagodniejszej zależności** (R3: runda VaR/ES na danych nie startuje w tej postaci). Realniejsze komórki mają więcej zależności i nie mogą być łatwiejsze, więc B tylko opisuje, jak daleko od progu. Opcje dla użytkownika: (a) reguła K′ (inne kryterium, np. MDE ≤ 0,20, albo test na wielu dniach z osobną pre-rejestracją), (b) zamknięcie rundy VaR/ES na danych, (c) szerszy koszyk — wymaga **zmiany decyzji użytkownika** o czterech monetach, więc tylko za jego zgodą. |
| T0 = TAK, T1 = T2 = T3 = TAK | **Reguła K mierzalna przy K = 4 w całym przedziale z 020, także przy przesunięciach poziomu.** 018 może być zlecona po danych za październik 2026 i powtórce 020 (kryterium niżej). |
| T0 = TAK, T2 = TAK; T3 ≠ TAK | **Caveats:** mierzalna w środku, nie w górze przedziału; 018 tylko, gdy powtórka 020 da ρ̂ ≤ ρ̂ środka + 1 SE (ustali pre-rejestracja 018); decyzja użytkownika. |
| T2 = NIE, moc wyroczni ≥ 80 %, K-b (GARCH) < 80 % | test sam ma moc, traci ją **estymator** (GARCH-t nie widzi poziomu): opcja (d) prognoza z uwzględnieniem poziomu to osobna runda (nowy model, własny licznik), nie ta; reguła K′ jak wyżej. |
| T2 = NIE, K-a > 10 %, K-b ≥ 80 % | reguła K ma moc, ale **odrzuciłaby poprawny model klasy GARCH-t** przy przesunięciach poziomu (fałszywe alarmy); K nie nadaje się jako bramka dla GARCH-t bez korekty poziomu; opcje jak wyżej. |
| T2 = NIE, moc wyroczni < 80 % | **strukturalnie** za mało niezależnych monet (cztery monety niosą ok. 1,8 niezależnej dziennie); żaden estymator tego nie naprawi; opcje (a)–(c) z pierwszego wiersza. |
| T1/T2/T3 = WSTRZYMANE | brak wniosku dla komórki; naprawa kontroli (Revision). Jeśli niezaliczoną kontrolą jest tylko K2 (moc wobec zan30 < 95 %), praktycznie to samo co NIE (test głuchy przy K = 4), formalnie WSTRZYMANE. |
| B2 „niedostępna” (STOP 1 albo 2) | pytanie dla warunków z danych **bez odpowiedzi**; stoi tylko wynik A0 (T0 = NIE → wiersz pierwszy; T0 = TAK → wracam do użytkownika z opcjami, 018 nadal wstrzymana). Mechanizm przesunięć poziomu uznany za niewystarczający. |
| B2 przechodzi tylko dzięki odsetkowi w [41,3; 46,3) % | poziom wariancji **nic nie dodał** do tego, co sięgał LV2c (44,5 %); komórki B liczą się jako scenariusze zależności, nie jako „wyjaśnienie” granicy; wniosek o regule K niezmieniony. |
| T0 = NIE, T2 = TAK (lub odwrotnie w tym sensie, że B łatwiejsze od A0) | wynik nietypowy; opisać i nie wyciągać wniosku bez sprawdzenia kalibracji (KAL, K-gen-D, N2). |
| N2: sam poziom daje VR ≥ 2,26 | przedział 020 mógł powstać bez zależności `rho`, `rho_szok`; wtedy VR miesza zależność z poziomem i trzeba to napisać w wniosku (opis, bez wpływu na werdykty). |

### Propozycja kryterium zgodności dla powtórki 020 (karta 018; ostateczne zapisze pre-rejestracja 018)

Jak w 019, z B3 w miejsce A2: powtórka 020 na danych do 2026-10-31 jest zgodna z laboratorium, gdy ρ̂ powtórki ≤ ρ̂ komórki B3 (≈ 0,60, o ile B3 wyszła TAK)
**oraz** odsetek dopasowań przy granicy ∈ [41; 61] %. Jeśli B3 nie wyszła TAK, kryterium dotyczy najwyższej komórki z werdyktem TAK.

### Czego NIE robię

- Nie uruchamiam karty 018 ani nie liczę odsetka trafień na prawdziwych danych; nie badam prawdziwych szeregów (stabilność σ̄ w oknach to osobny, opisowy
  odczyt danych, poza tą rundą).
- Nie zmieniam plików zamrożonych, progów 10 % i 80 %, poziomu p, estymatora ani granicy persystencji 0,9999.
- Nie stroję generatora na odrzuceniach testu zbiorczego (kalibracja wyłącznie na VR i odsetku przy granicy); nie dobieram ziaren.
- Nie dotykam alpha, nie wkładam `data/` do gita, nie scalam do `main`.

### Decyzje projektowe podjęte na delegację (2026-10-08; zapis także w `STATUS.md`)

1. **Baza poziomu wariancji = LV2 (α + β = 0,98), nie trwałość 0,9999 z 019.** Powód: przegląd 019 (pkt 5) — przy 0,9999 panel jest „zapadniętym IGARCH”
   (mediana |r| ≈ 0,12 % przy `daily_vol` 4 %); poziom L ma dać granicę mechanizmem, nie parametrem. Ścieżka odwrotu: komórki B z α + β = 0,9999 jak w 019.
2. **Okno celu [41,3; 61,3] %** zamiast [46,3; 56,3] % (po fakcie, powód i konsekwencja wyżej); środek celu zostaje 51,3 %. Ścieżka odwrotu: stare okno i próg
   STOP 1 = 46,3 % (wtedy STOP 1 jest znacznie bardziej prawdopodobny).
3. **Trzy komórki B (dół, środek, góra przedziału z 020) i komórka A0**; B2 główna. Ścieżka odwrotu: werdykt tylko z B2 i A0.
4. **K7a bramkuje tylko w A0** (w B opis), bo przy przesunięciach poziomu „prawdziwe” ν dopasowania nie jest 5, a 020 pokazuje ν̂ 4,14. Ścieżka odwrotu: bramka
   [4,0; 6,5] także w B (grozi WSTRZYMANE z powodu ν̂, nie z powodu testu).
5. ***D* = 300 dni (ok. 7 reżimów na 2 091 dni) z zapasowym *D* = 150**; bez prawdziwych szeregów to dobór rzędu wielkości (hossa 2021, krach 2022,
   cisza 2023), nie pomiar. Ścieżka odwrotu: inne *D* wyłącznie w nowej pre-rejestracji.
6. **Kolumny wyroczni (`zan10`, `zan20`) jako opis** oddzielają moc samego testu od jakości estymatora; bez wpływu na werdykt komórki.
7. **1 000 paneli na punkt kalibracji** (019: 400), bo koszt jest niski, a SD pojedynczego panelu ≈ 26 pp; poprawki z przeglądu 019 (NaN → STOP, straż znaku
   siecznej, `potwierdz` bez marnowania korekt, cel poniżej początku siatki, BLAS przy `workers ≤ 1`, K-gen-N na 400 panelach, testy trybów `main`) idą do
   nowego runnera `symulacje/run_lv2d.py` z testami.

---

## Dodatek 1 do pre-rejestracji (2026-10-08): wynik kalibracji i doprecyzowania — zapisany PRZED przebiegiem rejestrowym

Treść powyżej zostaje bez zmian. Poniżej tylko to, co wyszło z pilotaży na ziarnie 20_262_101 (które drukują wyłącznie VR, ρ̂, odsetek przy granicy,
niezbieżne, persystencję, ν̂ i rozrzut skali), oraz opis kilku miejsc, w których pre-rejestracja zostawiła szczegół do rozstrzygnięcia w kodzie.
Przebieg rejestrowy (ziarno 20_262_021) **jeszcze się nie odbył**; nie widziałem żadnej statystyki testu zbiorczego z LV2d.

### Artefakty (sumy SHA-256)

| plik | SHA-256 |
|---|---|
| `kalibracja.json` | `cced579c8c56fa02e41a9d9c48e46852d3f1e7cfd1e912bcc15749bed8571d24` |
| `raw_kalibracja.txt` | `17372094067da4051e9c734637346ae28b7c1f06efd76680049fb480a5fcf455` |
| `raw_kontrola_n.txt` | `630a98cb6e96e29d09537d69b21fd91522459bbe73c6a1c73fc489bea78c6042` |

Runner: commit `93c6d43` (`symulacje/run_lv2d.py`, 72 testów; pełny zestaw 1 342 testów zielony). Kalibracja trwała 2 218 s na 28 procesach.

### Wynik kalibracji (nie było STOP 1 ani STOP 2)

| element | wynik |
|---|---|
| K-gen-N (ujemna, 400 paneli) | **zaliczona**: ρ̂ = +0,0021 ± 0,0010 (wymagany przedział ±0,02), VR 1,006 |
| punkt zerowy siatki (*s* = 0) | odsetek przy granicy 2,3 % ± 0,2 pp (próg zepsucia 10 %) |
| krok 1, *D* = 300 | odsetek przy granicy rośnie monotonicznie: 2,3 / 3,5 / 13,3 / 29,8 / 46,9 / 59,8 / 67,9 % dla *s* = 0 … 1,5; *D* = 150 nie był potrzebny |
| ***s*\*** | **1,086** (interpolacja do środka celu 51,3 %; wygładzone maksimum 67,9 % przekraczało środek, więc gałąź „płaskowyż” się nie uruchomiła) |
| potwierdzenie amplitudy (1 000 nowych paneli) | przy granicy **52,5 % ± 1,1 pp**, niezbieżne 0,00 % → przyjęte w rundzie 0, bez korekt; mieści się też w **starym** oknie [46,3; 56,3] % |
| N2 (ρ = 0, ρ_szok = 0, *s*\*, *D* = 300; 500 paneli) | **VR 1,052 ± 0,005** (ρ̂ 0,017): sam poziom wariancji prawie nie wytwarza VR |
| ścieżka S (`rho = 0,8`) | VR 1,928 / 2,097 / 2,261 / 2,450 / 2,698 dla `rho_szok` = 0 … 1 |
| ścieżka R↑ (`rho_szok = 1`) | VR 2,698 / 2,901 / 3,113 / 3,399 dla `rho` = 0,80 … 0,95 |
| ścieżka R↓ (`rho_szok = 0`) | VR 1,185 / 1,307 / 1,486 / 1,689 / 1,949 dla `rho` = 0,20 … 0,80 |

Komórki po potwierdzeniu VR na 1 000 świeżych paneli (wszystkie przyjęte w rundzie 0, niezbieżne 0,00 %):

| komórka | ścieżka | parametry | VR potwierdzenia (cel ± 0,14) | odsetek przy granicy |
|---|---|---|---|---|
| A0 | brak kalibracji | `rho` 0,8, `rho_szok` 0, *s* = 0 | — (K-gen-D w przebiegu rejestrowym) | — |
| B1 | R↓ | `rho` **0,666**, `rho_szok` 0, *s* = 1,086, *D* = 300 | 1,712 ± 0,007 (cel 1,717) | 50,7 % ± 1,0 pp |
| B2 | S | `rho` 0,8, `rho_szok` **0,504**, *s* = 1,086, *D* = 300 | 2,266 ± 0,009 (cel 2,264) | 51,5 % ± 1,1 pp |
| B3 | R↑ | `rho` **0,828**, `rho_szok` 1,0, *s* = 1,086, *D* = 300 | 2,788 ± 0,011 (cel 2,811) | 54,0 % ± 1,1 pp |

Wszystkie parametry mają α = 0,08, α + β = 0,98, `persystencja = None`. Dopasowana persystencja w pilotażach to 0,991 (dopasowanie widzi trwałość poziomu
jako trwałość GARCH), ν̂ ≈ 4,95–5,0.

### Które przewidywania z tabeli (zapisanej wcześniej) kalibracja już rozstrzygnęła

Tabeli nie edytuję; to rozliczenie, nie poprawka.

| przewidywanie | wynik kalibracji |
|---|---|
| kalibracja odsetka możliwa, *D* = 300 (75 %) | trafione |
| *s*\* ∈ 0,5–1,25 (mediana 0,9) | trafione co do przedziału (1,086); wyżej niż mediana |
| odsetek w ogóle sięga 51,3 % (60 %) | trafione |
| B2 przechodzi potwierdzenie VR (85 %) | trafione |
| B1 osiągalna (65 %) | trafione, ale tylko dlatego, że ścieżka R↓ pozwala zejść do `rho` = 0,666; sam poziom przy `rho` = 0,8 daje już VR 1,93 > 1,717 |
| B3 wymaga R↑ (55 %) | trafione (`rho` = 0,828, bo na ścieżce S VR kończy się na 2,698 < 2,811) |
| **N2: sam poziom daje VR 1,3–1,9 (60 %)** | **chybione**: 1,052. Poziom wariancji prawie niczego nie dokłada do VR; cały VR z 020 niosą `rho` i `rho_szok`, a poziom niesie odsetek przy granicy. Zgodnie z wierszem „N2” tabeli konsekwencji: VR z 020 nie powstał bez zależności między monetami. |
| K-gen-N zaliczona (95 %) | trafione |

### Doprecyzowania w kodzie (pre-rejestracja zostawiła szczegół otwarty)

Żadne z nich nie zmienia progu, p, estymatora ani reguły K. Pierwsze sześć jest zapisane w `symulacje/run_lv2d.py` i przypięte testami; w tej kalibracji
**żadne z (a)–(d), (g) nie zostało uruchomione** (wszystko przeszło w rundzie 0 i interpolacja dała *s*\*), więc na wynik nie wpłynęły; wiążą dopiero
ewentualną powtórkę.

- **(a)** SE w progu płaskowyżu (maksimum surowe − 2 SE) = SE punktu, w którym surowy odsetek ma maksimum.
- **(b)** „Cel poza zakresem ścieżki”: komórka pozostaje dostępna, gdy cel leży w odległości ≤ 0,14 (tolerancja VR) od zakresu ścieżki; decyduje potwierdzenie.
  Wybór ścieżki (R↓ / S / R↑) jest bez tolerancji, wprost z reguły *T* < VR(S, 0) / ≤ VR(S, 1) / > VR(S, 1).
- **(c)** Gdy VR mieści się w tolerancji, ale niezbieżne > 2 %: korekty sieczne nie ruszają (nie ma czego korygować po VR); komórka „niedostępna”.
- **(d)** Sieczna: punkt siatki po stronie celu o wygładzonym VR najbliższym celowi i z właściwym znakiem nachylenia; w przeciwnym razie środek do najbliższego
  punktu siatki po tej stronie; wynik obcięty do zakresu siatki; brak punktu po stronie celu → brak korekty.
- **(e)** Straż punktu zerowego (*s* = 0, odsetek przy granicy > 10 % → błąd, nie wynik) jest bramką kalibracji; przeszła (2,3 %).
- **(g)** Nieudane potwierdzenie amplitudy (STOP 2) kończy kalibrację bez próby z *D* = 150 (zgodnie z „STOP 2 jak STOP 1” w R4).
- **(f)** Druga droga (opis, nie bramka): `druga_droga.py` w katalogu rundy liczy VR, ρ̂, odsetek przy granicy i niezbieżne dla A0, B1, B2, B3 na 100 świeżych
  panelach (ziarno 27_182_818, `spawn_key = (indeks komórki,)`) **bez** `run_lv2d`, `prognoza_garch_tnu`, `filtr_sigma2`, `vr_rho` i `var_es_t` — wprost z
  `dopasuj_garch_t`, własnej rekurencji σ² w pętli i `scipy.stats.t`. Opiera się na tym samym generatorze (jego własności mają osobne testy).

### Sprawdzenie anomalii w wydruku

Ścieżka S przy `rho_szok` = 1 i ścieżka R↑ przy `rho` = 0,80 to te same parametry, a wydruk pokazuje identyczne VR 2,698 i ρ̂ 0,5660. Sprawdziłem: ziarna
paneli obu punktów są **rozłączne** (0 wspólnych z 500), a odsetek przy granicy, ν̂ i persystencja różnią się (55,1 vs 54,3 %; 5,01 vs 4,97; 0,9914 vs 0,9909).
To przypadkowa zbieżność (rzędu 1–2 % szansy), nie ten sam panel; nie wpływa na dobór parametrów.

### Przebieg rejestrowy (następny krok)

```
PYTHONPATH=. python -m symulacje.run_lv2d rejestr --workers 28 \
    --kalibracja runs/2026-10-08_021-lv2d-regimy-wariancji/kalibracja.json --zapisz data/lv2d_wyniki_paneli.npz
```

Jeden przebieg, A0 + B1 + B2 + B3 po 4 000 paneli, ziarno 20_262_021. Powtórka jest dozwolona wyłącznie po **awarii technicznej** (przerwany proces, brak
miejsca), na tych samych ziarnach i z jawnym zapisem w README; powtórka z powodu wyniku jest niedozwolona. Niezależna druga droga na 100 panelach (powyżej)
idzie po przebiegu rejestrowym, żeby nie wpływać na jego konfigurację.
