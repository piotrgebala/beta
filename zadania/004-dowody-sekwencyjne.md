---
id: 004
tytul: reporter F3 — e-procesy i Bayes dla dziennika alpha + laboratorium fałszywych alarmów
typ: badawcze
status: w_toku
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

(dopisuje orkiestrator)
