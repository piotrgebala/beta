# LD1 — laboratorium F3: e-procesy dla dziennika alpha przy codziennym zaglądaniu (2026-10-01)

> **STATUS: PRE-REJESTRACJA (przed przebiegiem).**

## W skrócie — prostym językiem

Dziennik alpha oceniamy dziś trzy razy (po 3, 6 i 12 miesiącach) progiem z = 2,31. Chcemy obok mieć
„licznik dowodu”, na który wolno patrzeć codziennie bez zawyżania fałszywych alarmów (e-proces). Na sztucznych
dziennikach sprawdzamy dwie rzeczy: czy licznik rzadko krzyczy bez powodu i czy widzi prawdziwy zysk co najmniej
tak dobrze jak trzy odczyty z ADR-09. To tylko REPORTER — o nodze dalej decyduje ADR-09.

## Metadane

- Zadanie 004 (etap E3). D3 nierozstrzygnięta — budujemy reporter, co jest zgodne z obiema opcjami D3
  (rekomendacja „tylko reporter”); żadne kryterium alpha się nie zmienia.
- Kod: `dowody/eproces.py` (mieszanka jednostronna po połówce N(0, τ²), postać zamknięta zgodna z całką
  numeryczną do 1e-8), `dowody/bayes.py`, `dowody/nogi.py` (μ, σ nóg = kopia alpha, test zgodności),
  `dowody/raport.py`; testy `tests/test_dowody.py`.
- Skrypt `symulacje/run_ld1.py`; komenda `python -m symulacje.run_ld1` → `raw_output.txt`.
- Dane: WYŁĄCZNIE syntetyczne; 20 000 ścieżek × 365 dni na komórkę, ziarno 20261001.

## Pre-rejestracja (zapisana przed przebiegiem)

- **Mechanizm (R1):** brak — kalibracja przyrządu.
- **e-procesy:** obalenie (H0: μ = zakładane, m0 = μ_d, strona −1), potwierdzenie (H0: μ ≤ 0, strona +1);
  σ zakładana z ADR-09; τ = μ_d / σ_d² (alternatywa: zero przewagi / zakładane μ); próg e ≥ 40 (α = 2,5 %,
  jak łączna jednostronna szansa fałszywego obalenia w ADR-09). Patrzymy CODZIENNIE przez 365 dni.
- **Porównanie:** ADR-09 — trzy odczyty po 92/182/365 dniach, z = Σ (x − m0) / (σ √n) < −2,31 (obalenie),
  analogicznie > 2,31 (potwierdzenie, tylko do porównania mocy).
- **Rozkłady dziennych zwrotów:** normalny; t₃ (grube ogony); t₃ + GARCH(1,1) (grupowanie zmienności).
  Nogi: TS1, CP1, R1, X1 z μ, σ z ADR-09.
- **Bramka 1 (PRD F3):** fałszywe alarmy obu e-procesów ≤ 5 % (górna granica Wilsona 95 %), dla każdej nogi
  i każdego rozkładu.
- **Bramka 2 (PRD F3):** moc potwierdzenia przy prawdziwym +15 %/rok ≥ mocy trzech odczytów z = 2,31
  (rozkład normalny, każda noga).
- **Opis:** fałszywe alarmy ADR-09, moc obalenia przy μ = 0 (e-proces vs ADR-09).
- **Werdykt:** bramka 1 i 2 → reporter gotowy jako kandydat na kryterium (opcja D3-b do rozważenia);
  tylko bramka 1 → reporter tylko opisowy (D3-a); bramka 1 nie → reporter niegotowy, poprawka przyrządu.
- **Liczniki:** 0 wariantów, POZA licznikami (dane syntetyczne; dziennika nie czytamy w tej rundzie).
