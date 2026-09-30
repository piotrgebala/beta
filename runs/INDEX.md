# runs/ — spis treści

## Stan wiedzy — skrót

Jedna runda kalibracyjna (NC1B — przyrząd `miara` zaliczył kontrolę negatywną; 0 wariantów). Stan wiedzy odziedziczony: `alpha/runs/INDEX.md` (wnioski 1–111) i `docs/PRD.md` §2.

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
