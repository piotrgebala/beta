---
id: 013
tytul: bundle na GitHubie — 4 nowe repo (bundle, miara, kolektory, wykonanie)
typ: konto
status: czeka_na_decyzje
zlecil: uzytkownik
decyzja_uzytkownika: "2026-10-05: „stwórz wszystkie repa na bundle oraz uzupełnij w nich README oraz CLAUDE.md”"
utworzono: 2026-10-05
zalezy_od: []
budzet: "Ty: ~10 min; Claude: kilka minut"
---

# 013 — bundle na GitHubie

## Po co

Szkielety bundla (ADR `bundle/docs/adr/0001-bundle-repozytoriow.md`) stoją lokalnie w `~/bundle`, `~/miara`,
`~/kolektory`, `~/wykonanie` — po jednym commicie, bez kopii na GitHubie. Zasada 28 (commit i push) i odtworzenie
serwera (`bundle/klonuj.sh`) wymagają ich na GitHubie.

## Zakres

- **Ty:** na GitHubie 4 puste repo o tych nazwach (bez README) + dostęp z serwera: albo klucz wdrożeniowy na
  każde repo (wzór `github-beta`, instrukcja w `bundle/README.md`), albo jeden klucz w ustawieniach konta
  (prościej, ale daje dostęp do wszystkich Twoich repo).
- **Claude:** `git remote add origin …` i push gałęzi `main` w każdym z 4 repo; aktualizacja mapy w
  `bundle/README.md` (linki).

## Czego NIE robić

Claude nie tworzy kluczy dostępowych ani nie zmienia adresów zdalnych bez Twojej wyraźnej zgody (zabezpieczenie
Claude Code blokuje to w trybie automatycznym).

## Kryteria odbioru (dowody)

`git -C ~/<repo> status -sb` pokazuje gałąź zgodną z `origin/main` dla wszystkich 4 repo.

## Wynik

(dopisuje orkiestrator)
