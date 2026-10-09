# 024 — czy model prawdopodobieństwa likwidacji zgadza się z historią (BTC, ETH, SOL, BNB)

**Status: ZAKOŃCZONA, werdykt Caveats (poniżej, sekcja „Wynik”). Pre-rejestracja (sekcje R1–R4, Przewidywania, Granice) zapisana w commicie `6134ed0` PRZED odczytem high/low; kod części z wynikami `b5904a2`; jedno uruchomienie rejestrowe.**
Typ: pytanie o ryzyko (nie o zwrot). Licznik „ryzyko 2021+”: **0 → 1** (uruchomienie rejestrowe 2026-10-09).
Rejestr zwrotów alpha (N = 40) nietknięty: nic tu nie liczy zwrotu strategii.

## Pytanie prostym językiem

Kalkulator z karty 023 mówi, jak prawdopodobne jest „dotknięcie” ceny likwidacji w ciągu 7 dni (np. przy dźwigni 3×
cena musi spaść ok. o 32 %). Karta 023 ostrzega, że to prawdopodobnie liczba za niska. Ta runda sprawdza to na prawdziwej
historii: **ile razy cena rzeczywiście dotknęła progu likwidacji w ciągu 7 dni od wejścia, a ile razy spodziewał się tego model?**
Jeśli rzeczywistych zdarzeń jest wyraźnie więcej, kalkulator nie może pokazywać swojego P bez poprawki.

## R1. Mechanizm jednym zdaniem

Likwidacje wzmacniają ruch (zlikwidowani muszą sprzedać), a ogony zwrotów krypto są grubsze, niż wynika z rozkładu t o stałych
parametrach wyestymowanych na zwykłych dniach — więc model, który zakłada ciągły ruch ze stałą zmiennością, zaniża szansę
rzadkiego, głębokiego ruchu; tracą ci, którzy wierzą w to P i trzymają za dużą dźwignię.

## R2. Hipoteza (zbiór informacyjny × formuła × target × horyzont)

- **Informacja:** zwroty dzienne koszyka do zamknięcia dnia wpisu (panel wspólny, 2 091 dni; kolejność i wycięcia jak w 017–021).
- **Formuła (zamrożona, bez strojenia):** GARCH(1,1)-t walk-forward (pierwsze dopasowanie na 400 zwrotach, ponowne co 30 dni, ciepły start;
  `modele/likwidacja_model.py`), σ̂ na dzień po wpisie stała w oknie, `p_likwidacji(..., dni = 7, dotkniecie = True)` z `modele/ryzyko_pozycji.py`.
- **Target:** zdarzenie „dotknięcie progu”: pozycja otwarta po cenie zamknięcia dnia *d*; long: `low_{d+k} ≤ close_d · (1 − (1/L − mmr))`,
  short: `high_{d+k} ≥ close_d · (1 + (1/L − mmr))` dla którego(kolwiek) *k* = 1…7. Dzienna świeca jest dokładna dla dotknięcia (łapie wahnięcia
  śróddzienne).
- **Horyzont:** 7 dni. **Dźwignie:** 3× (poziom główny), 5× i 8× (opisowe: sprawdzają ogon tam, gdzie zdarzeń jest więcej). **mmr = 1 %**
  (jak w alpha LQ1, żeby liczby były porównywalne). Strony: long i short.
- To jest dokładnie to, co robi kalkulator z karty 023. Nic nie jest tu dobierane po fakcie.

## R3. Mierzalność (policzona PRZED odczytem wyników; `raw_mierzalnosc.txt`)

Z modelu (nie z cen high/low): oczekiwana liczba zdarzeń. 1 671 wpisów z pełnym oknem 7 kolejnych dni na monetę, 4 monety.
Cztery monety nie są czterema obserwacjami (R12): dzielę „E z bloków niezależnych 7-dniowych” przez VR = 2,264 (karta 020, K = 4).

| L | strona | E okien (nakładających się) | E w blokach 7 d | **E niezależnych** |
|---|---|---|---|---|
| 3× | long | 61,9 | 8,62 | 3,81 |
| 3× | short | 171,1 | 23,92 | 10,56 |
| **3× razem** | | | 32,5 | **14,4** |
| 5× | long / short | 365 / 569 | 51 / 80 | 22,6 / 35,4 |
| 8× | long / short | 1 122 / 1 350 | 159 / 191 | 70,1 / 84,5 |

