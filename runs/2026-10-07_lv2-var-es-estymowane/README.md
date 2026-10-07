# LV2 — laboratorium VaR/ES dla prognoz ESTYMOWANYCH: czy test zbiorczy i test porównawczy nadają się na pierwszą rundę na danych (2026-10-07)

> **STATUS: PRE-REJESTRACJA — przebieg rejestrowy jeszcze nie wykonany.** Zapisana 2026-10-07 przed
> pełnym przebiegiem (ziarno `20261016`, 5 000 paneli). Progi i reguły poniżej nie zmieniają się po
> obejrzeniu wyniku. Ewentualne zmiany po przeglądzie (krok 2 planu z karty 016) trafią do sekcji
> „Zmiany po przeglądzie, przed pełnym przebiegiem” razem z uzasadnieniem. Sekcje Wynik / Co na plus i
> na minus / Werdykt / Wniosek zostaną dopisane po przebiegu.

## W skrócie — prostym językiem

LV1 pokazała, że test zbiorczy (liczenie po dniach, nie po monetach) wykrywa prognozę ryzyka zaniżoną o
ok. 8 %. Ale tylko dla prognozy-**wyroczni**, czyli takiej, w której znamy prawdziwą zmienność. Prawdziwa
prognoza musi zmienność oszacować z danych. I wtedy LV1 zobaczyła coś niepokojącego: nawet rozsądne,
codziennie liczone prognozy (okno 60 dni, EWMA) test zbiorczy odrzucał w 78–98 % sztucznych paneli,
choć ogon był dobry. Prawdopodobna przyczyna (hipoteza z LV1): sam błąd szacowania zmienności daje za
dużo przekroczeń VaR.

Zanim jakakolwiek runda VaR/ES dotknie prawdziwych danych, LV2 odpowiada — na sztucznych cenach, w
których prawdę znamy — na trzy pytania:

- **(a)** Czy test zbiorczy jest **uczciwy dla modelu poprawnego, ale oszacowanego z danych** (GARCH-t
  dopasowywany od nowa co 30 dni na danych, które naprawdę pochodzą z GARCH-t)? Jeśli taki model odrzuca
  częściej niż w ok. 10 % przypadków, to „odrzucono” na prawdziwych danych niczego nie znaczy.
- **(b)** Czy test **porównawczy** (miara straty FZ0 i test Diebolda–Mariano na dziennych średnich po
  monetach) odróżni od siebie dwie prognozy estymowane przy ok. 1 600 dniach i 20 monetach? To inne
  pytanie niż „czy prognoza jest dobra”: „czy ta jest lepsza od tamtej”.
- **(c)** Reguła: które z tych pytań (jeśli którekolwiek) wolno zadać w pierwszej rundzie na danych.

Dwa pytania mają dwie osobne reguły: **K** (bezwzględne, z (a)) i **P** (porównawcze, z (b)). Runda jest
MIERZALNA, gdy choć jedna z nich da TAK. Każda reguła ma kontrole samego laboratorium (rozmiar na prawdziwej
prognozie, moc wobec zaniżenia o 30 %, wiarygodność estymatora GARCH i błędu standardowego testu DM). Gdy
kontrola zawiedzie, wynik to WSTRZYMANE — to błąd laboratorium, nie wniosek o danych.

Uczciwie o oczekiwaniu: przed zapisem tej pre-rejestracji obejrzeliśmy pilotaż 480 paneli (poza rejestrem,
inne ziarno). Wygląda na to, że **K da TAK** (z małym zapasem przy 1 %), a **P da NIE** (test porównawczy
za słaby, by przy 1 600 dniach odróżnić EWMA od GARCH-t). Przewidywania W1–W4 zapisano po tym pilotażu, więc
**nie są ślepe**. Dokładna oś czasu — w sekcji „Co sprawdzono PRZED zapisem kryteriów”.

## Metadane

- **Pre-rejestracja zamrożona w commicie:** `HASH_PRE_REJESTRACJI` (README, kod i testy; pełny przebieg
  idzie z tego stanu kodu; hash wpisany w następnym commicie, bez zmian kodu ani progów).
- Zadanie 016 (`zadania/016-laboratorium-lv2-var-es-estymowane.md`), kontynuacja LV1 (zadanie 009).
  Runda kalibracyjna, nie hipoteza rynkowa: **R1 — brak mechanizmu rynkowego** (nic nie przewidujemy,
  mierzymy własności przyrządu przy naszych n i dla prognoz estymowanych).
- Kod (commit `009204b`): `symulacje/run_lv2.py` (przebieg, reguły K i P, wydruk), `symulacje/prognozy_lv2.py`
  (19 prognoz estymowanych na jednym panelu), `symulacje/garch_t.py` (własny estymator GARCH(1,1)-t
  metodą największej wiarygodności, sprawdzony niezależnie pakietem `arch` 8.0.0), `symulacje/porownanie_lv2.py`
  (strata FZ0, strata kwantylowa, wzory zamknięte na oczekiwane straty, test DM), testy `tests/test_lv2.py`
  (88 testów, 159 przypadków). **Nie zmieniane:** zamrożony `miara/var_es.py` (po KV1), `miara/dm.py`
  (HAC), `symulacje/moc_var_es.py` (test zbiorczy LV1: A lub B lub C, Bonferroni, bootstrap-t po dniach),
  `symulacje/garch_panel.py` (generator).
- Komenda: `python -m symulacje.run_lv2 --workers 16 > runs/2026-10-07_lv2-var-es-estymowane/raw_output.txt`.
  `--smoke` sprawdza tylko, że kod działa (4 panele po 700 dni, 8 monet); `--panele` i `--ziarno` dają
  pilotaż z nagłówkiem „PILOTAŻ — NIE JEST PRZEBIEGIEM REJESTROWYM”. Na stdout idą tylko liczby
  odtwarzalne; czas i postęp idą na stderr.
- Dane: WYŁĄCZNIE syntetyczne (`symulacje.garch_panel.generuj_panel`: GARCH(1,1) α 0,08, β 0,90, szok
  dzienny t z ν = 5, zmienność bezwarunkowa 4 %/dzień, czynnik rynkowy ρ = 0,8). Nie czytamy `data/`;
  R16 (dane od 2021) nie dotyczy.
