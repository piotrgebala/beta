# beta — status (plan, decyzje, ryzyka, backlog)

## Decyzje użytkownika

- **2026-09-30** — D1: „osobne repo”; D5: „niech nazywa się beta” (`docs/PRD.md` §15, ADR [0001](docs/adr/0001-osobne-repo.md)).

- **2026-09-30** — „Rób co chcesz, ma działać”: przyjęte jako zgoda na rekomendacje **D2** (F0 → F1 → F2,
  F3 równolegle) i **D4** (dane 5m top-20 od 2021). D3 i D6 nadal otwarte.

- **2026-10-05** — **D6: tak** — DVOL (Deribit) jako źródło dla modeli zmienności, tylko DVOL (pełne opcje
  dopiero, gdy F2 pokaże wartość); zadanie 006. Nowa zasada 28 w `CLAUDE.md`: commit i push po każdej
  większej zmianie.

- **2026-10-05** — „stwórz wszystkie repa na bundle oraz uzupełnij w nich README oraz CLAUDE.md”: bundle
  zaprojektowany (ADR `bundle/docs/adr/0001`), lokalnie założone `~/bundle`, `~/miara`, `~/kolektory`,
  `~/wykonanie` (szkielety). Na GitHubie zakłada je użytkownik (instrukcja w `bundle/README.md`).

## Otwarte decyzje (z PRD §15)

- **D3** — rola oceny sekwencyjnej wobec ADR-09 alpha (rekomendacja: tylko reporter); **termin przed 2026-12-24**.

## Bieżące zadania

Tablica: [`zadania/`](zadania/). Stan na 2026-10-05.

**Zrobione — czekają na Twój przegląd (`do_przegladu`):**

- **001** — fundament: przyrząd `miara` zgodny z alpha (132 wektory), loader z `min_start`, CI, NC1B zaliczona.
  Razem z 002 zamyka E0 — brakuje tylko Twojej decyzji „E0 zamknięty”.
- **002** — dane: 196 symboli top-20 × 5m/1d od 2021, manifest + skład w repo, raport jakości DQ1 (Ready).
- **003** — laboratorium LM1: test porównania prognoz (DM) działa poprawnie.
- **004** — reporter F3 dla dziennika alpha + LD1; jego rola czeka na D3.
- **005** — runda F2-1: **NIEMIERZALNA** na progu (MDE 0,103 > 0,10), licznik 0 → dalej 011.
- **006** — DVOL BTC/ETH od 2021-03-24, zgodny z kopią alpha.
- **007** — raport tygodniowy (`python -m raporty.tydzien`), pierwszy: `raporty/tygodnie/2026-W41.md`.

**Do zrobienia:**

| id | zadanie | status | zależy od |
|---|---|---|---|
| 008 | przyrząd VaR/ES (Kupiec, Christoffersen, Acerbi–Szekely) z kontrolami | `nowe` | — |
| 009 | laboratorium LV1: czy testy VaR/ES mają moc przy naszej historii | `nowe` | 008 |
| 010 | rejestr cech + automatyczny test przecieku | `nowe` | — |
| 011 | następny krok F2: F2-1b (monety z pełną historią) albo tylko ES/likwidacje | `czeka_na_decyzje` | 005, 014 |
| 012 | automat: DVOL codziennie, Binance co miesiąc, raport w niedzielę | `nowe` | 007 |
| 013 | bundle na GitHubie (4 nowe repo) — **Twój krok**, potem push | `czeka_na_decyzje` | — |
| 014 | wspólna obsługa martwych ogonów i dziur archiwum w danych 5m | `nowe` | 002 |

## Kolejka

**008 → 009 → 014 → 010 → 012.** Warunkowo: F2-1b po decyzji 011 = (a) (po 014). Po Twoim kroku w 013:
push 4 repo bundla. Linię crona dla 012 dodajesz Ty.

## Decyzje czekające na Ciebie

1. **E0 zamknięty?** — wszystko z listy jest (001 + 002). Rekomendacja: tak.
2. **011** — F2-1b czy tylko ES/likwidacje. Rekomendacja: F2-1b (VaR/ES idzie i tak).
3. **D3** — rola F3 (rekomendacja: tylko reporter, D3-a); termin przed 2026-12-24.
4. **PR #1** — scalenie gałęzi `claude/fervent-fermi-vfctk6` do `main` (testy: 229 zielonych).
5. **013** — 4 puste repo na GitHubie + klucze (instrukcja w `~/bundle/README.md`).

## Backlog (bez kart)

- Migracja `beta/miara` → pakiet `miara` — po E2 (ADR `bundle/0001` pkt 3; Poprawka w alpha).
- Migracja `beta/dane` → repo `kolektory` — po 013, osobną decyzją.
- Top-50 (FR-01) — gdy runda będzie tego potrzebować (`--top 50`).
- Tor F5 (likwidacje, Hyperliquid) — magazyn cech point-in-time; pierwszy odczyt najwcześniej 2027-09.
- F4 portfel — po E2.

## Ryzyka

Pełna tabela: `docs/PRD.md` §14. Najważniejsze: traktowanie nowego repo jako „świeżego startu” licznika prób
(zasada 22) i oczekiwanie, że ML znajdzie przewagę tam, gdzie alpha zmierzyła jej brak.
