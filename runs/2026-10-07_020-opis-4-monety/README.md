# 020 — opis zależności trafień VaR 5 % dla BTC, ETH, SOL, BNB (karta opisowa, bez oceny prognozy)

## Metadane

- Karta: `zadania/020-opis-zaleznosci-4-monety.md`. Zlecenie: decyzja użytkownika z 2026-10-07 („rób tylko prognozy na eth btc sol, bnb”,
  `STATUS.md`, „Decyzje użytkownika”). Poprzednik: 017 (`runs/2026-10-07_017-inwentarz-i-rho/`).
- Licznik: **opisowy, poza licznikami.** „Ryzyko ogona (VaR/ES) 2021+” **zostaje 0**: nic tu nie testuje prognozy. Rejestr zwrotów
  alpha nietknięty.
- Kod: `modele/opis_rho_h.py` + `tests/test_opis_rho_h.py`, commit `35eb867` (miara jest ta sama co w 017, `modele/pomiar_rho_h.py`
  bez zmian). Pełny zestaw testów przed commitem: 1 180 przeszło, 1 pominięty.
- Komenda (po zatwierdzeniu pre-rejestracji): `python -m modele.opis_rho_h > runs/2026-10-07_020-opis-4-monety/raw_output.txt`.
- Status tego pliku: pre-rejestracja (commit `afe6791`, przed przebiegiem) + wynik z przebiegu 2026-10-07.

## Pre-rejestracja (zapisana przed przebiegiem)

### Wnioski skumulowane, które dotyczą tej karty

`[2026-10-07, 017]`: na 15 monetach trafienia VaR 5 % są zsynchronizowane silniej niż w laboratorium (VR 8,0 wobec 4,95; ρ̂ 0,50, SE
0,07), a w 27 % dopasowań GARCH-t staje na granicy persystencji. `[2026-10-07, LV1]`: pojedyncza moneta wykrywa zaniżenie σ tylko w
10–17 % przypadków, więc siła testu zależy od liczby monet. Wynika z tego projekt tej karty: po zawężeniu koszyka do 4 monet liczby z
017 i LV2 nie dotyczą już tego, o co pytamy, więc trzeba zmierzyć zależność dla tej czwórki, zanim ktokolwiek policzy moc testu.

### R1 — mechanizm jednym zdaniem

Jeśli BTC, ETH, SOL i BNB przekraczają VaR w tych samych dniach (krach dotyka wszystkich naraz), to cztery monety niosą mniej niezależnej
informacji, niż mówi ich liczba, więc test zbiorczy ma przy K = 4 mniejszą moc i inne fałszywe alarmy niż w LV2; karta mierzy tę
zależność, nie oceniając samych trafień. (Pomiar warunku, nie hipoteza o rynku; żadnej „drugiej strony” handlowej nie zakłada.)

### R2 — zbiór informacyjny × formuła × target × horyzont

- zbiór informacyjny: dzienne log-zwroty BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT do dnia t − 1 (świece 1d Binance USDT-M, od 2021-01-01,
  obcięte na 2026-09-30 włącznie, jak 017);
- formuła: ta sama co w 017 i w przyszłej 018: `dopasuj_garch_t`, zerowa średnia, refit co 30 dni, okno rosnące od 400 dni, ogon t_ν̂,
  wariancja początkowa z próby;
- target: S_t = liczba monet (0…4) z przekroczeniem VaR 5 % w dniu t (trafienie = `r < q`); ocenia się wyłącznie **rozrzut** S_t,
  nie jej średnią;
- horyzont: 1 dzień.

### R3 — mierzalność

Pomiar opisowy, bez testu hipotezy, więc rachunek mocy nie dotyczy. Precyzja (SE) jest częścią wyniku: przy K = 4 jest ona znacznie
gorsza niż przy K = 15, co jest jednym z powodów tej karty (patrz „Przewidywanie”). Efekt zależności na liczbę niezależnych monet
opisuje wzór przybliżony K / (1 + (K − 1) ρ): przy ρ = 0,5 cztery monety niosą informację ok. 1,6 niezależnej monety dziennie (R12).
To opis, nie kryterium.

### R4 — jedna zmienna, licznik, reguła STOP

- Jedna zmienna: lista monet (4 zamiast 15). Reszta jak w 017.
- Stałe, których po obejrzeniu wyniku nie ruszam: p = 5 %; długość bloku bootstrapu L = 20 (L = 10 i 40 to tylko opis wrażliwości);
  B = 2 000; ziarno 20261007; lista monet; definicja trafienia; kryteria kontroli (niżej).
