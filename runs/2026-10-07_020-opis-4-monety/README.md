# 020 — opis zależności trafień VaR 5 % dla BTC, ETH, SOL, BNB (karta opisowa, bez oceny prognozy)

## Metadane

- Karta: `zadania/020-opis-zaleznosci-4-monety.md`. Zlecenie: decyzja użytkownika z 2026-10-07 („rób tylko prognozy na eth btc sol, bnb”,
  `STATUS.md`, „Decyzje użytkownika”). Poprzednik: 017 (`runs/2026-10-07_017-inwentarz-i-rho/`).
- Licznik: **opisowy, poza licznikami.** „Ryzyko ogona (VaR/ES) 2021+” **zostaje 0**: nic tu nie testuje prognozy. Rejestr zwrotów
  alpha nietknięty.
- Kod: `modele/opis_rho_h.py` + `tests/test_opis_rho_h.py`, commit `35eb867` (miara jest ta sama co w 017, `modele/pomiar_rho_h.py`
  bez zmian). Pełny zestaw testów przed commitem: 1 180 przeszło, 1 pominięty.
- Komenda (po zatwierdzeniu pre-rejestracji): `python -m modele.opis_rho_h > runs/2026-10-07_020-opis-4-monety/raw_output.txt`.
- Status tego pliku: **pre-rejestracja** (sekcja „Wynik” jest pusta do czasu przebiegu).

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

Wydruk **nie zawiera** odsetka trafień, statystyk testu zbiorczego, testów Kupca ani Christoffersena, progu 0,282, wyniku bramki ani
okna C2. Test jednostkowy pilnuje, że tych napisów i odsetka trafień w wydruku nie ma. Wynik idzie wyłącznie na stdout.

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

## Wynik

(po przebiegu)

## Użyte skille

(po przebiegu)
