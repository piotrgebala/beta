# 017 — inwentarz 15 monet i zależność trafień ρ_h (karta opisowa, bez oceny prognozy)

## Metadane

- Karta: `zadania/017-dane-pod-runde-var-es-inwentarz-i-rho.md`. Rodzic: LV2 (`runs/2026-10-07_lv2-var-es-estymowane/`,
  sekcja „Werdykt”, warunki przeniesienia 1 i 2).
- Licznik: **opisowy, poza licznikami**. Licznik „ryzyko ogona (VaR/ES) 2021+” **zostaje 0**: nic tu nie testuje
  prognozy. Rejestr zwrotów alpha nietknięty.
- Komenda (po zatwierdzeniu pre-rejestracji): `python -m modele.pomiar_rho_h > runs/2026-10-07_017-inwentarz-i-rho/raw_output.txt`.
- Status tego pliku: pre-rejestracja zapisana w `c9bee1c` (sekcja „Pre-rejestracja”, bez zmian po przebiegu), kod `9a4ea39`; wynik, weryfikacja, werdykt i wniosek — sekcje od „Wynik w skrócie” w dół (przebieg 2026-10-07).

## Pre-rejestracja (zapisana przed przebiegiem)

### Wnioski skumulowane, które dotyczą tej karty

`[2026-10-07, LV2]`: generator laboratorium ma tylko zależność gaussowską przez wspólny czynnik (ρ = 0,8), więc
prawdziwe krachy są bardziej synchroniczne, a moc i rozmiar testu zbiorczego mogą być na danych gorsze; stąd warunek 2
przeniesienia (zmierzyć ρ_h na prawdziwych danych). Wynika z tego cały projekt tej karty: zmierzyć zależność trafień,
nie oceniając samych trafień.

### R1 — mechanizm jednym zdaniem

Jeśli w prawdziwych danych monety przekraczają VaR w tych samych dniach częściej niż w laboratorium, to test
zbiorczy ma więcej fałszywych alarmów, niż pokazało LV2 (8,2 % / 5,5 %), więc wynik karty 018 byłby nie do odczytania;
karta mierzy tę zależność, zanim ktokolwiek zacznie oceniać prognozę. (Karta nie zakłada żadnej „drugiej strony”
handlowej: to pomiar warunku przeniesienia, nie hipoteza o rynku.)

### R2 — zbiór informacyjny × formuła × target × horyzont

- zbiór informacyjny: dzienne log-zwroty 15 monet do dnia t − 1 (świece 1d Binance USDT-M, od 2021-01-01, obcięte na
  2026-09-30 włącznie, jak F2-1b);
- formuła: dokładnie ta klasa prognoz, co w 018: `symulacje.garch_t.dopasuj_garch_t`, zerowa średnia, refit co 30 dni,
  okno rosnące od 400 dni, ogon t_ν̂, wariancja początkowa z próby;
- target: S_t = liczba monet z przekroczeniem VaR 5 % w dniu t (trafienie = `r < q`, ta sama definicja co
  `miara.var_es._trafienie`); ocenia się wyłącznie **rozrzut** S_t, nie jej średnią;
- horyzont: 1 dzień.

### R3 — mierzalność

Pomiar opisowy, bez testu hipotezy, więc rachunek mocy nie dotyczy. Precyzja pomiaru (SE) jest częścią bramki
(ρ̂ + 2 SE), więc słabo wyznaczone ρ̂ przesuwa wynik w stronę „018 nie startuje”, nie „startuje”.

### R4 — jedna zmienna, licznik, reguła STOP

- Jedna zmienna: okno danych (dziś: wszystkie dni wspólne do 2026-09-30). Jedno zapowiedziane powtórzenie: na
  końcowym oknie karty 018 (po dopłynięciu danych za październik 2026), tą samą funkcją i tymi samymi stałymi.
  To ten sam wariant, nie nowy; wynik z końcowego okna nadpisuje wynik dzisiejszy.
- Stałe, których po obejrzeniu wyniku nie ruszam: p = 5 %; próg 0,282; długość bloku bootstrapu L = 20; liczba
  replikacji B = 2 000; ziarno 20261007; lista i kolejność monet; definicja trafienia.
- Reguła STOP: jeśli kod nie da się uruchomić na wszystkich 15 monetach (brak pliku, NaN w zwrotach wspólnego panelu,
  niezbieżne dopasowanie, które zatrzymuje pętlę), przebieg się zatrzymuje z komunikatem; niczego nie omijam po cichu.

### Dane i inwentarz wstępny (zrobiony przed pre-rejestracją, bez żadnej prognozy)

Lista i kolejność (F2-1b, `python -m modele.run_f21b --tylko-monety`): BNBUSDT, BTCUSDT, ETHUSDT, XRPUSDT, SOLUSDT,
DOGEUSDT, ADAUSDT, LINKUSDT, AVAXUSDT, LTCUSDT, BCHUSDT, DOTUSDT, FILUSDT, ETCUSDT, NEARUSDT.

Świece 1d (`data/binance_um/1d/<SYMBOL>.parquet`, przez `wczytaj_swiece`, R16): 10 monet ma po 2 099 świec
(2021-01-01…2026-09-30, kalendarz pełny); XRP, SOL, LTC, FIL i NEAR mają po 2 094 (brak 5 dni: 2022-02-26…28 i
2022-04-01…02, te same wspólne dziury co w DQ1). Zero duplikatów, zero cen ≤ 0.

Zwrot dzienny = log(close_t / close_{t−1}) liczony tylko wtedy, gdy istnieją **oba kolejne dni kalendarzowe**. Dla
pięciu monet z dziurami nieważnych jest więc 7 dat zwrotu (26, 27, 28 II i 1 III 2022; 1, 2 i 3 IV 2022). **Panel
wspólny** = daty, w których zwrot jest poprawny dla wszystkich 15 monet. Z dziennych świec wynika:
2 098 − 7 = 2 091 wierszy wspólnych (zgodnie z „2 091 / 2 099” w F2-1b).

### Rozstrzygnięcie okna (zakres 2a–2c karty)

- **2a.** Świece 1d mają dni potrzebne do zwrotów, z wyjątkiem 5 dziur wyżej (nieusuwalne: brak w źródle).
- **2b.** Okno C2 wymaga 400 + 1 700 = **2 100 wierszy wspólnych**. Dziś jest ich 2 091, czyli **brakuje 9**. Komórka
  C2 jest wymagana „dokładnie”, więc nie obcinam oceny do 1 691 dni. Po dopłynięciu października 2026 (automat
  miesięczny, spodziewane ok. 2026-11-01) wierszy będzie 2 091 + 31 = 2 122, jeśli w październiku nie pojawią się nowe
  dziury.
