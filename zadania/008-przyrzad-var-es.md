---
id: 008
tytul: przyrząd VaR/ES — testy Kupca, Christoffersena i Acerbiego–Szekelya z kontrolami
typ: badawcze
status: nowe
zlecil: uzytkownik
decyzja_uzytkownika: "2026-10-05: „rozpisz sobie kolejne taski, zaplanuj i zacznij realizować” + akceptacja planu (007–012)"
utworzono: 2026-10-05
zalezy_od: []
budzet: "Opus, 1 sesja"
---

# 008 — przyrząd VaR/ES (FR-32, cel G2)

## Po co

Cel G2 (prognoza ryzyka ogona przechodząca testy wsteczne) i reguła STOP F2-1 (F2 → ES/likwidacje) wymagają
przyrządu do oceny VaR i ES. R8: każdy przyrząd ma kontrolę pozytywną i negatywną.

## Zakres

- `miara/var_es.py`: test Kupca (pokrycie bezwarunkowe, LR_uc), Christoffersena (niezależność LR_ind
  i pokrycie warunkowe LR_cc), test ES Acerbiego–Szekelya Z2 z p-wartością z symulacji pod H0.
- Kontrola negatywna: na `symulacje.garch_panel.generuj_panel` z prawdziwym VaR/ES (znany model) odsetek
  odrzuceń ≈ poziom testu (przedział Wilsona).
- Kontrola pozytywna: VaR/ES z rozkładu normalnego przy ogonach t → testy odrzucają (moc > 80 % przy dużym n).
- Testy jednostkowe (wzory na małych przykładach, zgodność z ręcznym rachunkiem) + `hypothesis`.

## Czego NIE robić

Żadnych prognoz VaR na prawdziwych danych (to runda z pre-rejestracją, po LV1).

## Kryteria odbioru (dowody)

Testy zielone; tabela kontroli (rozmiar, moc) w README rundy kalibracyjnej albo w karcie.

## Wynik

(dopisuje orkiestrator)
