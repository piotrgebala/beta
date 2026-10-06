"""
nogi.py — stałe nóg dziennika alpha do reportera F3 (KOPIA, nie import: alpha tylko do odczytu, zasada 23).

Źródło: `alpha/backtest/odczyt_dziennika.py::LEGS` i `alpha/dziennik/README.md` → „Zmiana kryteriów odczytu”
(decyzja użytkownika 2026-09-27). μ, σ roczne arytmetyczne (średnia dzienna × 365, σ dzienna × √365).
Zgodność z alpha pilnuje `tests/test_dowody.py` (gdy alpha jest obok).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

DNI_W_ROKU = 365
Z_ADR09 = 2.31  # jeden próg na 3 odczytach (łącznie 2,5 % jednostronnie)
DNI_ODCZYTOW = (92, 182, 365)
DATY_ODCZYTOW = (date(2026, 12, 24), date(2027, 3, 24), date(2027, 9, 23))


@dataclass(frozen=True)
class Noga:
    name: str
    opis: str
    plik: str
    kolumna: str
    mu: float  # zakładana średnia roczna
    sigma: float  # zakładana zmienność roczna

    @property
    def mu_d(self) -> float:
        return self.mu / DNI_W_ROKU

    @property
    def sigma_d(self) -> float:
        return self.sigma / DNI_W_ROKU**0.5


NOGI = (
    Noga("TS1", "trend tygodniowy, likwidacja 2×", "wyniki.csv", "r_trend", 0.1069, 0.1812),
    Noga(
        "CP1", "premia Coinbase na BTC, likwidacja 3×", "wyniki.csv", "r_coinbase", 0.3104, 0.3511
    ),
    Noga("R1", "portfel R1 (trend + premia)", "wyniki.csv", "r_port", 0.1817, 0.2166),
    Noga("X1", "momentum przekrojowe, średnia 7 faz", "x1_wyniki.csv", "r_x1", 0.0949, 0.3626),
)