- **2c.** Reguła okna dla 018 (do powtórzenia w jej pre-rejestracji): panel wspólny do 2026-10-31 włącznie, **ostatnie
  2 100 wierszy**; pierwsze 400 to historia, ostatnie 1 700 to ocena. Jeśli wierszy będzie < 2 100, 018 nie startuje i
  wraca do użytkownika.
- Wniosek z góry: **dziś 018 nie może ruszyć** (okno się nie domyka), niezależnie od tego, jaki wyjdzie ρ̂. Decyzję
  „czekać na październik zamiast zmieniać komórkę” podjąłem na delegacji (STATUS.md, tabela decyzji); ścieżka
  odwrotu: użytkownik może zaakceptować ocenę na 1 691 dniach jako udokumentowane odstępstwo od C2.
- Dziury 5 dat wycięte ze wszystkich monet sklejają kalendarz (po 2022-02-25 następny wiersz to 2022-03-02, po
  2022-03-31 wiersz 2022-04-04). Filtr GARCH traktuje te dni jako sąsiednie; to 2 sklejenia na ponad 2 000 wierszy
  i opisuję je jako ograniczenie, nie poprawiam.

### Pomiar

1. Prognoza VaR 5 % dla dni 400…koniec panelu: `modele.pomiar_rho_h.prognoza_garch_tnu`. To kopia samej pętli bloku
   GARCH z `symulacje/prognozy_lv2.zbuduj_zrodla` (`dopasuj_garch_t`, `filtr_sigma2`, ν̂, `var_es_t`), bez źródeł
   pobocznych (kod `symulacje/` jest zamrożony od `24c8863`). Parytet z `zbuduj_zrodla` + `prognoza(zr, "garch_tnu", p)`
   sprawdza test (zgodność do 1e-12 na panelu syntetycznym), a test przecieku pilnuje, że prognoza na dzień t nie zależy
   od zwrotów z dni ≥ t.
2. S_t = liczba trafień w dniu t, VR = Var(S_t; ddof = 1) / (K p (1 − p)) z p = 0,05 **nominalnym** (tak jak w LV2),
   ρ̂ = (VR − 1) / (K − 1), K = 15.
3. **Błąd standardowy ρ̂:** kołowy bootstrap blokowy po dniach. Z wektora S_t (długość n) losuję ⌈n / L⌉ początków bloków
   o długości L = 20 (równomiernie, indeksy kołowe), skracam do n, liczę ρ̂* tym samym wzorem; B = 2 000 replikacji,
   `numpy.random.default_rng(20261007)`. SE = odchylenie standardowe ρ̂* (ddof = 1). Blok 20 dni ma uchwycić
   skupianie się zmienności (persystencja GARCH ≈ 0,98) w rozrzucie S_t. Wrażliwość SE na L = 10 i L = 40 jest
   **opisem**, bramka bierze tylko L = 20.
4. **Bramka (warunek 2 z LV2):** ρ̂ + 2 SE ≤ 0,282 (VaR 5 %, wartość `garch_tnu` z przebiegu rejestrowego LV2).
5. **Wydruk:** inwentarz (tabela monet, wspólny panel), okno, VR, ρ̂, SE (L = 20, 10, 40), ρ̂ + 2 SE, wynik bramki,
   kontrole R8. **Nie drukuje** odsetka trafień, statystyk testu zbiorczego ani testów Kupca i Christoffersena, nie
   zapisuje macierzy trafień. Test jednostkowy pilnuje, że wydruk nie zawiera odsetka trafień. Wynik idzie wyłącznie
   na stdout.
6. **Ograniczenie, zapisane z góry:** VR z nominalnym p miesza zależność trafień z poziomem trafień (jeśli prognoza
   trafia częściej niż 5 %, VR rośnie). Rozdzielenie ich wymagałoby ujawnienia odsetka trafień, czego karta ma nie
   robić. Dlatego niepowodzenie bramki znaczy „VR większe niż w laboratorium”, nie „zależność większa”; w obu
   przypadkach następny krok jest ten sam (laboratorium z silniejszą zależnością albo szerszy koszyk, patrz niżej) i
   żadnej alternatywnej miary po obejrzeniu wyniku nie liczę.

### Kontrole R8 (silnik pomiaru)

Obie na panelach syntetycznych z `symulacje.garch_panel.generuj_panel` (15 monet × 2 100 dni, ν = 5, GARCH
(0,08; 0,90), σ̄ = 4 %), 10 paneli na kontrolę, ziarna 1…10 (dodatnia) i 101…110 (ujemna), ta sama funkcja
pomiarowa co dla prawdziwych danych:

- **Dodatnia:** ρ = 0,8 (jak LV2). Oczekiwane średnie ρ̂ ≈ 0,282 (wartość rejestrowa LV2 dla `garch_tnu`, C2, 5 %);
  kryterium zaliczenia: średnia z 10 paneli w przedziale [0,242; 0,322].
- **Ujemna:** ρ = 0 (monety niezależne). Oczekiwane ρ̂ ≈ 0; kryterium: |średnia z 10 paneli| ≤ 0,03.

Niezaliczenie którejś kontroli = silnik nie nadaje się do bramki; wynik prawdziwych danych jest wtedy podany, ale
werdykt karty to Revision.

### Przewidywanie (zapisane przed wynikiem)

Spodziewam się ρ̂ **powyżej** 0,282 i bramki, która **nie przechodzi** (moje prawdopodobieństwo: ok. 65 %). Powód:
generator łączy monety tylko wspólnym czynnikiem gaussowskim, a w prawdziwych danych krachy dotykają wszystkich monet
naraz i wspólny szok zmienności podnosi liczbę trafień w jednym dniu. Zaskoczeniem byłoby ρ̂ ≤ 0,24.

### Co wynika z którego wyniku (zapisane z góry)