Wymagane E (moc 80 %, jednostronny test Poissona, α = 5 %): zaniżenie 1,5× → E ≥ 31; 2× → E ≥ 10; 3× → E ≥ 3,5.
**Poziom główny (3× long + short razem, E ≈ 14,4) jest mierzalny dla zaniżenia ≥ 2×** (nie dla 1,5×; wynik „nie wykazano” nie
znaczy wtedy „model dobry”). 5× i 8× są mierzalne nawet dla 1,5×. Przybliżenie: VR=2,264 pochodzi ze zwrotów, nie z progowych
zdarzeń — pokażę wyniki także dla VR = 1 i 4 jako opis wrażliwości. Dodatkowa uwaga: dopasowanie GARCH-t jest przy granicy lub
niezbieżne w 72 % / 68 % / 0 % / 66 % dni dla BTC / ETH / SOL / BNB (dla tych monet σ̂ to w praktyce silnie wygładzony poziom).

## R4. Kryteria zapisane z góry

1. **Zdarzenie niezależne:** trafienia (dowolna moneta, dowolna strona danego poziomu) o dniach wpisu odległych o ≤ 7 dni scalam w jeden
   klaster (łańcuchowo). **O** = liczba klastrów na poziom.
2. **Statystyka:** `O` wobec `E niezależnych` z R3; p = P(Poisson(E) ≥ O), jednostronnie. Iloraz `O / E`.
3. **Poziom główny (jedyny rozstrzygający): 3×, long + short razem.** Werdykt „**model zaniża**” gdy **p < 0,05 ORAZ O/E ≥ 1,5**
   (dwa warunki, jak R9). W przeciwnym razie „**nie wykazano zaniżenia**” (z zaznaczeniem mocy: wykrywalne ≥ 2×).
4. 5× i 8× oraz 3× osobno long/short: opis (p i iloraz), bez własnego werdyktu. Wrażliwość na VR ∈ {1; 2,264; 4}: opis.
5. **Co z tym zrobię:** „model zaniża” → w kalkulatorze P likwidacji dostaje etykietę „zaniżone o czynnik ≈ O/E (3×)” i jest mnożone
   przez ten czynnik w wydruku, nigdy nie służy do zwiększania dźwigni; „nie wykazano” → etykieta „dolne oszacowanie, niepotwierdzone”.
   W obu przypadkach kalkulator służy tylko do ZMNIEJSZANIA ekspozycji.
6. **Reguła STOP:** jeżeli przed werdyktem okaże się, że dane high/low mają dziury w >5 % okien albo kolumny są złe — przerywam, nie liczę
   werdyktu, wpisuję przyczynę. Przebieg rejestrowy robię **raz**; nie powtarzam z powodu wyniku, nie zmieniam L, mmr, h ani
   procedury po obejrzeniu wyniku (to byłby nowy wariant z osobnym licznikiem).

## Przewidywania (zapisane przed wynikiem; po rachunku z E, żeby nie powtórzyć błędu mocy z 021)

- O/E dla 3× będzie ≥ 1,5 (model zaniża) — pewność ok. 60 %. Ogony po 2021 (maj 2021, czerwiec 2022, listopad 2022, październik 2025)
  to szybkie ruchy, których t_ν ze stałą σ nie przewiduje.
- Dla 8× O/E będzie bliżej 1 niż dla 3× (głębokie progi zależą od ogona, płytkie od σ), choć to może się odwrócić — pewność ok. 50 %.
- Short: model zakłada symetrię zwrotu log, a rzeczywiste ogony są asymetryczne; nie przewiduję kierunku różnicy.

## Granice (zapisane z góry)

- Świece to ceny ostatniej transakcji (*last price*); giełda likwiduje po cenie *mark*, mniej podatnej na wahnięcia → obserwowane zdarzenia
  są górnym oszacowaniem prawdziwych likwidacji. Wynik „model zaniża” może więc być częściowo artefaktem.
- Brak opłat, funduszu, stopni mmr giełdy i dokładania depozytu; stała dźwignia od wejścia.
- Cztery monety z jednej epoki (2021–2026), kilka rzeczywistych kryzysów: wynik opisuje te kryzysy, nie ich rozkład.
- Kontrole pozytywna i negatywna silnika: test braku podglądu przyszłości (`tests/test_likwidacja_model.py`) oraz test wzoru na symulacji
  (`tests/test_ryzyko_pozycji.py`); na danych syntetycznych z modelem zgodnym ze wzorem kontrola negatywna (O/E ≈ 1) jest częścią przebiegu
  testowego runnera (dopisana przed uruchomieniem).

## Wynik (`raw_output.txt`, jedno uruchomienie rejestrowe)

