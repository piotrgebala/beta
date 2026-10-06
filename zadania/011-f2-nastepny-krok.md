---
id: 011
tytul: następny krok F2 po F2-1 (NIEMIERZALNA) — F2-1b po długości danych albo ES/likwidacje
typ: badawcze
status: do_przegladu
zlecil: orkiestrator
decyzja_uzytkownika: "2026-10-06: „LV1: poprawiona, 011: a, E0: zamknij”"
utworzono: 2026-10-05
zalezy_od: [005, 014]
budzet: "Opus, 1 sesja"
---

# 011 — następny krok F2

## Po co

F2-1 wyszła NIEMIERZALNA na samym progu (MDE 0,103 > 0,10): pytanie „czy HAR bije prognozę dziennika” jest
otwarte. Przyczyna leży w projekcie rundy (pięć monet z krótką historią przy kryterium 16/20), nie w danych.

## Opcje

- **(a) F2-1b (rekomendacja)** — nowy wariant: monety dobrane po DŁUGOŚCI danych (pełny OOS ~1 700 dni, top-20
  point-in-time, kontrakt żywy cały okres). Pre-rejestracja, bramka MDE na ślepo (centrowane straty) przed testem
  DM. Licznik „zmienność 2021+”: 0 → 1 przy teście. Ograniczenie do opisania: populacja „monet z długą historią”.
- **(b) tylko STOP z pre-rejestracji** — F2 przechodzi do ES/likwidacji (008–009), HAR odkładamy.

Zadania 008–009 idą w obu wariantach. F2-1b korzysta ze wspólnej obsługi dni ważnych (zadanie 014).

## Wynik

2026-10-06: decyzja użytkownika **(a) F2-1b**. Pre-rejestracja w `runs/` (osobna runda), bramka MDE na ślepo przed testem DM.

**2026-10-06 — wynik F2-1b** (`runs/2026-10-06_f21b-har-vs-dziennik-dlugie/`, pre-rejestracja `674eada`): 15 monet
z pełną historią, bramka MIERZALNA (MDE 0,091), test DM: t > 1,96 w **11/15** (wymagane 12), żadna moneta
istotnie gorsza → **NIEPOZYTYWNY**. Licznik „zmienność 2021+” = 1. STOP: HAR odkładamy, F2 idzie przez
VaR/ES (LV2) i likwidacje; bez F2-1c.

