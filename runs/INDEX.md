# runs/ — spis treści

## Stan wiedzy — skrót

Trzy rundy kalibracyjne (0 wariantów): NC1B — przyrząd `miara` zaliczył kontrolę negatywną; LM1 — test DM na QLIKE ma poprawny rozmiar, a F2-1 jest mierzalna tylko warunkowo (MDE 0,066 przy N_eff/n 0,78, ale 0,10–0,11 przy 0,3 — przeliczyć na prawdziwym kształcie strat przed startem); LD1 — e-procesy dla dziennika alpha poprawne (fałszywe alarmy ≤ 0,5 %), ale w rok prawie ślepe, więc F3 zostaje tylko reporterem (rekomendacja D3-a). Stan wiedzy odziedziczony: `alpha/runs/INDEX.md` (wnioski 1–111) i `docs/PRD.md` §2.

## Liczniki

| licznik | baza | odczyty | próg |
|---|---|---|---|
| zwroty strategii na historii 2021–2026 | **wspólny z alpha** (`odczyty_historii.csv`) | 40 (stan alpha 2026-09-30) | t ≈ 3,84 (DSR) |
| prognoza zmienności 2021+ | beta | 0 | t 1,96 + Holm |
| ryzyko ogona (VaR/ES) 2021+ | beta | 0 | testy PRD §10.4 |

## Tabela rund

| ID | data | katalog | opis | licznik | wynik |
|---|---|---|---|---|---|
| NC1B | 2026-09-30 | [nc1b-kontrola-negatywna-miara](2026-09-30_nc1b-kontrola-negatywna-miara/README.md) | Kontrola negatywna i czułości przyrządu `miara` na generatorze alpha (40 losowań × 20 monet × 2 000 dni), reguły trend 7 dni i przekrój top/bottom 5; pre-rejestracja `45c0b1b` | **0 — POZA licznikami** (kalibracja, dane syntetyczne) | **ZALICZONA:** śr. t −0,28 / −0,24, alarmy 2/80 = 2,5 % [0,7; 8,7] (alpha 3,3 %); czułość t +6,9…+40,4 w 40/40. **Ready** |
| LM1 | 2026-09-30 | [lm1-moc-dm-qlike](2026-09-30_lm1-moc-dm-qlike/README.md) | Laboratorium F1: rozmiar i moc DM (QLIKE, HAC) dla kryterium F2 (≥ 16/20 monet t > 1,96), generator GARCH(1,1)-t z RV, bootstrap stacjonarny, n × ρ; pre-rejestracja `0efaedb` | **0 — POZA licznikami** (dane syntetyczne) | **MIERZALNA wg reguły (MDE 0,066 ≤ 0,10), Caveats:** kontrole DM ✓ (3,8 % / 4,9 %; 99,8 %); przy N_eff/n ≈ 0,3 MDE 0,10–0,11 → warunek: przeliczyć na prawdziwym kształcie strat |
| LD1 | 2026-10-01 | [ld1-eproces-dziennik](2026-10-01_ld1-eproces-dziennik/README.md) | Laboratorium F3: e-procesy obalenia i potwierdzenia przy codziennym zaglądaniu 365 dni vs 3 odczyty ADR-09 (z 2,31), 4 nogi × 3 rozkłady; pre-rejestracja `aea82dd` | **0 — POZA licznikami** (dane syntetyczne) | **Bramka 1 TAK** (fałszywe alarmy ≤ 0,54 %), **bramka 2 NIE** (moc +15 %: ≤ 0,1 % vs 5–10 % ADR-09) → reporter opisowy, D3-a. **Ready** |
| DQ1 | 2026-10-05 | [dq1-jakosc-binance](2026-10-05_dq1-jakosc-binance/README.md) | Jakość świec Binance USDT-M 5m/1d top-20 point-in-time od 2021 (196 symboli, zadanie 002); manifest `f1b0e58` | **0 — POZA licznikami** (opis danych) | **Ready:** 0 duplikatów, 0 niespójnych OHLC, kontrola BTC ✓; 33 symbole z martwym ogonem po wycofaniu, wspólne dziury 2022-02-26…28 i 2022-04-01…02 |
