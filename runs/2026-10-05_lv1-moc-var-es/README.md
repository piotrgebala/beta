# LV1 — laboratorium VaR/ES: czy testy wsteczne odróżnią dobrą prognozę od złej przy n = 600–2 100 dni (2026-10-05)

> **STATUS: ZAKOŃCZONA — MIERZALNA przy p = 1 % i p = 5 % (reguła poprawiona), Caveats.** Przebieg
> 2026-10-06, 32 min (16 procesów; czas z stderr, nie z `raw_output.txt`), z commitu `a067344` (kod = `f8a6a0f`).
> Sekcje Wynik / Werdykt / Wniosek są na końcu pliku. Poniżej oryginalny wstęp pre-rejestracji (bez zmian):
> progi poniżej były zapisane przed obejrzeniem wyniku i po nim się ich nie zmieniało.
>
> **Po przeglądzie (3 recenzentów, 2026-10-06) projekt i dwa progi zmieniono, przed pełnym
> przebiegiem.** Wszystkie zmiany są w sekcji „Zmiany po przeglądzie, przed pełnym przebiegiem”.
> Dwie z nich (x\* = 0,10 przy p = 5 % i ii-a tylko przy p = 1 %) zrobiono PO pilotażu i wiadomo,
> że przestawiają przewidywany wynik dla p = 5 %; to był **punkt decyzyjny 7 dla użytkownika**.
> **Decyzja użytkownika 2026-10-06: „LV1: poprawiona”** — obowiązuje reguła poprawiona; werdykt według
> reguły pierwotnej skrypt drukuje obok jako opis (nie werdykt).

## W skrócie — prostym językiem

Mamy sprawdzony przyrząd do oceny prognoz ryzyka ogona (KV1, 19/19), ale KV1 testował go na bardzo
długich sztucznych seriach (20 000–200 000 dni). Prawdziwa historia ma **600–2 100 dni** (od 2021
roku), a monety są ze sobą mocno skorelowane. Przy VaR 1 % i 1 600 dniach spodziewamy się tylko ok.
16 przekroczeń na monetę. Pytanie LV1: **czy przy takiej ilości danych test w ogóle odróżni dobrą
prognozę od złej?** Jeśli nie, to rundy VaR/ES na prawdziwych danych nie ma sensu zaczynać (zasada
R3: najpierw rachunek, czy wynik w ogóle da się zmierzyć).

Jak sprawdzamy: generujemy sztuczne ceny 20 monet, w których **prawdę znamy**, i wystawiamy testom
prognozy dobre i złe (normalny rozkład zamiast grubych ogonów, stała zmienność, zaniżona zmienność o
5–30 %, zbyt krótkie okna). Patrzymy, jak często test mówi „zła prognoza” w jednym i w drugim
przypadku.

Dwie rzeczy są ważne:

1. **20 monet to nie 20 niezależnych obserwacji** (R12). W dniu paniki przekraczają VaR naraz.
   Dlatego liczymy **dni** (ile monet przekroczyło VaR w danym dniu), a nie 20 × n osobnych trafień.
   Test, który liczy wszystkie trafienia jak niezależne, mylił się w 27–45 % przypadków, a powinien w ok. 5 %
   (to nasza kontrola, że problem jest prawdziwy).
2. **Test pojedynczej monety nie wykrywa naraz obu klasycznych błędów** (przewidywanie P1): Z2 ma
   ok. 80 % mocy wobec rozkładu normalnego, ale tylko ok. 28 % wobec stałej zmienności, a Kupiec i
   Christoffersen poniżej 50 % wobec obu. Dlatego ocena na prawdziwych danych ma się opierać na
   teście zbiorczym po dniach.

Reguła rundy dla każdego poziomu ryzyka (1 % i 5 %) osobno: **MIERZALNA**, gdy na komórce głównej
(n = 1 600 dni, ρ generatora 0,8) test zbiorczy ma poprawny rozmiar, wykrywa w ≥ 80 % przypadków
stałą zmienność (oba p) i rozkład normalny zamiast t5 (tylko p = 1 %, bo przy 5 % normalny VaR jest
ostrożniejszy od prawdziwego, czyli to nie jest zaniżenie ryzyka) oraz wykrywa zaniżenie zmienności
o 10 % (oba p). Inaczej **NIEMIERZALNA** i nie zaczynamy rundy VaR/ES na prawdziwych danych przy
tej długości historii. Gdy zawiodą kontrole samego laboratorium: **WSTRZYMANY** (diagnoza i
najwyżej jedna runda LV1b).

## Metadane

- **Pre-rejestracja zamrożona w commicie:** `f8a6a0f` (README, kod i testy; pełny przebieg idzie z tego stanu
  kodu; decyzja użytkownika w punkcie 7 dopisana w następnym commicie, bez zmian kodu ani progów).
- Zadanie 009 (`zadania/009-laboratorium-lv1-var-es.md`, PRD FR-32, cel G2). Runda kalibracyjna, nie hipoteza
  rynkowa: **R1 — brak mechanizmu** (nic nie przewidujemy, mierzymy moc przyrządu przy naszych n).
- Kod: `symulacje/run_lv1.py` (przebieg, reguła, wydruk), `symulacje/moc_var_es.py` (zestaw prognoz
  i testy zbiorcze po dniach), testy `tests/test_lv1.py` (ręczne wzory, własności `hypothesis`,
  mikro kontrole R8, determinizm przy różnej liczbie procesów, okablowanie reguły). Przyrząd per
  moneta to zamrożony `miara/var_es.py` (po KV1) — nie zmieniany w tej rundzie.
- Komenda: `python -m symulacje.run_lv1 > runs/2026-10-05_lv1-moc-var-es/raw_output.txt` (zalecane
  `--workers 16`). Skrót do sprawdzenia, że kod działa: `--smoke` (jego liczby NIE są wynikiem i nie
  służą do wyboru progów). Na stdout idą tylko liczby odtwarzalne; czas idzie na stderr.
- Dane: WYŁĄCZNIE syntetyczne (`symulacje.garch_panel.generuj_panel`: GARCH(1,1) α 0,08 β 0,90, szok
  dzienny t z ν = 5, zmienność bezwarunkowa 4 %/dzień, czynnik rynkowy o sile ρ). Nie czytamy
  `data/`; R16 (dane od 2021) nie dotyczy.
- Determinizm (R19): ziarno główne `20261009`; `SeedSequence.spawn` per zadanie (rozkłady zerowe Z2,
  panele, bootstrap), więc wynik nie zależy od liczby procesów (`--workers`; pilnują tego testy).
  Ziarna pilotaży przed zapisem kryteriów były INNE niż rejestrowe (31415, 987654321, 555000111,
  777, 2718, 4242 i pochodne); wynik rundy powstanie wyłącznie z ziarna `20261009`.
