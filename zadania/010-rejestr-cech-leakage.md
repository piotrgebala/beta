---
id: 010
tytul: rejestr cech + automatyczny test przecieku (FR-10…13)
typ: infra
status: do_przegladu
zlecil: uzytkownik
decyzja_uzytkownika: "2026-10-05: „rozpisz sobie kolejne taski, zaplanuj i zacznij realizować” + akceptacja planu (007–012)"
utworzono: 2026-10-05
zalezy_od: []
budzet: "Opus, 1 sesja"
---

# 010 — rejestr cech i test przecieku

## Po co

R7 i FR-11: cecha bez testu przecieku nie trafia do modelu. Potrzebne przed HAR-X (DVOL, funding) i torem F5.

## Zakres

- `cechy/rejestr.yaml`: nazwa, zbiór informacyjny, opóźnienie publikacji, data dodania, runda.
- `cechy/zmiennosc.py`: czyste funkcje `compute_<nazwa>(df) -> pd.Series` (RV dzień/tydzień/miesiąc, DVOL
  z opóźnieniem, funding), okna tylko wstecz.
- Jeden test przechodzący po CAŁYM rejestrze: zmiana danych po t nie zmienia wartości cechy w t (FR-11);
  test masy punktowej (FR-12).

## Czego NIE robić

Żadnych modeli ani odczytów.

## Kryteria odbioru (dowody)

Test rejestru zielony; cecha z celowym przeciekiem (kontrola pozytywna) jest przez test złapana.

## Wynik

2026-10-05: `cechy/rejestr.yaml` (cechy zmienności z kluczem wariantu `<zbiór>|<formuła>|opóźnienie=<dni>`, R2),
`cechy/zmiennosc.py` (`compute_*`: rv_dzien, rv_tydzien, rv_miesiac jako log RV i średnie, okna 7 i 30 dni jak
`modele/zmiennosc.py`; dvol_opozn z opóźnieniem 1 dnia; funding z opóźnieniem), `cechy/przeciek.py`
(`sprawdz_przeciek`, `masa_punktowa`, `walidacja_progu_percentylowego` — FR-12) i `tests/test_cechy.py`.

- **Kryterium odbioru:** test przechodzący po całym rejestrze jest zielony; cecha z celowym przeciekiem
  (kontrola pozytywna, kilka klas przecieków) jest przez harness łapana; brak funkcji `compute_*` albo wpisu
  w rejestrze = błąd testu.
- **Do wiedzy:** (1) porównanie bit w bit (rtol = 0) — przy przyszłych redukcjach numerycznych może wymagać
  tolerancji; (2) perturbowane są tylko kolumny liczbowe (przeciek przez oś czasu / długość nie jest wykrywany);
  (3) opóźnienie DVOL 1 dzień jest zachowawcze, niezweryfikowane względem czasu publikacji Deribit;
  (4) dzień funding częściowy bez flagi; (5) test sprawdza wiersz `| F2-1 |` w `runs/INDEX.md`.
- Przegląd: trzech niezależnych recenzentów (mutacje ręczne), poprawki high/medium zastosowane.