- Determinizm (R19): ziarno główne `20261016`; `SeedSequence.spawn` na panel, a w panelu osobno generator
  i bootstrap; kolejność wyników zachowuje `imap`, więc wynik **nie zależy od liczby procesów**
  (pilnują tego testy). Ziarna pilotaży przed zapisem kryteriów były INNE (777 dla pilotaży 16 i 480
  paneli, 810000 dla pilotażu 64 paneli, własne ziarna dla pilotaży estymatora). Ziarno rejestrowe
  użyto dotąd tylko w teście działania `--smoke` (4 panele); **w pełnej konfiguracji nikt go nie uruchomił**.
- Czas: pilotaż 480 paneli = 174 s na 16 procesach, czyli ok. 5,8 s na panel na rdzeń; 5 000 paneli ≈
  **30 min** na 16 procesach (zakres 20–60 min). Uruchamiać bez innych równoległych przebiegów.

## Pre-rejestracja (zapisana przed przebiegiem)

### Wnioski skumulowane, które dotyczą tej rundy (jedno zdanie)

LV1 (2026-10-06): realistyczne prognozy estymowane (okno 60, EWMA 0,94) przy poprawnym ogonie t5 są
odrzucane przez test zbiorczy w 78–98 % paneli, a rozmiar tego testu zmierzono tylko dla wyroczni,
natomiast F2-1b (2026-10-06, NIEPOZYTYWNY 11/15 → STOP → ryzyko ogona) i KV1 (19/19 przy bardzo dużych
n i ρ = 0) mówią, że następny krok to ryzyko ogona, ale dopiero po sprawdzeniu przyrządu na prognozie
estymowanej — stąd w LV2 H0 to model poprawny i dopasowany z danych (GARCH-t), obok pytania
bezwzględnego jest pytanie porównawcze, a komórką główną jest ta z LV1 (n = 1 600, 20 monet, ρ = 0,8).

### Pytanie i mechanizm (R1)

Nie przewidujemy rynku, tylko kalibrujemy przyrząd; „kto traci po drugiej stronie” nie dotyczy. Trzy
pytania: (a) rozmiar i moc testu zbiorczego LV1, gdy prognoza jest poprawnie określona, ale
estymowana (reguła K); (b) moc testu porównawczego FZ0 + Diebold–Mariano dla prognoz estymowanych (reguła P);
(c) która z reguł pozwala zacząć pierwszą rundę VaR/ES na danych. Mechanizm sprawdzanej hipotezy
(z LV1, tam niesprawdzanej): szum w σ̂ nie zeruje się w średniej — prognoza z zaniżonym σ̂ ma więcej
trafień, niż prognoza z zawyżonym σ̂ ich traci — więc test bezwzględny odrzuca nawet poprawny model
częściej niż nominalnie. Pytanie jest ilościowe: o ile częściej, i czy przy poprawnie określonym GARCH-t
mieści się to w progu.

### Konwencje

Zwrot dzienny r_it (moneta i, dzień t); q_it = kwantyl rzędu p (ujemny); es_it = E[r | r < q_it] (ujemny);
trafienie I_it = 1{r_it < q_it}, równość NIE jest trafieniem (zamrożony `miara/var_es.py`). Odrzucamy H0,
gdy p-wartość < 5 % (test zbiorczy: każdy ze składników A, B, C na α/3 = 1,67 %; DM: dwustronnie
|t| > 1,96, albo jednostronnie t > 1,96, gdy wskazano). Test z niezdefiniowaną statystyką (NaN) to **brak
odrzucenia**; liczymy je osobno (`niezdef`). Panel ma 2 100 dni: dni 0–399 to historia (rozgrzewka i
trening), dni 400–2099 to okres oceny (1 700 dni). **Każda prognoza dnia t używa wyłącznie zwrotów z dni
< t** (R6/R7; patrz testy poniżej). Komórki są **zagnieżdżone w jednym panelu**: C1 = pierwsze 20 monet i
pierwsze 1 600 dni oceny, C2 = pierwsze 15 monet i pierwsze 1 700 dni oceny; każda ma własne indeksy bootstrapu.

### Projekt

| element | wartość |
|---|---|
| generator | GARCH(1,1) α 0,08 β 0,90, t5, zmienność 4 %, czynnik rynkowy ρ = 0,8 (korelacja zwrotów ok. 0,62), K = 20 monet; bez zależności ogonowej i bez wspólnej zmienności |
| panel | 2 100 dni, generowany RAZ na panel; okres oceny 1 700 dni po 400 dniach historii |
| komórka główna **C1** | K = 20 monet, n = 1 600 dni oceny (jak w LV1); **tylko ona wchodzi do reguł i werdyktu** |
| komórka opisowa **C2** | K = 15 monet, n = 1 700 dni oceny (populacja F2-1b); drukowana jako OPIS tej samej reguły |
| poziomy | p ∈ {1 %, 5 %}, każdy osobno |
| panele | **5 000** (jedna wspólna seria paneli dla wszystkich prognoz, strat i komórek) |
| bootstrap testu zbiorczego | 999 replikacji po dniach (wspólne indeksy dla wszystkich prognoz i p w danym panelu i n) |
| test porównawczy | DM na dziennych średnich po monetach różnicy strat, wariancja HAC Newey–West (`miara.dm`, opóźnienie 7 przy n ≥ 1 600); bez poprawki Harveya–Leyborne'a–Newbolda |
| precyzja | SE odsetka ≤ **0,71 pp** (0,57 pp przy mocy 80 %, 0,31 pp przy 5 %) |
| okres treningu GARCH | rosnące okno od dnia 0 do początku bloku b ≥ 400; refit co 30 dni (57 bloków × 20 monet = 1 140 dopasowań na panel) |

**Dlaczego 5 000 paneli.** SE odsetka odrzuceń ma być wyraźnie mniejszy niż pasmo rozmiaru (±2,5 pp wokół
5 % to ok. 8 SE, bo SE rozmiaru wynosi 0,31 pp) i niż odstępy między progami a oczekiwanymi wartościami
(pilotaż: K-a 7,9 % przy progu 10 %, czyli ok. 5,5 SE przy 5 000 paneli; 1,7 SE samego pilotażu). Panele
komórek C1 i C2 są zależne (ten sam panel), więc porównania między komórkami są opisowe.

### Rachunek mierzalności (R3)