Dane: 1 671 wpisów z pełnym oknem 7 dni (98,8 %), świece high/low/close kompletne i spójne dla wszystkich 2 091 dni panelu (STOP z R4.6 nie zadziałał).

**Poziom główny — 3×, long + short razem:**

| O (klastry dotknięć) | E (model, niezależne) | O/E | p (Poisson) | progi z góry | werdykt skryptu |
|---|---|---|---|---|---|
| **23** | 14,37 | **1,60** | **0,0217** | p < 0,05 ORAZ O/E ≥ 1,5 | oba spełnione → „model zaniża” |

Opis pozostałych poziomów (bez własnego werdyktu, R4.4):

| poziom | O | E niezal. | O/E | p | O/E przy VR 1 / 4 |
|---|---|---|---|---|---|
| 3× long | 10 | 3,81 | 2,63 | 0,006 | 1,16 / 4,64 |
| 3× short | 18 | 10,56 | 1,70 | 0,023 | 0,75 / 3,01 |
| 5× long | 36 | 22,64 | 1,59 | 0,006 | 0,70 / 2,81 |
| 5× short | 49 | 35,38 | 1,39 | 0,017 | 0,61 / 2,45 |
| 8× long | 55 | 70,09 | 0,78 | 0,97 | 0,35 / 1,39 |
| 8× short | 54 | 84,48 | 0,64 | 1,00 | 0,28 / 1,13 |

Opis „na surowo”, bez klastrów (nakładające się okna 7-dniowe, 4 monety): 3× long 89 trafień wobec 61,9 oczekiwanych (iloraz 1,44),
3× short 108 wobec 171,1 (0,63), razem 3× **197 wobec 233 (0,85)**. 5×: 1,18 / 0,78. 8×: 1,08 / 0,96. Z 197 trafień okien 3× aż 127 (64 %) to SOL
(BTC 8, ETH 45, BNB 17). Pierwsze dni 23 klastrów głównego poziomu: od 2022-05-04 (Luna) przez 2022-11-01 (FTX) po 2026-08-14.

Przeliczenie niezależne (`przeliczenie_niezalezne.py`, zwykła pętla po plikach parquet i σ̂/ν̂ z zapisu, bez importu funkcji runnera):
**O = 23, E = 14,37, O/E = 1,60, p = 0,0217** — zgodne co do cyfry.

## Ocena przewidywań (zapisanych przed wynikiem)

- „O/E dla 3× ≥ 1,5” (pewność 60 %): **trafione** (1,60) — ale tylko o 0,10 ponad próg.
- „8× bliżej 1 niż 3×” (50 %): **trafione** dla stron osobno (8×: 0,78 i 0,64 wobec 3×: 2,63 i 1,70); wiersz „8× razem” (O/E 0,15) NIE jest
  porównywalny — patrz „Co na minus”.
- Short: nie przewidywałem kierunku; wyszło, że klastry 3× short też przekraczają model (1,70), choć na surowych oknach model short ZAWYŻA (0,63).

## Co na plus (+)

- Pre-rejestracja przed wynikiem; kod, testy (w tym `hypothesis` na klastrach i monotoniczności dotknięć) i kontrole symulacyjne zacommitowane przed przebiegiem.
- Kontrola negatywna na symulacji z modelem zgodnym: O/E 0,89 (oczekiwane 0,82–1,0: model to górne przybliżenie dla ścieżki ciągłej, siatka 48 kroków dziennych ją ścina);
  kontrola pozytywna (σ prawdziwa 2× większa): 2,46 (zakres 2,0–3,0). Test braku podglądu przyszłości dla σ̂ walk-forward (`tests/test_likwidacja_model.py`).
- Druga droga zgodna co do cyfry; dane high/low kompletne.
- Wynik jest spójny co do kierunku z zastrzeżeniem karty 023 („P likwidacji to dolne oszacowanie”) i z kosztem likwidacji 3× zmierzonym w alpha (LQ1).

## Co na minus (−)

- **Wynik brzegowy i zależny od przyjętej miary.** O/E = 1,60 przy progu 1,5 i p = 0,022 przy 0,05. E zależy od VR = 2,264 (karta 020, mierzone na zwrotach, nie na zdarzeniach
  progowych): przy VR = 1 O/E = 0,71 (model NIE zaniża), przy VR = 4 — 2,83. Zasada „dwa warunki” jest spełniona tylko dla VR zapisanego z góry.
