---
id: 005
tytul: runda F2-1 — HAR-RV vs zmienność dziennika (kod + pre-rejestracja; przebieg na serwerze)
typ: badawcze
status: do_przegladu
zlecil: uzytkownik
decyzja_uzytkownika: "2026-10-01: „zrób to, co możesz bez dostępu do Internetu; później odpalę sesję zdalną na serwerze”"
utworzono: 2026-10-01
zalezy_od: [002, 003]
budzet: "Opus, 1 sesja na serwerze"
---

# 005 — F2-1

## Po co

Etap E2: pierwsza runda drabiny modeli zmienności (R17). Warunek z LM1: MDE na prawdziwym kształcie strat.

## Zakres

- `dane/rv.py` (RV z 5m), `modele/zmiennosc.py` (baseline = EWMA 60 dziennika, HAR-RV walk-forward),
  `modele/run_f21.py` (bramka MDE → DM), testy `tests/test_zmiennosc.py`.
- Pre-rejestracja `runs/2026-10-01_f21-har-vs-dziennik/README.md` — zapisana przed danymi.

## Na serwerze (po zadaniu 002)

```
python -m modele.run_f21 > runs/2026-10-01_f21-har-vs-dziennik/raw_output.txt
```
Potem: wynik w README rundy, wiersz w `runs/INDEX.md`, licznik „zmienność 2021+”.

## Wynik

2026-10-05 (serwer): Poprawka 1 przed przebiegiem (`cc4cea1`: martwe dni RV = 0 nieważne; bramka po kalendarzu
z brakami, bo okresy 20 monet nie mają części wspólnej). Przebieg: **NIEMIERZALNA** — MDE kryterium 0,103 > 0,10
(walidacja: ziarna 1–5 → 0,100–0,102), test DM nie uruchomiony, licznik „zmienność 2021+” = 0. Przyczyna: pięć
monet z krótkim OOS (WIF, SUI, FTM, PEPE, MATIC; MDE 0,115–0,150) przy kryterium 16/20. Werdykt **Caveats**,
pytanie otwarte. Dalszy krok F2 → zadanie 011 (decyzja użytkownika).
