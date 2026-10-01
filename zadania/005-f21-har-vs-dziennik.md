---
id: 005
tytul: runda F2-1 — HAR-RV vs zmienność dziennika (kod + pre-rejestracja; przebieg na serwerze)
typ: badawcze
status: czeka_na_dane
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

(dopisuje orkiestrator)
