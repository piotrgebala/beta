# Tablica zadań beta

Te same zasady co w alpha (`alpha/zadania/README.md`, alpha CLAUDE.md zasada 21): pliki `NNN-<slug>.md`
według `SZABLON.md`; statusy `nowe` → `w_toku` → `do_przegladu` → `zrobione` (poza tym `czeka_na_decyzje`,
`odrzucone`). Na polecenie „wykonaj zadania z tablicy” sesja staje się orkiestratorem; ciężka praca w
subagentach na gałęziach `zadanie-NNN-<slug>`. Zadania `badawcze` bez zapisanej decyzji użytkownika →
`czeka_na_decyzje`. Scalanie tylko na dowodach (testy, log, komenda, hash).
