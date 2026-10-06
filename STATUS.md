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

Tablica: [`zadania/`](zadania/). Stan na 2026-10-06.

**Zrobione — czekają na Twój przegląd (`do_przegladu`):**

- **001** — fundament: przyrząd `miara` zgodny z alpha, loader z `min_start`, CI, NC1B zaliczona.
- **002** — dane: 196 symboli top-20 × 5m/1d od 2021, manifest, DQ1 (Ready).
- **003** — LM1: test porównania prognoz (DM) działa poprawnie.
- **004** — reporter F3 + LD1; rola czeka na D3.
- **005** — F2-1: NIEMIERZALNA na progu (MDE 0,103 > 0,10), licznik 0 → 011.
- **006** — DVOL BTC/ETH od 2021-03-24.
- **007** — raport tygodniowy.
- **008** — przyrząd VaR/ES; kontrola KV1 **ZALICZONA 19/19** (Caveats: duże n, ρ = 0).
- **010** — rejestr cech + test przecieku (kontrola pozytywna łapie celowe przecieki).
- **012** — automat: wszystkie 3 tryby uruchomione z sukcesem; cron włączony 2026-10-06.
- **014** — `dane/dni.py::dni_wazne`: parytet z Poprawką 1 F2-1 20/20, martwe dni zgodne z DQ1.
- **015** — pobieranie Binance przyrostowe: automat miesięczny pobiera tylko nowy miesiąc (bieg bez nowości 25 s).

**Czekają na Twoją decyzję:** 009 (punkt 7 LV1), 011, 013 — niżej.

## Kolejka

Po decyzji w 009: pełny przebieg LV1 (~30 min) → README z werdyktem. Dalej, zależnie od LV1 i 011:
F2-1b (jeśli 011 = a) albo pre-rejestracja pierwszej rundy VaR/ES na danych (wymaga też kontroli
rozmiaru przy ESTYMOWANYM modelu — „LV2”, opisane w README LV1).

## Decyzje czekające na Ciebie

1. **E0 zamknięty?** — rekomendacja: tak.
2. **009 / LV1 punkt 7** — reguła poprawiona (rekomendacja) czy pierwotna; szczegóły w karcie 009.
3. **011** — F2-1b czy tylko ES/likwidacje. Rekomendacja: F2-1b.
4. **D3** — rola F3 (rekomendacja: tylko reporter, D3-a); termin przed 2026-12-24.
5. **PR #1** — scalenie gałęzi `claude/fervent-fermi-vfctk6` do `main` (851 testów zielonych).
6. **013** — 4 puste repo na GitHubie + klucze (instrukcja w `~/bundle/README.md`).
7. **Skład top-20 po 2026-06** — lista monet bierze się z `alpha/.../universe_full`, który kończy się
   w czerwcu 2026; nowe wejścia do top-20 nie są pobierane. Aktualizacja = Poprawka w alpha (karta 015).

## Backlog (bez kart)

- Migracja `beta/miara` → pakiet `miara` — po E2 (ADR `bundle/0001` pkt 3; Poprawka w alpha).
- Migracja `beta/dane` → repo `kolektory` — po 013, osobną decyzją.
- Top-50 (FR-01) — gdy runda będzie tego potrzebować (`--top 50`).
- Tor F5 (likwidacje, Hyperliquid) — magazyn cech point-in-time; pierwszy odczyt najwcześniej 2027-09.
- F4 portfel — po E2.
- Wolumen 5m vs 1d różny w 600 dniach (161 symboli) — przyczyny nie badano (karta 014).

## Ryzyka

Pełna tabela: `docs/PRD.md` §14. Najważniejsze: traktowanie nowego repo jako „świeżego startu” licznika prób
(zasada 22) i oczekiwanie, że ML znajdzie przewagę tam, gdzie alpha zmierzyła jej brak.
