# beta — status (plan, decyzje, ryzyka, backlog)

## Decyzje użytkownika

- **2026-09-30** — D1: „osobne repo”; D5: „niech nazywa się beta” (`docs/PRD.md` §15, ADR [0001](docs/adr/0001-osobne-repo.md)).

## Otwarte decyzje (z PRD §15)

- **D2** — kolejność filarów (rekomendacja: F0 → F1 → F2, F3 równolegle, potem F4, F5; F6 warunkowo).
- **D3** — rola oceny sekwencyjnej wobec ADR-09 alpha (rekomendacja: tylko reporter); **termin przed 2026-12-24**.
- **D4** — pobranie danych 5m dla top-20 od 2021-01-01 (rekomendacja: tak).
- **D6** — DVOL (Deribit) jako źródło dla modeli zmienności (rekomendacja: tak, tylko DVOL).

## Bieżące zadania

Tablica: [`zadania/`](zadania/).

- **001** — `do_przegladu` (2026-09-30): port `miara` z parytetem alpha, loader, CI zielone, NC1B zaliczona.
  Do zamknięcia E0 brakuje manifestu danych (zadanie 002) i Twojej decyzji „E0 zamknięty”.
- **002** i **003** — `czeka_na_decyzje` (D4, D2).

## Ryzyka

Pełna tabela: `docs/PRD.md` §14. Najważniejsze: traktowanie nowego repo jako „świeżego startu” licznika prób
(zasada 22) i oczekiwanie, że ML znajdzie przewagę tam, gdzie alpha zmierzyła jej brak.