Laboratorium jest mierzalne, jeśli (1) jego rozdzielczość jest dużo mniejsza niż marginesy kryteriów oraz
(2) każde kryterium może zawieść (inaczej reguła nic nie rozstrzyga).

1. **Rozdzielczość.** SE ≤ 0,71 pp przy 5 000 panelach. Pasma kontroli rozmiaru (K1, K4, K6) mają ±2,5 pp
   wokół 5 % (8 SE); próg mocy 95 % (K2, K5) leży daleko od wyników pilotażu (100 %); K-a: zapas 2,1 pp
   (pilotaż) = 5,5 SE rejestrowego przebiegu; K-b: moc 99,4–99,6 % wobec progu 80 %. Rozdzielczość
   bootstrapu: B = 999 daje p-wartości na siatce 1/1 000, a próg α/3 = 1,67 % to ok. 17 przekroczeń (test
   `test_rozdzielczosc_bootstrapu_pozwala_testom_a_i_b_odrzucac_na_poziomie_alfa_przez_3`).
2. **Obalalność (kryteria mogą zawieść).** Gdyby K-a stosować do prognozy `ewma94_t5` (σ z EWMA, ogon t5),
   zawiodłoby ono z dużym zapasem: 77–86 % odrzuceń w pilotażach wobec progu 10 %. Gdyby K-b dotyczyło σ
   zaniżonego tylko o 5 %, zawiodłoby też (pilotaż 480: moc testu zbiorczego wobec wyroczni × 0,95 to
   47 % / 53 %, wobec progu 80 %). P-a i P-b w pilotażu **nie** są spełnione (patrz niżej): reguła P
   potrafi więc dać NIE, a reguła K w pilotażu daje TAK. Żadna reguła nie jest trywialnie spełniona;
   P-a i P-b nie są też niemożliwe z konstrukcji (moc DM rośnie z n i ze zbliżaniem się prognoz do
   wyroczni), tylko przy n = 1 600 pilotaż pokazuje 35 % / 76 % mocy pary głównej.
3. **Koszt:** ok. 30 min na 16 procesach.

Werdykt rachunku: **przebieg może wystartować** — rozdzielczość jest dużo mniejsza niż marginesy
kryteriów, a każde kryterium może zawieść. To rachunek dla samego laboratorium; „MIERZALNA /
NIEMIERZALNA” w regule rundy (niżej) dotyczy dopiero pierwszej rundy na prawdziwych danych.

### Prognozy (19, wszystkie F_{t−1}-mierzalne)

Prognoza = (q, es) = σ̂_t · (Q, ES), gdzie (Q, ES) to kwantyl i ES poziomu p dla standaryzowanej innowacji
o wariancji 1; ogon jest stały w bloku 30 dni i odświeżany co blok.

| nazwa | σ̂ | ogon | rola |
|---|---|---|---|
| `wyr_t5` | σ_t wyroczni (z generatora) | t5 (prawdziwy) | **kontrola negatywna K1, K4** (H0 prawdziwa); druga strona każdego porównania z wyrocznią |
| `zan05` … `zan30` | wyrocznia × (1 − x), x ∈ {0,05; 0,10; 0,15; 0,20; 0,30} | t5 | krzywa mocy, MDE; `zan30` = **kontrola pozytywna K2, K5** |
| `okno60_t5` | okno 60 dni | t5 | opis, W1, W2, para realistyczna |
| `ewma94_t5` | EWMA λ = 0,94 | t5 | opis, W1, W2, **baseline pary głównej P-b** (R17) |
| `garch_t5` | GARCH(1,1)-t, refit co 30 dni na rosnącym oknie | t5 | opis, para realistyczna |
| `garch_tnu` | jw. | t_ν̂ (ν̂ z dopasowania danego bloku i monety) | **prognoza „poprawnie określona, estymowana”: K-a, K-b (w wersji ×0,90), P-b** |
| `garch_tnu_zan10`, `garch_tnu_zan20` | `garch_tnu` × 0,90 / × 0,80 | t_ν̂ | **K-b** (zan10), opis (zan20) |
| `har_t5` | HAR-RV (`modele.zmiennosc.prognoza_har`), własny harmonogram refitów co 30 dni od dnia 395 | t5 | opis (HAR odłożony po F2-1b; tu tylko jako opis), para realistyczna |
| `okno60_ep`, `ewma94_ep`, `garch_ep` | jak wyżej | empiryczny, reszty wszystkich monet razem | opis (nie w C2, bo C2 to podpanel) |
| `okno60_ec`, `ewma94_ec`, `garch_ec` | jak wyżej | empiryczny, reszty każdej monety osobno | opis |

Reszty standaryzowane do ogonów empirycznych: dla okna i EWMA z ich własnych σ̂_s (s ∈ [60, b)), dla GARCH
z filtra przepuszczonego z parametrami bloku b przez dni < b („reszty w próbie”: parametry widziały te
same dni, ale filtr nie widzi dni ≥ b). Bez żadnego zwrotu z dnia ≥ t w prognozie dnia t:
`test_prognozy_nie_zalezą_od_przyszlosci_obciecie_panelu` oraz
`test_zaburzenie_dnia_t_nie_zmienia_prognoz_na_dni_do_t_wlacznie`.

### Test zbiorczy (bez zmian względem LV1)

Jednostką jest dzień (R12). S_t = Σ_i I_it, d_t = Σ_i (U_it − 1), U_it = r_it I_it / (p es_it). A: pokrycie
(t-test średniej S_t względem K·p, dwustronny z równymi ogonami), B: grupowanie trafień (okno 10 dni,
dwustronny z równymi ogonami), C: ogon (średnia d_t, jednostronny). Zbiorczy = A lub B lub C, każdy na
α/3 (Bonferroni), p-wartości z bootstrapu-t po dniach (B = 999). Kod: `symulacje/moc_var_es.py`
(`testy_zbiorcze`, `odrzuca_zbiorczo`), bez żadnej zmiany względem LV1.

### Straty i test porównawczy

- **FZ0** (Patton–Ziegel–Chen 2019), dolny ogon, v = VaR, e = ES (obie ujemne): S = −1/(p e) · 1{r ≤ v}
  (v − r) + v/e + log(−e) − 1. Ocenia razem VaR i ES; różnica FZ0 dwóch prognoz nie zależy od wspólnej
  skali zwrotu. Jest to strata PRAWIDŁOWA (w oczekiwaniu najmniejsza dla prawdziwych (VaR, ES)); wzory
  zamknięte na oczekiwane straty pod t_ν dla σ wyroczni są w `oczekiwana_strata`.