| wynik | zdanie w karcie |
|---|---|
| okno się nie domyka (dziś, 2 091 < 2 100) | „018 nie startuje dziś, bo okno C2 ma 2 091 z 2 100 wierszy; może ruszyć po danych za październik 2026” (ta część zapisana już teraz) |
| ρ̂ + 2 SE ≤ 0,282 | do tego zdania dochodzi: „bramka zależności przechodzi na oknie dzisiejszym; do powtórzenia na końcowym oknie 018” |
| ρ̂ + 2 SE > 0,282 | „018 nie startuje, bo zależność trafień przekracza laboratorium; następny krok: LV2c (silniejsza zależność, np. wspólny szok zmienności) albo szerszy koszyk; decyzja o zleceniu LV2c to autonomia badawcza, bez licznika” |

## Wynik w skrócie — prostym językiem

**Co zrobiliśmy.** Wzięliśmy prawdziwe ceny dzienne 15 monet (od 2021-01-01 do 2026-09-30) i puściliśmy na nich tę
samą prognozę ryzyka, którą badało laboratorium LV2: **VaR 5 %**, czyli stratę, którą moneta ma przekraczać w 5
dniach na 100 (liczy ją model GARCH-t, dopasowywany od nowa co 30 dni). **Nie sprawdzaliśmy, czy ta prognoza jest
dobra**, i nie patrzyliśmy, jak często moneta ją przekracza. Zmierzyliśmy jedno: czy monety przekraczają swój VaR
**w tych samych dniach** („zależność trafień”, znak **ρ**) i czy jest to bardziej zsynchronizowane niż w sztucznym
świecie z laboratorium.

**Po co.** Test, którym karta 018 miała ocenić prognozę, wyskalowaliśmy w laboratorium (fałszywy alarm 5,5 % przy
VaR 5 %). Gdyby prawdziwe monety były bardziej zsynchronizowane niż sztuczne, ten test mógłby zachowywać się inaczej,
niż pokazało laboratorium, i wynik 018 byłby trudny do odczytania.

**Wynik.**

- **Prawdziwe monety są wyraźnie bardziej zsynchronizowane niż w laboratorium.** ρ̂ = **0,50** (przedział ±2 błędy
  standardowe: ok. 0,36–0,64), w laboratorium 0,28. Obrazowo, przy założeniu, że każda moneta przekracza VaR w ok.
  5 % dni: w laboratorium, gdy jedna moneta przekroczyła VaR, to z pozostałych robiła to w tym samym dniu średnio co
  trzecia; w prawdziwych danych — co druga. Bramka (ρ̂ + 2 SE ≤ 0,282) **nie przechodzi**: 0,64 > 0,282, a nawet
  dolny koniec przedziału (0,36) leży powyżej progu. (Sama bramka jest ostrożna: nie przeszłaby też przy zależności
  dokładnie jak w laboratorium — patrz sekcja 3. Wniosek opieram więc na dolnym końcu przedziału, nie na samym
  niepowodzeniu bramki.)
- **Okno danych też się dziś nie domyka.** Komórka C2 wymaga 2 100 dni wspólnych dla 15 monet, jest 2 091 (brakuje
  9). Samo to wystarczyłoby, żeby 018 dziś nie ruszyła.
- **Osobna obserwacja o estymatorze** (opisowa, poza bramką): w 227 z 855 dopasowań (27 %) model GARCH dochodzi do
  górnej granicy „pamięci zmienności” (0,9999); w laboratorium było to 2,2 %. Dotyczy głównie BTC, ETH, BNB i DOGE.
  Laboratorium nie odtwarza więc tego, jak estymator zachowuje się na prawdziwych cenach.

**Zdanie rozstrzygające (kryterium odbioru karty): 018 nie startuje, bo zależność trafień przekracza laboratorium
(ρ̂ = 0,50, dolny koniec przedziału 0,36 i ρ̂ + 2 SE = 0,64, wszystkie > 0,282) i dodatkowo okno C2 ma 2 091 z 2 100 wierszy.** Następny krok: LV2c, czyli laboratorium z
zależnością i trwałością zmienności ustawionymi na wzór prawdziwych danych (karta 019; decyzja badawcza, bez licznika;
ścieżka odwrotu w `STATUS.md`).

**Czego z tego NIE wolno wyciągać.** To nie jest ocena prognozy ani dowód, że test z LV2 się psuje: nie wiemy, jak
zachowa się przy takiej zależności, i właśnie to ma sprawdzić LV2c. Nie wiemy też, ile z 0,50 to „zależność”, a ile
„poziom trafień” (jeśli prognoza trafia częściej niż w 5 % dni, ρ̂ rośnie; zapisane z góry w pkt. 6 pre-rejestracji,
a odsetka trafień karta celowo nie drukuje).

## Wynik

Wszystkie liczby z tej sekcji pochodzą z `raw_output.txt` (jedyny przebieg `python -m modele.pomiar_rho_h` na
prawdziwych danych; stan kodu = commit `9a4ea39`, drzewo plików śledzonych bez zmian; czas 62 s; model deterministyczny,
ziarno bootstrapu 20261007), chyba że wskazano inaczej.

### 1. Inwentarz

| grupa | monety | świec 1d | ważnych zwrotów | braki w kalendarzu |
|---|---|---|---|---|
| pełny kalendarz (10) | BNB, BTC, ETH, DOGE, ADA, LINK, AVAX, BCH, DOT, ETC | 2 099 | 2 098 | brak |
| pięć dziur (5) | XRP, SOL, LTC, FIL, NEAR | 2 094 | 2 091 | 2022-02-26, -27, -28 i 2022-04-01, -02 |

Wszystkie 15 monet: pierwsza świeca 2021-01-01, ostatnia 2026-09-30 (kolejność w wydruku: BNB, BTC, ETH, XRP, SOL,
DOGE, ADA, LINK, AVAX, LTC, BCH, DOT, FIL, ETC, NEAR). Dziury i brak duplikatów zgodne z inwentarzem wstępnym
z pre-rejestracji (które powstało przed jakąkolwiek prognozą).

**Panel wspólny:** 2 091 wierszy (2021-01-02 … 2026-09-30). Daty wycięte przez dziurę u którejś monety (7): 2022-02-26,
-27, -28, 2022-03-01, 2022-04-01, -02, -03. Sprawdzenie: 2 098 − 7 = 2 091.

### 2. Okno (zakres 2a–2c karty)

