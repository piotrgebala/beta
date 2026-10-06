---
id: 009
tytul: laboratorium LV1 — moc testów VaR/ES przy n ≈ 1 600 dni × 20 monet
typ: badawcze
status: w_toku
zlecil: uzytkownik
decyzja_uzytkownika: "2026-10-06: „LV1: poprawiona, 011: a, E0: zamknij”"
utworzono: 2026-10-05
zalezy_od: [008]
budzet: "Opus, 1 sesja, równolegle na 32 rdzeniach"
---

# 009 — LV1

## Po co

R3: zanim jakakolwiek runda VaR/ES dotknie danych, liczymy, czy przy naszej długości historii testy w ogóle
odróżnią dobry model od złego (przy VaR 1 % i 1 600 dniach spodziewamy się ~16 przekroczeń na monetę — mało).

## Zakres

- Pre-rejestracja w `runs/RRRR-MM-DD_lv1-moc-var-es/` przed przebiegiem: generator GARCH-t skalibrowany do
  momentów krypto (jak LM1), modele „prawdziwy” vs „zły” (normalny, za krótkie okno), poziomy 1 % i 5 %,
  n ∈ {600, 1 000, 1 600}, kryterium zbiorcze po monetach, reguła MIERZALNA/NIEMIERZALNA.
- Symulacja równoległa (multiprocessing), jawne ziarna (R19).

## Czego NIE robić

Żadnych prawdziwych danych — licznik 0 (dane syntetyczne).

## Kryteria odbioru (dowody)

README rundy z werdyktem, `raw_output.txt`, wiersz w `runs/INDEX.md`.

## Wynik

2026-10-06: pre-rejestracja gotowa i zamrożona w gicie (`f8a6a0f`): `symulacje/run_lv1.py`,
`symulacje/moc_var_es.py`, `tests/test_lv1.py` (48 testów), `runs/2026-10-05_lv1-moc-var-es/README.md`.
Trzech niezależnych recenzentów (pilotaże na innych ziarnach, ręczne mutacje — wszystkie wykryte).
Najważniejsza poprawka: test zbiorczy (dzienne sumy trafień, R12) z bootstrapem-t o równych ogonach.
Poprzednia wersja prawie nie odrzucała po stronie „za dużo trafień”, czyli przy zaniżonym ryzyku.

**Czeka na Twoją decyzję (punkt 7 w README) przed pełnym przebiegiem (~30 min):**
- **(a) reguła poprawiona (rekomendacja):** x\* = 0,10 przy obu p; „moc wobec normalnej” jest
  kryterium tylko przy p = 1 %. Przy 5 % rozkład normalny ZAWYŻA VaR (prognoza ostrożniejsza niż
  prawda), więc żądanie, by test go odrzucał, mierzyło wykrywanie ostrożności, a nie ryzyka. To ten
  sam błąd projektu, który w KV1 usunięto przed wynikiem.
- **(b) reguła pierwotna:** x\* = 0,05 przy 5 % i „normalna” jako kryterium przy obu p.

Zmiany do (a) zrobiono PO pilotażu, który wskazuje, że przestawiają przewidywany wynik dla p = 5 %
z NIEMIERZALNA na MIERZALNA — dlatego wybór jest Twój. Skrypt drukuje werdykt według obu reguł,
więc jeden przebieg wystarczy przy każdym wyborze.
