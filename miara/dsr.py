"""
dsr.py — próg t skorygowany o liczbę prób (DSR, Bailey & López de Prado 2014) i odczyt WSPÓLNEGO
rejestru odczytów historii (zasady R5 i 22).

Port 1:1 z `alpha/backtest/dsr.py` (parytet: `tests/test_parytet_alpha.py`, zasada 24). Jedyna
różnica: domyślna ścieżka rejestru wskazuje plik ALPHA (`data.alpha_repo` w `config/settings.yaml`)
— beta nie ma własnego budżetu odczytów na historii 2021–2026, a rejestr tylko czyta (zasada 23).

Wzory:
    E[max t](N) = (1 − γ) Φ⁻¹(1 − 1/N) + γ Φ⁻¹(1 − 1/(N e))
    DSR = Φ( (SR − SR0) √(T − 1) / √(1 − g3·SR + (g4 − 1)/4 · SR²) ),  SR0 = E[max t] · √V, V = 1/T
    t*(N, DSR) = E[max t](N) + Φ⁻¹(DSR)   (granica dużej próby, rozkład normalny)
Dwie metody liczenia N (skrypt drukuje obie i żadnej nie wybiera; obowiązującą zapisuje
`alpha/STATUS.md` — dziś metoda AU4 = Σ wariantów):
- metoda AU4 = Σ wariantów po wierszach `odczyt_programu = tak`;
- z odczytami 0-wariantowymi = Σ max(wariantow, 1).

    python -m miara.dsr              # N z rejestru alpha, progi dla rundy 1-wariantowej
    python -m miara.dsr --k 5        # progi dla rundy z 5 wariantami
    python -m miara.dsr --n 41       # progi dla dowolnego N
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import yaml
from scipy.optimize import brentq
from scipy.stats import norm

EULER_GAMMA = 0.5772156649
ROOT = Path(__file__).resolve().parents[1]


def _rejestr_alpha() -> Path:
    """Rejestr WSPÓLNY z alpha (zasada 22): `<data.alpha_repo>/runs/odczyty_historii.csv`, tylko odczyt."""
    cfg = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    return (ROOT / cfg["data"]["alpha_repo"] / "runs" / "odczyty_historii.csv").resolve()


REJESTR = _rejestr_alpha()
KOLUMNY = (
    "nr",
    "data",
    "runda",
    "katalog",
    "baza",
    "rodzaj",
    "odczyt_programu",
    "wariantow",
    "uwagi",
)
BAZY = frozenset({"krypto-2021-2026", "tradfi-1990-2026", "krypto-na-żywo", "inna", "stara-baza"})
RODZAJE = frozenset({"werdykt", "opis-z-wynikiem", "bez-wyniku"})
ODCZYT = frozenset({"tak", "nie"})
LATA_HISTORII = 5.5  # 2021-01-01 → 2026-06-30
DSR_PROGI = (0.80, 0.95)


# ---------------------------------------------------------------------------- wzory (kopia AU4)


def expected_max_t(n: int) -> float:
    """Oczekiwane maksimum n niezależnych standardowych normalnych (przybliżenie BLdP; n ≤ 1 → 0)."""
    if n <= 1:
        return 0.0
    g = EULER_GAMMA
    return float((1 - g) * norm.ppf(1 - 1 / n) + g * norm.ppf(1 - 1 / (n * math.e)))


def expected_max_sr(n_trials: int, var_sr: float) -> float:
    """Oczekiwane maksimum N Sharpe'ów o wariancji `var_sr` przy prawdziwym SR = 0 (jak AU4)."""
    return math.sqrt(var_sr) * expected_max_t(n_trials)


def deflated_sharpe(sr: float, sr0: float, t: float, g3: float, g4: float) -> float:
    """P(prawdziwy SR > SR0) z poprawką na długość próby, skośność i kurtozę (Bailey & LdP 2014)."""
    den2 = 1 - g3 * sr + (g4 - 1) / 4 * sr**2
    if den2 <= 0:
        raise ValueError(
            f"wzór DSR nie działa: 1 − g3·SR + (g4 − 1)/4·SR² = {den2:.3g} ≤ 0 "
            f"(SR {sr:.3g}, g3 {g3}, g4 {g4})"
        )
    den = math.sqrt(den2)
    return float(norm.cdf((sr - sr0) * math.sqrt(t - 1) / den))


