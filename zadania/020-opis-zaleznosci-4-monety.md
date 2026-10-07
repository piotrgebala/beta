---
id: 020
tytul: opis zależności trafień VaR 5 % dla koszyka BTC, ETH, SOL, BNB (karta opisowa, jak 017)
typ: badawcze
status: nowe
zlecil: orkiestrator
decyzja_uzytkownika: "2026-10-07: „rób tylko prognozy na eth btc sol, bnb” (STATUS.md, Decyzje użytkownika); karta jest moim wykonaniem tej decyzji"
utworzono: 2026-10-07
zalezy_od: [017]
budzet: "Opus, 1 sesja"
---

# 020 — opis zależności trafień dla 4 monet

## Po co

Po zmianie koszyka na BTC, ETH, SOL, BNB nie wiemy, jaką zależność trafień (VR, ρ̂) i jaki odsetek dopasowań GARCH-t przy
granicy daje ta czwórka. Te liczby są celem kalibracji laboratorium dla K = 4 (karta 019). Karta jest opisowa: nic nie
ocenia, nie liczy odsetka trafień i nie podbija licznika „ryzyko 2021+” (zostaje 0).

## Zakres

1. Pre-rejestracja w gicie PRZED przebiegiem (zasada 26): `runs/RRRR-MM-DD_020-…/README.md`; ta sama miara i ten sam
   moduł co 017 (`modele/pomiar_rho_h.py`, bez zmian), lista monet = 4, panel wspólny do 2026-09-30, `p = 5 %`,
   bootstrap blokowy L = 20, B = 2 000, ziarno zapisane z góry.
2. Raport: liczba dni oceny, VR, ρ̂ = (VR − 1)/3, SE bootstrapem, odsetek dopasowań przy granicy persystencji,
   rozbicie na monety (tylko granica; nie trafienia). Bez bramki zgodności i bez werdyktu o kalibracji.
3. Kontrole R8 jak w 017 (dodatnia i ujemna), druga droga jak w `druga_droga.py`, przegląd kodu, jeśli kod się zmienia.
4. Zapisać z góry, że to **drugi odczyt tych samych danych** (podzbiór panelu z 017): służy do kalibracji, nie do
   potwierdzenia wyniku 017.

## Czego NIE robić

- Nie liczyć odsetka trafień ani nie oceniać prognoz; nie uruchamiać 018.
- Nie zmieniać `dopasuj_garch_t` ani zamrożonych plików LV2.
- Nie dotykać `data/` w gicie ani rejestru alpha.

## Kryteria odbioru

- Commit pre-rejestracji poprzedza przebieg; `raw_output.txt`; README z wynikiem, „Kogo NIE ma w zbiorze”, werdykt
  podpisany przez Claude; wiersz w `runs/INDEX.md` (licznik: poza licznikami); testy i lint zielone; commit i push.

## Wynik

(dopisuje orkiestrator)