| co | wartość |
|---|---|
| potrzeba dla C2 | 2 100 wierszy wspólnych (400 historii + 1 700 oceny) |
| jest | **2 091** → **NIE DOMYKA SIĘ (brakuje 9)** |
| dni oceny w tym przebiegu | **1 691** (2022-02-06 … 2026-09-30; 7 wyciętych dat leży wewnątrz tego okresu) |
| po danych za październik 2026 | 2 091 + 31 = 2 122 ≥ 2 100, o ile nie pojawią się nowe dziury (do sprawdzenia po 2026-11-01) |

Przebieg jest więc na 1 691 dniach oceny, a nie na 1 700 wymaganych w C2. Reguła zapisana z góry (2c): 018 używa
ostatnich 2 100 wierszy panelu do 2026-10-31; jeśli będzie ich mniej, 018 nie startuje.

### 3. Zależność trafień (VaR 5 %, GARCH-t, K = 15)

| wielkość | prawdziwe dane (017) | laboratorium LV2, `garch_tnu`, 5 % |
|---|---|---|
| VR = Var(S_t) / (K p (1 − p)) | **7,997** | 4,95 (C2), 6,36 (C1) |
| ρ̂ = (VR − 1) / (K − 1) | **0,4998** | 0,282 (wartość rejestrowa, próg) |
| SE, bootstrap blokowy L = 20 (bramka) | **0,0695** | — |
| SE, L = 10 / L = 40 (opis) | 0,0724 / 0,0661 | — |
| ρ̂ + 2 SE | **0,6388** | próg 0,282 |
| ρ̂ − 2 SE | 0,3608 (liczone z podanych wartości; nie jest częścią bramki) | — |
| (ρ̂ − 0,282) / SE | 3,1 (liczone z podanych wartości) | — |
| **Bramka (ρ̂ + 2 SE ≤ 0,282)** | **NIE PRZECHODZI** | |

Zakres zamiast fałszywej precyzji: ρ̂ ≈ 0,50 ± 0,14 (2 SE). SE jest mało wrażliwe na długość bloku (0,066–0,072), więc
wybór L = 20 nie rozstrzyga o wyniku. To nie jest sytuacja graniczna: sam punktowy ρ̂ (0,50) leży powyżej progu 0,282, a bramka
przeszłaby dopiero przy ρ̂ ≤ 0,282 − 2 SE ≈ 0,14.

**Zastrzeżenie o samej bramce (uwaga z przeglądu kodu, przeliczona osobno).** Bramka z pre-rejestracji jest ostrożna.
Na dziesięciu panelach syntetycznych z zależnością dokładnie jak w laboratorium (kontrola dodatnia, ρ = 0,8; ρ̂ średnio
0,29) SE bramkowe wynosi ok. 0,035, więc ρ̂ + 2 SE ≈ 0,36 i **bramka nie przechodzi na żadnym z 10 paneli**
(`bramka_na_kontrolach.py`, wynik w `bramka_na_kontrolach_output.txt`; dane syntetyczne, po przeglądzie, poza
bramką). Przy takim SE przeszłaby dopiero przy ρ̂ ≲ 0,21, a przy SE z prawdziwych danych (0,07) przy ρ̂ ≲ 0,14. Samo
„NIE PRZECHODZI” nie dowodzi więc, że zależność jest większa niż w laboratorium (tak brzmiało sformułowanie
w pre-rejestracji). Wniosek o większej zależności opieram na czym innym: punktowy ρ̂ = 0,50 leży 3,1 SE powyżej 0,282,
a dolny koniec przedziału (0,36) też. SE rośnie razem z poziomem ρ̂, więc większy SE na prawdziwych danych (0,07 wobec
0,035) nie jest osobną przesłanką. Konsekwencja dla przyszłości: kryterium zgodności, którym będzie oceniana powtórka
017 przed ewentualną 018, musi być takie, które MOŻE przejść przy zależności z laboratorium (patrz Rekomendacja, pkt 2).

### 4. Diagnostyka estymatora (wydruk przebiegu + diagnostyka dodatkowa)

| co | prawdziwe dane (017) | LV2 (dane syntetyczne) |
|---|---|---|
| dopasowań GARCH-t | 855 (15 monet × 57 refitów) | — |
| niezbieżnych | 0 | 0,00 % |
| **przy granicy zakresu parametrów** | **227 (26,5 %)** | 2,2 % (kontrola K7d: ≤ 5 %) |
| średnia persystencja α̂ + β̂ | 0,9688 | 0,972 |
| średnie ν̂ (grubość ogona) | 4,14 | 5,23 |

Diagnostyka dodatkowa (`diagnostyka_brzegu.py`, **po** obejrzeniu wyniku bramki, poza pre-rejestracją, tylko parametry
estymatora, bez trafień): **wszystkie 227 dopasowań przy granicy leżą na tej samej granicy, persystencji
α̂ + β̂ = 0,9999** (żaden inny parametr nie dotyka swojej granicy). Rozkład po monetach (z 57 refitów): DOGE 43, BTC 41,
ETH 39, BNB 37, ETC 15, NEAR 15, AVAX 11, XRP 8, DOT 8, FIL 8, ADA 2, SOL 0, LINK 0, LTC 0, BCH 0. Cztery monety
(DOGE, BTC, ETH, BNB) dają 160 z 227. Średnia persystencja 0,969 jest niemal taka jak w laboratorium, ale rozkład
jest inny: na prawdziwych danych część dopasowań ma zmienność prawie bez „zapominania” (wariancja bliska
niestacjonarnej), a reszta ma niższą persystencję. Czy to psuje kalibrację VaR, tej karty nie rozstrzyga (nie patrzy na trafienia).

### 5. Kontrole R8 (silnik pomiaru, ta sama funkcja co dla prawdziwych danych)

| kontrola | panele syntetyczne (15 × 2 100) | średnia ρ̂ | kryterium | wynik |
|---|---|---|---|---|
| dodatnia | ρ = 0,8 jak w LV2, ziarna 1…10 | 0,2917 (panele 0,262–0,322) | [0,242; 0,322] | **ZALICZONA** |
| ujemna | ρ = 0 (monety niezależne), ziarna 101…110 | 0,0000 (panele −0,008…0,006) | \|średnia\| ≤ 0,03 | **ZALICZONA** |

Obie kontrole zaliczone, więc silnik pomiaru odtwarza znaną zależność (≈ 0,28 przy ρ = 0,8) i nie widzi zależności,
której nie ma. Dodatnia kontrola daje 0,29 wobec wartości rejestrowej LV2 0,282: mieści się w kryterium i w szumie
dziesięciu paneli.

### 6. Przewidywanie z pre-rejestracji