- Jeden przebieg. Brak powtórek na tym oknie. Powtórzenie na końcowym oknie (dane za październik 2026) należy do pre-rejestracji 018,
  nie do tej karty.
- Reguła STOP: brak pliku, NaN w panelu wspólnym albo niezbieżne dopasowanie zatrzymuje przebieg z komunikatem; niczego nie omijam po
  cichu.

### Dane (inwentarz sprawdzony przed pre-rejestracją, bez żadnej prognozy)

`panel_wspolny(["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT"])` daje **2 091 wierszy**, 2021-01-02 … 2026-09-30, 7 dat wyciętych. BTC, ETH
i BNB mają po 2 099 świec, SOL ma 2 094 (te same pięć dziur co w 017: 2022-02-26…28 i 2022-04-01…02). Panel jest więc dokładnie
tym samym zbiorem dat co panel 15 monet z 017, a dla każdej monety dopasowania GARCH-t są **te same** co w 017 (dopasowanie danej monety
zależy tylko od jej własnych zwrotów z tych dat). Pełny inwentarz pojawi się w `raw_output.txt`.

### Co już widziałem (jawnie, bo wpływa na to, co jest „nowe”)

- z 017: agregaty dla 15 monet (VR 7,997; ρ̂ 0,4998; SE 0,0695; 227 z 855 dopasowań przy granicy);
- z `diagnostyka_brzegu_output.txt` (017, po wyniku): rozkład dopasowań przy granicy po monetach. Dla naszej czwórki: BNB 13 + 24 = 37,
  BTC 11 + 30 = 41, ETH 9 + 30 = 39, SOL 0 → **117 z 228** (51 %);
- nie widziałem: S_t dla żadnej monety ani dla żadnego podzbioru, żadnego odsetka trafień.

Dlatego liczba dopasowań przy granicy (117 z 228) **nie jest nową informacją**; służy jako kontrola spójności z 017. Nowa jest jedna
rzecz: VR i ρ̂ dla K = 4. To drugi odczyt tych samych danych (podzbiór panelu z 017); służy do kalibracji laboratorium 019, nie do
potwierdzenia wyniku 017.

### Pomiar

Funkcja `modele.pomiar_rho_h.pomiar` bez zmian (parytet z zamrożonym `symulacje.prognozy_lv2` pilnuje `tests/test_pomiar_rho_h.py`).
Wydruk (`modele/opis_rho_h.py`):

1. inwentarz i panel (jak 017);
2. K, dni oceny, liczba dopasowań, niezbieżnych, przy granicy, średnia persystencja i ν̂;
3. VR = Var(S_t; ddof = 1) / (K p (1 − p)), ρ̂ = (VR − 1) / (K − 1), SE (L = 20), wrażliwość SE (L = 10, 40);
4. przedział ρ̂ ± 2 SE i odpowiadający mu przedział VR (to **opis**: bez progu, bez bramki, bez okna C2);
5. kontrola spójności z 017: oczekiwane 228 dopasowań i 117 przy granicy;
6. kontrole R8 (niżej).

Wydruk **nie zawiera** odsetka trafień, statystyk testu zbiorczego, testów Kupca ani Christoffersena, progu bramki, wyniku bramki ani
okna C2. (Liczba 0,282 pojawia się wyłącznie jako wartość oczekiwana kontroli dodatniej R8, nie jako próg.) Test jednostkowy pilnuje, że tych napisów i odsetka trafień w wydruku nie ma. Wynik idzie wyłącznie na stdout.

Ograniczenie, zapisane z góry (jak w 017): VR przy nominalnym p miesza zależność trafień z poziomem trafień; ich rozdzielenie
wymagałoby odsetka trafień, którego karta nie liczy.

### Kontrole R8 (silnik pomiaru dla K = 4)

Panele syntetyczne z `generuj_panel` (4 monety × 2 091 dni, ν = 5, GARCH (0,08; 0,90), σ̄ = 4 %), ta sama funkcja pomiarowa co dla
prawdziwych danych, **40 paneli na kontrolę**: ziarna 1…40 (dodatnia, ρ = 0,8) i 101…140 (ujemna, ρ = 0).

**Pilotaż** (na syntetycznych danych, przed pre-rejestracją; ziarna rozłączne od rejestrowych: 5001…5020 dodatnia, 5101…5120 ujemna):
dodatnia: średnia ρ̂ 0,2767, odchylenie panelu 0,054 (zakres 0,171…0,382); ujemna: średnia 0,0087, odchylenie 0,027 (zakres
−0,035…0,064). Przy K = 4 wynik z pojedynczego panelu jest więc ok. 2,5 razy bardziej rozrzucony niż przy K = 15 (tam ok. 0,02), dlatego kryteria są
szersze niż w 017 i oparte na średniej z 40 paneli (SE średniej ≈ 0,009 i ≈ 0,004).

