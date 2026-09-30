# LM1 — laboratorium F1: moc testu DM na stracie QLIKE przed rundą F2-1 (2026-09-30)

> **STATUS: ZAMKNIĘTA — MIERZALNA (według reguły), z zastrzeżeniem.** Kontrole DM zaliczone (negatywna
> 3,8 % i 4,9 %, pozytywna 99,8 %). MDE kryterium F2 przy n = 2 100, ρ = 0,8: **0,066 ≤ 0,10**.
> Zastrzeżenie: wynik zależy od autokorelacji różnicy strat — przy N_eff/n ≈ 0,3 (szkic PRD) MDE rośnie do
> 0,10–0,11, czyli na granicę. Przed startem F2-1 MDE trzeba przeliczyć na prawdziwym kształcie strat.
> Pre-rejestracja `0efaedb`. 0 wariantów, poza licznikami.
> Poprzednio: **PRE-REJESTRACJA (przed przebiegiem).**

## W skrócie — prostym językiem

Zanim porównamy na prawdziwych danych nowy model zmienności (HAR-RV) z tym, czego dziennik używa dziś
(odchylenie z okna wstecz), sprawdzamy na sztucznych danych, **jak dużą przewagę nasz test w ogóle
zauważy**. Jeśli prawdopodobna przewaga jest mniejsza niż to, co test widzi — runda F2-1 nie startuje
(zasada R3), bo niczego by nie rozstrzygnęła.

## Metadane

- Zadanie 003 (etap E1). Decyzja użytkownika 2026-09-30: „Rób co chcesz, ma działać” — przyjęta jako
  zgoda na rekomendacje D2 (kolejność F0 → F1 → F2) i D4.
- Kod: `miara/dm.py` (QLIKE, HAC Newey–West, DM), `symulacje/garch_panel.py` (generator GARCH(1,1)-t
  z czynnikiem rynkowym i RV), `symulacje/moc_dm.py` (bootstrap stacjonarny, moc, MDE); testy
  `tests/test_dm_symulacje.py` (m.in. HAC = statsmodels do 1e-10, brak przecieku σ² i prognoz).
- Skrypt `symulacje/run_lm1.py`; komenda `python -m symulacje.run_lm1` → `raw_output.txt`.
- Dane: WYŁĄCZNIE syntetyczne. Generator: GARCH(1,1) α 0,08 β 0,90, szok dzienny t (ν 5), zmienność
  4 %/dzień, czynnik rynkowy ρ ∈ {0; 0,5; 0,8}, RV = wariancja dnia × χ²₂₈₈/288 (szum pomiaru 5m).
  Kalibracja tylko do momentów (nigdy do średniej); dopasowanie do momentów PRAWDZIWYCH monet czeka
  na dane z zadania 002 (sieć środowiska blokuje dziś `data.binance.vision`).

## Pre-rejestracja (zapisana przed przebiegiem)

- **Mechanizm (R1):** brak — kalibracja przyrządu, nie hipoteza rynkowa.
- **Kryterium F2 (PRD §10.4), którego moc liczymy:** DM t > 1,96 na korzyść modelu w ≥ 16 z 20 monet
  i żadna moneta z t < −1,96. Strata QLIKE, HAC Newey–West z L = ⌊4 (n/100)^{2/9}⌋.
- **Kształt różnicy strat:** okno 30 dni − wyrocznia σ² na panelu 20 × 20 000 dni, centrowany per moneta
  (H0), bootstrap stacjonarny z tymi samymi indeksami dla wszystkich monet (blok średnio 30 dni; wrażliwość
  10 i 60), 1 000 losowań, efekt δ w jednostkach odchylenia różnicy strat, siatka 0…0,30 co 0,005.
- **Siatka:** n ∈ {500; 1 000; 2 100} dni OOS × ρ ∈ {0; 0,5; 0,8}. MDE = najmniejsze δ z mocą ≥ 80 %.
- **Kontrola NEGATYWNA DM:** dwie bliźniacze prognozy σ²·e^η (η ~ N(0; 0,25²) niezależnie) na 50 panelach
  × 20 monet (ρ = 0) — ZALICZENIE, gdy odsetek |t| > 1,96 ∈ [2,5 %; 7,5 %] przy n = 2 100 i n = 500.
- **Kontrola POZYTYWNA DM:** wyrocznia σ² vs prognoza stała σ̄² — ZALICZENIE, gdy t > 1,96 w ≥ 95 %
  z 1 000 szeregów (n = 2 100).
- **Reguła werdyktu dla F2-1:** MIERZALNA ⇔ MDE kryterium przy n = 2 100 i ρ = 0,8 (ostrożny koniec
  korelacji krypto 0,47–0,86) ≤ 0,10 (efekt ze szkicu PRD: t ≈ 0,1 × √700 ≈ 2,6). Inaczej NIEMIERZALNA.
  Jeśli którakolwiek kontrola nie przejdzie — werdykt wstrzymany do naprawy przyrządu.
- **Opis (nie kryterium):** δ wyroczni i δ EWMA wobec okna w świecie generatora (górna granica i
  realistyczny konkurent), N_eff/n różnicy strat, korelacja różnic strat między monetami.
- **Liczniki:** 0 wariantów, POZA licznikami (dane syntetyczne; licznik „zmienność 2021+” = 0 bez zmian).

## Wynik

`raw_output.txt` (17 s). Dwie poprawki skryptu PRZED pierwszym wydrukiem liczb: `straty()` wołało
`.iloc`/`.to_numpy()` na tablicy numpy (przebieg padał w sekcji 1, zanim cokolwiek wypisał). Projekt i
kryteria bez zmian.