Przewidziałem ρ̂ powyżej 0,282 i bramkę, która nie przechodzi (ok. 65 %); zaskoczeniem byłoby ρ̂ ≤ 0,24. **Wynik
potwierdził przewidywanie** (kierunkowo; liczbowej wartości nie zapisywałem). Zgodność z przewidywaniem jest sama
w sobie czerwoną flagą walidacji („wynik idealnie potwierdza oczekiwanie”), dlatego sprawdziłem go drugą drogą
i kontrolami (sekcja „Weryfikacja niezależna”).

### 7. Odstępstwa i dopiski względem pre-rejestracji (uczciwie)

1. **Wydruk ma jedną linię więcej niż lista z pkt. 5 pre-rejestracji:** diagnostykę GARCH (liczby dopasowań,
   niezbieżnych, przy granicy, średnia persystencja, średnie ν̂). Dopisałem ją w kodzie przed przebiegiem (po commicie
   pre-rejestracji `c9bee1c`, przed commitem kodu `9a4ea39` i przed przebiegiem; wyniku nie znałem). Dotyczy parametrów
   estymatora, nie trafień.
2. **Persystencja:** pre-rejestracja uzasadniała blok L = 20 persystencją „≈ 0,98”; w danych średnia to 0,9688 (z 27 %
   dopasowań na granicy 0,9999). SE jest niewrażliwe na L (0,066–0,072), więc bez znaczenia dla bramki; L = 20 zostaje.
3. **Po obejrzeniu wyniku bramki, poza pre-rejestracją i poza bramką, dodałem trzy rzeczy:** (a) drugą drogę
   (`druga_droga.py`), (b) diagnostykę granicy (`diagnostyka_brzegu.py`), (c) rachunek arytmetyczny dla 7 wyciętych dat
   (sekcja „Kogo NIE ma w zbiorze”). Żadna nie zmienia wyniku bramki i żadna nie liczy ani nie drukuje odsetka trafień.
4. **Kolejność:** pre-rejestracja `c9bee1c` (16:37 UTC) → kod i testy `9a4ea39` (16:44) → jeden przebieg (16:44–16:45)
   → opis wyniku. Plik wynikowy `raw_output.txt` zatwierdzam bez interpretacji; interpretacja jest tylko w tym README.
   Do werdyktu używam wyłącznie SE z ziarna rejestrowego 20261007; SE z ziarna 4242 (druga droga) służy tylko do
   sprawdzenia.
5. **Po przeglądzie kodu** (sekcja „Przegląd kodu 017”) dodałem: (d) `bramka_na_kontrolach.py` (bramka na panelach
   syntetycznych, bez prawdziwych danych) oraz (e) 11 testów do `tests/test_pomiar_rho_h.py`. **Kod modułów
   (`modele/pomiar_rho_h.py`, `dane/zwroty_dzienne.py`) nie został zmieniony**, więc liczby z `raw_output.txt` nadal
   pochodzą z kodu `9a4ea39`.

## Weryfikacja niezależna

Metody zgodne z `data:validate-data` i `data:statistical-analysis` (liczby przeliczone drugą drogą, bez przechodzenia
przez te same funkcje, tam gdzie to możliwe).

| # | sprawdzenie | wynik |
|---|---|---|
| 1 | **VR i ρ̂ drugą drogą** (`druga_droga.py`): własny kod panelu zwrotów (pandas, bez `panel_wspolny`), zamrożone `zbuduj_zrodla` + `prognoza(…, "garch_tnu", 0.05)` i `wklady_dzienne` z `symulacje/` oraz własny wzór VR | VR 7,997, ρ̂ 0,4998, dni oceny 1 691, panel 2 091 × 15 — **identyczne** z przebiegiem rejestrowym; diagnostyka GARCH też identyczna (855 / 0 / 227 / 0,9688 / 4,14) |
| 2 | **SE drugą drogą**: bootstrap blokowy zapisany inaczej (pętla, `np.take(…, mode="wrap")`), inne ziarno (4242) | SE 0,0675 wobec 0,0695; różnica 0,002 mieści się w szumie bootstrapu (przy B = 2 000 błąd samego SE ≈ 1,6 %, czyli ≈ 0,001 na każdy; różnicy dwóch ≈ 0,0016); ρ̂ + 2 SE = 0,635 wobec 0,639 |
| 3 | **Niezależność tej weryfikacji — ograniczenie.** Druga droga używa tego samego estymatora `dopasuj_garch_t` (jak z założenia musi: tak zapisano w LV2), więc *nie* sprawdza samego estymatora | estymator sprawdzono osobno w LV2 wobec pakietu `arch` 8.0.0 (README LV2, sekcja „Weryfikacja niezależna”); tu tego nie powtarzałem |
| 4 | Testy jednostkowe: parytet `prognoza_garch_tnu` z zamrożonym `zbuduj_zrodla` + `prognoza` (zgodność do 1e-12, p = 5 % i 1 %), test przecieku (zmiana zwrotów z dni ≥ t nie zmienia VaR do t), `hypothesis` dla VR i niezmienniczości na kolejność dni, test end-to-end (wydruk bez odsetka trafień i bez testów Kupca/Christoffersena, brak nowych plików) | 1 163 testy zielone (1 pominięty) w stanie `9a4ea39`; po przeglądzie dodano 11 testów: razem 1 174 testy zielone (1 pominięty); ruff i black zielone |
| 5 | Kontrole R8 (sekcja 5) | dodatnia i ujemna ZALICZONE |
| 6 | Arytmetyka: 2 098 − 7 = 2 091; 2 091 − 400 = 1 691; refitów (2 091 − 400) / 30 → 57 na monetę × 15 = 855; 2 091 + 31 = 2 122; VR 7,997 ∈ [1; K = 15] | spójne |
| 7 | Przegląd kodu 017 (niezależny agent, tylko do odczytu; sekcja „Przegląd kodu 017” niżej) | **Approve** — nic, co zmieniłoby podane liczby; 8 uwag (testy, bramka, drobne), opisane i załatwione niżej |
| 8 | Wiarygodność wielkości: ρ̂ ∈ [−1/(K−1); 1], VR ∈ [0; K] | 0,50 i 8,0 mieszczą się; to wartość pośrednia, nie skrajna |

### Przegląd kodu 017