- **Dodatnia:** |średnia z 40 paneli − 0,282| ≤ 0,03 (0,282 = wartość rejestrowa LV2 dla `garch_tnu`, C2, 5 %).
- **Ujemna:** |średnia z 40 paneli| ≤ 0,02.

Niezaliczenie którejś kontroli = silnik nie nadaje się jako cel kalibracji; wynik prawdziwych danych jest wtedy podany, ale werdykt
karty to Revision.

### Przewidywanie (zapisane przed wynikiem)

- Spójność z 017: ZGODNA (228 dopasowań, 117 przy granicy); prawdopodobieństwo 95 %.
- Kontrole R8: obie ZALICZONA (pilotaż mieści się w kryteriach z zapasem); 90 %.
- ρ̂ dla czwórki **w przedziale 0,40…0,70**, punkt ok. 0,55; P(ρ̂ > 0,282) ≈ 90 %. Powód (rozumowanie a priori, nie pomiar): BTC, ETH,
  SOL i BNB to największe, najbardziej skorelowane ze sobą monety, a trzy z nich mają prognozę z granicą persystencji (powolna
  adaptacja do nowej zmienności), więc w dniach krachu trafiają razem.
- SE (L = 20) ≈ 0,09 (zakres 0,05…0,14): w pilotażu laboratoryjnym odchylenie ρ̂ między panelami to 0,054, a prawdziwe dane mają
  silniejszą zależność (większe ρ̂ daje większy rozrzut), więc SE powinno być wyższe. Zaskoczeniem byłoby SE < 0,04.

### Co wynika z którego wyniku (zapisane z góry)

| wynik | zdanie w karcie / następny krok |
|---|---|
| spójność NIEZGODNA | wyniku nie interpretować; wyjaśnić różnicę dopasowań wobec 017; 019 nie rusza |
| kontrola R8 NIEZALICZONA | werdykt Revision; liczby podane, ale nie służą jako cel kalibracji dla 019 |
| kontrole i spójność ZALICZONE | VR (K = 4) i ρ̂ są celem kalibracji laboratorium 019; tolerancję wokół celu ustala pre-rejestracja 019, nie ta karta |
| SE (L = 20) > 0,15 | cel słabo wyznaczony: propozycja dla 019, żeby użyła co najmniej trzech scenariuszy zależności (dolny, środkowy i górny koniec ρ̂ ± 2 SE) zamiast jednego punktu; ostateczny projekt w pre-rejestracji 019 |
| dolny koniec ρ̂ − 2 SE ≤ 0,282 | dla czwórki nie mamy dowodu, że zależność przekracza laboratorium; 019 obejmuje wtedy także scenariusz LV2 (ρ = 0,8, bez wspólnego szoku) dla K = 4 |
| dolny koniec ρ̂ − 2 SE > 0,282 | jak dla 15 monet: 019 musi odtworzyć zależność ponad laboratorium |

W każdym przypadku następny krok to 019 przeliczona na K = 4, a nie 018. Karta 020 nie decyduje o uruchomieniu żadnej rundy.

## Wynik w skrócie — prostym językiem

**Co zrobiliśmy.** To samo, co w karcie 017, ale tylko dla czterech monet, które wskazałeś: BTC, ETH, SOL, BNB. Prognoza ryzyka
to **VaR 5 %**, czyli strata, którą moneta ma przekraczać w 5 dniach na 100 (liczy ją model GARCH-t, dopasowywany od nowa co 30 dni).
Nie sprawdzaliśmy, czy prognoza jest dobra, i nie liczyliśmy, jak często moneta ją przekracza. Zmierzyliśmy jedno: czy te cztery
monety przekraczają VaR **w tych samych dniach** (znak **ρ**).

**Wynik.**

- **ρ̂ = 0,42** (przedział ±2 błędy standardowe: 0,24–0,60). W laboratorium LV2 było 0,28, w karcie 017 dla 15 monet 0,50. Przedział
  obejmuje obie liczby, więc **dla czwórki nie umiemy powiedzieć**, czy zależność jest większa niż w laboratorium. Punkt leży
  wyżej niż laboratorium, ale niepewność jest duża.
- **Błąd standardowy 0,09** wobec 0,07 przy 15 monetach. Cztery monety to mało: wyniki z tak małego koszyka są mniej dokładne.
- **Ile „niezależnych” monet mamy dziennie.** Wzór przybliżony K / VR daje 4 / 2,26 = **ok. 1,8** (dla 15 monet z 017: 15 / 8,0 =
  ok. 1,9). Czyli cztery monety niosą dziennie mniej więcej tyle informacji o ogonie, co 1,8 monety niezależnej (R12); 11 dodatkowych
  monet z 017 prawie nic tej liczby nie zmieniało. To obserwacja opisowa, **nie** dowód, że test na czterech monetach ma tę samą moc
  co na piętnastu: moc trzeba zmierzyć (karta 019).
