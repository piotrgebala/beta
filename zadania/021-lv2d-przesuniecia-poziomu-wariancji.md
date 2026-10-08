---
id: 021
tytul: LV2d — nowa pre-rejestracja po STOP 1 karty 019 (laboratorium z przesunięciami poziomu wariancji; scenariusz LV2 dla K = 4)
typ: badawcze
status: nowe
zlecil: orkiestrator
decyzja_uzytkownika: "2026-10-07: delegacja — „miejsca w których potrzebna jest moja decyzja sam sobie odpowiedz wedługo swojej najlepszej wiedzy”; kartę otworzył Claude po STOP 1 w karcie 019 (README rundy 019, „Wynik”); wykonanie nie jest jeszcze zlecone"
utworzono: 2026-10-08
zalezy_od: [019, 020]
budzet: "Opus, 1–2 sesje (nowa pre-rejestracja, kalibracja, przebieg rejestrowy)"
---

# 021 — LV2d: nowa pre-rejestracja po STOP 1 w 019

## Po co

Karta 019 zakończyła się regułą STOP 1 (werdykt Revision): generator LV2c nie umie dojść do odsetka dopasowań GARCH-t przy
granicy persystencji ≥ 46,3 % (cel z 020: 51,3 % ± 5 pp). Najlepszy punkt pilotażu to 44,5 % ± 1,3 pp (α = 0,16), a od α ≥ 0,12 odsetek
leży na płaskowyżu 41–44 %. Zależność trafień (VR) cel osiąga (2,20–2,22 wobec 2,264 ± 0,14). Przebiegu rejestrowego z regułą K **nie było**,
więc pytanie z 019 — czy reguła K (rozmiar ≤ 10 %, moc ≥ 80 %) jest mierzalna dla 4 monet — zostaje bez odpowiedzi.
Pre-rejestracja 019 zabrania zmiany generatora i progów po STOP 1, więc dalszy krok to **nowa pre-rejestracja**, nie poprawka starej.

## Zakres (do rozstrzygnięcia w pre-rejestracji; rekomendacja Claude na pierwszym miejscu)

1. **(b) Generator z przesunięciami poziomu wariancji (rekomendowane).** Hipoteza mechanizmu: w danych 2021–2026 poziom zmienności
   długiego okresu się przesuwa (hossa 2021, krach 2022, cisza 2023), a stacjonarny GARCH z α + β ≤ 0,9999 daje przy granicy najwyżej
   ok. połowę dopasowań (granica jest jednostronna, więc nawet przy prawdziwej wartości dokładnie na granicy estymator ląduje na niej
   w ok. 50 % przypadków). 51 % z danych oznacza więc „poza granicą”, czego sama trwałość nie wytworzy. Nowy plik generatora
   (np. `symulacje/garch_panel_regimy.py`; `garch_panel_wspolny_szok.py` i pliki LV2 zamrożone), pokrętłem amplituda i liczba
   przesunięć σ̄ (wspólnych dla monet), cel kalibracji ten sam co w 019 (VR 2,264 ± 0,14; przy granicy 51,3 % ± 5 pp).
   Uczciwe zastrzeżenie do zapisania w pre-rejestracji: mechanizm wybrany po obejrzeniu STOP 1, więc to wyjaśnienie po fakcie;
   zgodność z danymi sprawdzić opisowo (stabilność σ̄ w oknach prawdziwych szeregów to nowy odczyt danych, ale opisowy,
   jak 017 i 020, poza licznikami).
2. **(c) Komórka A0 (scenariusz LV2 dla K = 4: ρ = 0,8, bez wspólnego szoku, α + β = 0,98) wchodzi do tej samej pre-rejestracji
   niezależnie od (b).** Nie wymaga kalibracji, a odpowiada na pytanie, które w 019 pozostało bez wyniku: moc K-b przy czterech
   monetach w najłagodniejszej zależności. Przewidywanie z 019: ok. 58 % (40–75), więc reguła K prawdopodobnie niemierzalna już tu.
3. **(a) Poluzowanie celu odsetka przy granicy (np. ≥ 40 %) odradzam** jako samodzielne rozwiązanie: byłoby to przesunięcie
   słupków po obejrzeniu wyniku. Dopuszczalne tylko jako komórka opisowa obok (b), nigdy jako zastępstwo.
4. Reguła K, progi 10 % i 80 %, poziom p = 5 %, `dopasuj_garch_t`, granica 0,9999, runner `run_lv2c` (kontrole, test zbiorczy):
   bez zmian; nowe są tylko generator i jego kalibracja. Ziarna rejestrowe i pilotażowe nowe (rozłączne z 20_261_019, 20_261_091
   i 31_415_926).
5. Pre-rejestracja w gicie PRZED kalibracją i przebiegiem rejestrowym (R1–R4, zasada 26), przewidywania i tabela konsekwencji z góry.
6. Własny katalog rundy, wiersz w `runs/INDEX.md`. Licznik: **poza licznikami** (dane syntetyczne).

## Czego NIE robić

- Nie uruchamiać karty 018 ani nie liczyć odsetka trafień na prawdziwych danych.
- Nie zmieniać plików zamrożonych (LV2, `garch_panel_wspolny_szok.py`, `run_lv2c.py` poza dopisaniem nowego generatora do wyboru),
  progów, p, estymatora ani granicy 0,9999.
- Nie stroić generatora na odrzuceniach testu zbiorczego (kalibracja tylko na VR i odsetku przy granicy).
- Nie dotykać alpha; `data/` nie do gita; nie scalać do `main`.

## Kryteria odbioru (dowody)

- Commit pre-rejestracji poprzedza kalibrację i przebieg rejestrowy; w README hash.
- Kalibracja wg STOP z góry; przebieg rejestrowy z K-a, K-b, K1, K2, K7 dla A0 i komórki z (b); druga droga; „Kogo NIE ma w zbiorze”;
  werdykt Ready/Caveats/Revision podpisany przez Claude.
- `python -m pytest -q` i `python -m ruff check . && python -m black --check .` zielone; commit i push.

## Wynik

(dopisuje orkiestrator)