- **PINB:** strata kwantylowa (p − 1{r < v})(r − v) samego VaR, dzielona przez wspólną wagę σ̂ (EWMA 0,94,
  znana w t − 1, więc strata nadal prawidłowa). Tylko opis i pary zerowe (K4).
- Strata dnia = **średnia po monetach** (R12: 20 monet to nie 20 obserwacji). Δ_t = strata_A − strata_B,
  t = średnia Δ / błąd HAC; **t > 0 oznacza, że B jest lepsza** (mniejsza strata).
- **Pary „dokładnie zerowe” (rozmiar DM pod prawdziwą H0):** prognoza A = wyrocznia × c_A (c_A ∈ {0,9; 0,8}),
  prognoza B = wyrocznia × c_B, gdzie c_B > 1 jest dobrane tak, by OCZEKIWANE straty A i B były równe
  (druga gałąź paraboli straty). Wtedy H0 „równe oczekiwane straty” jest prawdziwa, choć żadna prognoza nie
  jest prawdziwa. Mnożniki (ν = 5; wyliczone brentq, sprawdzone: oczekiwane straty A i B równe do 1e-8):

  | strata, p | c_A = 0,9 → c_B | c_A = 0,8 → c_B |
  |---|---|---|
  | FZ0, 1 % | 1,126683 | 1,344627 |
  | PINB, 1 % | 1,116078 | 1,276016 |
  | FZ0, 5 % | 1,120401 | 1,302395 |
  | PINB, 5 % | 1,109835 | 1,243453 |

- **K6 (rozmiar DM po wyśrodkowaniu na parach realistycznych):** t_c = (d̄ − średnia d̄ po panelach) / błąd
  HAC. Pary realistyczne to `okno60_t5 → ewma94_t5`, `ewma94_t5 → garch_tnu`, `okno60_t5 → garch_tnu`,
  `garch_tnu → garch_t5`, `ewma94_t5 → har_t5`, `ewma94_t5 → ewma94_ep`. Pod H0 „prawdziwa średnia
  różnica = jej średnia po panelach” odsetek |t_c| > 1,96 powinien wynosić ok. 5 %, jeśli błąd HAC jest
  wiarygodny. To kontrola błędu standardowego (opóźnienia HAC), nie rozmiar absolutny.

### Kryteria

Wszystkie liczone na **komórce głównej C1 (K = 20, n = 1 600, ρ = 0,8), osobno dla p = 1 % i p = 5 %**.
Kody są w kodzie (`ocen_k`, `ocen_p`) i w wydruku.

**Reguła K — pytanie bezwzględne (test zbiorczy LV1 na prognozie estymowanej).**

| kod | rola | co | wymaganie | bramkuje |
|---|---|---|---|---|
| **K1** | kontrola negatywna (R8) | rozmiar testu zbiorczego na `wyr_t5` | odsetek odrzuceń ∈ [2,5 %; 7,5 %] | każdy wniosek |
| **K2** | kontrola pozytywna (R8) | moc testu zbiorczego wobec `zan30` (σ wyroczni − 30 %) | ≥ 95 % | każdy wniosek |
| **K7a** | kontrola estymatora | średnia ν̂ GARCH-t po panelach (prawda 5) | ∈ [4,0; 6,5] | każdy wniosek |
| **K7b** | kontrola estymatora | średnia α̂ + β̂ (prawda 0,98) | ∈ [0,95; 0,995] | każdy wniosek |
| **K7c** | kontrola estymatora | odsetek dopasowań bez zbieżności | ≤ 2 % | każdy wniosek |
| **K7d** | kontrola estymatora | odsetek dopasowań przy granicy zakresu parametrów | ≤ 5 % | każdy wniosek |
| **K-a** | kryterium (kalibracja) | rozmiar testu zbiorczego na `garch_tnu` (poprawny model, estymowany) | odsetek odrzuceń ≤ **10 %** | — |
| **K-b** | kryterium (kalibracja) | moc testu zbiorczego na `garch_tnu_zan10` (σ̂ × 0,90) | ≥ **80 %** | — |

**Reguła P — pytanie porównawcze (DM na stracie FZ0).**

| kod | rola | co | wymaganie | bramkuje |
|---|---|---|---|---|
| **K4** | kontrola negatywna (R8) | rozmiar DM (dwustronny) na 4 parach dokładnie zerowych {FZ0, PINB} × {c_A 0,9; 0,8}; liczy się NAJGORSZA z czterech | odsetek odrzuceń ∈ [2,5 %; 7,5 %] | każdy wniosek |
| **K5** | kontrola pozytywna (R8) | moc DM-FZ0 (jednostronnie t > 1,96): `zan30` wobec `wyr_t5` | ≥ 95 % | każdy wniosek |
| **K6a** | kontrola HAC | rozmiar DM-FZ0 po wyśrodkowaniu na parach realistycznych: NAJWIĘKSZY z sześciu | ≤ 7,5 % | **tylko wniosek TAK** |
| **K6b** | kontrola HAC | jw.: NAJMNIEJSZY z sześciu | ≥ 2,5 % | **tylko wniosek NIE** |
| **K7a–d** | kontrola estymatora | jak w regule K | jak wyżej | każdy wniosek |
| **P-a** | kryterium (mierzalność) | MDE zaniżenia σ testu DM-FZ0 wobec wyroczni (moc 80 %, siatka x ∈ {0; 0,05; 0,10; 0,15; 0,20; 0,30}) | MDE ≤ **0,10** (realizacja: moc po wygładzeniu maksimum narastającym przy x = 0,10 ≥ 80 %) | — |
| **P-b** | kryterium (mierzalność) | moc DM-FZ0 (t > 1,96, B lepsza) pary głównej `ewma94_t5 → garch_tnu` | ≥ **80 %** | — |

**Uzasadnienia progów.**

- **K1, K4, K6 [2,5 %; 7,5 %], K2, K5 ≥ 95 %:** jak w LV1 (pasmo ±2,5 pp = ok. 8 SE rozmiaru; kontrola
  pozytywna wobec σ − 30 % ma dawać ≈ 100 %, inaczej laboratorium jest głuche).