- **Spójność z 017: zgodna.** Te same dopasowania modelu co w 017: 228, z czego 117 (51 %) przy granicy „pamięci zmienności” 0,9999
  (laboratorium: 2,2 %). Ta liczba nie jest nową informacją, tylko dowodem, że pomiar nie rozjechał się z 017.
- **Kontrole silnika zaliczone** na syntetycznych panelach 4 × 2 091 dni: wiadoma zależność daje średnią ρ̂ 0,286 (oczekiwane 0,282),
  jej brak daje 0,010 (oczekiwane 0).

**Zdanie rozstrzygające.** Zależność trafień dla BTC, ETH, SOL i BNB to ρ̂ = 0,42 (VR = 2,26), ze zbyt dużą niepewnością (SE 0,09),
żeby odróżnić ją od laboratorium (0,28) albo od 15 monet (0,50); laboratorium 019 dla K = 4 ustawia się na VR = 2,26 i obejmuje też
scenariusz z LV2. Żadna runda na danych nie startuje.

**Czego z tego NIE wolno wyciągać.** To nie jest ocena prognozy. VR przy nominalnym 5 % miesza zależność z poziomem trafień (odsetka
trafień celowo nie liczono), więc „zależność 0,42” to hipoteza robocza. To także nie jest drugi, niezależny dowód do wyniku 017: to
ten sam zbiór dat i te same dopasowania, tylko podzbiór monet.

## Wynik

Zrobione 2026-10-07. Komenda: `python -m modele.opis_rho_h > runs/2026-10-07_020-opis-4-monety/raw_output.txt` (jeden przebieg, wydruk
w `raw_output.txt`). Kod `35eb867` (poprawki po przeglądzie: `c61555b`), pre-rejestracja `afe6791`.

### 1. Dane i dopasowania

| pozycja | wartość |
|---|---|
| panel wspólny | 2 091 wierszy, 2021-01-02 … 2026-09-30, 4 monety, 7 dat wyciętych |
| dni oceny (po 400 dniach historii) | 1 691 (ocena od 2022-02-06) |
| dopasowań GARCH-t / niezbieżnych / przy granicy | 228 / 0 / 117 (51 %) |
| średnia persystencja α + β / średnie ν̂ | 0,9703 / 4,14 |
| spójność z 017 (oczekiwane 228 i 117) | **ZGODNA** |

### 2. Zależność trafień

| miara | wartość |
|---|---|
| VR = Var(S_t) / (K p (1 − p)) | **2,264** |
| ρ̂ = (VR − 1) / (K − 1) | **0,4213** |
| SE, bootstrap blokowy L = 20 (B = 2 000, ziarno 20261007) | **0,0911** |
| SE wrażliwość (opis): L = 10 / L = 40 | 0,0931 / 0,0909 |
| ρ̂ ± 2 SE | [0,2391; 0,6035] |
| odpowiadający przedział VR | [1,717; 2,811] |
| laboratorium LV2 (`garch_tnu`, 5 %, C2): ρ_h / VR przy K = 4 wg wzoru 1 + (K − 1) ρ | 0,282 / 1,85 |
| 017, 15 monet: ρ̂ (SE) | 0,4998 (0,0695) |

Różnica ρ̂ (15 monet) − ρ̂ (4 monety) = 0,08, mniej niż jeden SE czwórki (0,09). Obie liczby liczone są na tych samych datach, więc to
nie jest test różnicy, tylko opis: nie ma podstaw, by twierdzić, że czwórka jest mniej albo bardziej zależna niż piętnastka.

### 3. Kontrole R8 (40 paneli syntetycznych 4 × 2 091 dni, ziarna rozłączne od pilotażu)

| kontrola | średnia ρ̂ | sd panelu | kryterium | wynik |
|---|---|---|---|---|
| dodatnia (ρ = 0,8, oczekiwane ≈ 0,282) | 0,2859 | 0,0588 | \|średnia − 0,282\| ≤ 0,03 | **ZALICZONA** |
| ujemna (ρ = 0, oczekiwane ≈ 0) | 0,0101 | 0,0209 | \|średnia\| ≤ 0,02 | **ZALICZONA** |

