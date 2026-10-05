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
| E0 | fundament: repo, CI, przyrząd `miara` z parytetem alpha, manifest danych | ✅ gotowe (001, 002) — czeka na Twoje „E0 zamknięty” |
| E1 | laboratorium symulacji + rachunek mocy | 🔍 do przeglądu (003 LM1: Caveats; 004 LD1) |
| E2 | zmienność i ryzyko ogona (HAR-RV, GARCH, VaR/ES) | 🔄 dane są (002, 006); F2-1 NIEMIERZALNA (005) → 011; dalej VaR/ES (008, 009) |
| E3 | dowody sekwencyjne dla dziennika alpha (przed 2026-12-24) | ✅ reporter gotowy (004); czeka na D3 |
| E4 | portfel i wielkość pozycji | — |
| E5 | tor ML na nowe dane (likwidacje, Hyperliquid) | — |
| E6 | meta-labeling (warunkowo) | — |

## Status

2026-09-30 — repo założone (decyzja użytkownika: „osobne repo i niech nazywa się beta”). Tego samego dnia:
przyrząd `miara` przeniesiony z alpha z testem parytetu (132 wektory, tolerancja 1e-12), CI, kontrola
negatywna NC1B zaliczona. Zero odczytów historii.

## Zastrzeżenie

Projekt badawczy. Nie jest poradą inwestycyjną i nie składa zleceń.
