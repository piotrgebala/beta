---
id: 022
tytul: po wyniku 021 — reguła K′ (bootstrap blokowy) jako diagnostyka albo prognoza widząca poziom wariancji
typ: badawcze
status: czeka_na_decyzje
zlecil: orkiestrator
decyzja_uzytkownika: "brak — propozycja Claude po wyniku karty 021; zmiana zamrożonej reguły K po obejrzeniu wyniku wymaga Twojej zgody (STATUS.md, decyzja #14)"
utworzono: 2026-10-08
zalezy_od: [021]
budzet: "Opus, 1–2 sesje (pre-rejestracja, ewentualny przebieg rejestrowy na laboratorium LV2d)"
---

# 022 — co dalej po wyniku 021

## Po co

Karta 021 (Caveats) pokazała, że zamrożona reguła K ma moc przy czterech monetach, ale odrzuca estymowany GARCH-t w komórkach B (rozmiar testu K-a
28,7 / 20,3 / 17,0 % wobec progu 10 %). Rozrzut odsetka trafień GARCH-t między panelami jest 1,40–1,64 raza większy, niż zakłada błąd dla niezależnych dni (wyrocznia: 1,00–1,01),
a sam średni błąd dałby tylko 2,5–3,2 % odrzuceń. Źródło jest mieszane (małe prawdziwe zaniżenie ryzyka + za wąski błąd testu przy zależnych trafieniach) i z obecnego
wydruku nie da się go rozdzielić. Przy zamrożonej regule runda 018 na danych jest NIEMIERZALNA w scenariuszu jak w danych (R3).

## Zakres (do rozstrzygnięcia przez użytkownika; rekomendacja Claude na pierwszym miejscu)

1. **(a′) Reguła K′ z bootstrapem blokowym w teście A (i odpowiednikiem dla B i C) — jako diagnostyka** na tym samym laboratorium LV2d (komórki A0, B1–B3, nowe ziarna, własny licznik).
   Cel: ile z K-a w B to wada błędu testu. **Zmienia zamrożoną regułę po obejrzeniu wyniku, więc wymaga Twojej zgody i osobnej pre-rejestracji** z kryteriami zapisanymi z góry.
   Uczciwe zastrzeżenia do zapisania w pre-rejestracji: (i) długość bloku to kluczowy wybór — fazy poziomu wariancji mają średnio 300 dni, a ocena ma 1 691 dni, więc to kilka faz;
   blok zdolny je uchwycić (≥ 100 dni) daje kilkanaście bloków i słaby bootstrap, a krótki (np. 20 dni, jak w 017 i 020) ich nie uchwyci; mierzalność K′ trzeba policzyć (R3) przed uruchomieniem;
   (ii) rachunek z n_eff (z błędem większym o 1,40–1,64 raza) daje moc K-b tylko ok. 62–71 % < 80 %, więc K′ może przenieść porażkę z K-a na K-b i potwierdzić, że przy kilku niezależnych
   fazach poziomu GARCH-t na realnych danych nie da się zwalidować — wynik wart wiedzieć, ale nie „naprawa”.
2. **(d) Prognoza widząca poziom wariancji** (np. filtr z krótszą pamięcią albo wykrywanie przesunięć tylko z przeszłości, R6) oceniona regułą K bez zmian na laboratorium LV2d.
   Mieści się w autonomii badawczej, ale to program, nie pojedyncza runda, a jego ocena na danych napotka to samo ograniczenie liczby faz. Wracam do niego, jeśli (a′) pokaże,
   że po poprawce błędu K-a przechodzi, a model dalej zawodzi.
3. **(b) Zamknięcie rundy VaR/ES na danych** — rozsądne, jeśli (a′) potwierdzi, że niemierzalność wynika z liczby faz, a nie z modelu. **(c) Szerszy koszyk** nie leczy tego problemu
   (poziom wariancji jest wspólny dla monet, 20 monet to nadal te same kilka faz, R12) i zmienia Twoją decyzję o czterech monetach; nie rekomenduję.

## Czego NIE robić

- Nie uruchamiać karty 018 ani nie liczyć odsetka trafień na prawdziwych danych.
- Nie zmieniać plików zamrożonych (`run_lv2c.py`, `run_lv2.py`, `run_lv2d.py`, `garch_t.py`, `miara/var_es.py`), progów 10 % i 80 %, p, estymatora ani granicy 0,9999; K′ to nowy plik.
- Nie luzować progu K-a po fakcie ani nie stroić generatora na odrzuceniach testu zbiorczego.
- Nie używać ziaren z 021 (20_262_101, 20_262_021, 20_269_999, 27_182_818) ani wcześniejszych.
- Nie dotykać alpha; `data/` nie do gita; nie scalać do `main`.

## Kryteria odbioru (dowody)

- Twoja zgoda zapisana w polu `decyzja_uzytkownika`; pre-rejestracja w gicie PRZED przebiegiem (R1–R4), rachunek mierzalności K′ przed uruchomieniem (R3);
  przewidywania mocy zapisane dopiero po rachunku z n_eff.
- `python -m pytest -q` i `python -m ruff check . && python -m black --check .` zielone; commit i push na gałąź.

## Wynik

(dopisuje orkiestrator)