def required_t(
    n: int, dsr: float = 0.95, n_obs: int | None = None, g3: float = 0.0, g4: float = 3.0
) -> float:
    """Najmniejsze t = SR·√T, przy którym najlepszy z n prób ma DSR ≥ `dsr`.

    Bez `n_obs`: granica dużej próby i rozkładu normalnego, t* = E[max t](n) + Φ⁻¹(dsr).
    Z `n_obs` (T, liczba obserwacji) oraz skośnością g3 i kurtozą g4: dokładne rozwiązanie wzoru DSR.
    Pierwiastka szukamy od SR0 (tam DSR = 0,5) w stronę zadanego `dsr`, podwajając krok od
    1/√T; przy grubych ogonach DSR ma asymptotę Φ(±2√(T − 1)/√(g4 − 1)) — poziom poza nią jest
    nieosiągalny i daje czytelny ValueError, tak jak ujemne wyrażenie pod pierwiastkiem.
    """
    if n < 1:
        raise ValueError(f"n (liczba prób) musi być ≥ 1, jest {n}")
    if not 0.0 < dsr < 1.0:
        raise ValueError(f"dsr musi leżeć w (0; 1), jest {dsr}")
    if n_obs is None:
        return expected_max_t(n) + float(norm.ppf(dsr))
    if n_obs < 3:
        raise ValueError(f"n_obs musi być ≥ 3, jest {n_obs}")
    sr0 = expected_max_sr(n, 1.0 / n_obs)

    def f(s: float) -> float:
        return deflated_sharpe(s, sr0, n_obs, g3, g4) - dsr

    kierunek = 1.0 if dsr >= 0.5 else -1.0
    krok = 1.0 / math.sqrt(n_obs)
    a, fa = sr0, f(sr0)
    if fa == 0.0:
        return float(sr0 * math.sqrt(n_obs))
    for k in range(40):
        b = sr0 + kierunek * krok * 2**k
        fb = f(b)
        if fa * fb <= 0:
            return float(brentq(f, min(a, b), max(a, b)) * math.sqrt(n_obs))
        a, fa = b, fb
    raise ValueError(
        f"dsr {dsr} nieosiągalne przy n_obs {n_obs}, g3 {g3}, g4 {g4} "
        "(asymptota wzoru DSR przy grubych ogonach lub krótkiej próbie)"
    )


def min_annual_sr(t: float, lata: float = LATA_HISTORII) -> float:
    """Roczny SR, który na `lata` latach daje statystykę t (t = SR_roczny · √lata)."""
    return t / math.sqrt(lata)


# ---------------------------------------------------------------------------- rejestr


def load_registry(path: Path = REJESTR) -> list[dict[str, str]]:
    """Wiersze rejestru jako słowniki (wartości tekstowe, bez konwersji)."""
    with open(path, encoding="utf-8-sig", newline="") as f:  # -sig: plik z BOM (Excel)
        return list(csv.DictReader(f))


def _odczyty(rows: list[dict[str, str]], do_nr: int | None) -> list[dict[str, str]]:
    return [
        r
        for r in rows
        if r["odczyt_programu"] == "tak" and (do_nr is None or int(r["nr"]) <= do_nr)
    ]


def n_program(rows: list[dict[str, str]], do_nr: int | None = None) -> int:
    """N do DSR: Σ max(wariantow, 1) po odczytach programu (do wiersza `do_nr` włącznie)."""
    return sum(max(int(r["wariantow"]), 1) for r in _odczyty(rows, do_nr))


def n_warianty(rows: list[dict[str, str]], do_nr: int | None = None) -> int:
    """N metodą AU4: sama suma wariantów odczytów programu (bez odczytów 0-wariantowych)."""
    return sum(int(r["wariantow"]) for r in _odczyty(rows, do_nr))


def registry_errors(rows: list[dict[str, str]]) -> list[str]:
    """Błędy formatu i spójności rejestru (pusta lista = rejestr poprawny)."""
    errs: list[str] = []
    seen_kat: set[str] = set()
    prev_data = ""
    for i, r in enumerate(rows, 1):
        tag = f"wiersz {i} ({r.get('katalog', '?')})"
        if tuple(r) != KOLUMNY:
            errs.append(f"{tag}: kolumny {tuple(r)} ≠ {KOLUMNY}")
            continue
        if any(v is None for v in r.values()):
            errs.append(f"{tag}: brak pól (za mało wartości w wierszu)")
            continue
        if r["nr"] != str(i):
            errs.append(f"{tag}: nr {r['nr']} ≠ {i} (numeracja ciągła od 1)")
        if r["data"] < prev_data:
            errs.append(f"{tag}: data {r['data']} wcześniejsza niż w wierszu wyżej")
        prev_data = r["data"]
        if not r["katalog"].startswith(r["data"] + "_"):
            errs.append(f"{tag}: katalog nie zaczyna się od daty {r['data']}")
        if r["katalog"] in seen_kat:
            errs.append(f"{tag}: duplikat katalogu")
        seen_kat.add(r["katalog"])
        if not r["runda"].strip():
            errs.append(f"{tag}: pusta runda")
        if not r["uwagi"].strip():
            errs.append(f"{tag}: puste uwagi (każda decyzja tak/nie ma uzasadnienie)")
        if r["baza"] not in BAZY:
            errs.append(f"{tag}: baza {r['baza']!r} spoza {sorted(BAZY)}")
        if r["rodzaj"] not in RODZAJE:
            errs.append(f"{tag}: rodzaj {r['rodzaj']!r} spoza {sorted(RODZAJE)}")
        if r["odczyt_programu"] not in ODCZYT:
            errs.append(f"{tag}: odczyt_programu {r['odczyt_programu']!r} spoza {sorted(ODCZYT)}")
        if r["odczyt_programu"] == "tak" and r["rodzaj"] == "bez-wyniku":
            errs.append(f"{tag}: odczyt programu bez wyniku — sprzeczność")
        if not r["wariantow"].isdigit():
            errs.append(f"{tag}: wariantow {r['wariantow']!r} nie jest liczbą ≥ 0")
            continue
        krypto = r["baza"] in ("krypto-2021-2026", "stara-baza")
        if krypto and int(r["wariantow"]) > 0 and r["odczyt_programu"] == "nie":
            errs.append(f"{tag}: warianty zużyte na historii krypto, a odczyt_programu = nie")
    return errs