Uwaga: średnia kontroli ujemnej (0,0101) jest o ok. 3 SE średniej (0,003) powyżej zera, a pilotaż dał 0,0087. Przyczyny nie badałem;
jedna z możliwych to poziom trafień estymowanego modelu różny od nominalnego 5 % (VR przy nominalnym p miesza go z zależnością, patrz
„Co na minus”). Kryterium (≤ 0,02) jest spełnione z zapasem 0,01. Przy odczycie ρ̂ = 0,42 trzeba pamiętać, że tyle (ok. 0,01, czyli
ułamek SE) może siedzieć w wyniku niezależnie od prawdziwej zależności.

### 4. Przewidywania z pre-rejestracji a wynik

| przewidywanie | wynik | trafione? |
|---|---|---|
| spójność z 017: ZGODNA (95 %) | ZGODNA | tak |
| kontrole R8 obie ZALICZONE (90 %) | obie ZALICZONE | tak |
| ρ̂ w przedziale 0,40…0,70, punkt ok. 0,55 | 0,4213 | przedział tak (przy dolnym brzegu); punkt chybiony o 0,13, czyli ok. 1,4 SE |
| P(ρ̂ > 0,282) ≈ 90 % | 0,4213 > 0,282; ale ρ̂ − 2 SE = 0,239 < 0,282 | punkt tak, dowód nie |
| SE (L = 20) ≈ 0,09 (zakres 0,05…0,14) | 0,0911 | tak |

Mój punkt (0,55) był za wysoki: rozumowanie a priori („największe, najbardziej skorelowane monety trafiają razem”) przeszacowało
zależność trafień. Trafienia w VaR zależą od tego, czy prognoza zmienności nadąża za szokiem, a nie tylko od korelacji cen.

### 5. Co wynika z którego wyniku (reguły zapisane z góry)

- **Kontrole i spójność ZALICZONE** → VR (K = 4) = 2,264 i ρ̂ = 0,4213 są celem kalibracji laboratorium 019. Tolerancję wokół celu
  ustala pre-rejestracja 019, nie ta karta.
- **ρ̂ − 2 SE = 0,239 ≤ 0,282** → dla czwórki nie mamy dowodu, że zależność przekracza laboratorium; 019 obejmuje także scenariusz LV2
  (ρ = 0,8, bez wspólnego szoku) dla K = 4.
- **SE = 0,091 ≤ 0,15** → wiersz o trzech scenariuszach zależności nie jest wymagany; czy 019 użyje szerszego zakresu niż jeden
  punkt, rozstrzyga jej pre-rejestracja.
- Następny krok: 019 przeliczona na K = 4. Karta 020 niczego nie uruchamia.

## Weryfikacja niezależna

**Druga droga** (`druga_droga.py`, wynik `druga_droga_output.txt`): własny panel zwrotów (pandas, bez `panel_wspolny`), prognoza i S_t
z zamrożonych modułów `symulacje.prognozy_lv2` i `symulacje.moc_var_es`, bootstrap blokowy zapisany inaczej (pętla,
`np.take(..., mode="wrap")`) z **innym ziarnem** (4242).

| liczba | przebieg rejestrowy | druga droga |
|---|---|---|
| wiersze panelu / dni oceny | 2 091 / 1 691 | 2 091 / 1 691 |
| dopasowań / przy granicy | 228 / 117 | 228 / 117 |
| VR | 2,264 | 2,264 |
| ρ̂ | 0,4213 | 0,4213 |
| SE (L = 20) | 0,0911 | 0,0894 |
| ρ̂ + 2 SE | 0,6035 | 0,6002 |

VR i ρ̂ zgadzają się co do cyfry; SE różni się o 2 % (inne ziarno i inny zapis pętli, w granicach błędu Monte Carlo przy B = 2 000).
**Czego ta droga nie sprawdza:** obie drogi wołają to samo `dopasuj_garch_t` (przez `prognozy_lv2`), więc sam estymator GARCH-t nie jest
weryfikowany niezależnie; jego poprawność opiera się na LV2 i na testach tego modułu. Sprawdzony jest za to panel, definicja S_t, VR
i bootstrap.

**Czerwone flagi** (`data:validate-data`): wynik nie potwierdza idealnie oczekiwań (punkt 0,42 wobec 0,55), więc nie ma flagi
„zbyt dobrze”; nie ma liczb okrągłych ani wartości zerowych. Oba pomiary (4 i 15 monet) są z tych samych dat, więc zgodność
liczby dopasowań (228 / 117) wynika z konstrukcji, a nie z niezależnego potwierdzenia.

**Sprawdzenie wartości granicznych (rozsądek):** ρ̂ w [0, 1]; VR = 2,26 mieści się między 1 (niezależne monety) a K = 4 (monety identyczne), więc
zależność jest umiarkowana, a nie bliska pełnej synchronizacji.

