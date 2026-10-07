# 017 — inwentarz 15 monet i zależność trafień ρ_h (karta opisowa, bez oceny prognozy)

## Metadane

- Karta: `zadania/017-dane-pod-runde-var-es-inwentarz-i-rho.md`. Rodzic: LV2 (`runs/2026-10-07_lv2-var-es-estymowane/`,
  sekcja „Werdykt”, warunki przeniesienia 1 i 2).
- Licznik: **opisowy, poza licznikami**. Licznik „ryzyko ogona (VaR/ES) 2021+” **zostaje 0**: nic tu nie testuje
  prognozy. Rejestr zwrotów alpha nietknięty.
- Komenda (po zatwierdzeniu pre-rejestracji): `python -m modele.pomiar_rho_h > runs/2026-10-07_017-inwentarz-i-rho/raw_output.txt`.
- Status tego pliku: **pre-rejestracja** (sekcja „Wynik” jest pusta do czasu przebiegu).

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

## Wynik

(po przebiegu)

## Użyte skille

(po przebiegu)