**Świat generatora** (20 000 dni × 20 monet): zmienność 3,9–4,0 %/dzień, nadwyżka kurtozy 10–12,
acf(r²) 0,15–0,18, korelacja zwrotów 0 / 0,37 / 0,60 dla ρ 0 / 0,5 / 0,8. Wyrocznia bije okno 30 dni
o δ ≈ 0,11–0,12, EWMA 0,94 o δ ≈ 0,11. Różnica strat ma acf1 ≈ 0,04 i N_eff/n ≈ 0,78; korelacja różnic
strat między monetami ≈ 0,00 (!).

**Kontrole przyrządu DM:**

| kontrola | n | wynik | kryterium |
|---|---|---|---|
| negatywna (bliźniacze prognozy) | 2 100 | 38/1 000 = 3,8 % [2,8; 5,2], sd t 0,995 | ✓ ∈ [2,5; 7,5] % |
| negatywna | 500 | 49/1 000 = 4,9 % [3,7; 6,4], sd t 1,019 | ✓ |
| pozytywna (wyrocznia vs stała) | 2 100 | 998/1 000 = 99,8 %, mediana t 7,5 | ✓ ≥ 95 % |
| opis: wyrocznia vs okno 30 | 2 100 / 500 | 99,5 % / 86,5 %, mediana t 5,4 / 2,8 | — |

**MDE (δ = średnia / odchylenie różnicy strat; moc 80 %):**

| ρ | n = 500 | n = 1 000 | n = 2 100 |
|---|---|---|---|
| 0,0 | 0,116 | 0,088 | 0,064 |
| 0,5 | 0,114 | 0,086 | 0,063 |
| 0,8 | 0,118 | 0,090 | **0,066** |

MDE jednej monety jest o ~0,005 niższe. Pod H0 (δ = 0) kryterium nie przechodzi ani razu na 1 000
losowań. Długość bloku bootstrapu 10 / 60 daje 0,064 / 0,067.

**Reguła z pre-rejestracji:** 0,066 ≤ 0,10 → **MIERZALNA**.

### Diagnostyka dopisana PO przebiegu (reguła werdyktu bez zmian)

`raw_output_korelacja.txt`, skrypt `symulacje/run_lm1_korelacja.py`. Powód: generator nie dał korelacji
różnic strat między monetami, a szkic PRD zakładał N_eff/n ≈ 0,33 zamiast 0,78. Wymuszona korelacja D
(c) i autokorelacja AR(1) φ = 0,5 (N_eff/n ≈ 0,30), n = 2 100:

| korel. D | N_eff/n | MDE kryterium |
|---|---|---|
| 0,00 / 0,33 / 0,62 / 0,91 | 0,71–0,79 | 0,064 / 0,069 / 0,069 / 0,066 |
| 0,00 / 0,34 / 0,63 / 0,91 | 0,28–0,30 | **0,100 / 0,108 / 0,110 / 0,108** |

Korelacja między monetami prawie nie przesuwa MDE (efekt dotyczy wszystkich monet naraz, próg jest per
moneta). Decyduje autokorelacja straty: MDE ≈ 2,8 / √N_eff.

## Co na plus (+) / Co na minus (−)

**(+)** Przyrząd DM ma poprawny rozmiar (3,8 % i 4,9 % przy nominalnych 5 %, sd t ≈ 1) mimo grubych
ogonów (kurtoza ~11) i wykrywa znany sygnał. HAC zgodny ze statsmodels do 1e-10. Kryterium F2 nie
przechodzi na szumie (0/1 000). Przy ~2 100 dniach OOS test widzi przewagę δ ≈ 0,07, jeśli strata ma
autokorelację jak w generatorze.
**(−)** W świecie generatora nawet WYROCZNIA wygrywa z oknem 30 dni tylko o δ ≈ 0,12, a EWMA o 0,11 —
zakładane 0,10 dla HAR jest blisko sufitu, więc realny zysk HAR może leżeć PONIŻEJ MDE. Generator nie
odtwarza wspólnej zmienności rynku (korelacja różnic strat ≈ 0) ani długiej pamięci zmienności, którą ma
krypto; przy N_eff/n ≈ 0,3 MDE = 0,10–0,11, czyli werdykt przechodzi w NIEMIERZALNĄ. Momenty kalibrowane
„na oko” do typowych wartości krypto — prawdziwe czekają na dane (zadanie 002, zablokowane siecią).

## Werdykt

**Caveats.** Według reguły z pre-rejestracji F2-1 jest MIERZALNA (MDE 0,066 ≤ 0,10). Wynik jest jednak
warunkowy: zależy od autokorelacji różnicy strat. **Warunek startu F2-1:** przeliczyć MDE bootstrapem na
CENTROWANEJ różnicy strat okno − EWMA z prawdziwych danych (sam kształt, bez średniej — nie zużywa
licznika „zmienność 2021+”). Jeśli MDE > 0,10 → F2-1 NIEMIERZALNA przy n ≈ 2 100; wtedy albo tydzień
(horyzont 7 dni) zamiast dnia, albo dłuższa historia, albo rezygnacja.

## Wniosek

**Prostym językiem:** nasz test porównujący prognozy zmienności działa poprawnie — na szumie myli się
tak rzadko, jak powinien, a prawdziwą przewagę widzi. Czy zobaczy przewagę HAR nad obecnym oknem,
zależy od tego, jak „lepkie” są błędy prognoz w prawdziwych danych: w naszym sztucznym świecie — tak,
przy lepkości zakładanej w PRD — ledwo, na granicy. Rozstrzygną to prawdziwe dane, zanim runda F2-1 ruszy.

## Użyte skille

Brak wczytanych skilli w tej sesji — procedura rundy wzorowana na alpha NC1 i CLAUDE.md beta (zasady 25–26).
