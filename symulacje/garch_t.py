"""
garch_t.py — własny estymator GARCH(1,1) z innowacjami t Studenta (maksymalna wiarygodność) dla LV2.

Model: r_t = σ_t ε_t, ε_t ~ t_ν o wariancji 1 (tak samo jak w `generuj_panel`), średnia zwrotu = 0,
    σ²_t = ω + α r²_{t−1} + β σ²_{t−1},   σ²_0 = średnia r² z próby dopasowania (backcast).

Dlaczego własny, a nie `arch`: LV2 dopasowuje ten model ok. 1 100 razy na panel × tysiące paneli;
rekurencja wariancji idzie przez `scipy.signal.lfilter` i cała próbka dopasowania mieści się w jednym
wywołaniu (kilka ms). Poprawność sprawdza niezależnie pakiet `arch` (`tests/test_lv2.py`).
Dopasowanie liczymy na zmiennych bez skali (r² / backcast), więc wynik nie zależy od jednostek zwrotu.

Walk-forward (`prognozy_lv2.zbuduj_zrodla`): refit co `krok` dni na ROSNĄCYM oknie r_0 … r_{b−1}
(b = początek bloku), prognoza σ²_t dla t w bloku z filtra przepuszczonego przez całą historię
r_0 … r_{t−1} z parametrami tego bloku — w prognozie nie ma ani jednego zwrotu z dnia ≥ t.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np
from scipy.optimize import minimize
from scipy.signal import lfilter
from scipy.special import expit, gammaln, logit

P_MAX = 0.9999  # granica persystencji α + β
NU_MIN, NU_MAX = 2.5, 100.0
_GRANICE = (
    (-20.0, 3.0),  # log ω̃
    (-6.0, 9.2),  # logit(persystencja / P_MAX)
    (-8.0, 8.0),  # logit(α / (α + β))
    (float(np.log(NU_MIN - 2.0)), float(np.log(NU_MAX - 2.0))),  # log(ν − 2)
)
_STARTY_ZIMNE = ((0.05, 0.90, 8.0), (0.10, 0.85, 5.0), (0.15, 0.75, 4.0))  # (α, β, ν)


class DopasowanieGarchT(NamedTuple):
    omega: float
    alpha: float
    beta: float
    nu: float
    backcast: float  # σ²_0 w jednostkach r²
    nll: float  # średnia ujemna log-wiarygodność na obserwację (jednostki bez skali)
    zbiezny: bool
    brzeg: bool  # któryś parametr przy granicy dopuszczalnego zakresu


def _parametry(theta: np.ndarray) -> tuple[float, float, float, float]:
    """(ω̃, α, β, ν) z parametrów nieograniczonych θ."""
    pers = P_MAX * float(expit(theta[1]))
    udzial = float(expit(theta[2]))
    return (
        float(np.exp(theta[0])),
        pers * udzial,
        pers * (1.0 - udzial),
        2.0 + float(np.exp(theta[3])),
    )


def _theta(omega: float, alpha: float, beta: float, nu: float) -> np.ndarray:
    """Odwrotność `_parametry`, obcięta do granic (start dla optymalizatora)."""
    pers = min(max(alpha + beta, 1e-6), P_MAX * 0.99999)
    udzial = min(max(alpha / max(alpha + beta, 1e-12), 1e-6), 1.0 - 1e-6)
    th = np.array(
        [np.log(max(omega, 1e-12)), logit(pers / P_MAX), logit(udzial), np.log(max(nu, 2.01) - 2.0)]
    )
    return np.clip(th, [g[0] for g in _GRANICE], [g[1] for g in _GRANICE])


def filtr_sigma2(
    x2: np.ndarray, omega: float, alpha: float, beta: float, s2_0: float
) -> np.ndarray:
    """σ²_0 … σ²_n (n + 1 liczb) z kwadratów zwrotów x2 (n liczb); σ²_n to prognoza na dzień n."""
    x2 = np.asarray(x2, dtype=float)
    y, _ = lfilter([1.0], [1.0, -beta], omega + alpha * x2, zi=[beta * s2_0])
    return np.concatenate([[s2_0], y])


def loglik_t(x2: np.ndarray, s2: np.ndarray, nu: float) -> float:
    """Średnia log-wiarygodność na obserwację: r_t | σ²_t ~ znormalizowane t_ν; s2 ma długość len(x2)."""
    stala = gammaln(0.5 * (nu + 1.0)) - gammaln(0.5 * nu) - 0.5 * np.log(np.pi * (nu - 2.0))
    wnetrze = -0.5 * np.log(s2) - 0.5 * (nu + 1.0) * np.log1p(x2 / (s2 * (nu - 2.0)))
    return float(stala + wnetrze.mean())


def _nll(theta: np.ndarray, x2: np.ndarray) -> float:
    omega, alpha, beta, nu = _parametry(theta)
    s2 = filtr_sigma2(x2[:-1], omega, alpha, beta, 1.0)  # σ²_0 … σ²_{n−1}
    wartosc = -loglik_t(x2, s2, nu)
    return wartosc if np.isfinite(wartosc) else 1e10


def _jedno(theta0: np.ndarray, x2: np.ndarray):
    return minimize(
        _nll,
        theta0,
        args=(x2,),
        method="L-BFGS-B",
        bounds=_GRANICE,
        options={"maxiter": 300, "ftol": 1e-12, "gtol": 1e-7},
    )


def _przy_granicy(theta: np.ndarray) -> bool:
    return any(abs(t - g[0]) < 1e-3 or abs(t - g[1]) < 1e-3 for t, g in zip(theta, _GRANICE))


def dopasuj_garch_t(r, start: DopasowanieGarchT | None = None) -> DopasowanieGarchT:
    """Maksymalna wiarygodność GARCH(1,1)-t na zwrotach r (≥ 100 obserwacji, średnia 0).

    `start` — poprzednie dopasowanie (ciepły start). Gdy ciepły start nie zbiegnie albo skończy przy
    granicy, próbujemy trzech startów zimnych i bierzemy najlepszy wynik. Wszystko deterministyczne.
    """
    r = np.asarray(r, dtype=float)
    if r.ndim != 1 or len(r) < 100 or not np.isfinite(r).all():
        raise ValueError("r: wektor ≥ 100 skończonych zwrotów")
    backcast = float(np.mean(r * r))
    if backcast <= 0:
        raise ValueError("zwroty tożsamościowo zerowe")
    x2 = r * r / backcast
    wyniki = []
    if start is not None:
        om, al, be, nu = start.omega / backcast, start.alpha, start.beta, start.nu
        wyniki.append(_jedno(_theta(om, al, be, nu), x2))
    if not wyniki or not wyniki[0].success or _przy_granicy(wyniki[0].x):
        for al, be, nu in _STARTY_ZIMNE:
            wyniki.append(_jedno(_theta(1.0 - al - be, al, be, nu), x2))
    najlepszy = min(wyniki, key=lambda w: w.fun)
    om, al, be, nu = _parametry(najlepszy.x)
    return DopasowanieGarchT(
        omega=om * backcast,
        alpha=al,
        beta=be,
        nu=nu,
        backcast=backcast,
        nll=float(najlepszy.fun),
        zbiezny=bool(najlepszy.success),
        brzeg=_przy_granicy(najlepszy.x),
    )
