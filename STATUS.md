# beta — status (plan, decyzje, ryzyka, backlog)

## Decyzje użytkownika

- **2026-09-30** — D1: „osobne repo”; D5: „niech nazywa się beta” (`docs/PRD.md` §15, ADR [0001](docs/adr/0001-osobne-repo.md)).

- **2026-09-30** — „Rób co chcesz, ma działać”: przyjęte jako zgoda na rekomendacje **D2** (F0 → F1 → F2,
  F3 równolegle) i **D4** (dane 5m top-20 od 2021). D3 i D6 nadal otwarte.

## Otwarte decyzje (z PRD §15)

- **D3** — rola oceny sekwencyjnej wobec ADR-09 alpha (rekomendacja: tylko reporter); **termin przed 2026-12-24**.
- **D6** — DVOL (Deribit) jako źródło dla modeli zmienności (rekomendacja: tak, tylko DVOL).

## Bieżące zadania

Tablica: [`zadania/`](zadania/).

- **001** — `do_przegladu` (2026-09-30): port `miara` z parytetem alpha, loader, CI zielone, NC1B zaliczona.
  Do zamknięcia E0 brakuje manifestu danych (zadanie 002) i Twojej decyzji „E0 zamknięty”.
- **002** — `w_toku`: kod pobierania gotowy i przetestowany bez sieci; uruchomienie na maszynie z internetem
  (instrukcja w karcie zadania) — chmura nie dopuszcza `data.binance.vision`.
- **003** — `do_przegladu`: runda LM1 — test DM działa poprawnie; F2-1 mierzalna tylko warunkowo
  (przeliczyć MDE na prawdziwym kształcie strat, gdy będą dane z 002).
- **004** — `do_przegladu`: reporter F3 (`python -m dowody.raport`) + LD1; czeka na D3.
- **005** — `czeka_na_dane`: runda F2-1 (HAR vs zmienność dziennika) — kod i pre-rejestracja gotowe,
  przebieg na serwerze po 002.

## Plan sesji na serwerze (z internetem)

1. `python -m dane.binance_vision --tf 5m 1d --uniwersum ../alpha/data/raw/universe_full --top 20` (zadanie 002),
   commit manifestu i składu.
2. `python -m modele.run_f21 > runs/2026-10-01_f21-har-vs-dziennik/raw_output.txt` (zadanie 005), domknięcie rundy.
3. `python -m dowody.raport` na aktualnym dzienniku alpha (opisowo).

## Ryzyka

Pełna tabela: `docs/PRD.md` §14. Najważniejsze: traktowanie nowego repo jako „świeżego startu” licznika prób
(zasada 22) i oczekiwanie, że ML znajdzie przewagę tam, gdzie alpha zmierzyła jej brak.