Wykonał go niezależny agent (osobny podagent, tylko do odczytu). Polecenie ułożyłem według wymiarów skilla
`engineering:code-review` (korektność, przeciek informacji z przyszłości, testy, wydruk); sam agent skilla nie
wczytywał. Zakazałem mu uruchamiać prawdziwy przebieg i liczyć S_t albo odsetki trafień z prawdziwych danych (odczytał
tylko inwentarz panelu), więc przegląd nie zdradził nic z wyniku. **Werdykt agenta: Approve.**

Potwierdził (sprawdzenia własne agenta na danych syntetycznych): panel 2 091 × 15 w kolejności F2-1b i 7 wyciętych dat
zgodnych z pre-rejestracją, R16 i obcięcie do 2026-09-30, błąd przy duplikatach i cenach niedodatnich; prognoza
`prognoza_garch_tnu` identyczna bitowo z zamrożonym `zbuduj_zrodla` + `prognoza` (różnica względna 0,0; K = 3, p = 5 %
i 1 %, n = 525 i 541); brak patrzenia w przyszłość; `pomiar()` równe zamrożonemu `wklady_dzienne` i wzorowi VR z
`run_lv2` do 1e-12; bootstrap równy naiwnej pętli na tych samych losowaniach; bramka używa tylko L = 20, stałe jak w
pre-rejestracji; wydruk bez odsetka trafień i bez statystyk testu zbiorczego, bez zapisów na dysk; kontrole R8
uruchomione przez agenta dają te same wartości (0,2917 i 0,0000).

| # | waga | uwaga | co z nią zrobiłem |
|---|---|---|---|
| 1 | średnia (testy) | zestawienie trafień z prognozami (`r[START:] < q`) nie było testowane: mutant `r[START−1:−1] < q` przeżywał wszystkie testy | **Załatwione:** test `pomiar()` wobec zamrożonego łańcucha (`zbuduj_zrodla` + `prognoza` + `wklady_dzienne`, 1e-12), analogiczny test dla `kontrola()` i test „kontrola(0,8) > kontrola(0)”. Mutant przesunięcia teraz wywala testy. Mutant `>` w `kontrola` jest dla VR **równoważny** (Var(K − S) = Var(S)), więc żaden test wartości go nie wykryje; zostawiam to bez zmian |
| 2 | średnia (testy) | stałe z pre-rejestracji nieprzypięte (B_BOOT, ziarno, ziarna kontroli przeżywały zmianę) | **Załatwione:** test stałych |
| 3 | niska–średnia (testy) | struktura bootstrapu przy n niepodzielnym przez L (mutanty `n//blok`, brak skrócenia do n, `integers(0, n−1)`, SE z ddof = 0 przeżywały) | **Załatwione:** porównanie z naiwną pętlą dla n = 1 691, 97, 100 i L = 10, 20, 40 oraz test SE z ddof = 1; wszystkie te mutanty teraz wywalają testy |
| 4 | niska | granica bramki `<=` nietestowana | **Załatwione:** test równości (przechodzi) i `nextafter` (nie przechodzi) |
| 5 | średnia (projekt, nie kod) | bramka nie może przejść przy zależności z laboratorium (SE ≈ 0,035 → ρ̂ + 2 SE ≈ 0,36) | **Sprawdzone osobno i potwierdzone: 0 z 10 paneli** (`bramka_na_kontrolach_output.txt`); skutki w sekcji 3, w werdykcie i w rekomendacji |
| 6 | niska | `panel_wspolny` nie sprawdza, że panel kończy się na `do` | w tym przebiegu wydruk „Panel wspólny … 2026-09-30” pokazuje koniec = `do`; dla karty 018 potrzebny `assert panel.index[-1] == do`, bo `--ostatnie 2100` przy niepełnym październiku po cichu przesunęłoby okno |
| 7 | drobne | `do` bez strefy czasowej daje TypeError; ceny walidowane przed obcięciem do `do`; lista monet skopiowana z `run_f21b`, nic nie pilnuje zgodności; osobny generator losowy na każde L (pre-rejestracja mówi o jednym; bramka L = 20 liczy się pierwsza, więc bez wpływu) | nie zmieniam kodu, który dał wynik rejestrowy; trafia do Backlogu uwag do kodu (poprawić przy następnej zmianie) |
| 8 | proces | `raw_output.txt` (16:45:41) nowszy niż commit kodu (16:44:29); druga droga używa ziarna 4242; `diagnostyka_brzegu.py` jest post hoc | zgodne z sekcją 7 (odstępstwa); potwierdzam, że werdykt używa tylko ziarna rejestrowego |

## Kogo NIE ma w zbiorze

1. **Monet, które nie mają pełnej historii od 2021-01-01** (koszyk to 15 monet z pełnymi danymi, dobór po długości
   danych jak w F2-1b). Brakuje wycofanych (DQ1: 33 symbole z martwym ogonem) i młodszych. Wynik dotyczy tego koszyka,
   nie „rynku krypto”. Kierunku wpływu na ρ̂ nie znam i nie zgaduję: monety, które upadły, mogły mieć własne krachy
   (obniżyłoby to zależność) albo upadać w dniach krachu całego rynku (podniosłoby).
2. **7 dat wyciętych z panelu** (2022-02-26, -27, -28, 2022-03-01, 2022-04-01, -02, -03), bo u któreś z pięciu monet nie
   ma świec. Nie wiem, czy w tych dniach były przekroczenia wspólne, więc liczę granicę arytmetyczną, nie zgaduję:
   gdyby w tych 7 dniach wszystkie 15 monet przekroczyło VaR (S = 15), ρ̂ wyniosłoby ok. **0,57–0,58** (wzrost o ok.
   0,07–0,08; przy założonej średniej S między 0,75 a 1,5, czyli 5–10 % dni na monetę); gdyby żadna nie przekroczyła (S = 0), ok. **0,498** (spadek
   o 0,002). Włączenie tych dat mogłoby więc podnieść ρ̂ najwyżej o ok. 0,08, a obniżyć o ok. 0,002. Wycięcie
   **nie może uratować bramki**, a jeśli już, to ρ̂ zaniża, czyli błąd jest ostrożny wobec wyniku „nie przechodzi”.
   (Rachunek na VR i n z wydruku; nie dotyka danych i nie ujawnia poziomu trafień.)
3. **Sklejenia kalendarza:** po wycięciu dat następny wiersz po 2022-02-25 to 2022-03-02, a po 2022-03-31 to 2022-04-04.
   Filtr GARCH traktuje je jak dni sąsiednie (dwa sklejenia na ponad 2 000 wierszy). Ograniczenie, nie poprawione.
