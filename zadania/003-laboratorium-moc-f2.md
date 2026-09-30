---
id: 003
tytul: laboratorium symulacji i rachunek mocy dla porównania prognoz zmienności
typ: badawcze
status: czeka_na_decyzje
zlecil: orkiestrator
decyzja_uzytkownika: "brak (PRD D2 — kolejność filarów)"
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

(dopisuje orkiestrator)
