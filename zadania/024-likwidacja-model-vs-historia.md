---
id: 024
tytul: czy P likwidacji z kalkulatora zgadza się z rzeczywistymi dotknięciami progów 2021–2026
typ: badawcze
status: w_toku
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

(po uruchomieniu)