4. **Pierwszych 400 wierszy panelu** (2021-01-02 … 2022-02-05) jako okresu oceny: są wyłącznie historią do uczenia
   (jak w LV2). Ocena zaczyna się 2022-02-06, więc hossa 2021 nie jest oceniana, a krachy 2022 tak.
5. **Jednej historii.** Prawdziwe dane to jedna realizacja; VR zależy od kilku dni wspólnych krachów, więc SE z bootstrapu
   blokowego (blok 20 dni) uwzględnia tę niepewność tylko częściowo. Mała wrażliwość SE na L (0,066–0,072) uspokaja,
   ale nie zastępuje drugiej historii.
6. **Rozdzielenia zależności i poziomu trafień.** VR z nominalnym p miesza oba (pre-rejestracja, pkt. 6). Karta nie
   mierzy odsetka trafień, więc nie wiem, ile z nadwyżki VR nad laboratorium (8,0 wobec 4,95) to prawdziwa zależność.
7. **Innych poziomów p i innych prognoz** (VaR 1 %, okno 60 dni, EWMA, HAR): poza zakresem karty.

## Co na plus (+) / Co na minus (−)

**Na plus (+)**

- Bramka rozstrzygnięta jednoznacznie: ρ̂ leży ok. 3,1 SE powyżej progu, wynik nie zależy od wyboru długości bloku
  (SE 0,066–0,072), a niezależny kod daje te same liczby (VR i ρ̂ identyczne, SE w granicach szumu).
- Kolejność rygoru zachowana: pre-rejestracja w gicie → kod i testy → jeden przebieg → opis; kontrole R8 zaliczone;
  wydruk bez odsetka trafień (pilnuje go test); licznik „ryzyko 2021+” nietknięty (zostaje 0).
- Karta zrobiła to, do czego służy: zatrzymała 018 przed uruchomieniem testu, którego zachowanie przy takiej zależności
  jest nieznane, bez zużycia budżetu licznika.
- Bonus opisowy: znaleziona rozbieżność estymatora z laboratorium (27 % dopasowań przy granicy persystencji wobec
  2,2 %), której nie wykryłaby żadna kontrola na danych syntetycznych.

**Na minus (−)**

- Okno C2 nie domyka się (2 091 < 2 100): przebieg dotyczy 1 691 dni, nie 1 700. Zapowiedziane powtórzenie na
  końcowym oknie (po październiku 2026) jest konieczne.
- Nie rozdzielono zależności od poziomu trafień (celowo); „VR większe niż w laboratorium” to dokładnie tyle, ile wiemy.
- Przewidywanie było tylko kierunkowe, a wynik je potwierdza. To czerwona flaga, którą łagodzą drugi kod, kontrole R8
  i niewielki wpływ wyciętych dat, ale nie znosi.
- Diagnostyka granicy, druga droga i rachunek dla wyciętych dat powstały **po** obejrzeniu wyniku bramki. Są opisowe i nie
  zmieniają bramki, ale nie były pre-rejestrowane.
- Druga droga dzieli estymator `dopasuj_garch_t` z przebiegiem rejestrowym (wiersz 3 weryfikacji), więc nie
  chroni przed błędem estymatora; tę ochronę dał tylko LV2.
- Autor kodu, autor pre-rejestracji i autor werdyktu to ta sama sesja Claude (R14 + delegacja); drugą parą oczu jest
  przegląd kodu (wiersz 7, Approve) i Twój przegląd karty.
- Bramka z pre-rejestracji jest ostrożna: nie przechodzi nawet przy zależności jak w laboratorium (0 z 10 paneli
  kontrolnych), więc jej niepowodzenie samo niczego nie dowodzi; wniosek stoi na ρ̂ − 2 SE = 0,36 > 0,282. Tę wadę
  projektu bramki zauważył dopiero przegląd, po przebiegu; nie zmieniam bramki wstecz, tylko opisuję i naprawiam
  kryterium dla powtórki.
- Jedna historia, jeden koszyk przeżywców, jedna wartość p.

## Werdykt

**Caveats.** Podpisuje Claude (R14: skrypt tylko drukuje liczby i wynik bramki). To werdykt modelu po opisanych
sprawdzeniach, nie przegląd człowieka; decyzje bramkowe są po stronie użytkownika.

Wynik mechaniczny reguł z pre-rejestracji: **okno C2 NIE DOMYKA SIĘ (2 091 < 2 100); bramka zależności NIE PRZECHODZI
(ρ̂ + 2 SE = 0,64 > 0,282); kontrole R8 ZALICZONE.** Pomiar jest wiarygodny w tym, co mierzy (VR i ρ̂ dla tego koszyka,
tej prognozy i tego okresu); to **Caveats**, nie Ready, z powodu ograniczeń wymienionych wyżej, z których najważniejsze:

1. okno niepełne (1 691 zamiast 1 700 dni), powtórzenie na końcowym oknie jest zapowiedziane z góry;
2. VR miesza zależność z poziomem trafień, więc „większa zależność” to hipoteza, nie pomiar;
3. koszyk 15 monet z pełną historią, jedna historia, jedno p;
4. weryfikacja drugą drogą nie obejmuje samego estymatora GARCH (patrz LV2);
5. bramka z pre-rejestracji jest ostrożna (nie przechodzi też przy zależności jak w laboratorium), więc wniosek
   o większej zależności opiera się na ρ̂ − 2 SE = 0,36 > 0,282, a nie na samym wyniku bramki.

To **nie** jest Revision: obie kontrole R8 zaliczone, druga droga potwierdza liczby, a ewentualna korekta wyciętych dat
może zmienić ρ̂ co najwyżej o ok. 0,08 w górę albo 0,002 w dół.

## Wniosek

1. Na prawdziwych danych 15 monet trafienia VaR 5 % są bardziej zsynchronizowane niż w laboratorium LV2: VR 8,0 wobec
   4,95 (ρ̂ ≈ 0,50 wobec 0,28). Warunek przeniesienia nr 2 z LV2 **nie jest spełniony** (wniosek stoi na ρ̂ − 2 SE = 0,36 > 0,282, nie na
   samej bramce, która jest ostrożna).
