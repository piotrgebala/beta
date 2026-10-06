---
id: 008
tytul: przyrząd VaR/ES — testy Kupca, Christoffersena i Acerbiego–Szekelya z kontrolami
typ: badawcze
status: do_przegladu
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

2026-10-05: `miara/var_es.py` (Kupiec LR_uc, Christoffersen ind/cc, Acerbi–Székely Z2 z p-wartością z symulacji,
wzory zamknięte VaR/ES dla normalnego i znormalizowanego t) + `tests/test_var_es.py` (142 testy, w tym `hypothesis`
i lekkie kontrole R8). Kontrole R8 w rundzie **KV1** (`runs/2026-10-05_kv1-kontrola-var-es/`, pre-rejestracja
`d9f83ed` przed przebiegiem): **ZALICZONA 19/19, Caveats** — rozmiar 4,6–5,1 % (nominalnie 5 %), moc wobec znanych
błędów ≥ 97,7 %, 0 niezdefiniowanych testów; wynik identyczny przy 8 i 32 procesach (R19).

- **Caveats (z KV1):** rozmiar sprawdzony tylko przy n = 20 000 / 200 000 dni, ρ = 0, prognoza-wyrocznia —
  rozmiar przy prawdziwym n (600–2 100 dni) i ρ > 0 mierzy LV1 (karta 009); Z2 nigdy samodzielnie
  (przy p = 5 % nie widzi „normalna vs t5”, bo błędy VaR i ES się kasują); LR_ind przy n·p² ≲ 1 orientacyjny;
  LR_cc liczone na n − 1 przejściach (może różnić się od podręcznikowego o rząd 1/n).
- Przegląd: trzech niezależnych recenzentów z mutacjami przed przebiegiem; zmiany po przeglądzie opisane
  w README KV1 (m.in. dodana POZYTYWNA 4 dla cc).
