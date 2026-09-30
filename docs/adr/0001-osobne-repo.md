# ADR-0001: osobne repo `beta` zamiast katalogu w `alpha`

**Status:** Accepted · **Data:** 2026-09-30 · **Decyzja:** użytkownik („osobne repo i niech nazywa się beta”)

## Kontekst
PRD programu ML (`docs/PRD.md`, D1) rozważał: (a) osobne repo z portem przyrządu, (b) katalog w alpha,
(c) osobne repo + wspólny pakiet przyrządu.

## Decyzja
(a) teraz; (c) do rozważenia po E2, gdy przyrząd się ustabilizuje.

## Konsekwencje
- **Łatwiej:** beta nie dotyka dziennika papierowego alpha (Poprawki), zamrożonych skryptów ani ich lintera.
- **Trudniej:** dwa przyrządy do utrzymania w zgodzie → test parytetu (CLAUDE.md zasada 24).
- **Pułapka:** osobne repo NIE daje nowego budżetu prób na historii 2021–2026 → wspólny rejestr odczytów
  (zasada 22).
- **Ścieżka odwrotu:** przeniesienie `beta` do katalogu w alpha jest mechaniczne (brak zależności odwrotnych).
