---
id: 009
tytul: laboratorium LV1 — moc testów VaR/ES przy n ≈ 1 600 dni × 20 monet
typ: badawcze
status: nowe
zlecil: uzytkownik
decyzja_uzytkownika: "2026-10-05: „rozpisz sobie kolejne taski, zaplanuj i zacznij realizować” + akceptacja planu (007–012)"
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

(dopisuje orkiestrator)
