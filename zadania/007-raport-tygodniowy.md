---
id: 007
tytul: raport tygodniowy (FR-40) — jedna strona prostym językiem
typ: infra
status: do_przegladu
zlecil: uzytkownik
decyzja_uzytkownika: "2026-10-05: „rozpisz sobie kolejne taski, zaplanuj i zacznij realizować” + akceptacja planu (007–012)"
utworzono: 2026-10-05
zalezy_od: []
budzet: "Opus, część sesji"
---

# 007 — raport tygodniowy

## Po co

PRD §5–6: raport tygodniowy to jedyny „ekran”, na który użytkownik patrzy (~30 min/tydzień, cel G6).

## Zakres

- `raporty/tydzien.py` → `raporty/tygodnie/RRRR-Www.md` (tydzień ISO, poniedziałek–niedziela UTC).
- Sekcje prostym językiem: 1) co się zmieniło (commity tygodnia, nowe wiersze `runs/INDEX.md`, statusy zadań),
  2) kluczowe liczby z jednym zdaniem „co z tego wynika”, 3) dziennik alpha (wydruk `dowody.raport`),
  4) decyzje czekające (z `STATUS.md` i kart `czeka_na_decyzje`), 5) plan na następny tydzień.
- Generator składa fakty z repo; zdania „co z tego wynika” i karty decyzji pisze Claude (R14: skrypt jest
  reporterem) — w pliku jest miejsce na komentarz, generator go nie nadpisuje.

## Czego NIE robić

Żadnych nowych odczytów historii; raport tylko streszcza to, co już jest w repo.

## Kryteria odbioru (dowody)

Testy na atrapie repo (git log, INDEX, karty); pierwszy raport 2026-W41 wygenerowany z prawdziwego repo.

## Wynik

2026-10-05: `raporty/tydzien.py` + 4 testy (`tests/test_raport_tydzien.py`: tydzień ISO, rundy z INDEX, karty,
decyzje, komentarz przetrwa ponowne generowanie). Pierwszy raport: `raporty/tygodnie/2026-W41.md` z kartami
decyzji E0, 011, D3 i PR #1. Uruchomienie: `python -m raporty.tydzien` (automat w niedzielę — zadanie 012).

2026-10-09 (rozszerzenie, propozycja (b) z karty 023): sekcja „3. Ryzyko pozycji na dziś” w raporcie — tabela z `modele.rozmiar_dzis`
(σ roczna, dźwignia z celu 18 %, dystans i P likwidacji 3× w 7 dni, kolumna ×1,6 z karty 024) dla BTC/ETH/SOL/BNB, stan na ostatni dzień danych;
brak danych → jedna linia z powodem (jak reporter F3). Decyzje przesunięte do sekcji 4. Opis, nie sygnał; nic nie liczy zwrotu strategii ani nie podbija liczników.