2. **018 nie startuje** (zależność ponad laboratorium oraz okno 2 091 / 2 100).
3. Wynik LV2 (fałszywy alarm 5,5 %, moc 99,5 %) pozostaje prawdziwy dla świata, w którym został zmierzony; nie wiemy
   jeszcze, czy przeniesie się na świat o VR ≈ 8. Trzeba to zmierzyć w laboratorium, nie zgadywać.
4. Estymator GARCH-t na prawdziwych cenach często „dobija do ściany” (27 % dopasowań, 0,9999), a w laboratorium prawie
   nigdy (2,2 %). Gdyby zastosować do tych danych próg kontroli K7d z LV2 (≤ 5 % przy granicy), nie zostałby
   spełniony. Dla BTC, ETH i BNB granicę osiąga 65–72 % refitów.

## Rekomendacja

1. **Zlecić LV2c jako kartę 019** (zrobione w ramach delegacji, patrz niżej). Nowa komórka laboratoryjna: 15 monet ×
   1 700 dni oceny po 400 historii (jak C2) z (i) zależnością, której VR dla `garch_tnu` przy 5 % wynosi ok. 8,0
   (cel: VR, nie ρ, bo to VR zmierzyliśmy), np. przez wspólny szok zmienności, oraz (ii) trwałością zmienności bliską
   granicy 0,9999 w części monet. Pytanie: czy rozmiar testu zbiorczego (reguła K) zostaje ≤ 10 % i czy moc wobec
   σ − 10 % zostaje ≥ 80 %. Własna pre-rejestracja, bez licznika (dane syntetyczne).
2. **018 zostaje wstrzymana** (`czeka_na_decyzje`). Warunki wznowienia: (a) LV2c pokazuje, że reguła K jest
   mierzalna przy VR ≈ 8; (b) dane za październik 2026 domykają okno 2 100 wierszy; (c) powtórka 017 na końcowym oknie
   (ten sam wariant, tą samą funkcją, wynik nadpisuje dzisiejszy) daje wynik zgodny z założeniami LV2c. „Zgodny”
   znaczy kryterium, które MOŻE przejść przy zależności z LV2c (np. ρ̂ w przedziale ± 2 SE od wartości z LV2c, SE z
   tego samego bootstrapu), zapisane w pre-rejestracji; obecna bramka ρ̂ + 2 SE ≤ 0,282 nie nadaje się, bo nie
   przechodzi nawet w laboratorium (sekcja 3). W okresie przejściowym 018 wymaga też `assert panel.index[-1] == do`.
3. **Szerszego koszyka nie wybieram.** ρ̂ jest własnością rynku, nie liczby monet, a młodsze monety nie mają
   2 100 dni. Nie wykluczam go na zawsze: to opcja, jeśli LV2c pokaże, że test jest niemierzalny przy VR ≈ 8.
4. Zmiany w kodzie estymatora (np. łagodniejsza górna granica persystencji) **nie** proponuję: LV2 wymaga „dokładnie
   `dopasuj_garch_t`”, a zmiana estymatora po obejrzeniu wyniku byłaby rozwidleniem. Obserwacja o granicy 0,9999
   trafia do projektu LV2c jako jeden z parametrów generatora.

### Decyzje wykonawcy (delegacja 2026-10-07)

| # | decyzja | dlaczego | jak cofnąć |
|---|---|---|---|
| 1 | **Zlecam LV2c (karta 019)**, unieważniając na tym punkcie decyzję 5 z `STATUS.md` („nie zlecam”) — jej własny wyzwalacz (i) właśnie zadziałał | decyzja 5 zakładała zlecenie LV2c dopiero po wyniku 017 pokazującym ρ̂ + 2 SE > 0,282; wynik jest 0,64. To autonomia badawcza (dane syntetyczne, bez licznika) | zmień status karty 019 na `odrzucone`; 018 zostaje wstrzymana na stałe (albo szerszy koszyk) |
| 2 | **018 → `czeka_na_decyzje`**, nie `odrzucone` | warunki wznowienia są zapisane (wyżej); odrzucenie byłoby przedwczesne | Twój wybór: `odrzucone`, jeśli nie chcesz rundy na danych |
| 3 | Licznik „ryzyko 2021+” zostaje **0** | karta 017 jest opisowa (nic nie testuje) | — |

## Użyte skille

W repozytorium beta nie ma rejestru użyć skilli (jak `tools/skill_audit.py` w alpha), więc godziny pochodzą z zapisu
sesji (czas UTC). Skille były wczytane w tej samej sesji co ta karta, **przed** pre-rejestracją `c9bee1c` (16:37) i
przed przebiegiem; dla 017 nie wczytywałem ich ponownie, tylko stosowałem ich listy kontrolne z kontekstu sesji:

| skill | kiedy | co wniósł do 017 |
|---|---|---|
| `clas5-runda` | wczytany 2026-10-06 16:52, przed pre-rejestracją | procedura rundy: pre-rejestracja przed wynikiem, katalog rundy, README z „Co na plus / Co na minus” i werdyktem, wiersz w `runs/INDEX.md` i wniosek skumulowany z liczbą |
| `data:validate-data` | 2026-10-07 10:59, przed pre-rejestracją | pytanie „kogo NIE ma w zbiorze”, przeliczenie drugą drogą, czerwona flaga „wynik idealnie potwierdza oczekiwanie” (sekcje „Weryfikacja niezależna”, „Kogo NIE ma w zbiorze”, „Wynik”, pkt. 6) |
| `data:statistical-analysis` | 2026-10-07 10:59, przed pre-rejestracją | zakres zamiast fałszywej precyzji (ρ̂ ≈ 0,50 ± 0,14), SE z bootstrapu blokowego zamiast samego progu, uwaga na wiele porównań (licznik opisowy, poza licznikami) |
| `engineering:code-review` | 2026-10-07 10:59, przed pre-rejestracją | wymiary przeglądu (korektność, edge-case'y, testy) w poleceniu dla agenta przeglądu — sekcja „Przegląd kodu 017”; agent sam skilla nie wczytywał |

**Luki (uczciwie).**

- `clas5-quant` i `quant-strategy-catalog` (CLAUDE.md, sekcja „Skille”) nie były wczytane; karta jest opisowa
  (pomiar warunku przeniesienia, bez hipotezy o rynku), więc metodologię brałem z `CLAUDE.md` i `docs/PRD.md` bez skilla.
  To formalna luka; nie sprawdzałem, co skille by dodały.
- `dataviz`: bez wykresów (same tabele), więc niepotrzebny.
