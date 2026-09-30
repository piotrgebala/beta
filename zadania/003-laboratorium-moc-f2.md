---
id: 003
tytul: laboratorium symulacji i rachunek mocy dla porównania prognoz zmienności
typ: badawcze
status: do_przegladu
zlecil: orkiestrator
decyzja_uzytkownika: "2026-09-30: „Rób co chcesz, ma działać” — zgoda na rekomendacje D2 i D4"
utworzono: 2026-09-30
zalezy_od: [001]
budzet: "Opus, 1–2 sesje"
---

# 003 — laboratorium i moc testu DM na QLIKE

## Po co

Etap E1 PRD. Zanim porównamy HAR-RV z oknem wstecz na prawdziwych danych, trzeba wiedzieć, jaki najmniejszy
zysk w stracie QLIKE przyrząd w ogóle zobaczy (zasada R3). Szkic w PRD (t ≈ 2,6) to założenie do sprawdzenia.

## Zakres

- `symulacje/`: GARCH(1,1)-t, bootstrap blokowy stacjonarny, czynnik rynkowy dla koszyka; kalibracja tylko do
  momentów (zmienność, kurtoza, autokorelacja kwadratów), nigdy do średniego zwrotu.
- Test DM z HAC (Newey–West) w `miara/`; kontrola pozytywna (prognoza z prawdziwego procesu vs okno wstecz)
  i negatywna (dwie prognozy równoważne → odrzucenia ≈ 5 %).
- MDE (minimalny wykrywalny efekt) dla n ≈ 2 100 dni/monetę i 20 monet ze skorelowanym czynnikiem.

## Czego NIE robić

Bez odczytu prawdziwych danych rynkowych; bez wyboru modelu.

## Kryteria odbioru (dowody)

Tabela MDE × n × korelacja w `runs/`; kontrola negatywna 5 % ± przedział z symulacji; werdykt MIERZALNA /
NIEMIERZALNA dla rundy F2-1.

## Wynik

2026-09-30, runda LM1 (`runs/2026-09-30_lm1-moc-dm-qlike/`), werdykt **Caveats**.

- `miara/dm.py` (QLIKE, MSE log RV, HAC NW = statsmodels do 1e-10, DM), `symulacje/garch_panel.py`,
  `symulacje/moc_dm.py`; 16 testów w `tests/test_dm_symulacje.py`.
- Kontrola negatywna DM: 3,8 % [2,8; 5,2] (n 2 100) i 4,9 % [3,7; 6,4] (n 500); pozytywna 99,8 %.
- Tabela MDE × n × ρ w README rundy; MDE kryterium przy n 2 100: 0,063–0,066 → MIERZALNA wg reguły.
- Zastrzeżenie (diagnostyka po przebiegu): przy N_eff/n ≈ 0,3 MDE 0,10–0,11 — przed F2-1 przeliczyć na
  centrowanej różnicy strat z prawdziwych danych (wymaga zadania 002).
- Bez bootstrapu na PRAWDZIWYCH zwrotach (brak danych) — generator zamiast tego.
