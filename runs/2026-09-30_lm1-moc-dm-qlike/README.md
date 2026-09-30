# LM1 — laboratorium F1: moc testu DM na stracie QLIKE przed rundą F2-1 (2026-09-30)

> **STATUS: PRE-REJESTRACJA (przed przebiegiem).**

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