# ---------------------------------------------------------------------------- raport CLI


def threshold_rows(ns: list[int], lata: float = LATA_HISTORII) -> list[str]:
    """Wiersze tabeli: N, E[max t], t* dla DSR 0,80 i 0,95, minimalny roczny SR na `lata`."""
    out = [
        (
            f"  {'N':>4} | E[max t] | t dla DSR 0,80 | t dla DSR 0,95 | "
            f"min. SR roczny na {lata:g} roku (0,80 / 0,95)"
        )
    ]
    for n in ns:
        t80, t95 = (required_t(n, d) for d in DSR_PROGI)
        out.append(
            f"  {n:4d} | {expected_max_t(n):8.2f} | {t80:14.2f} | {t95:14.2f} | "
            f"{min_annual_sr(t80, lata):.2f} / {min_annual_sr(t95, lata):.2f}"
        )
    return out


def report(rows: list[dict[str, str]], lata: float = LATA_HISTORII, k: int = 1) -> list[str]:
    """Raport do pre-rejestracji: obie liczby N i próg t dla rundy z `k` wariantami (N + max(k, 1)).

    Skrypt nie wybiera metody liczenia N — drukuje obie; która obowiązuje, mówi `STATUS.md`.
    """
    if k < 0:
        raise ValueError(f"k (liczba wariantów rundy) musi być ≥ 0, jest {k}")
    n_reg, n_au4 = n_program(rows), n_warianty(rows)
    k0 = sum(1 for r in _odczyty(rows, None) if int(r["wariantow"]) == 0)
    dk = max(k, 1)
    out = [
        (
            f"Rejestr odczytów historii: {len(rows)} wierszy (rund); "
            f"odczyty programu (wiersze liczone do N): {len(_odczyty(rows, None))}"
        ),
        f"  N metodą AU4 (Σ wariantów):                               {n_au4}",
        f"  N z {k0} odczytami 0-wariantowymi (Σ max(wariantów, 1)):     {n_reg}",
        "  Która liczba obowiązuje, zapisuje się w STATUS.md (skrypt jej nie wybiera).",
        (
            f"Planowana runda: k = {k} (liczba wariantów), zużyte próby max(k, 1) = {dk}; "
            f"progi dla N + {dk} = {n_au4 + dk} (metodą AU4) i {n_reg + dk} (z odczytami "
            "0-wariantowymi)."
        ),
    ]
    return out + threshold_rows(sorted({n_au4 + dk, n_reg + dk}), lata)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Próg t skorygowany o liczbę odczytów (DSR).")
    ap.add_argument("--n", type=int, nargs="*", help="progi dla podanych N zamiast rejestru")
    ap.add_argument("--lata", type=float, default=LATA_HISTORII, help="długość historii w latach")
    ap.add_argument("--rejestr", type=Path, default=REJESTR, help="ścieżka rejestru CSV")
    ap.add_argument("--k", type=int, default=1, help="liczba wariantów planowanej rundy (≥ 0)")
    a = ap.parse_args(argv)
    if a.k < 0:
        ap.error(f"--k musi być ≥ 0, jest {a.k}")
    if a.n:
        lines = threshold_rows(a.n, a.lata)
    else:
        rows = load_registry(a.rejestr)
        errs = registry_errors(rows)
        if errs:
            raise SystemExit("Rejestr niespójny:\n" + "\n".join(errs))
        lines = report(rows, a.lata, a.k)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
