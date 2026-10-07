---
id: 020
tytul: opis zależności trafień VaR 5 % dla koszyka BTC, ETH, SOL, BNB (karta opisowa, jak 017)
typ: badawcze
status: do_przegladu
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

Zrobione 2026-10-07. Runda: `runs/2026-10-07_020-opis-4-monety/README.md` (pre-rejestracja `afe6791`, kod `35eb867`, poprawki testów (`c61555b`)
i reguły STOP po niezależnym przeglądzie w osobnym commicie przed wynikiem; werdykt **Caveats**; licznik „ryzyko 2021+” zostaje 0 —
karta opisowa).

- **Zależność trafień dla BTC, ETH, SOL, BNB:** VR = 2,264, ρ̂ = 0,4213, SE = 0,0911 (bootstrap blokowy, L = 20; L = 10 / 40: 0,0931 /
  0,0909), ρ̂ ± 2 SE = [0,239; 0,604] (VR [1,72; 2,81]). Przedział obejmuje wartość laboratorium (0,282) i wynik 15 monet (0,500),
  więc dla czwórki nie umiemy powiedzieć, czy zależność jest większa niż w laboratorium.
- **Ile niezależnych monet dziennie** (wzór przybliżony K / VR): 4 / 2,26 = ok. 1,8; dla 15 monet z 017: ok. 1,9. Moc testu dla K = 4
  jest niezmierzona (to zadanie 019).
- **Spójność z 017: ZGODNA** (228 dopasowań, 117 przy granicy = 51 %); kontrole R8 dla K = 4 zaliczone (średnie ρ̂ 0,286 / 0,010).
- Druga droga (własny panel, zamrożone moduły LV2, inne ziarno) odtwarza VR i ρ̂ co do cyfry, SE 0,0894; nie weryfikuje estymatora
  `dopasuj_garch_t`.
- **Konsekwencja:** 019 jest przeliczana na K = 4 z celem VR = 2,26 i drugim scenariuszem LV2 (bez wspólnego szoku); 018 dalej
  wstrzymana.
