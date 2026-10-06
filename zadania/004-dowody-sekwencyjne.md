---
id: 004
tytul: reporter F3 — e-procesy i Bayes dla dziennika alpha + laboratorium fałszywych alarmów
typ: badawcze
status: do_przegladu
zlecil: uzytkownik
decyzja_uzytkownika: "2026-10-01: „zrób to, co możesz bez dostępu do Internetu”; D3 otwarta — reporter zgodny z opcją (a)"
utworzono: 2026-10-01
zalezy_od: [001]
budzet: "Opus, 1 sesja"
---

# 004 — dowody sekwencyjne (E3)

## Po co

PRD F3 / E3: reporter gotowy **przed 2026-12-24** (pierwszy odczyt dziennika alpha). Patrzenie codziennie
na klasyczny test zawyża fałszywe alarmy; e-proces na to pozwala.

## Zakres

- `dowody/`: e-proces obalenia i potwierdzenia, posterior normalny-normalny z priorem sceptycznym, CLI reportera
  czytające `alpha/dziennik/*.csv` (tylko odczyt).
- Laboratorium LD1: fałszywe alarmy przy codziennym zaglądaniu przez 365 dni i moc wobec 3 odczytów z = 2,31.

## Czego NIE robić

Nie zmieniać kryterium ADR-09 ani niczego w alpha; reporter nie wiąże (D3 = decyzja użytkownika).

## Kryteria odbioru (dowody)

Testy (postać zamknięta = całka, martyngał, kierunki, zgodność stałych z alpha); runda LD1 z werdyktem;
`python -m dowody.raport` działa na dzienniku alpha.

## Wynik

2026-10-01: `dowody/` (e-procesy, Bayes, stałe nóg, CLI `python -m dowody.raport`) + 16 testów; runda LD1
(`runs/2026-10-01_ld1-eproces-dziennik/`): fałszywe alarmy ≤ 0,54 % (bramka 1 ✓), moc w rok ≤ 0,9 %
wobec 3–11 % odczytów ADR-09 (bramka 2 ✗) → reporter opisowy; rekomendacja D3-a. Raport na migawce
dziennika z 2026-09-30 (6 dni): wszystkie E ≈ 1, brak dowodu w żadną stronę.

Do decyzji użytkownika przed 2026-12-24: D3 (rekomendacja: (a) tylko reporter).
