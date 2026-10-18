---
id: 027
tytul: F2-3 — HAR + pięć wskaźników technicznych vs czysty HAR na BTC, ETH, SOL, BNB (zmienność, nie kierunek)
typ: badawcze
status: czeka_na_decyzje
zlecil: uzytkownik
decyzja_uzytkownika: "2026-10-18: „przygotuj” (na pytanie, czy przygotować kartę; start przebiegu osobno)"
utworzono: 2026-10-18
zalezy_od: [010, 011, 025]
budzet: "Opus, 1 sesja"
---

# 027 — F2-3: HAR + wskaźniki techniczne

## Po co

Użytkownik zapytał, czy ML można oprzeć na wskaźnikach typu EMA, MACD, RSI. Kierunku ceny z cech wykresu nie
przewidujemy (alpha: p = 50,27 %). Zostaje prognoza zmienności, gdzie szczebel 5 drabiny F2 (DVOL) nie przeszedł.
Karta sprawdza jedną rzecz: czy pięć wskaźników technicznych poprawia HAR na QLIKE.

## Zakres

- `dane/ohlc.py`, `cechy/techniczne.py` + wpisy w `cechy/rejestr.yaml`, `modele/run_f23.py`.
- Testy: `tests/test_techniczne.py`, `tests/test_f23.py`, bramka przecieku w `tests/test_cechy.py`.
- Pre-rejestracja i (po starcie) wynik: `runs/2026-10-18_f23-har-techniczne/README.md`.

## Czego NIE robić

Nie przewidywać kierunku (to odczyt zwrotu i podbicie rejestru alpha); nie dodawać MACD, wolumenu, funding,
DVOL w tej rundzie; nie luzować progu ani bramki po fakcie; nie uruchamiać boostingu.

## Kryteria odbioru (dowody)

Testy i lint zielone; commit pre-rejestracji przed `raw_output.txt`; po starcie wiersz wyniku w `runs/INDEX.md`
i licznik „zmienność 2021+” 2 → 3 tylko jeśli bramka MIERZALNA.

## Wynik

Pre-rejestracja gotowa, przebieg na stratach NIE uruchomiony (czeka na zielone światło użytkownika).
Przewidywane MDE 0,10 (0,09–0,12), P(MIERZALNA) ≈ 45 %, P(POZYTYWNY) ≈ 4 %.