- **K-a ≤ 10 %:** dwukrotność poziomu nominalnego. Test zbiorczy dla modelu poprawnego, ale estymowanego,
  ma wolno być nieco liberalny (Escanciano–Olmo 2010: ryzyko estymacji zaburza rozmiar testów
  wstecznych), ale powyżej 10 % odrzucenie przestaje być sygnałem (co dziesiąty poprawny model wyglądałby
  na zły). **To nie jest próg wyprowadzony z teorii, tylko wybór po obejrzeniu pilotażu 64 paneli**
  (`garch_tnu`: 6,2 % przy 1 % i 4,7 % przy 5 %) — patrz „Co sprawdzono PRZED zapisem kryteriów”. Ma
  chronić przed dwukrotną nominalną liberalnością, nie wynika z żadnej funkcji straty użytkownika.
- **K-b ≥ 80 % przy x = 0,10:** ta sama kotwica co w LV1 (kryterium iii): zaniżenie σ o 10 % to „standardowy
  błąd modelu” (normalny kontra t5 przy 1 %: 2,326 vs 2,606); pozycja dobrana pod cel zmienności jest wtedy
  o ok. 11 % za duża. Przy estymowanym modelu pytamy, czy ta moc przeżyje szum estymacji.
- **K7 (zakresy):** sprawdzają estymator, nie rynek. Estymator ma odtwarzać generator w granicach
  błędu skończonej próby: ν̂ ∈ [4,0; 6,5] wokół 5 (ν̂ jest z natury skośne w prawo i niedoszacowuje
  ciężkości ogona), α̂ + β̂ ∈ [0,95; 0,995] wokół 0,98 (MLE zaniża persystencję w skończonej próbie),
  brak zbieżności ≤ 2 %, przy granicy ≤ 5 %. Zakresy są **szerokie celowo**: awaria oznacza zepsuty
  estymator, a nie niedokładność. Wybrane po pilotażach estymatora (nie ślepo, patrz wyżej).
- **P-a ≤ 0,10 i P-b ≥ 80 %:** P-a to ta sama kotwica x\* = 0,10 co w LV1, ale dla testu porównawczego
  wobec wyroczni (czy porównanie w ogóle widzi zaniżenie σ o 10 %). P-b pyta wprost: czy test odróżni
  najprostszy baseline (EWMA 0,94, t5; R17) od poprawnego modelu GARCH-t(ν̂), przy 1 600 dniach. Moc 80 % to
  zwykły standard mocy, jak w LM1 i LV1.
- **Dlaczego K6 ma dwie bramki jednostronne.** Błąd HAC (opóźnienie Newey–West) może być za mały (test
  liberalny: za często „istotnie”) albo za duży (test zachowawczy: za rzadko). Test **zbyt liberalny** może
  tylko zawyżać moc, więc wniosek NIE (moc za mała mimo zawyżenia) pozostaje ważny, a podważa tylko
  wniosek TAK → K6a bramkuje TAK. Test **zbyt zachowawczy** może tylko zaniżać moc, więc wniosek TAK pozostaje
  ważny, a podważa tylko wniosek NIE → K6b bramkuje NIE. Progi 2,5 % i 7,5 % bez zmian względem wersji
  pierwotnej (jedna kontrola dwustronna dla obu wniosków); zmiana zrobiona po pilotażu (patrz niżej).

### Reguła decyzji (R4 / reguła STOP)

Dla każdego p osobno, na komórce głównej C1. Wynik każdej z dwóch reguł (K, P) to jedno z trzech:

- **WSTRZYMANE** ⇔ zawodzi którakolwiek kontrola „każdy wniosek” **tej reguły** (K: K1, K2, K7a–d;
  P: K4, K5, K7a–d), **albo** zawodzi kontrola bramkująca wyciągnięty wniosek (tylko reguła P: K6a przy
  wniosku TAK, K6b przy wniosku NIE). Błąd laboratorium, nie wniosek o danych.
- **TAK** (pytanie mierzalne) ⇔ wszystkie kontrole bramkujące przeszły ORAZ wszystkie kryteria
  (K: K-a i K-b; P: P-a i P-b) są spełnione.
- **NIE** (pytanie niemierzalne) ⇔ kontrole bramkujące przeszły, a co najmniej jedno kryterium nie.

W wydruku wynik reguły K lub P nazywa się **MIERZALNE** (= TAK), **NIEMIERZALNE** (= NIE) albo
**WSTRZYMANE**; wynik rundy to **MIERZALNA / NIEMIERZALNA / WSTRZYMANA**. Każdą regułę i regułę rundy
wydruk podaje osobno dla C1 (kryteria) i C2 (opis).

**Reguła rundy** (`regula_rundy`): runda pierwszej analizy VaR/ES na danych przy poziomie p jest

- **MIERZALNA(p)** ⇔ K albo P daje TAK; dozwolone są tylko pytania z wynikiem TAK;
- **WSTRZYMANA(p)** ⇔ żadne pytanie nie dało TAK i któreś jest WSTRZYMANE;
- **NIEMIERZALNA(p)** ⇔ ani K, ani P nie dało TAK i żadne nie jest WSTRZYMANE (obie NIE).

**WSTRZYMANA ⇒ STOP:** najpierw diagnoza, potem **najwyżej jedna** runda LV2b. W LV2b wolno zmienić
wyłącznie to, co diagnoza wskaże jako błąd laboratorium (np. opóźnienie HAC w DM, ustawienia estymatora);
NIE wolno zmieniać progów, prognoz, generatora, komórek ani liczby paneli. Druga WSTRZYMANA to
NIEMIERZALNA(p) i karta decyzji do użytkownika.

**MIERZALNA(p) ⇒ pierwsza runda VaR/ES na danych może wejść do pre-rejestracji** (osobna karta, licznik
„ryzyko 2021+”, PRD §11.4), ale tylko przy warunkach przeniesienia zapisanych TERAZ:

1. **Zakres.** (a) ≥ 20 monet, każda z ≥ 1 600 dniami OOS po ≥ 400 dniach historii (komórka C1), **albo**
   (b) populacja 15 monet × ≥ 1 700 dni OOS (komórka C2, jak F2-1b), ale tylko jeśli ta sama reguła
   (to samo pytanie, to samo p) daje TAK także w C2 — C2 jest drukowana jako OPIS tej decyzji, nie jest
   kryterium werdyktu rundy. Przy mniejszym n lub K potrzebna jest nowa pre-rejestracja laboratorium.
