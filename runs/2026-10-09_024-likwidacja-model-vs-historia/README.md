# 024 — czy model prawdopodobieństwa likwidacji zgadza się z historią (BTC, ETH, SOL, BNB)

**Status: PRE-REJESTRACJA (zapisana przed odczytem cen high/low). Wyniku jeszcze nie ma.**
Typ: pytanie o ryzyko (nie o zwrot). Licznik „ryzyko 2021+”: **0 → 1 w chwili uruchomienia** (decyzja #1 w `STATUS.md`).
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

## Użyte skille

`clas5-runda` (procedura), `data:statistical-analysis` (test Poissona, mierzalność), `engineering:code-review` (przed scaleniem) — wpis
uzupełnię przy wyniku.
