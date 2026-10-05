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

Tablica: [`zadania/`](zadania/).

- **001** — `do_przegladu` (2026-09-30): port `miara` z parytetem alpha, loader, CI zielone, NC1B zaliczona.
  Manifest danych jest (002) — do zamknięcia E0 brakuje tylko Twojej decyzji „E0 zamknięty”.
- **002** — `do_przegladu` (2026-10-05): 196 symboli top-20 × 5m/1d od 2021 pobrane, manifest + skład w repo,
  raport jakości DQ1 (Ready): 33 symbole z „martwym ogonem” po wycofaniu, wspólne dziury 2022-02/04.
- **003** — `do_przegladu`: runda LM1 — test DM działa poprawnie; F2-1 mierzalna tylko warunkowo
  (przeliczyć MDE na prawdziwym kształcie strat, gdy będą dane z 002).
- **004** — `do_przegladu`: reporter F3 (`python -m dowody.raport`) + LD1; czeka na D3.
- **005** — `do_przegladu` (2026-10-05): runda F2-1 **NIEMIERZALNA** na progu (MDE 0,103 > 0,10); test DM
  nieuruchomiony, licznik 0; pięć monet z krótką historią zjada zapas kryterium 16/20 → decyzja w 011.
- **006** — `do_przegladu` (2026-10-05): DVOL BTC/ETH 1D od 2021-03-24 pobrany, czysty, kontrola pozytywna ✓.

## Plan sesji na serwerze (2026-10-05)

Wykonane: 002 (dane + DQ1), 006 (DVOL), 005 (F2-1 NIEMIERZALNA), reporter F3 na dzienniku (10–11 dni, e ≈ 1).
Następne (plan zaakceptowany 2026-10-05): karty 007–012 → 007 raport tygodniowy → 008 przyrząd VaR/ES →
009 laboratorium LV1 → 010 rejestr cech.

## Ryzyka

Pełna tabela: `docs/PRD.md` §14. Najważniejsze: traktowanie nowego repo jako „świeżego startu” licznika prób
(zasada 22) i oczekiwanie, że ML znajdzie przewagę tam, gdzie alpha zmierzyła jej brak.
