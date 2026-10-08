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
   ok. połowę dopasowań (hipoteza z pamięci, NIE sprawdzona w źródle: granica jest jednostronna, więc nawet przy prawdziwej wartości
   dokładnie na granicy estymator mógłby lądować na niej w ok. 50 % przypadków). 51 % z danych oznaczałoby wtedy „poza granicą”,
   czego sama trwałość nie wytworzy. Pierwszy krok pre-rejestracji: krótka kontrola tej hipotezy (np. czy estymator z sufitem
   0,99980 i prawdziwą trwałością 0,9999 daje pułap ok. 50 %, czy mniej). Nowy plik generatora
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
4. Reguła K, progi 10 % i 80 %, poziom p = 5 %, `dopasuj_garch_t`, granica 0,9999, kontrole i test zbiorczy z `run_lv2c`: bez zmian;
   nowe są tylko generator i jego kalibracja. Ziarna rejestrowe i pilotażowe nowe (rozłączne z 20_261_019, 20_261_091
   i 31_415_926). Ziarno 20_261_019 jest częściowo odsłonięte przez próbę dymną `rejestr --smoke` (README 019, „Ujawnienie”); próby
   dymne 021 na ziarnie spoza wszystkich ziaren rejestrowych i pilotażowych.
5. **Poprawki z przeglądu kodu 019 przed pre-rejestracją** (README 019, „Przegląd kodu”): runner 019 jest zamrożony, bo wytworzył
   wynik STOP 1, więc poprawki idą do **nowego pliku** (np. `symulacje/run_lv2d.py`, import tego, co niezmienione), z testami:
   (i) reguła STOP (3) „NaN → STOP” zaimplementowana (NaN w pilotażu, kalibracji i przebiegu rejestrowym); (ii) straż znaku nachylenia
   w siecznej (znika `xfail` w `tests/test_run_lv2c_przeglad.py`); (iii) `potwierdz` nie marnuje korekt, gdy VR jest w tolerancji, a zawodzi
   tylko odsetek przy granicy; (iv) krok 2b: cel poniżej v na początku siatki daje początek siatki, nie `None` (znika drugi `xfail`);
   (v) jednowątkowy BLAS także przy `workers <= 1`; (vi) K-gen-N na liczbie paneli dającej realną czułość, testy trybów `kalibruj`
   i `kontrola-n` w `main`.
6. **Wnioski projektowe z przeglądu 019 dla nowej kalibracji:** (a) wybór α* jako „pierwszego powyżej progu” jest podatny na przekleństwo
   zwycięzcy — wybierać z plateau (np. środek zakresu spełniającego warunek) albo zapisać z góry, że potwierdzenie jest na świeżych
   panelach z tolerancją wynikającą z SE; (b) przy α + β = 0,9999 panel jest „zapadniętym IGARCH” (mediana |r| ≈ 0,12 % przy `daily_vol`
   4 %), więc kalibracja ma sprawdzać także rozsądek skali (np. rozkład |r|), a nie tylko VR i odsetek przy granicy; (c) 100 % trafień
   w granicę to górna granica trwałości estymatora (sufit ≈ 0,99980 < 0,9999 generatora) — przy generatorze z przesunięciami poziomu
   rozważyć, czy cel ma dotyczyć flagi `brzeg` w ogóle, czy konkretnie trwałości; (d) tolerancja ± 5 pp jest wąska wobec SE celu
   (SD pojedynczego panelu ≈ 26 pp, 51,3 % z czterech monet ma podobny rząd błędu) — zapisać w pre-rejestracji uczciwy przedział celu.
7. Pre-rejestracja w gicie PRZED kalibracją i przebiegiem rejestrowym (R1–R4, zasada 26), przewidywania i tabela konsekwencji z góry.
8. Własny katalog rundy, wiersz w `runs/INDEX.md`. Licznik: **poza licznikami** (dane syntetyczne).


## Czego NIE robić

- Nie uruchamiać karty 018 ani nie liczyć odsetka trafień na prawdziwych danych.
- Nie zmieniać plików zamrożonych (LV2, `garch_panel_wspolny_szok.py`, `run_lv2c.py`; poprawki z przeglądu idą do nowego pliku, p. wyżej),
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
