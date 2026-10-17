---
id: 025
tytul: F2-2 — HAR + log DVOL vs czysty HAR na BTC i ETH (szczebel 5 drabiny F2, warunek wejścia do ML)
typ: badawcze
status: do_przegladu
zlecil: uzytkownik
decyzja_uzytkownika: "2026-10-17: „tak” (na pytanie o HAR + DVOL jako pierwszy krok, po którym ML w ogóle ma sens)"
utworzono: 2026-10-17
zalezy_od: [006, 010, 011]
budzet: "Opus, 1 sesja"
---

# 025 — F2-2: HAR + DVOL

## Po co

Proces ML jeszcze nie ruszył: w repo nie ma żadnego modelu uczącego się, a PRD wpuszcza boosting dopiero po
tym, jak szczeble 4–5 drabiny F2 przejdą bramkę. Szczebel 4 (HAR) przeszedł tylko brzegowo (F2-1b, 11/15).
Karta sprawdza szczebel 5 w jedynym wariancie, na który mamy dane: HAR + log DVOL na BTC i ETH.

## Zakres

- `modele/run_f22.py`, `prognoza_har(..., dodatkowe=...)`, parametr progu `z` w `moc_kryterium_braki`,
  `tests/test_f22.py`.
- Pre-rejestracja i wynik: `runs/2026-10-17_f22-har-dvol/README.md`.

## Czego NIE robić

Nie dodawać funding/OI w tej rundzie; nie luzować progu po fakcie; nie uruchamiać boostingu.

## Kryteria odbioru (dowody)

Testy i lint zielone; commit pre-rejestracji przed `raw_output.txt`; wiersz w `runs/INDEX.md`.

## Wynik

2026-10-17, commit pre-rejestracji `f12d7ff`, wynik w `runs/2026-10-17_f22-har-dvol/README.md`.
Bramka MIERZALNA (MDE 0,099 ≤ 0,10). t QLIKE +0,50 (BTC) i −0,07 (ETH) przy progu 2,24 → **NIEPOZYTYWNY (Caveats)**.
Licznik „zmienność 2021+”: 1 → 2. Boosting nie wchodzi, bez F2-2b. Niezależne przeliczenie HAC zgodne.