- Czas: patrz „Zmiany po przeglądzie”, pkt 12 (nowy pomiar jednostki pracy). Uruchamiać bez
  innych równoległych przebiegów na maszynie.

## Pre-rejestracja (zapisana przed przebiegiem)

### Pytanie i mechanizm (R1)

Nie przewidujemy rynku. Pytanie jest o przyrząd: przy `n` dniach historii i `K = 20` skorelowanych
monetach, czy test wsteczny VaR/ES odrzuca prognozę błędną o znanej wielkości w ≥ 80 % przypadków i
nie odrzuca prawdziwej częściej niż w ok. 5 %. „Kto traci po drugiej stronie” nie dotyczy (brak
strategii). Wynik tej rundy wchodzi w decyzję, czy i przy jakich n wolno zacząć rundę VaR/ES na
danych (po karcie 008).

### Konwencje

Zwrot dzienny r_it (moneta i, dzień t); q_it = kwantyl rzędu p (ujemny); es_it = E[r | r < q_it];
trafienie I_it = 1{r_it < q_it} (równość NIE jest trafieniem). Odrzucamy H0 („prognoza poprawna”),
gdy p-wartość < 5 %. Test z niezdefiniowaną statystyką (NaN) to **brak odrzucenia**; liczymy je
osobno. Wszystkie prognozy są oceniane na tych samych dniach: panel ma n_max + 60 dni, pierwsze 60
(`WARM`) idą na rozgrzewkę okien i EWMA, a mniejsze n to **początkowy fragment** tego samego panelu
(zagnieżdżone n).

### Projekt

| element | wartość |
|---|---|
| generator | GARCH(1,1) α 0,08 β 0,90, t5, zmienność 4 %, czynnik rynkowy ρ ∈ {0,5; 0,8}, K = 20 monet |
| poziomy | p ∈ {1 %, 5 %} |
| długość | n ∈ {600, 1 000, 1 600} + 2 100 jako komórka opisowa; komórka główna **n = 1 600, ρ = 0,8** |
| panele | **5 000 na ρ** (10 000 razem), generowane RAZ na ρ na n_max = 2 100 (+ 60 dni rozgrzewki) |
| bootstrap | 999 replikacji po dniach (wspólne indeksy dla wszystkich prognoz i p w danym panelu i n) |
| rozkład zerowy Z2 | 20 000 losowań na (n, p, rodzina), raz na cały przebieg |
| precyzja | SE odsetka odrzuceń √(π(1−π)/5000) ≤ **0,71 pp** (0,57 pp przy mocy 80 %, 0,31 pp przy 5 %) |
| korelacja zwrotów | ρ to korelacja ukrytego czynnika normalnego, NIE zwrotów: średnia korelacja zwrotów monet wynosi ok. **0,37 przy ρ = 0,5 i 0,62 przy ρ = 0,8** (0,79 przy ρ = 1; pomiar recenzenta); rynek wg LM1: 0,47–0,86 |

**Dlaczego 5 000 paneli.** Szum symulacji ma być wyraźnie mniejszy niż pasmo rozmiaru (±2,5 pp wokół
5 % to ok. 8 SE, bo SE rozmiaru wynosi 0,31 pp) i niż odstępy między progami (np. moc 93 % wobec
progu 80 % w pilotażu to ok. 18 SE). Panele z różnych n są zależne
(to ten sam panel), więc porównania między komórkami o różnym n są opisowe, a nie testem.

**Prognozy** (σ_t wyroczni generatora jest znane w t − 1; wszystkie F_{t−1}-mierzalne):

| nazwa | q, es | rola |
|---|---|---|
| prawdziwa | σ_t, kwantyl i ES znormalizowanego t5 | kontrola negatywna (H0 prawdziwa) |
| normalna | σ_t, kwantyl i ES normalne | kryterium ii-a przy p = 1 % (grube ogony pominięte); przy p = 5 % opis |
| stala | σ = 4 % stałe, t5 | kryterium ii-b (zmienność w czasie pominięta) |
| zanizenie_05/10/15/20/30 | σ_t · (1 − x), x ∈ {0,05; 0,10; 0,15; 0,20; 0,30}, t5 | krzywa mocy, MDE; x = 0,30 = kontrola pozytywna K2 |
| es_za_niski | q prawdziwe, ES z ilorazu normalnego (ok. 13 % za niskie) | opis |
| okno10, okno60 | σ z 10 / 60 ostatnich dni, t5 | opis (H0 dla nich fałszywa, odrzucenie = moc) |
| ewma94 | EWMA λ = 0,94, t5 | opis |

**Testy per moneta** (średni odsetek monet odrzuconych z 20; to opis i przewidywanie P1, nie
kryterium): Kupiec LR_uc, Christoffersen LR_cc, Acerbi–Székely Z2 (p-wartość z rozkładu zerowego dla
rodziny „t” albo „normal”; Z2 policzone raz na (n, p, rodzina)). Wszystko z zamrożonego
`miara/var_es.py`.

**Test zbiorczy po dniach (R12).** Jednostką jest dzień t, a nie para (moneta, dzień). S_t = Σ_i
I_it (liczba monet z trafieniem). Pod H0 z prognozą F_{t−1}-mierzalną E[S_t | przeszłość] = K·p
(różnica martyngałowa), więc test nie zakłada niezależności monet ani stałej korelacji. Efektywna
liczba niezależnych monet w pilotażu: wariancja S_t jest 3,0 razy (p = 1 %, ρ = 0,8) i 6,2 razy (p =
5 %) większa niż przy niezależnych monetach, czyli 20 monet daje ok. 6,6 i 3,2 niezależnych (N_eff ≤
n, R10/R12).

- **A pokrycie**: t-Studenta średniej S_t względem K·p, dwustronny **z równymi ogonami**
  (odpowiednik Kupca).
- **B niezależność**: studentyzowana kowariancja S_t (centrowanego średnią próby) ze średnią 10
  poprzednich dni, dwustronny **z równymi ogonami** (odpowiednik Christoffersena: grupowanie
  trafień w czasie). Nie reaguje na zły POZIOM trafień, to robi A.
- **C ogon**: t-Studenta średniej d_t = Σ_i (U_it − 1), U_it = r_it I_it / (p · es_it), jednostronny
  (odrzucamy, gdy średnia d_t > 0, czyli ogon niedoszacowany; odpowiednik Z2).
