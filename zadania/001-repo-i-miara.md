---
id: 001
tytul: fundament repo i port przyrządu miara z testem parytetu
typ: infra
status: nowe
zlecil: uzytkownik
decyzja_uzytkownika: "2026-09-30: osobne repo i niech nazywa się beta"
utworzono: 2026-09-30
zalezy_od: []
budzet: "Opus, 1–2 sesje"
---

# 001 — fundament repo i port przyrządu `miara`

## Po co

Etap E0 PRD (§12). Bez przyrządu identycznego z alpha wyniki obu repo nie są porównywalne (CLAUDE.md zasada 24).

## Zakres

- Port do `miara/` z alpha: `backtest/metrics.py` (mierzalność, Wald, break-even, `expected_trades`,
  `measurability_report`), część pomiarowa `backtest/checkpoint_lib.py` (`summarize_trade_returns`, N_eff ≤ n),
  `backtest/dsr.py`, `backtest/negative_control.py`. Bez zależności od reszty alpha.
- `tests/test_parytet_alpha.py`: wektory wejściowe → wartości oczekiwane policzone kodem alpha (zapisane jako
  fixture z hashem commita alpha), tolerancja 1e-12.
- Loader danych z filtrem `data.min_start` (`config/settings.yaml`) w jednej funkcji + test.
- CI GitHub Actions: pytest + ruff + black na każdym pushu.
- `requirements-lock.txt` z wersjami zainstalowanymi na serwerze.

## Czego NIE robić

Żadnych odczytów danych rynkowych; żadnych zmian w alpha; bez modeli.

## Kryteria odbioru (dowody)

Zielone CI; test parytetu obejmuje ≥ 1 wektor na każdą przeniesioną funkcję publiczną; kontrola negatywna NC1
odtworzona na generatorze (fałszywe alarmy w przedziale z alpha, wniosek 79).

## Wynik

(dopisuje orkiestrator)
