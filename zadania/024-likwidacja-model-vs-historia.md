---
id: 024
tytul: czy P likwidacji z kalkulatora zgadza się z rzeczywistymi dotknięciami progów 2021–2026
typ: badawcze
status: do_przegladu
zlecil: uzytkownik
decyzja_uzytkownika: "2026-10-09: „Tak” (na propozycję porównania modelowego dystansu i P likwidacji z zapisem rzeczywistych dotknięć progów na historii)"
utworzono: 2026-10-09
zalezy_od: [023]
budzet: "Opus, 1–2 sesje"
---

# 024 — model P likwidacji kontra historia

## Po co

Karta 023 pokazuje P(likwidacja w 7 dni) z modelu (t_ν, stała σ) i sama ostrzega, że to dolne oszacowanie. Ta runda sprawdza
na historii BTC, ETH, SOL, BNB, czy rzeczywistych dotknięć progu było więcej, niż model przewidywał. To pytanie o ryzyko:
licznik „ryzyko 2021+” rośnie 0 → 1 przy uruchomieniu części z wynikami.

## Zakres

1. Pre-rejestracja (`runs/2026-10-09_024-likwidacja-model-vs-historia/README.md`) + rachunek mierzalności (`raw_mierzalnosc.txt`) —
   ZACOMMITOWANE przed odczytem high/low.
2. Dopiero potem: runner z wynikami (świece przez jedną funkcję ładującą, R16), testy detekcji dotknięcia i bootstrapu/klastrów,
   jedno uruchomienie rejestrowe, README z wynikiem, „Co na plus / Co na minus”, werdykt, wiersz w `runs/INDEX.md`, decyzja w `STATUS.md`.

## Czego NIE robić

- Nie zmieniać L, mmr, horyzontu, reguły decyzji ani procedury po obejrzeniu wyniku (nowy wariant = osobny licznik).
- Nie używać wyniku do zwiększania dźwigni; kalkulator służy tylko do zmniejszania ekspozycji.
- Nie dotykać alpha (tylko odczyt), dziennika, kapitału ani plików zamrożonych; `data/` nie idzie do gita.

## Kryteria odbioru (dowody)

- `pytest`, `ruff`, `black` zielone; test braku podglądu przyszłości dla σ̂ walk-forward.
- Pre-rejestracja w gicie wcześniej niż jakikolwiek kod czytający high/low (kolejność commitów w `git log`).
- Wynik: O/E na poziomie głównym (3×, long + short) z p i werdyktem „model zaniża” / „nie wykazano zaniżenia”.

## Wynik

Werdykt **Caveats** (szczegóły: README rundy). 3× long+short: O = 23 klastrów wobec E = 14,37 (O/E 1,60, p 0,0217) → formalnie „model zaniża”;
brzegowo: O/E 0,71 przy VR 1 i 2,83 przy VR 4, na surowych oknach 0,85, 64 % trafień to SOL, ceny last zamiast mark. Przeliczenie niezależne zgodne.
Skutek: `modele/rozmiar_dzis.py` pokazuje też P 3× ×1,6; licznik „ryzyko 2021+” = 1.