2. **Zależność.** Współczynnik VR dziennej sumy trafień (VR = Var(S_t)/(K p (1 − p))) zmierzony na
   prawdziwych danych dla prognozy `garch_tnu`-podobnej (osobna karta, licznik opisowy) nie przekracza
   VR komórki C1 z tego przebiegu dla `garch_tnu` (wydruk podaje go przy każdym p; pilotaż: ok. 3,2 przy 1 %
   i 6,4 przy 5 %). Inaczej trzeba policzyć nową komórkę z silniejszą zależnością.
3. **Klasa prognozy.** Wniosek K dotyczy klasy „GARCH(1,1)-t dopasowany walk-forward (refit co 30 dni, rosnące
   okno ≥ 400 dni), ogon t_ν̂”. Okno 60 dni i EWMA mają W1 (odrzucane w ≥ 70 % paneli): test bezwzględny jest dla
   nich z założenia nieinformatywny i wolno je oceniać wyłącznie testem porównawczym (jeśli P = TAK) albo
   opisowo. Prognozę i ogon zapisuje pre-rejestracja rundy na danych.
4. **Pytanie.** Wolno zadać wyłącznie pytania z wynikiem TAK; odrzucenie prognozy testem bezwzględnym
   znaczy „nie skalibrowana”, nie „bezużyteczna” (LV1).

**NIEMIERZALNA(p)** ⇒ **żadna runda VaR/ES na prawdziwych danych przy tym poziomie nie startuje** (R3).
Alternatywy — niżej.

Skrypt jest neutralnym reporterem (R14): drukuje liczby, kryteria i wynik reguł; werdykt (Ready / Caveats
/ Revision) podpisuje Claude po przebiegu. Wydruk oznacza „[w granicach 2 SE od progu]” każde kryterium lub
kontrolę, której wartość leży bliżej progu niż 2 SE (przy takich werdykt jest wrażliwy na losowość), oraz
przy kontrolach K6a/K6b „[bramkuje tylko wniosek …]”.

### Przewidywania (zapisane PO obejrzeniu pilotażu, więc nie ślepe; falsyfikowalne)

Sprawdzane w kodzie (`przewidywania`) dla komórki głównej, osobno dla p = 1 % i 5 %; **nie wchodzą do reguł**.

- **W1.** Test zbiorczy odrzuca `okno60_t5` i `ewma94_t5` w ≥ **70 %** paneli (LV1: 78–98 %; pilotaż 480:
  77,3 % / 80,6 %, czyli dla EWMA zapas jest mały).
- **W2.** Średnia strata FZ0 ponad wyrocznię jest ściśle malejąca: `okno60_t5` > `ewma94_t5` > `garch_tnu`
  (pilotaż: tak, przy 1 % i 5 %).
- **W3.** P-a **niespełnione** (MDE zaniżenia σ testu DM-FZ0 > 0,10; pilotaż: 0,140 / 0,131).
- **W4.** P-b **niespełnione** (moc DM-FZ0 pary `ewma94_t5 → garch_tnu` < 80 %; pilotaż: 35,2 % / 75,8 %).

**Oczekiwanie łączne (nie ślepe):** K = TAK (K-a przy 1 % blisko progu: 7,9 ± 1,2 % w pilotażu), P = NIE,
a więc runda MIERZALNA wyłącznie przez pytanie bezwzględne K. W razie niespełnienia któregoś z W1–W4 albo
takiego łącznego wyniku opisujemy to wprost.

### Co NIE jest kryterium (opis)

Wynik komórki C2; wszystkie prognozy poza `wyr_t5`, `zan30`, `garch_tnu`, `garch_tnu_zan10` w regule K i
poza `wyr_t5`/`zan…` i parą główną w regule P; składniki A, B, C testu zbiorczego; test A po stronie „za
dużo trafień”; VR; strata PINB poza K4; ogony empiryczne (`ep`, `ec`), `garch_t5`, `har_t5`, `okno60_t5`,
`ewma94_t5` (z wyjątkiem pary głównej); „koszt estymacji” (średnia różnica straty prognozy estymowanej
względem wyroczni); pełna tabela odsetków odrzuceń testu DM dla wszystkich 36 porównań; kolumny
uśrednionych t. Odsetek odrzuceń testu zbiorczego dla okien i EWMA to **moc** (H0 dla nich fałszywa), nie
rozmiar.

### Co sprawdzono PRZED zapisem kryteriów (pełna jawność, R3)

Oś czasu (UTC, 2026-10-06; ustalona z zapisów sesji) i co z niej wynika dla ślepoty projektu:

**1. Estymator GARCH-t (17:07–17:09).** Własny estymator (`symulacje/garch_t.py`) porównano z pakietem `arch`
8.0.0 przy tym samym backcaście (test `test_dopasowanie_zgodne_z_pakietem_arch_przy_tym_samym_backcast`),
sprawdzono odtwarzanie parametrów generatora na długich seriach, zgodność ciepłego i zimnego startu oraz
niezależność od jednostek zwrotu. Pilotaże estymatora na pojedynczych seriach miały własne ziarna.

**2. Pilotaż 64 paneli (17:11:45, skrypt poza repo, ziarno bazowe 810000; to NIE jest wynik rundy).** Odsetek
odrzuceń testu zbiorczego, p = 1 % / 5 %: `garch_tnu` 6,2 % / 4,7 %; `okno60_t5` 100 % / 93,8 %;
`ewma94_t5` 85,9 % / 79,7 %. Test DM-FZ0 pary `ewma94_t5 → garch_tnu`, odsetek t > 1,96 (B lepsza): 37,5 % /
68,8 %. **Progi K-a (≤ 10 %) i zakresy K7 zapisano w kodzie PO tym pilotażu (17:22:07)** — nie są ślepe.
SE pilotażu 64 paneli jest duży (ok. 3 pp przy 6 %).

**3. Test działania i pilotaże 16 i 480 paneli (17:28–17:35, ziarno 777).** `--smoke` (17:28:36) sprawdził,
że kod działa. Pilotaż 480 paneli (17:29:08–17:32:03; 174 s na 16 procesach) pokazał: (komórka C1, p = 1 % /
p = 5 %; **to NIE jest wynik rundy**)