- **Test zbiorczy LV1 = A lub B lub C**, każdy na poziomie α/3 = 1,67 % (Bonferroni). Rozkłady
  p-wartości: **bootstrap-t po dniach** (losowanie dni ze zwracaniem). Jednostronny C:
  (1 + #{t* ≥ t}) / (1 + 999). Dwustronne A i B: p = min(1; 2·min(prawa, lewa)), gdzie lewa =
  (1 + #{t* ≤ t}) / (1 + 999) — każda strona dostaje ok. połowę poziomu.
- **Test naiwny** (tylko kontrola K3): Kupiec na wszystkich 20·n trafieniach jak na niezależnych.

**Dlaczego bootstrap-t z równymi ogonami (wersja po przeglądzie).** Statystyki t testów A, B i C
są pod H0 skośne w lewo (S_t jest prawoskośne: skupiska trafień w dniach paniki). Łączny rozmiar
testu zbiorczego jest wtedy dobry zarówno z N(0,1), jak i z symetrycznym bootstrapem, ale **strony
są nierówne**: odrzucenia biorą się prawie wyłącznie z lewej strony (za mało trafień, VaR
ostrożny), a prawa strona — za dużo trafień, czyli zaniżone ryzyko, które chcemy wykrywać — prawie
nie odrzuca. Pomiar pod H0 (pilotaż autora po przeglądzie, ziarno 86420, 2 000 paneli, ρ = 0,8,
n = 1 600, poziom α/3 = 1,67 %, czyli ok. 0,83 % na stronę):

| test, p | N(0,1) lewa / prawa | bootstrap symetryczny lewa / prawa | bootstrap równe ogony lewa / prawa |
|---|---|---|---|
| A, 1 % | 1,50 / 0,40 | 1,15 / 0,20 | 0,65 / 0,75 |
| B, 1 % | 1,90 / 0,20 | 1,10 / 0,00 | 0,40 / 0,80 |
| A, 5 % | 1,10 / 0,50 | 1,00 / 0,30 | 0,70 / 0,70 |
| B, 5 % | 1,10 / 0,35 | 0,90 / 0,30 | 0,50 / 0,60 |

(SE ok. 0,2 pp.) C jest jednostronny prawy: 1,55 % (p = 1 %) i 1,70 % (p = 5 %) przy nominalnych
1,67 %. Dlatego bootstrap zostaje (N(0,1) nie wyrównuje stron), ale z równymi ogonami. Wybór
uzasadnia wyłącznie rozkład pod H0 (kontrola rozmiaru każdej strony), nie moc wobec alternatyw.
Pierwotne uzasadnienie („N(0,1) miało rozmiar 6–11 %”) nie odtwarza się dla obecnych statystyk
(recenzent: N(0,1) daje łącznie 4,8–5,0 %); najpewniej dotyczyło wcześniejszej wersji testu B
(opóźnienie 1 dnia, bez centrowania) — patrz „Zmiany po przeglądzie”. Założenie bootstrapu: dni są
wymienialne (jak w generatorze, gdzie ε_it = r_it/σ_it jest iid po t); na prawdziwych danych przy
zmiennej w czasie korelacji to jest ograniczenie (patrz niżej).

### Kryteria

Wszystkie liczone na **komórce głównej: ρ = 0,8, n = 1 600, osobno dla p = 1 % i p = 5 %**, na
teście zbiorczym (A lub B lub C, α/3). Kody K1–K3, ii-a, ii-b, iii są w kodzie (`ocen`) i w wydruku.
(Oznaczenia ze zlecenia: (i) = K1, (ii) = ii-a i ii-b, (iii) = iii.)

| kod | rola | co | wymaganie |
|---|---|---|---|
| **K1** | kontrola negatywna (R8) | rozmiar testu zbiorczego na prognozie „prawdziwa” | odsetek odrzuceń ∈ [2,5 %; 7,5 %] |
| **K2** | kontrola pozytywna (R8) | moc testu zbiorczego wobec σ zaniżonego o 30 % | ≥ 95 % |
| **K3** | kontrola laboratorium | rozmiar naiwnego Kupca (20·n trafień jak niezależne), ρ = 0,8 | > 10 % |
| **ii-a** | mierzalność, **tylko p = 1 %** | moc zbiorczego wobec prognozy „normalna” | ≥ 80 % (przy p = 5 %: drukowane jako opis) |
| **ii-b** | mierzalność | moc zbiorczego wobec prognozy „stala” | ≥ 80 % |
| **iii** | mierzalność | MDE zaniżenia σ (moc 80 %, x ∈ {0; 0,05; 0,10; 0,15; 0,20; 0,30}, interpolacja liniowa) | ≤ **0,10** przy obu p |

**Kontrola K3 jest kryterium (kontrola ujemna laboratorium), nie tylko opisem.** Powód: jeśli naiwny
test miałby poprawny rozmiar przy ρ = 0,8, to laboratorium nie odtwarza problemu R12, który ma
badać, a cały rachunek po dniach byłby bez sensu. Z rachunku: przy współczynniku wariancji VR (3,0 i
6,2 w pilotażu) rozmiar naiwnego Kupca ≈ 2(1 − Φ(1,96/√VR)) = 26 % i 43 %; próg 10 % jest daleko
poniżej, więc odpada tylko przy utracie zależności w generatorze. Przy ρ = 0,5 naiwny test jest
tylko opisem — także w mapie (tam K3 nie wchodzi do wyniku reguły dla ρ = 0,5).

**Uzasadnienie progu MDE (iii), wersja po przeglądzie: x\* = 0,10 przy OBU p.** Kotwica: różnica
między dwoma „standardowymi” wyborami rodziny rozkładu tam, gdzie jest ona prawdziwym ZANIŻENIEM
ryzyka. Przy p = 1 % normalny kwantyl jest o ok. 11 % mniejszy co do modułu niż kwantyl t5 o tej
samej wariancji (2,326 vs 2,606) — to jest „standardowy błąd modelu” rzędu 0,10. Ten sam próg
stosujemy przy p = 5 %, bo (1) zaniżane jest σ, a błąd σ ma tę samą wagę ekonomiczną przy każdym p
(pozycja dobrana pod cel zmienności jest o 1/(1 − x) − 1 ≈ 11 % za duża); (2) przy p = 5 % różnica
normalny vs t5 idzie w stronę OSTROŻNOŚCI (1,645 vs 1,561: normalny VaR jest większy), więc nie
mierzy zaniżenia i nie może być kotwicą; (3) próg w mierze trafień (π/p ≥ 1,5, przykład z karty)
dałby przy 5 % x ≈ 0,155, więc 0,10 jest wyborem ostrzejszym. Pierwotna kotwica x\* = 0,05 przy
5 % odpowiadała stosunkowi trafień 1,14 zamiast 1,46 przy 1 % — dwa różne standardy. x\* leży na
siatce, więc (iii) ⇔ moc testu zbiorczego przy x = 0,10 ≥ 80 % (przy wygładzeniu krzywej maksimum
narastającym); flaga „2 SE” dla iii jest liczona z tej mocy i jej SE.

**Dlaczego ii-a tylko przy p = 1 % (po przeglądzie).** Przy p = 5 % prognoza „normalna” daje
4,356 % trafień zamiast 5 % (VaR zawyżony o 5,4 %), a łącznie z ES jest w sensie Z2 lekko ostrożna
(E[U] = 0,985 < 1; rachunek zamknięty recenzenta). Kryterium ii-a przy 5 % żądałoby więc wykrycia
prognozy OSTROŻNEJ, a nie zaniżonego ryzyka — tego reguła nie ma mierzyć. Precedens: KV1 (komórka
Z2 przy 5 % przeniesiona do opisu). Przy 5 % moc wobec „normalna” jest drukowana jako opis (wiersz
„ii-a OPIS”). Przy p = 1 % normalna to prawdziwe zaniżenie (1,499 % trafień, E[U] = 1,75) i ii-a
zostaje kryterium.

**Kontrole R8.** Negatywna: K1 (prawdziwa prognoza nie jest odrzucana częściej niż ok. 5 %).
Pozytywna: K2 (σ zaniżone o 30 % wykrywane w ≈ 100 %). Dodatkowo kontrola laboratorium K3. Kontrola
negatywna K1 ma „zęby”: naiwny test miałby tu rozmiar 27–45 %, daleko poza pasmem.

### Reguła decyzji (R4 / reguła STOP)

Dla każdego p osobno, na komórce głównej:

- **WSTRZYMANY** ⇔ któraś z kontroli K1, K2, K3 nie spełniona (błąd laboratorium albo źle
  skalibrowany test zbiorczy, a nie wniosek o danych). Werdyktu MIERZALNA ani NIEMIERZALNA nie
  wydajemy. Wtedy najpierw diagnoza, a potem **najwyżej jedna** runda LV1b. W LV1b wolno zmienić
  wyłącznie kalibrację testu zbiorczego pod H0 (to, co decyduje o rozmiarze: sposób liczenia
  p-wartości, korektę, bootstrap); NIE wolno zmieniać progów K1–K3, ii, iii, kotwic, siatki,
  prognoz, generatora, komórki głównej ani liczby paneli. Jeśli LV1b też da WSTRZYMANY, to wynik
  jest **NIEMIERZALNA(p)** i idzie karta decyzji do użytkownika.
- **MIERZALNA(p)** ⇔ K1, K2, K3 spełnione ORAZ kryteria (ii-a przy p = 1 %, ii-b, iii) spełnione.
  Wtedy runda VaR/ES na danych przy poziomie p może wejść do pre-rejestracji (osobna karta, z
  własnym licznikiem „ryzyko 2021+”), ale tylko przy dwóch warunkach przeniesienia, zapisanych
  teraz:
  1. **Zakres:** w rundzie na danych jest ≥ 20 monet i każda ma ≥ 1 600 dni OOS (po okresie
     treningu, jak w F21). Przy mniejszym n albo K potrzebna jest nowa pre-rejestracja laboratorium
     (mapa jest tylko opisem do planowania, nie zgodą).
  2. **Zależność:** współczynnik VR dziennej sumy przekroczeń zmierzony na prawdziwych danych
     (osobna karta, licznik opisowy; np. względem kwantyla z kroczącego okna) nie przekracza VR
     komórki głównej z tego przebiegu (wydruk podaje go przy każdym p; pilotaż: ok. 3,0 przy 1 % i
     6,3 przy 5 %). Inaczej trzeba policzyć nową komórkę z silniejszą zależnością.
- **NIEMIERZALNA(p)** ⇔ kontrole przeszły, a co najmniej jedno z kryteriów nie. Wtedy **żadna
  runda VaR/ES na prawdziwych danych przy poziomie p i tej długości historii nie startuje** (R3).
  Alternatywy opisane niżej.

Skrypt jest neutralnym reporterem (R14): drukuje liczby, kryteria i wynik reguły; werdykt (Ready /
Caveats / Revision) podpisuje Claude po przebiegu. Wydruk oznacza kryteria, których wartość leży w
odległości < 2 SE od progu („[w granicach 2 SE od progu]”), bo przy nich werdykt jest wrażliwy na
losowość. Dotyczy to wszystkich kryteriów, także iii (flaga z mocy przy x = 0,10 i jej SE).

Komórka główna (n = 1 600, ρ = 0,8, czyli korelacja zwrotów ok. 0,62) to przypadek **środkowy**
dla rynku (0,47–0,86 wg LM1), a nie ostrożny koniec: górna część rynku leży poza zasięgiem tego
generatora (nawet ρ = 1 daje 0,79). Stąd warunek przeniesienia „Zależność” wyżej. Mapa wyniku reguły w
pozostałych komórkach (ρ × p × n, w tym n = 600, 1 000, 2 100 i ρ = 0,5) jest drukowana jako
**opis do planowania** (od jakiej długości historii i przy jakiej korelacji reguła by przeszła);
nie jest werdyktem ani zgodą na rundę przy krótszej historii.

### Przewidywania (zapisane przed przebiegiem, falsyfikowalne)

- **P1 (przewidywanie; nie wchodzi do reguły; rozpisane per test po przeglądzie).** Przy p = 1 %,
  n = 1 600, ρ = 0,8, testy per moneta (średni odsetek odrzuconych monet):
  - **P1a:** Kupiec i Christoffersen cc mają moc < 80 % wobec „normalna” i wobec „stala”;
  - **P1b:** Z2 ma moc < 80 % wobec „stala”;
  - **P1c:** Z2 ma moc wobec „normalna” w przedziale [60 %; 95 %] (przedział z pilotaży: 79,9 %,
    80,7 %; nie ślepy).
  Wydruk sprawdza każdy wiersz („P1 sprawdziło się” tylko, gdy wszystkie trzy). Powód: ok. 16
  trafień na monetę; Z2 widzi ogon, ale nie dynamikę zmienności.
- **P2.** Przy p = 5 % w komórce głównej spełnione są wszystkie kryteria, czyli **MIERZALNA(5 %)**
  (po zmianie x\* i zakresu ii-a; patrz pilotaż po przeglądzie). Moc wobec „normalna” przy 5 %
  (opis) wyniesie ok. 40 %, bo ta prognoza jest ostrożna (rachunek niżej).
- **P3.** Przy p = 1 % w komórce głównej spełnione są wszystkie kryteria, czyli **MIERZALNA(1 %)**.

P2 i P3 zostały sformułowane **po obejrzeniu pilotażu** (patrz niżej), więc nie są ślepe; P1a i P1b
wynikają z liczby trafień na monetę i z KV1. Gdy P2 lub P3 zawiodą, opisujemy to wprost.

### Co NIE jest kryterium (opis)

Pełna tabela odsetków odrzuceń (Kupiec, cc, Z2 per moneta; A, B, C i zbiorczy; test naiwny) dla
wszystkich prognoz × p × n × ρ; średni odsetek trafień i średnie Z2; MDE per test; rozkłady zerowe
Z2; mapa reguły w komórkach pozostałych; prognozy okno10, okno60, ewma94, es_za_niski; moc wobec
„normalna” przy p = 5 %; nowe kolumny: A po stronie „za dużo trafień” (A>0), test bez B („A lub C”
na α/2, wrażliwość ii-b na test B) i VR. Odsetek odrzuceń dla okien i EWMA to **moc** (H0 dla nich
fałszywa), nie rozmiar. Dotyczy to też Z2 per moneta: rozkład zerowy Z2 jest rozkładem prognozy
wyroczni, więc odrzucenie okna/EWMA to moc wobec złego σ, a nie test rozmiaru.

### Co sprawdzono PRZED zapisem kryteriów (pełna jawność, R3)

**1. Czy kryteria da się spełnić i czy da się je obalić (R3 na poziomie projektu).** Przed zapisem
progów uruchomiono silnik `run_lv1` na ziarnach pilotażowych (nie rejestrowych): 1 200 paneli ρ =
0,8 (ziarno 31415) i 400 paneli na ρ pełnej siatki (ziarno 987654321). Wniosek o spełnialności:
rozmiar testu zbiorczego mieścił się w 2,8–6,8 % we wszystkich komórkach (SE pilotażu ok. 1 pp), moc
wobec σ·0,70 wynosiła ≈ 100 %, naiwny Kupiec miał rozmiar 27 % (p = 1 %) i 45 % (p = 5 %). Wniosek o
obalalności: reguła potrafi dać **NIE** (p = 5 % w pilotażu: ii-a 48,8 % i MDE 0,080 > 0,05) i
**TAK** (p = 1 %: ii-a 99,8 %, ii-b 93,2 %, MDE 0,085), więc nie jest trywialnie spełniona ani
niemożliwa. Okablowanie reguły sprawdzają testy jednostkowe na liczbach sztucznych (każde kryterium
osobno przestawia werdykt, WSTRZYMANY ma pierwszeństwo, granice progów). Kod testów sprawdzono
mutacjami na kopii poza repozytorium. Testy pokrywają: wzory, znak, stronę testu, look-ahead,
okablowanie reguły, zagnieżdżenie n w panelu, różne ziarna paneli, przypięcie konfiguracji, test
naiwny = Kupiec, wygładzenie MDE (po przeglądzie dopisano testy dla mutantów, które recenzent
pokazał jako przeżywające — patrz „Zmiany po przeglądzie”, pkt 10).

**2. Pilotażowe pomiary w komórce głównej (n = 1 600, ρ = 0,8; to NIE jest wynik rundy).**

| | K1 rozmiar | K2 moc σ·0,70 | K3 naiwny | ii-a normalna | ii-b stała | iii MDE |
|---|---|---|---|---|---|---|
| p = 1 % | 4,8 % | 100 % | 27,0 % | 99,8 % | 93,2 % | 0,085 |
| p = 5 % | 6,8 % (±1,3) | 100 % | 45,0 % | 48,8 % | 99,0 % | 0,080 |

(Tabela wyżej: wersja PRZED przeglądem — symetryczny bootstrap, stare progi.)

Test per moneta, p = 1 %, n = 1 600, ρ = 0,8, moc wobec „normalna” / „stala”: Kupiec 44,5 / 35,8 %,
Christoffersen cc 36,2 / 44,8 %, Z2 79,9 / 27,2 %. K1 przy p = 5 % = 6,8 ± 1,3 % w tym pilotażu to
szum 400 paneli: większe pilotaże recenzentów dały 4,63 ± 0,38 % (3 000 paneli), 3,7 %, 3,8 %, 5,0 %
i 5,2 %, więc ryzyko WSTRZYMANY przez K1 przy 5 % jest małe. Mapa pilotażu (opis): przy p = 1 %
reguła przechodziła od n = 1 600 (ρ = 0,8) albo n = 1 000 (ρ = 0,5), a przy n = 600 nigdy.

**3. Rachunek mocy testu A wobec „normalna” (R3; ziarna 4242+).** Z momentów S_t na 60 panelach:
przesunięcie średniej S_t wynosi K(p − π) = 0,133 monety dziennie przy p = 5 % (π = 4,35 %) i
sd(S_t) = 2,43 (ρ = 0,8), czyli statystyka z = 0,133 · √1 600 / 2,43 = 2,18. Moc testu A wynosi więc
ok. 59 % na poziomie 5 % i ok. 42 % na poziomie α/3; test zbiorczy (A lub B lub C) w pilotażu:
48,8 %. By test A osiągnął 80 % na poziomie α/3, trzeba z ≈ 3,24, czyli n ≈ 1 600 · (3,24/2,18)² ≈ 3 500
dni. Przy p = 1 % przesunięcie jest −0,097 monety dziennie przy sd 0,77, z = 5,0, moc A ≈ 99,6 %. To
jest rachunek, który pokazał, że ii-a przy p = 5 % zawodzi z konstrukcji (normalna jest tam
ostrożna, a test C jednostronny jej nie widzi), nie z powodu słabego testu. Po przeglądzie ii-a
przy 5 % jest więc opisem (patrz „Dlaczego ii-a tylko przy p = 1 %”).

**4. Poprawki testu zbiorczego w trakcie pilotaży (jawnie, bo wybierane na danych pilotażu).** (a)
N(0,1) dla t → bootstrap-t po dniach. Zmierzone wtedy 6–11 % dotyczyło wersji z ówczesnym testem
B (przed poprawkami b i c); dla obecnych statystyk łączny rozmiar z N(0,1) jest poprawny, a
prawdziwym powodem bootstrapu są nierówne strony (patrz wyżej; tę wadę naprawiono dopiero po
przeglądzie równymi ogonami). (b) Pierwotny test B z opóźnieniem 1 dnia nie miał mocy wobec
„stala” → okno 10 dni. **Wypróbowano 5 długości okna: 1, 3, 5, 10, 20 dni** (każdą w wersji
dwustronnej i prawostronnej, skrypt pilotażowy p4, ziarna 2718+), czyli 10 wariantów B. To wybór
na pilotażu, który niesie ii-b: przy p = 1 % bez testu B zbiorczy ma wobec „stala” tylko ok. 55 %
(recenzent, ziarno 778), więc **ii-b przy p = 1 % stoi na teście B**. Wydruk podaje dlatego test
„A lub C” bez B jako opis. (c) Test B na niecentrowanej kowariancji reagował na zły POZIOM trafień
(przeciek pokrycia) → centrowanie średnią próby. (d) Silnik był za wolny (ok. 15 s na panel na rdzeń
przy dużym obciążeniu maszyny) → bootstrap partiami, ten sam wynik. Te zmiany są częścią
rejestrowanego projektu; pilotaż nie jest więc ślepy (P2, P3).

**5. Pomiary czasu i tryb smoke.** Czasy panelu i całego przebiegu — wyżej w Metadanych. `--smoke`
(n = 150 i 250, 6 paneli na ρ, bootstrap 99, rozkład zerowy 400) sprawdza tylko, że kod działa i że
wynik nie zależy od liczby procesów; jego liczb nie użyto do wyboru progów ani projektu.

**6. Czego nie sprawdzano.** Pełnego przebiegu nie uruchamiano (10 000 paneli), także po
przeglądzie. Nie czytano żadnych prawdziwych danych. Nie sprawdzano rozmiaru dla estymowanego
modelu (patrz Ograniczenia).

### Zmiany po przeglądzie, przed pełnym przebiegiem (2026-10-06, pełna jawność)

Trzech niezależnych recenzentów przeczytało kod i README i zrobiło własne pilotaże na ziarnach
spoza rejestru (13579, 55501, 777–779). Błędu zmieniającego wynik w kodzie ani w zamrożonym
`miara/var_es.py` nie znaleźli. Zmiany (żadna nie korzysta z ziarna rejestrowego `20261009`,
którego nikt jeszcze nie uruchomił w pełnej konfiguracji):

1. **Test A i B: równe ogony zamiast symetrycznego |t\*| ≥ |t|** (recenzenci 1 i 3; pomiar autora
   dla A, B, C w tabeli „Dlaczego bootstrap-t z równymi ogonami”). Powód: rozmiar każdej strony pod
   H0. Strona „za dużo trafień” testu A miała 0,07–0,2 % zamiast ok. 0,83 %, a test B po stronie
   grupowania 0,0 %. Kod: `p_boot(..., "rowne")`.
2. **Uzasadnienie bootstrapu poprawione** (recenzent 3): N(0,1) ma dobry rozmiar łączny, ale nie
   wyrównuje stron; liczby 6–11 % dotyczyły wcześniejszej wersji B.
3. **ii-a tylko przy p = 1 %; przy p = 5 % „normalna” to opis** (recenzent 1). Uzasadnienie
   zamknięte: przy 5 % normalna jest ostrożna (4,356 % trafień, E[U] = 0,985). Zmiana PO
   pilotażu, przestawia przewidywany wynik dla 5 % → punkt decyzyjny 7.
4. **x\* = 0,10 także przy p = 5 %** (recenzent 1; było 0,05). Uzasadnienie zamknięte w sekcji
   „Uzasadnienie progu MDE”. Pilotaż dał przy 5 % MDE 0,080 (przed zmianą 1) i 0,079 (po niej),
   więc zapas to tylko ok. 0,02 — flaga 2 SE dla iii jest teraz liczona. Zmiana PO pilotażu →
   punkt decyzyjny 7. Recenzent 2 radził NIE zmieniać progów po fakcie; przyjąłem argument
   recenzenta 1 (próg 0,05 mierzył błąd w stronę ostrożności, więc był błędem projektu, nie
   kwestią surowości), ale decyzję zostawiam użytkownikowi.
5. **Flaga „2 SE od progu” dla iii** (recenzenci 1–3): z mocy przy x = 0,10 i jej SE.
6. **K3 w mapie tylko przy ρ = 0,8** (recenzenci 1–3), zgodnie z tym, co README mówiło od początku.
7. **Reguła STOP dla LV1b** (recenzent 1): najwyżej jedna runda, zmieniać wolno tylko kalibrację
   pod H0; druga porażka = NIEMIERZALNA.
8. **Warunki przeniesienia MIERZALNEJ** (recenzent 1): zakres (≥ 20 monet, ≥ 1 600 dni OOS) i
   zależność (VR na danych ≤ VR komórki głównej; VR jest nową kolumną wydruku). Korelacja zwrotów
   generatora (0,37 / 0,62) podana wprost; komórka główna nie jest już nazywana „ostrożną”.
9. **Ograniczenia dopisane:** K1 tylko dla wyroczni (potrzebna kontrola LV2 z estymowanym modelem),
   Z2 per moneta dla okien/EWMA to moc, ii-b stoi na teście B z oknem dobranym na pilotażu (lista
   5 wypróbowanych okien), siatka x bez 0,25.
10. **Testy** (recenzent 2; z 40 do 47): zagnieżdżenie n w jednym panelu (r[:n], idx < n, rozkład
    zerowy dla tego n), różne ziarna paneli i różne ρ, przypięcie całej konfiguracji
    pre-rejestracji, test naiwny = Kupiec (przypadek, w którym cc daje inną decyzję), wygładzenie
    MDE, równe ogony na skośnych danych, ii-a tylko przy 1 %, K3 w mapie, flaga iii, nowe kolumny.
    Mutacje na kopii poza repo: 8 z 11 mutantów, które u recenzenta przeżyły (M05a, M05b, M05c,
    M06c, M17, N03, N04, N10), jest teraz wykrywanych; pozostałe 3 (N01, N02, M26: inne
    `glowne_n`, `ns`, `RHO_GLOWNE`) łapie wprost przypięcie konfiguracji. Wykrywanych jest też 8
    nowych (powrót do symetrycznego A, stare x\*, ii-a przy
    5 %, brak flagi iii, K3 w mapie, zły VR, zły „A lub C”) są wykrywane.
11. **P1 rozpisane per test** (recenzenci 1 i 3) na P1a–P1c; P2 przeformułowane (MIERZALNA(5 %)).
12. **Procesy przez forkserver** zamiast fork (recenzent 2: ostrzeżenie o fork w procesie z
    wątkami). Wynik bez zmian (ziarna z SeedSequence). Czas: jednostka pracy = 1 panel (4 długości
    n × 2 poziomy × 12 prognoz, bootstrap 999) = **1,35 s na rdzeń** (pomiar 2026-10-06, obciążenie
    ok. 14); rozkłady zerowe Z2 ok. 8 s łącznie. 10 000 paneli / 16 procesów = ok. 14 min w
    idealnych warunkach; z SMT i obciążeniem maszyny realnie **ok. 30 min (zakres 15–70 min)**.
    Uruchamiać bez innych równoległych przebiegów.
13. Nazwa werdyktu ujednolicona: WSTRZYMANY. Usunięto ze scratchpadu starą zmutowaną kopię kodu
    (`mut/symulacje`, `mut/miara`), która myliła pilotaże recenzenta.

**Pilotaż autora PO zmianach** (ziarno 97531, spoza rejestru; 1 500 paneli, ρ = 0,8, n = 1 600,
bootstrap 999, rozkład zerowy Z2 5 000; to NIE jest wynik rundy):

| | K1 rozmiar | K2 | K3 naiwny | ii-a normalna | ii-b stała (bez B) | iii MDE (moc przy 0,10) | VR | wynik |
|---|---|---|---|---|---|---|---|---|
| p = 1 % | 3,6 ± 0,5 % | 100 % | 24,7 % | 100 % | 98,7 % (55,4 %) | 0,082 (98,0 %) | 3,01 | MIERZALNA |
| p = 5 % | 3,8 ± 0,5 % | 100 % | 40,7 % | opis: 37,7 % | 99,1 % (69,1 %) | 0,079 (99,4 %) | 6,31 | MIERZALNA |

Test A po stronie „za dużo trafień” pod H0: 0,8 % i 0,7 % (nominalnie ok. 0,83 %). P1a–P1c:
sprawdziły się (Kupiec 45,0 / 36,0 %, cc 36,3 / 44,3 %, Z2 82,4 / 27,1 %). Moc zbiorczego wobec
σ·0,95: 47,9 % (1 %) i 54,1 % (5 %).

### Co zrobić, gdy wynik jest NIEMIERZALNA (alternatywy, nie ruchy tej rundy)

Każda alternatywa to nowe pytanie z własnym licznikiem (PRD §11.4) i własną pre-rejestracją:

1. **Czekać na dłuższą historię** albo czytać mapę: od jakiego n (i przy jakiej korelacji) reguła
   przechodzi.
2. **Porównywać prognozy między sobą** (np. dwie prognozy VaR/ES na jednej stracie kwantylowej i
   teście Diebolda–Mariano), zamiast sprawdzać pojedynczą prognozę wobec bezwzględnego wzorca; to
   inny test, wymaga osobnego laboratorium mocy (jak LM1).
3. **Raport opisowy bez werdyktu:** liczba trafień i średnia strata ponad VaR, bez „zdał / nie
   zdał”.
4. **Tylko poziom, który przeszedł** (np. wyłącznie p = 1 %, jeśli 5 % jest NIEMIERZALNA), albo
   zmierzyć faktyczną korelację koszyka na prawdziwych danych (osobna karta) i dopiero wtedy wybrać
   komórkę z mapy.

### Ograniczenia

- Generator ma stałą korelację ρ i niezależne mieszanie t oraz GARCH dla każdej monety (zależność
  tylko przez czynnik normalny), więc **brak zależności ogonowej i wspólnej zmienności**. Korelacja
  zwrotów to tylko 0,37 (ρ = 0,5) i 0,62 (ρ = 0,8), a VR dziennej sumy trafień w komórce głównej ok.
  3,0 (p = 1 %) i 6,3 (p = 5 %). Prawdziwe krachy są bardziej synchroniczne, N_eff na danych może
  być mniejsze, a moc niższa niż tu — stąd warunek przeniesienia „Zależność” w regule.
- **K1 dotyczy tylko prognozy-wyroczni** (σ_t znane dokładnie). Rozmiar testu zbiorczego dla
  poprawnego, ale ESTYMOWANEGO modelu (błąd estymacji parametrów, Escanciano–Olmo 2010) jest
  nieznany; okna i EWMA są źle wyspecyfikowane, więc mierzą moc, nie rozmiar. Przed rundą na
  danych potrzebna jest osobna kontrola (np. LV2: GARCH(1,1)-t dopasowywany w kroczącym oknie
  365 dni jako H0).
- ii-b mierzy test B z oknem 10 dni dobranym na pilotażu do trwałości GARCH tego generatora (α
  0,08, β 0,90). Na danych o innej strukturze grupowania moc wobec stałej zmienności będzie inna.
- Bootstrap po dniach zakłada wymienialność dni; przy zmiennej w czasie korelacji monet jest tylko
  pierwszego rzędu.
- Siatka MDE to x ∈ {0; 0,05; 0,10; 0,15; 0,20; 0,30} (bez 0,25; MDE między 0,20 a 0,30 jest
  interpolowane przez lukę 0,10); wartość „> 0,30” znaczy „nieosiągalne na siatce”. Próg x\* = 0,10
  leży w gęstej części siatki.
- Komórka główna jest jedna (n = 1 600, ρ = 0,8). Inne komórki są opisem, nie dowodem.
- Z2 per moneta nie jest kryterium; przy p = 5 % Z2 nie ma mocy wobec „normalna” z konstrukcji
  (KV1).
- Pilotaż nie był ślepy: P2 i P3 zapisano po jego obejrzeniu.

### Liczniki

- **0 wariantów**, POZA licznikami: dane syntetyczne, kalibracja przyrządu.
- Wspólny rejestr odczytów alpha (`odczyty_historii.csv`, N = 40): **bez zmian** — żaden zwrot
  strategii nie jest odczytywany na historii.
- Licznik „ryzyko 2021+” (PRD §11.4): **bez zmian (0)** — nie testujemy żadnej prognozy VaR/ES na
  prawdziwych danych.
- R15: LLM nie występuje w żadnej ścieżce decyzyjnej; przyrząd i skrypt są deterministyczne (R19).

### Decyzje wykonawcy (poza zleceniem) — do przeglądu

1. **Test zbiorczy = A lub B lub C z Bonferronim i bootstrapem-t po dniach.** Zlecenie żądało testu
   zbiorczego po dziennych sumach i „lepszego, jeśli rozmiar zły”; przegląd pokazał nierówne
   strony testów dwustronnych (prawie zerowy rozmiar strony „zaniżone ryzyko”), więc rejestrujemy
   bootstrap-t z równymi ogonami.
2. **5 000 paneli na ρ** (SE ≤ 0,71 pp), bootstrap 999, rozkład zerowy 20 000; **zalecane 16
   procesów**.
3. **K2 ≥ 95 %** (zlecenie: „~100 %”) i **K3 > 10 %** (naiwny test jako kontrola ujemna
   laboratorium); awaria K2 lub K3 daje WSTRZYMANY tak samo jak awaria K1.
4. **x\* = 0,10 przy obu p** (po przeglądzie; pierwotnie 0,10 / 0,05) z kotwicy normalny vs t5
   przy p = 1 % (zlecenie podało kotwicę, nie liczbę).
5. **P2 i P3 jako przewidywania** obok P1 ze zlecenia.
6. **Siatka mocy x ∈ {0; 0,05; 0,10; 0,15; 0,20; 0,30}**; MDE przez wygładzenie maksimum
   narastającym i interpolację.
7. **Punkt decyzyjny dla użytkownika (przed pełnym przebiegiem):** zatwierdzić zmiany po
   przeglądzie — x\* = 0,10 przy p = 5 % (było 0,05) i ii-a przy p = 5 % jako opis (było
   kryterium). Obie zrobiono PO pilotażu, który dał przy 5 % MDE 0,080 i moc wobec „normalna”
   ok. 45–49 %, więc wiadomo, że przestawiają przewidywany wynik dla 5 % z NIEMIERZALNA na
   MIERZALNA. Uzasadnienie jest zamknięte (rachunek, nie liczby pilotażu), ale wybór i tak należy
   do użytkownika. Jeśli użytkownik ich nie zatwierdzi: wracamy do progów pierwotnych (0,05 i ii-a
   przy obu p), a pozostałe zmiany (równe ogony, flagi, warunki przeniesienia, STOP) zostają.
   **Rozstrzygnięte 2026-10-06 przez użytkownika: reguła poprawiona.** Werdykt według reguły pierwotnej
   jest drukowany jako opis („OPIS (nie werdykt): reguła PIERWOTNA”).

## Wynik

Źródło: `raw_output.txt`. Komórka główna ρ = 0,8, n = 1 600 dni, K = 20 monet, 5 000 paneli
(SE odsetka ≤ 0,7 pp).

| kryterium | p = 1 % | p = 5 % | wymaganie |
|---|---|---|---|
| K1 rozmiar testu zbiorczego (prognoza prawdziwa) | 3,9 % | 4,3 % | [2,5; 7,5] % |
| K2 moc wobec σ zaniżonego o 30 % | 100 % | 100 % | ≥ 95 % |
| K3 rozmiar „naiwnego” Kupca (20·n jak niezależne) | 25,8 % | 45,0 % | > 10 % |
| ii-a moc wobec prognozy normalnej | 100 % | (opis) 41,2 % | ≥ 80 % (tylko 1 %) |
| ii-b moc wobec prognozy stałej | 98,3 % | 99,4 % | ≥ 80 % |
| iii MDE zaniżenia σ | 0,083 | 0,079 | ≤ 0,10 |
| **wynik reguły (obowiązującej)** | **MIERZALNA** | **MIERZALNA** | |
| opis: reguła pierwotna | MIERZALNA | NIEMIERZALNA | (x\* = 0,05; ii-a przy 5 %) |

- **Przewidywania:** P1 (testy pojedynczej monety za słabe) sprawdziło się: Kupiec per moneta 44 % / 36 %
  (normalna / stała), cc 36 % / 44 %, Z2 81 % / 27 %. P2 i P3 (MIERZALNA przy 5 % i 1 %) też się
  sprawdziły. Nie były ślepe (zapisane po pilotażu).
- **Najmniejszy zapas:** iii przy p = 1 %: MDE 0,083 przy progu 0,10 (zapas ok. 0,017); skrypt nie zgłosił
  flagi „blisko progu” (2 SE) dla żadnego kryterium.
- **Warunek przeniesienia na dane:** VR dziennej sumy trafień na prawdziwych danych ≤ 2,98 (p = 1 %)
  i ≤ 6,29 (p = 5 %).
- **Mapa (opis):** przy n = 600 dni reguła daje NIEMIERZALNA (ρ = 0,8, obie p; ρ = 0,5 przy 1 %); od
  n = 1 000 wszędzie MIERZALNA. MDE testu zbiorczego przy ρ = 0,8: 0,122 / 0,094 / 0,083 / 0,077
  (p = 1 %, n = 600 / 1 000 / 1 600 / 2 100).
- **Opis, ważne dla następnej rundy:** realistyczne prognozy z ESTYMOWANĄ σ i poprawnym ogonem t5 mają za
  dużo trafień (okno 60 dni: 1,38 % zamiast 1 %; EWMA 0,94: 1,28 %; przy 5 %: 5,89 % i 5,83 %);
  prawdopodobna przyczyna: błąd estymacji σ pogrubia ogon (hipoteza, w tej rundzie niesprawdzana). Test zbiorczy odrzuca je w 78–98 % paneli. Jeśli tak jest też na prawdziwych
  danych, odrzucenie prognozy nie znaczy „model bezużyteczny”, tylko „nie skalibrowany”.
- **Opis:** test zbiorczy słabo widzi zaniżony ES przy dobrym VaR (es_za_niski: 26 % przy 1 %, 47 % przy
  5 %); Z2 per moneta 17 % i 35 %.

## Co na plus (+) / Co na minus (−)

**(+)** Wszystkie trzy kontrole silnika przeszły: rozmiar 3,9 % i 4,3 %; zaniżenie σ o 30 % łapane w 100 %;
naiwne traktowanie 20 monet jak niezależnych daje 26–45 % fałszywych alarmów, czyli R12 jest istotne
i test zbiorczy je obsługuje. Przy ~1 600 dniach i 20 monetach wykrywamy zaniżenie zmienności o ok.
8 % (p = 1 % i 5 %). Pojedyncza moneta wykrywa dopiero ok. 14–17 % przy p = 1 % i ok. 10–13 % przy p = 5 %. Przewidywania sprawdziły się.
**(−)** (1) Reguła przy 5 % była poprawiona po pilotażu (decyzja użytkownika). Według reguły pierwotnej
przy 5 % wyszłoby NIEMIERZALNA. (2) K1 dotyczy prognozy-wyroczni. Rozmiar przy modelu estymowanym jest
nieznany, a prognozy realistyczne są odrzucane, więc przed rundą na danych potrzebna jest kontrola LV2.
(3) Generator ma tylko gaussowską zależność między monetami (stałe ρ, bez wspólnych skoków), więc to
raczej górne oszacowanie mocy. Warunek VR trzeba sprawdzić na danych. (4) Test B (grupowanie) ma okno
10 dni dobrane na pilotażu tego generatora. (5) Zaniżony ES przy dobrym VaR jest słabo wykrywalny.

## Werdykt

**Caveats.** Według reguły z pre-rejestracji (poprawionej, decyzja użytkownika 2026-10-06) LV1 jest
**MIERZALNA przy p = 1 % i p = 5 %**: przy ok. 1 600 dniach × 20 monetach test zbiorczy odróżnia dobrą
prognozę ryzyka od zaniżonej o ok. 8 % zmienności. Warunki przed jakąkolwiek rundą VaR/ES na prawdziwych
danych:
1. **LV2:** rozmiar i moc przy prognozie ESTYMOWANEJ (okno/EWMA/GARCH dopasowany na danych). Pytanie
   rundy na danych powinno być porównawcze albo dotyczyć kalibracji, bo w tym generatorze test odrzucał
   nawet rozsądne modele estymowane (EWMA 78 %, okno 60 dni 93–98 %).
2. Populacja ≥ 20 monet z ≥ 1 600 dniami OOS; monety z ok. 600 dniami osobno albo wcale.
3. Sprawdzić VR na danych (≤ 2,98 / 6,29) bez patrzenia na wynik prognoz.
4. Licznik „ryzyko 2021+”: 0 (bez zmian, dane syntetyczne).

## Wniosek

**Prostym językiem:** w sztucznym świecie podobnym do naszego (ok. 4–5 lat, 20 monet) prognozy ryzyka da się
sprawdzić, ale tylko zbiorczo dla całego koszyka. Na prawdziwych danych zależy to od warunków z Werdyktu. Pojedyncza moneta to za mało. Wykryjemy, jeśli prognoza zaniża
wahania o ok. 8 % lub więcej. Jest jedna niespodzianka: w symulacji nawet rozsądne, codziennie liczone prognozy
(okno 60 dni, EWMA) test uznawał za źle skalibrowane, prawdopodobnie dlatego, że samo szacowanie zmienności pogrubia ogon. Następny
krok (LV2) powie, jak uczciwie oceniać takie realistyczne prognozy, zanim dotkniemy prawdziwych danych.

## Użyte skille

Brak wczytanych skilli (rachunki i kod własne; procedura rundy wg CLAUDE.md beta, zasady 25–26).