- **Dwie miary liczenia dają różne odpowiedzi.** Na klastrach 3× O/E = 1,60, na surowych oknach 0,85 (model zawyża short 0,63, zaniża long 1,44). Klastry sklejają łańcuchowo
  trafienia (≤ 7 dni) i obniżają O w kryzysach, E z bloków 7-dniowych / VR nie ma tej samej definicji — O i E nie są liczone na jednej skali (przy 8× „razem”
  klastry zlewają się do 23 przy E = 154, więc ten wiersz jest bezużyteczny; to przyczyna, dla której 5× i 8× zapisałem jako opis).
- **Zaniżenie dotyczy głównie long, a ciężar niesie SOL i kilka epizodów** (127 z 197 trafień okien 3× to SOL; 23 klastry na 5 lat i 4 monety). Cztery monety z jednej epoki
  (R12) — wynik opisuje te kryzysy, nie rozkład przyszłych.
- Ceny to *last price*, giełda likwiduje po *mark price* → obserwowane dotknięcia są górnym oszacowaniem prawdziwych likwidacji (Granice, pkt 1). Brak opłat, funduszu, stopni mmr.
- σ̂ GARCH-t jest przy granicy persystencji w 66–72 % dni dla BTC/ETH/BNB; nie przeszła testu kalibracji (018 wstrzymana).
- Moc: dla zaniżenia 1,5× E = 14,4 to za mało na 80 % mocy, więc „nie wykazano” nie byłoby dowodem poprawności; wykryto zaniżenie ok. 1,6×, czyli tuż nad granicą mierzalności.

## Wniosek (prostym językiem)

Na historii BTC, ETH, SOL i BNB cena dotknęła progu likwidacji przy 3× w ciągu 7 dni około **1,6 raza częściej** (liczone w niezależnych epizodach), niż mówi model z kalkulatora.
Formalnie spełnia to oba warunki z pre-rejestracji, więc **kalkulator ma pokazywać P likwidacji 3× razy 1,6** (etykieta „zaniżone”). Ale to wynik na granicy:
zależy od tego, jak liczymy „niezależne” epizody, a na surowych oknach model wypada raczej poprawnie (0,85). Wniosek praktyczny jest jeden i ostrożny: **nie ufać modelowemu P jako górnej granicy
bezpieczeństwa, trzymać dźwignię poniżej celu z modelu, nie zwiększać jej.** Ten wynik nie jest dowodem na żadną strategię.

## Werdykt: **Caveats**

Formalnie „model zaniża” (3×, O/E 1,60, p 0,022), przeliczenie niezależne zgodne, kontrole symulacyjne zaliczone; zastrzeżenia obowiązkowe przy każdym użyciu: wynik brzegowy, zależny od VR i od sposobu
liczenia klastrów, głównie long i SOL, *last price* zamiast *mark*. Pytanie, czy zaniżenie jest realne (inna miara, więcej danych, dłuższa historia), pozostaje otwarte — nowa runda = nowy wariant z osobną pre-rejestracją
i licznikiem „ryzyko 2021+” 1 → 2.

## Skutek dla kalkulatora (karta 023)

`modele/rozmiar_dzis.py`: stała `KOREKTA_P_3X = 1.6` i kolumna `P_likw_3x_7d_kor_%` = min(100, 1,6 × P_likw_3x_7d_%) obok modelowej. Korekta dotyczy tylko poziomu 3× (jedynego z werdyktem);
służy wyłącznie do ZMNIEJSZANIA ekspozycji, nie do zwiększania dźwigni.

## Użyte skille

- `clas5-runda` — procedura rundy (pre-rejestracja przed wynikiem, katalog rundy, wiersz w INDEX, wniosek skumulowany).
- `data:statistical-analysis` — test Poissona i rachunek mocy (R3), ostrożność przy wielu miarach i wrażliwości na VR.
- `data:validate-data` — druga droga niezależna, sprawdzenie kompletności i spójności high/low, red-flag „wynik tuż nad progiem”.
- `engineering:code-review` — przegląd własnego kodu przed scaleniem (poniżej).

### Przegląd kodu (`engineering:code-review`)

Przejrzane: `modele/likwidacja_zdarzenia.py`, `modele/run_lq024.py`, `modele/likwidacja_model.py`, testy. Brak błędów zmieniających liczby (potwierdza druga droga).
Uwagi: (1) O i E na różnych definicjach „niezależności” (opisane w „Co na minus”; wynika z pre-rejestracji, nie zmieniane po fakcie); (2) wpis `ok` i `p[::DNI]` liczone na tablicach
przefiltrowanych — spójne z `run_lq024_mierzalnosc` (E zgodne co do cyfry z rachunkiem mierzalności); (3) `dotkniecia` zgłasza wyjątek przy wpisie bez pełnego okna zamiast cicho obcinać.
Werdykt przeglądu: Ready.