| wielkość | p = 1 % | p = 5 % | wymaganie |
|---|---|---|---|
| K1 rozmiar `wyr_t5` | 3,1 % | 4,8 % | [2,5; 7,5] % |
| K2 moc `zan30` | 100 % | 100 % | ≥ 95 % |
| K-a rozmiar `garch_tnu` | 7,9 ± 1,2 % | 5,0 ± 1,0 % | ≤ 10 % |
| K-b moc `garch_tnu_zan10` | 99,4 % | 99,6 % | ≥ 80 % |
| K4 najgorsza para zerowa | 6,0 % (FZ0, c_A 0,8) | 5,6 % | [2,5; 7,5] % |
| K5 moc DM-FZ0 `zan30` | 100 % | 100 % | ≥ 95 % |
| K6 DM-FZ0 wyśrodkowany: największy / najmniejszy z 6 par | 7,3 / 2,5 % | 9,0 / 2,9 % | ≤ 7,5 / ≥ 2,5 % |
| P-a MDE DM-FZ0 (moc przy x = 0,10) | 0,140 (50,0 %) | 0,131 (59,0 %) | ≤ 0,10 (≥ 80 %) |
| P-b moc `ewma94_t5 → garch_tnu` | 35,2 % | 75,8 % | ≥ 80 % |
| K7 (oba p razem): ν̂ / α̂+β̂ / bez zbieżności / przy granicy | 5,232 / 0,9722 / 0,00 % / 2,10 % | | [4,0; 6,5] / [0,95; 0,995] / ≤ 2 % / ≤ 5 % |
| opis: test zbiorczy, MDE zaniżenia σ (wyrocznia) | 0,082 | 0,079 | |
| opis: VR dziennej sumy trafień `garch_tnu` (`wyr_t5`) | 3,20 (3,03) | 6,36 (6,30) | |
| W1 (min z okno60, ewma94) / W2 (okno60 − garch_tnu, FZ0) | 0,773 / 0,080 | 0,806 / 0,058 | ≥ 0,70 / > 0 |
| opis C2: K-a / P-a / P-b | 9,4 % / 0,141 / 33,3 % | 4,4 % / 0,130 / 73,5 % | |

Moc DM-FZ0 wobec wyroczni (x = 0; 0,05; 0,10; 0,15; 0,20; 0,30): p = 1 %: 5,9; 14,4; 50,0; 87,3; 99,2; 100,0 %;
p = 5 %: 5,4; 19,6; 59,0; 93,1; 99,8; 100,0 %. Rozkład wyniku: K → TAK (K-a przy 1 % z małym zapasem; C2
przy 1 % jeszcze bliżej progu: 9,4 %), P → NIE (W3, W4 spełnione). Pilotaż pokazał też, że reguły potrafią dać
oba wyniki, czyli nie są trywialne (R3).

**4. Zmiany PO obejrzeniu pilotażu 480 (17:41–17:52; przed tą pre-rejestracją i przed przebiegiem rejestrowym).**

- **K6: jedna kontrola dwustronna → dwie bramki jednostronne (K6a, K6b)** (17:48). Pierwotnie wszystkie 6
  par realistycznych musiało mieścić się w [2,5; 7,5] %, a porażka wstrzymywała każdy wniosek. W pilotażu
  przy p = 5 % dwie pary (`okno60_t5 → ewma94_t5` i `garch_tnu → garch_t5`) dały 9,0 %, więc stara
  kontrola wstrzymałaby regułę P przy 5 %; nowa daje tam NIE (najmniejszy 2,9 % ≥ 2,5 %; K6a bramkuje
  tylko TAK). **Zmiana jest po fakcie** i przestawia przewidywany wynik reguły P przy 5 % z WSTRZYMANE na
  NIE; werdykt rundy (MIERZALNA przez K) się nie zmienia. Uzasadnienie logiczne — w „Uzasadnieniach progów”;
  progi liczbowe bez zmian. Przy p = 1 % obie nowe bramki leżą na krawędzi (7,3 % przy 7,5 %; 2,5 % przy
  2,5 %), więc w przebiegu rejestrowym K6a lub K6b może zawieść; skutek: P = WSTRZYMANE. Przy oczekiwanym
  P = NIE wniosku o rundzie to nie zmienia, o ile K = TAK.
- **P-a: realizacja przez moc przy x\* = 0,10 po wygładzeniu maksimum narastającym** (17:41), zamiast
  interpolowanego MDE (x\* leży na siatce, więc to to samo kryterium bez zaokrągleń interpolacji;
  wydruk nadal podaje MDE). W pilotażu bez wpływu na wynik (moc 50,0 / 59,0 %).
- **Panele 3 000 → 5 000** (17:51): zmniejsza SE, by zapas K-a był rozróżnialny (SE ≤ 0,71 pp).
- **Test przypięcia konfiguracji** (`test_konfiguracja_progi_i_prognozy_zgodne_z_pre_rejestracja`) zapisuje
  progi, ziarno, komórki i listę prognoz z tej pre-rejestracji; zmiana któregokolwiek w kodzie wymaga zmiany
  w README (oraz w teście).

**5. Kod testów i commit.** Testy jednostkowe powstały równolegle z kodem (17:33–17:55); commit kodu
`009204b` (17:56:28). Testy pokrywają m.in.: wzory strat na liczbach ręcznych, wartości oczekiwane
(porównanie z całkowaniem), pary zerowe, DM na wzorze ręcznym i znak, estymator GARCH względem `arch`, brak
zaglądania w przyszłość (zaburzenie dnia t nie zmienia prognoz do t włącznie), podpanel = te same monety
i dni, okablowanie reguł (każdy próg domknięty na granicy, bramki K6, tabela prawdy reguły rundy),
determinizm niezależny od liczby procesów, przypięcie konfiguracji, znacznik pilotażu. Mikro kontrole R8
na małych panelach: wyrocznia ma poprawny rozmiar, `zan30` jest wykrywane, pary zerowe nie odrzucają zbyt
często. Mutacje na kopii poza repozytorium — w kroku przeglądu.

