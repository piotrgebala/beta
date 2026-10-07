# beta

Program badawczy: **modele matematyczne i uczenie maszynowe na perpetualach krypto** — zmienność i ryzyko
ogona, sekwencyjna ocena dowodów, portfel, tor ML na nowe dane. Następca metodologii CLAS-5
(repo `alpha`). Plan: [`docs/PRD.md`](docs/PRD.md). Zasady: [`CLAUDE.md`](CLAUDE.md).

## Miejsce w bundlu

beta jest jednym z repozytoriów programu CLAS-5 (mapa i wspólne zasady: repo `bundle`, ADR
`bundle/docs/adr/0001-bundle-repozytoriow.md`). Docelowo: przyrząd pomiarowy przechodzi do pakietu `miara`
(po E2), pobieranie danych (`dane/`) do repo `kolektory`; beta zostaje przy modelach, laboratorium,
dowodach i portfelu. Zleceń nie składa — to rola zamrożonego repo `wykonanie`.

## Kamienie milowe

| etap | zakres | status |
|---|---|---|
| E0 | fundament: repo, CI, przyrząd `miara` z parytetem alpha, manifest danych | ✅ **zamknięty** 2026-10-06 (001, 002; decyzja użytkownika) |
| E1 | laboratorium symulacji + rachunek mocy | 🔍 do przeglądu (003 LM1: Caveats; 004 LD1) |
| E2 | zmienność i ryzyko ogona (HAR-RV, GARCH, VaR/ES) | 🔄 F2-1b NIEPOZYTYWNY (11/15; licznik zmienności = 1) → HAR odłożony; VaR/ES: KV1 ✓ (008), LV1 MIERZALNA (009), LV2 (016) MIERZALNA tylko z pytaniem bezwzględnym → 017 (bramka zależności NIE PRZECHODZI: VR 8,0 wobec 4,95; okno 2 091 z 2 100) → LV2c (019); 018 (pierwsza runda na danych) wstrzymana |
| E3 | dowody sekwencyjne dla dziennika alpha (przed 2026-12-24) | ✅ reporter gotowy (004); D3-a (tylko reporter) rozstrzygnięte 2026-10-07 na delegację |
| E4 | portfel i wielkość pozycji | — |
| E5 | tor ML na nowe dane (likwidacje, Hyperliquid) | — |
| E6 | meta-labeling (warunkowo) | — |

## Status

2026-09-30 — repo założone (decyzja użytkownika: „osobne repo i niech nazywa się beta”). Tego samego dnia:
przyrząd `miara` przeniesiony z alpha z testem parytetu (132 wektory, tolerancja 1e-12), CI, kontrola
negatywna NC1B zaliczona. Zero odczytów historii.

## Zastrzeżenie

Projekt badawczy. Nie jest poradą inwestycyjną i nie składa zleceń.
