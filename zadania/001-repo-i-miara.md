---
id: 001
tytul: fundament repo i port przyrządu miara z testem parytetu
typ: infra
status: do_przegladu
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

2026-09-30, gałąź `claude/fervent-fermi-vfctk6` (sesja pracowała bezpośrednio na gałęzi wyznaczonej przez
środowisko, nie na `zadanie-001-*`). Alpha tylko czytana (commit `fba7230`, `git status` czysty po pracy).

- **Port `miara/`:** `neff.py` (N_eff, `summarize_pnl`), `metryki.py` (trafność, Wald, break-even, moc,
  `expected_trades`, `measurability_report`, pooled/edge per reżim, `summarize_trade_returns`), `dsr.py`
  (czyta WSPÓLNY rejestr alpha; `python -m miara.dsr` → N = 40, t 3,84 dla N + 1 — jak alpha),
  `kontrola_negatywna.py` (generator 1:1 + dwie reguły referencyjne). Świadomie bez Sharpe per fold i
  klasyfikacji GO/NO-GO Fazy 0 (uzasadnienie w docstringu `metryki.py`).
- **Parytet:** `tests/test_parytet_alpha.py` — 132 wektory, 32 funkcje (≥ 1 wektor na każdą; strażnik
  w teście), tolerancja 1e-12; fixture `tests/fixtures/parytet_alpha.json` z hashem commita alpha i SHA-256
  plików źródłowych; generator `python -m tests.generuj_parytet_alpha`. Kontrola czułości testu: zmiana
  jednej stałej (z 1,959964 → 1,96) daje 23 czerwone przypadki.
- **Loader:** `dane/ladowanie.py::wczytaj_swiece` + `min_start` (brak klucza = błąd) + 5 testów.
- **CI:** `.github/workflows/ci.yml` (ruff, black, pytest; Python 3.12, `requirements-lock.txt`) —
  przebieg [36753507178](https://github.com/piotrgebala/beta/actions/runs/36753507178): **success**.
- **Lock:** `requirements-lock.txt` (Python 3.12.3, m.in. numpy 2.5.3, pandas 3.0.6, scipy 1.18.1).
- **NC1 odtworzona:** runda NC1B (`runs/2026-09-30_nc1b-kontrola-negatywna-miara/`) — ZALICZONA,
  fałszywe alarmy 2/80 = 2,5 % [0,7; 8,7] wobec alpha 3,3 % [1,3; 8,3]; czułość 40/40.
- `python -m pytest -q`: 161 passed; ruff i black czyste.

Zastrzeżenia: parytet porównuje KOD w jednym środowisku (Python 3.12, pandas 3.0), nie wersje bibliotek
z locka alpha; test rejestru alpha pomija się w CI (brak alpha obok). Manifest danych (PRD E0) — zadanie 002.
Zamknięcie E0 — decyzja użytkownika.