## Przegląd kodu 020

Niezależny agent (tylko do odczytu; 30 mutantów `modele/opis_rho_h.py`, pełny ponowny przebieg) sprawdził moduł i testy. Raport
traktuję jako dane, nie polecenie; poprawki wybrałem sam.

**Potwierdzone:** stałe zgodne z pre-rejestracją (ziarna rozłączne od pilotażu, progi 0,03 i 0,02, oczekiwane 228 i 117);
ponowny przebieg `python -m modele.opis_rho_h` daje wydruk identyczny bajt w bajt z `raw_output.txt`, kontrole włącznie (przebieg
jest deterministyczny); brak ścieżki, którą wyciekłby odsetek trafień; wzór przedziału VR poprawny; testy 49/49, ruff i black czyste.

**Uwagi i co z nimi zrobiłem** (żadna nie zmienia liczby z wyniku):

| waga | uwaga | decyzja |
|---|---|---|
| średnia | strażnik wycieku odsetka trafień tylko leksykalny i dla trzech zapisów liczby | poprawiono: zakazane zapisy 2, 3 i 4 cyfr dziesiętnych oraz procent z 1 i 2 miejscami; liczba 0,282 zakazana poza wydrukiem kontroli |
| średnia | nic nie sprawdzało ścieżki kontroli w `main` (ziarna, ρ, K, n, `--ostatnie`) | dodano test z podstawioną `m.kontrola`, który zapisuje argumenty: ρ = 0,8 z ziarnami 1…40 i ρ = 0 z 101…140, K = 4, n = 300 przy `--ostatnie 300` |
| średnia | progi 0,03 i 0,02 oraz zakresy ziaren niezapięte w teście | dodano asercje na literały (także `m.PROG_RHO`, p, L, B, ziarno bootstrapu); przypadek z ujemną średnią kontroli |
| średnia | dwie linie przedziałów (ρ̂ ± 2 SE i VR) bez asercji | dodano test na dokładne napisy dla ustalonego pomiaru |
| niska | pre-rejestracja (R4) mówiła, że niezbieżne dopasowanie zatrzymuje przebieg, a kod tylko drukował liczbę | **kod poprawiony**: `RuntimeError("STOP …")` przy niezbieżnych dopasowaniach, test; w przebiegu rejestrowym było ich 0, więc wydruk się nie zmienił (sprawdzone ponownym przebiegiem) |
| niska | przy `--ostatnie` wydruk nie podaje okna | dodano wiersz „Okno pomiaru” **tylko** przy `--ostatnie > 0` (rejestrowy wydruk bez zmian) |
| niska | README mówiło, że w wydruku nie ma 0,282, a jest w kontroli | poprawiono README (0,282 tylko jako wartość oczekiwana kontroli dodatniej) |

Po poprawkach sprawdziłem ręcznie 14 własnych mutantów modułu (próg różnicy 0,05, próg ujemnej 0,04, ziarna przesunięte, ziarna
zamienione, ρ zamienione, n = 2100, K = 15, `--ostatnie` ignorowane, brak `abs` przy kontroli ujemnej, brak reguły STOP, napis
„odsetek trafień” w wydruku, przedział VR liczony o 1 SE, ze współczynnikiem K zamiast K − 1): **testy zabijają wszystkie 14.**
Nie zabijam mutanta `<=` → `<` (bez znaczenia praktycznego) ani linii wyniku bramki bez słowa kluczowego (testu leksykalnego nie da się
na to uodpornić; tę ochronę daje przegląd kodu). Zapis odsetka trafień z dwiema cyframi pilnuje asercja numeryczna, ale jej nie mutowałem.

## Kogo NIE ma w zbiorze

1. **11 pozostałych monet z 017** (wyłączone decyzją użytkownika). Niczego nie wiemy o tym, jak ich trafienia łączą się z czwórką.
2. **Monety, które zniknęły z listy** (wycofane kontrakty, 33 martwe ogony w DQ1) i monety młodsze niż 2021. Czwórka to największe,
   „ocalałe” monety (ocalałość: przeżyły do 2026-09-30). Dni, w których moneta spada do zera albo znika z giełdy, w tej próbie nie
   występują; zależność w takim krachu może być zupełnie inna.
3. **Jedna historia.** 1 691 dni oceny w jednym świecie (od lutego 2022). Liczba niezależnych epizodów krachu jest mała (kilka), więc
   ρ̂ jest silnie zależne od tego, które epizody trafiły do okna. SE z bootstrapu blokowego (L = 20 dni) tego nie rozwiązuje, bo
   zakłada, że epizody dłuższe niż blok są niezależne.