**6. Czego nie sprawdzano.** Pełnego przebiegu rejestrowego (5 000 paneli, ziarno 20261016) nie
uruchamiano. Nie czytano żadnych prawdziwych danych. K-a na rozdzielczości rejestrowej (SE ok. 0,4 pp)
nie jest znane — pilotaż ma SE 1,2 pp. Nie badano zachowania estymatora przy zmianach reżimu, wspólnej
zmienności ani zależności ogonowej (generator ich nie ma).

### Zmiany po przeglądzie, przed pełnym przebiegiem

(do wypełnienia w kroku 2 planu: 3 niezależnych recenzentów, mutacje na kopii poza repo,
`arxitect:architecture-review`; pusta, dopóki przegląd się nie odbył)

### Co zrobić, gdy wynik jest NIEMIERZALNA albo WSTRZYMANA (alternatywy, nie ruchy tej rundy)

Każda alternatywa to nowe pytanie z własnym licznikiem (PRD §11.4) i własną pre-rejestracją:

1. **Raport opisowy bez werdyktu:** odsetek trafień, średni stosunek strat ponad VaR do ES, strata FZ0
   obok siebie dla prognoz, bez „zdał / nie zdał”.
2. **Dłuższa historia albo więcej monet** (top-50, FR-01): komórka C1 z większym n lub K; mapa z LV1/LV2 jako
   opis do planowania.
3. **Inna miara niż test zbiorczy:** np. test warunkowy z tzw. czynnikiem skalującym albo test oparty na
   oczekiwanym niedoborze na dłuższym horyzoncie — wymaga osobnego laboratorium.
4. **Tylko poziom, który przeszedł** (np. wyłącznie p = 1 %, jeśli 5 % jest NIEMIERZALNA), albo zmierzyć
   faktyczną zależność koszyka (VR) na prawdziwych danych i dopiero wtedy wybrać komórkę.

### Ograniczenia

- **Generator ma tylko zależność gaussowską przez wspólny czynnik** (stałe ρ; brak zależności ogonowej
  i wspólnej zmienności), więc VR dziennej sumy trafień to ok. 3,2 (1 %) i 6,4 (5 %); prawdziwe krachy są
  bardziej synchroniczne. Wynik to raczej górne oszacowanie mocy; stąd warunek „Zależność”.
- **Model poprawnie określony to najlepszy przypadek.** GARCH-t jest prawdziwą klasą modelu generatora, więc
  K-a mierzy tylko rozmiar testu przy błędzie estymacji parametrów, bez błędu specyfikacji. Na prawdziwych
  danych model jest zawsze w jakimś stopniu źle określony; TAK w K oznacza „test nie myli się, gdy model jest
  dobry” (warunek konieczny), nie „test wykryje każdy błąd specyfikacji”.
- **K1/K-a dotyczą klasy GARCH-t(ν̂) z refitem co 30 dni.** Rozmiar dla innych klas modeli (np. HAR jako prognoza
  VaR, modele z innymi innowacjami) jest nieznany.
- **Test DM bez poprawki HLN i z jednym opóźnieniem HAC (7).** K6 sprawdza błąd HAC na parach
  realistycznych, ale po wyśrodkowaniu na średniej po panelach (to nie jest rozmiar absolutny). Przy n = 1 600
  poprawka HLN jest pomijalna, ale to założenie, nie pomiar.
- **Reszty „w próbie” dla ogonów empirycznych GARCH** i ok. 16 trafień na monetę w ogonie 1 % → ogony
  empiryczne są szumne; to opis, nie kryterium.
- **Pilotaż nie był ślepy** (K-a, K7, K6, P-a i W1–W4 ustalono po jego obejrzeniu).
- **C2 (15 monet) to opis.** W pilotażu K-a w C2 przy p = 1 % wyniosło 9,4 %, bliżej progu niż w C1. Jeśli
  w przebiegu rejestrowym C2 nie da TAK, populacja 15 monet (F2-1b) nie spełnia warunku „Zakres (b)”; wtedy
  pierwsza runda na danych wymaga ≥ 20 monet (np. top-50 z danymi od 2021).
- Panel ma 2 100 dni, a refit idzie od 400 dni; krótsza historia (np. monety z ok. 600 dniami) jest poza
  zakresem tego laboratorium.

### Liczniki

- **0 wariantów**, POZA licznikami: dane syntetyczne, kalibracja przyrządu.
- Wspólny rejestr odczytów alpha (`odczyty_historii.csv`, N = 40): **bez zmian** — żaden zwrot strategii nie
  jest odczytywany na historii.
- Licznik „ryzyko ogona (VaR/ES) 2021+” (PRD §11.4): **bez zmian (0)** — nie testujemy żadnej prognozy VaR/ES
  na prawdziwych danych. Licznik „zmienność 2021+”: bez zmian (1, F2-1b).
- R15: LLM nie występuje w żadnej ścieżce decyzyjnej; przyrząd i skrypt są deterministyczne (R19).

### Decyzje wykonawcy (poza zleceniem) — do przeglądu

1. **Dwie reguły (K i P) i reguła rundy „K albo P”.** Karta pytała o (a), (b), (c); wybrany podział daje
   odpowiedź na (c) bez mieszania pytania bezwzględnego z porównawczym.
2. **K-a ≤ 10 %** (karta nie podała progu), wybrane po pilotażu 64 paneli; patrz uzasadnienie.
3. **K6 jako dwie bramki jednostronne** (po pilotażu 480; zmienia przewidywany wynik P przy 5 % z
   WSTRZYMANE na NIE, nie zmienia werdyktu rundy).
4. **Komórki C1 i C2:** C1 decyduje, C2 jest opisem i sprawdzianem populacji F2-1b (karta: „n = 1 600
   i 1 700 z F2-1b”); warunek „Zakres (b)” jest nowy.
5. **HAR i ogony empiryczne tylko jako opis** (karta: „HAR jako opis”, „ogon t5 i kwantyl empiryczny”).
6. **Własny estymator GARCH-t** (ok. 1 140 dopasowań na panel × 5 000 paneli; pakiet `arch` byłby za wolny),
   zwalidowany pakietem `arch` w testach.
7. **Data katalogu 2026-10-07** (karta wskazywała 2026-10-06 z dnia pisania kodu).
8. Żaden z punktów 2–4 nie zmienia werdyktu rundy w pilotażu (MIERZALNA przez K), więc nie jest punktem
   decyzyjnym dla użytkownika; wszystkie są do przeglądu.
