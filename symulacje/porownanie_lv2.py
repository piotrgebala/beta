"""
porownanie_lv2.py — porównawczy test prognoz VaR/ES dla LV2: straty, ich wartości oczekiwane (wzory
zamknięte) i test Diebolda–Mariano na dziennych średnich po monetach (R12: jednostką jest dzień).

Konwencja jak w `miara/var_es.py`: zwroty, nie straty; q (VaR) i es ujemne; trafienie = r < q.

Straty (obie PRAWIDŁOWE — w oczekiwaniu najmniejsze dla prawdziwych (VaR, ES)):
    FZ0   Fissler–Ziegel w wersji Pattona–Ziegel–Chen (2019), dolny ogon (v, e < 0):
          S = −1/(p e) · 1{r ≤ v}(v − r) + v/e + log(−e) − 1.   Ocenia RAZEM VaR i ES. Różnica FZ0 dwóch
          prognoz jest niezmiennicza względem wspólnej skali zwrotu i prognoz (człon log(−e) skraca się).
    PINB  strata kwantylowa (pinball) samego VaR, (p − 1{r < v})(r − v), dzielona przez WSPÓLNĄ wagę σ̂
          (w LV2: EWMA 0,94 monety; znana w t − 1, więc strata nadal prawidłowa; bez wagi dominują dni
          wysokiej zmienności). Waga jest wspólna dla wszystkich par, więc różnica par = różnica średnich.

Test porównawczy: Δ_t = średnia po monetach z (strata_A − strata_B) w dniu t, t = Diebold–Mariano z HAC
(Newey–West, `miara.dm`). Dodatnie t = prognoza B lepsza (mniejsza strata). Bez poprawki
Harveya–Leyborne'a–Newbolda na małą próbę: przy n ≥ 1 600 jest ona pomijalna (opóźnienie Newey–West 7).

Para „dokładnie zerowa” (rozmiar testu): prognozy wyroczni pomnożone przez c_A i c_B tak, że OCZEKIWANE
straty są równe — wtedy H0 „równe oczekiwane straty” jest prawdziwa, choć żadna prognoza nie jest
prawdziwa. Dla innowacji t_ν (σ wyroczni, wspólna dla wszystkich dni) wartość oczekiwana ma wzór zamknięty.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import brentq
from scipy.stats import t as student_t

from miara.dm import hac_variance
from miara.var_es import var_es_t

STRATY = ("fz0", "pinb")


def fz0(v, e, r, p: float) -> np.ndarray:
    """Strata FZ0 (Patton–Ziegel–Chen 2019) dla dolnego ogona: v, e < 0, e ≤ v; r zwrot."""
    v, e, r = (np.asarray(x, dtype=float) for x in (v, e, r))
    if not (np.all(e < 0) and np.all(v < 0)):
        raise ValueError("fz0: VaR i ES muszą być ujemne (zwroty, nie straty)")
    return -(np.where(r <= v, v - r, 0.0)) / (p * e) + v / e + np.log(-e) - 1.0


def pinball(v, r, p: float) -> np.ndarray:
    """Strata kwantylowa poziomu p dla kwantyla v: (p − 1{r < v})(r − v) ≥ 0."""
    v, r = np.asarray(v, dtype=float), np.asarray(r, dtype=float)
    return (p - (r < v)) * (r - v)


def straty_dzienne(r, q, es, p: float, waga) -> dict[str, np.ndarray]:
    """Dzienne średnie po monetach strat FZ0 i PINB (n × K → n); PINB dzielona przez `waga` (n × K).

    Waga = σ̂ znane w t − 1 (w LV2 wspólna dla wszystkich par: EWMA 0,94); dodatnia waga mierzalna
    względem F_{t−1} zachowuje prawidłowość straty kwantylowej. Różnica dwóch prognoz po monetach
    to różnica ich dziennych średnich, więc wystarczy jeden wektor na prognozę.
    """
    waga = np.asarray(waga, dtype=float)
    if not np.all(waga > 0):
        raise ValueError("waga musi być dodatnia")
    return {
        "fz0": fz0(q, es, r, p).mean(axis=1),
        "pinb": (pinball(q, r, p) / waga).mean(axis=1),
    }


def dm_wektor(delta) -> dict:
    """Test DM dla dziennej różnicy strat A − B (wektor n): {t, srednia, se}; t > 0 ⇒ B lepsza."""
    d = np.asarray(delta, dtype=float)
    s = float(hac_variance(d))
    se = math.sqrt(s / len(d)) if s > 0 else float("nan")
    return {
        "t": float(d.mean() / se) if s > 0 else float("nan"),
        "srednia": float(d.mean()),
        "se": se,
    }


# --- wartości oczekiwane pod prawdziwym t_ν (σ wyroczni, mnożnik prognozy c) --------------------------


def _calki_ogona(a: float, nu: float) -> tuple[float, float]:
    """(F(a), J(a)) dla innowacji ε o wariancji 1: F = P(ε ≤ a), J = E[ε 1{ε ≤ a}]."""
    s = math.sqrt((nu - 2.0) / nu)
    u = a / s
    return float(student_t.cdf(u, nu)), -s * float(student_t.pdf(u, nu)) * (nu + u * u) / (nu - 1.0)


def oczekiwana_strata(c: float, p: float, nu: float, strata: str) -> float:
    """E[strata] prognozy c·(VaR*, ES*) (σ wyroczni) przy innowacjach t_ν o wariancji 1.

    fz0: dla σ = 1 (poziom log σ znika w różnicach); pinb: dla σ = 1, waga 1/σ̂_A pominięta (stała).
    """
    if c <= 0:
        raise ValueError("c > 0")
    v0, e0 = (float(x) for x in var_es_t(1.0, p, nu))
    a, ee = c * v0, c * e0
    f, j = _calki_ogona(a, nu)
    i_a = a * f - j  # E[1{ε ≤ a}(a − ε)] ≥ 0
    if strata == "fz0":
        return -i_a / (p * ee) + a / ee + math.log(-ee) - 1.0
    if strata == "pinb":
        return -p * a + i_a
    raise ValueError(f"strata: {STRATY}, jest {strata!r}")


def mnoznik_zerowy(c_a: float, p: float, nu: float, strata: str) -> float:
    """c_B > 1 z E[strata(c_B)] = E[strata(c_A)] dla c_A < 1 (druga gałąź paraboli straty)."""
    cel = oczekiwana_strata(c_a, p, nu, strata)
    return float(brentq(lambda c: oczekiwana_strata(c, p, nu, strata) - cel, 1.0, 5.0, xtol=1e-12))