4. **Jedno p (5 %), jeden estymator (`dopasuj_garch_t`), jedna częstotliwość refitu (30 dni).** Dla VaR 1 % i dla innych prognoz
   zależność może być inna.
5. **Dni wycięte z panelu** (7 dat przez pięć dziur SOL): na tych dniach nie ma obserwacji, ale to tylko 0,3 % próby.
6. **Pierwsze 400 dni (2021-01-02 … 2022-02-05)** idą na historię dla modelu i nie są oceniane; ewentualna zależność z pierwszego
   roku (hossa 2021, krach maja 2021) nie wchodzi do ρ̂.
7. **Poziom trafień.** Nie liczyliśmy odsetka trafień (z założenia karty), więc nie rozdzielamy zależności od poziomu.

## Co na plus (+) / Co na minus (−)

**Plus**

- (+) Pomiar odtwarza dokładnie dopasowania z 017 (228 i 117); druga droga zgadza się co do cyfry w VR i ρ̂ (SE o 2 % inne przy innym ziarnie).
- (+) Kontrole R8 zaliczone dla K = 4 z kryteriami wyznaczonymi przed przebiegiem na niezależnych ziarnach.
- (+) Przewidywania z pre-rejestracji zapisane z góry; pomyłkę punktu (0,55 wobec 0,42) uznaję wprost.
- (+) Wynik daje liczbę-cel (VR = 2,26) dla laboratorium 019 i mówi uczciwie, że niepewność jest duża (SE 0,09).
- (+) Karta nie dotyka żadnego licznika i nie ocenia prognozy; test jednostkowy pilnuje braku bramki i odsetka trafień w wydruku.

**Minus**

- (−) SE 0,09 to niewiele wiedzy: przedział ±2 SE ma szerokość 0,36 i obejmuje wartość laboratoryjną (0,28) oraz wynik 015 monet (0,50).
- (−) To drugi odczyt tych samych danych co w 017 (podzbiór), więc nie wnosi niezależnego potwierdzenia, tylko kalibrację dla K = 4.
- (−) Druga droga dzieli estymator GARCH-t z przebiegiem rejestrowym; sam estymator nie jest sprawdzony niezależnie.
- (−) 51 % dopasowań przy granicy persystencji (wobec 2,2 % w laboratorium): estymator nadal zachowuje się inaczej niż w LV2 i 019 musi to
  odtworzyć.
- (−) VR miesza zależność z poziomem trafień.
- (−) Kontrola ujemna daje średnią ρ̂ +0,010 (ok. 3 SE powyżej zera); przyczyny nie badałem (możliwe: poziom trafień ≠ 5 %). Nie koryguję
  ρ̂ o tę wartość, bo korekta po obejrzeniu wyniku byłaby rozwidleniem.
- (−) Koszyk to cztery „ocalałe” monety, jedna historia.

## Werdykt

**Caveats.** Podpisuje Claude (R14: skrypt tylko drukuje liczby; przeglądu człowieka nie było, decyzje bramkowe zostają po Twojej
stronie).

Wynik mechaniczny reguł z pre-rejestracji: **spójność ZGODNA; kontrole R8 ZALICZONE; ρ̂ − 2 SE ≤ 0,282; VR (K = 4) = 2,264 jest celem
kalibracji dla 019.** Pomiar jest wiarygodny w tym, co mierzy (VR i ρ̂ czwórki w tym oknie), ale to **Caveats**, nie Ready, bo:

1. niepewność (SE 0,09) nie pozwala odróżnić czwórki od laboratorium ani od 15 monet;
2. to ten sam zbiór dat i te same dopasowania co 017, więc nie jest niezależnym potwierdzeniem;
3. druga droga nie weryfikuje estymatora GARCH-t;
4. VR miesza zależność z poziomem trafień;
5. cztery monety „ocalałe”, jedna historia, jedno p;
6. okno kończy się 2026-09-30; powtórka na końcowym oknie (dane za październik) jest sprawą pre-rejestracji 018.

To **nie** jest Revision: kontrole zaliczone, spójność zgodna, druga droga potwierdza VR i ρ̂.

## Wniosek

1. Dla BTC, ETH, SOL, BNB zależność dziennych trafień VaR 5 % to ρ̂ ≈ 0,42 (VR ≈ 2,26; SE 0,09; przedział 0,24–0,60). Nie umiemy
   odróżnić jej od laboratorium (0,28) ani od 15 monet (0,50).
2. Cztery monety niosą dziennie ok. 1,8 „niezależnej” monety. Wniosek z LV2 o mierzalności reguły K (20 i 15 monet) **nie przenosi się
   automatycznie** na K = 4: trzeba zmierzyć rozmiar i moc w laboratorium dla K = 4.
3. Estymator nadal dochodzi do granicy persystencji w 51 % dopasowań dla tych czterech monet (BTC, ETH, BNB; SOL 0 %).
4. 018 nie startuje: brak LV2c dla K = 4, brak danych za październik, brak własnej pre-rejestracji.

## Rekomendacja

1. **Zlecić pre-rejestrację 019 dla K = 4** (karta 019 jest już przeliczana na K = 4 w ramach decyzji użytkownika z 2026-10-07). Cel
   kalibracji: VR = 2,26 (ρ̂ 0,42) przy `garch_tnu` 5 %, z trwałością zmienności tak blisko granicy 0,9999, żeby ok. 50 %
   dopasowań dochodziło do granicy (tu: 51 %). Komórka: 4 monety × ok. 1 690 dni oceny po 400 historii. Scenariusze: (a) cel z tej karty;
   (b) LV2 bez wspólnego szoku (ρ = 0,8, VR ≈ 1,85) dla K = 4, bo przedział ±2 SE obejmuje wartość laboratorium. Czy dodać
   scenariusz górny (VR ≈ 2,8) i dolny (VR ≈ 1,7), rozstrzyga pre-rejestracja 019 (SE 0,09 jest wystarczająco duże, żeby warto
   było). Pytanie: czy reguła K (rozmiar ≤ 10 %, moc ≥ 80 %) zostaje mierzalna przy K = 4.
2. **018 zostaje wstrzymana** (warunki wznowienia: 019 dla K = 4, dane za październik, powtórka 020 na końcowym oknie, własna
   pre-rejestracja; licznik „ryzyko 2021+” 0 → 1 dopiero wtedy).
3. **Nie powiększam koszyka z powrotem do 15 monet.** To była Twoja decyzja; jeśli 019 pokaże, że reguła K przy K = 4 jest
   niemierzalna, wrócę do Ciebie z opcją rozszerzenia koszyka (według wzoru przybliżonego 15 monet dawało ok. 1,9 efektywnej monety wobec 1,8 dla czterech, więc
   samo rozszerzenie koszyka mogłoby niewiele dać; to hipoteza do zmierzenia w 019, nie wynik).

### Decyzje wykonawcy (delegacja 2026-10-07)

| # | decyzja | dlaczego | jak cofnąć |
|---|---|---|---|
| 1 | Zlecam pre-rejestrację 019 dla K = 4 z celem VR = 2,26 | przepis z pre-rejestracji 020 (kontrole i spójność zaliczone) | `zadania/019`: status `odrzucone`; 018 zostaje wstrzymana |
| 2 | 019 obejmuje też scenariusz LV2 bez wspólnego szoku | ρ̂ − 2 SE = 0,239 < 0,282 (reguła z pre-rejestracji 020) | usunąć scenariusz z pre-rejestracji 019 przed jej commitem |
| 3 | Licznik „ryzyko 2021+” zostaje **0** | karta opisowa, nic nie testuje prognozy | — |
| 4 | ρ̂ nie koryguję o +0,010 z kontroli ujemnej | korekta po obejrzeniu wyniku byłaby rozwidleniem | — |

## Użyte skille

W repozytorium beta nie ma rejestru użyć skilli, więc godziny pochodzą z zapisu sesji. Skille były wczytane w tej sesji **przed**
pre-rejestracją `afe6791`, a przy karcie 020 stosowałem ich listy kontrolne z kontekstu sesji, bez ponownego ładowania:

| skill | co wniósł do 020 |
|---|---|
| `clas5-runda` | procedura rundy: pre-rejestracja przed wynikiem, tabela „przewidywanie a wynik”, README z „Co na plus / Co na minus” i werdyktem, wiersz w `runs/INDEX.md` |
| `data:validate-data` | pytanie „kogo NIE ma w zbiorze”, druga droga, czerwone flagi, rozsądek wartości granicznych |
| `data:statistical-analysis` | zakres zamiast fałszywej precyzji (ρ̂ = 0,42, przedział 0,24–0,60), SE z bootstrapu blokowego, uwaga na efektywną liczbę monet |
| `engineering:code-review` | wymiary przeglądu (korektność, edge-case'y, testy) w poleceniu dla agenta niezależnego; agent sam skilla nie wczytywał |

**Luki (uczciwie).** `clas5-quant` i `quant-strategy-catalog` nie były wczytane; karta jest opisowa (pomiar warunku przeniesienia),
metodologię brałem z `CLAUDE.md` i `docs/PRD.md`. `dataviz`: bez wykresów. Czy te skille coś by dodały, nie sprawdzałem.
