"""
ryzyko_pozycji.py — wielkość pozycji, dystans do likwidacji i limit ES (F4, wersja minimalna, zero I/O).

To kalkulator, nie ocena: nie mówi, czy prognoza σ jest dobra (to pytanie rundy VaR/ES, licznik
„ryzyko 2021+”), tylko zamienia daną σ na dźwignię i na odległość od likwidacji. Lepsza σ nie tworzy
przewagi — skaluje tę, która jest (`docs/PRD.md` F2, „Zastosowanie”).

KONWENCJA: σ dzienna to odchylenie standardowe dziennego log-zwrotu; ES i VaR jako dodatnia strata
(ułamek ekspozycji); dźwignia = ekspozycja / depozyt; `mmr` = stawka depozytu utrzymania (ułamek).
Zasada 5 z alpha: sufit dźwigni wygrywa z każdym sizingiem — wynik zawsze przez jawne `min()`.

PRZYBLIŻENIA (zapisane, nie ukryte):
    * Cena likwidacji pozycji izolowanej: long P0·(1 − 1/L + mmr), short P0·(1 + 1/L − mmr). Bez opłat,
      funduszu i stopni mmr giełdy — to rząd wielkości dystansu, nie cena z giełdy.
    * Prawdopodobieństwo dotknięcia progu w ciągu h dni = 2 × P(zwrot h-dniowy poza progiem) (zasada
      odbicia, zero dryfu). Zwrot h-dniowy przyjmujemy jako t_ν o wariancji σ²h (bez grubszych ogonów
      po sumowaniu). To górne przybliżenie przy stałej σ; nie uwzględnia skoków σ ani cen śróddziennych.
    * Limit ES portfela: suma |w_i|·ES_i, czyli zero dywersyfikacji (ogony krypto są wspólne, R12).
"""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import t as student_t

from miara.var_es import var_es_t

DNI_W_ROKU = 365


def _dodatnia(x: float, nazwa: str) -> float:
    x = float(x)
    if not (math.isfinite(x) and x > 0):
        raise ValueError(f"{nazwa}: liczba skończona > 0, jest {x!r}")
    return x


def dzwignia_celu(
    sigma_dzien: float, cel_roczny: float, sufit: float, dni_w_roku: int = DNI_W_ROKU
) -> float:
    """Dźwignia, przy której zmienność pozycji = `cel_roczny`: min(cel / (σ√dni), sufit)."""
    s = _dodatnia(sigma_dzien, "sigma_dzien")
    cel = _dodatnia(cel_roczny, "cel_roczny")
    sufit = _dodatnia(sufit, "sufit")
    return min(cel / (s * math.sqrt(dni_w_roku)), sufit)


def dzwignia_konc(
    sigma_dzien: float,
    cel_roczny: float,
    sufit: float,
    es_dzienny: float | None = None,
    limit_es: float | None = None,
) -> float:
    """min(dźwignia z celu zmienności, sufit, limit_es / ES na jednostkę ekspozycji)."""
    d = dzwignia_celu(sigma_dzien, cel_roczny, sufit)
    if (es_dzienny is None) != (limit_es is None):
        raise ValueError("es_dzienny i limit_es podaje się razem albo wcale")
    if es_dzienny is not None:
        d = min(d, _dodatnia(limit_es, "limit_es") / _dodatnia(es_dzienny, "es_dzienny"))
    return d


def ruch_do_likwidacji(dzwignia: float, mmr: float, strona: str = "long") -> float:
    """Log-zwrot od ceny wejścia do ceny likwidacji: ujemny dla long, dodatni dla short."""
    d = _dodatnia(dzwignia, "dzwignia")
    if not (math.isfinite(mmr) and 0 <= mmr < 1):
        raise ValueError(f"mmr: ułamek w [0, 1), jest {mmr!r}")
    margines = 1.0 / d - mmr
    if margines <= 0:
        raise ValueError("depozyt nie pokrywa mmr: pozycja likwidowana od razu")
    if strona == "long":
        return -math.inf if margines >= 1.0 else math.log1p(-margines)  # 1× bez mmr: tylko cena 0
    if strona == "short":
        return math.log1p(margines)
    raise ValueError(f"strona: long albo short, jest {strona!r}")


def dystans_w_sigmach(
    dzwignia: float, mmr: float, sigma_dzien: float, strona: str = "long", dni: int = 1
) -> float:
    """|ruch do likwidacji| w jednostkach σ√dni (ile „typowych” ruchów dzieli cenę od likwidacji)."""
    s = _dodatnia(sigma_dzien, "sigma_dzien")
    if dni < 1:
        raise ValueError("dni ≥ 1")
    return abs(ruch_do_likwidacji(dzwignia, mmr, strona)) / (s * math.sqrt(dni))


def p_likwidacji(
    dzwignia: float,
    mmr: float,
    sigma_dzien: float,
    nu: float,
    strona: str = "long",
    dni: int = 1,
    dotkniecie: bool = True,
) -> float:
    """
    Przybliżone P(likwidacja w ciągu `dni` dni) przy stałej σ i t_ν (wariancja σ²·dni).
    `dotkniecie=True`: 2 × P(zwrot na koniec okresu poza progiem), obcięte do 1 (górne przybliżenie).
    """
    nu = _dodatnia(nu, "nu")
    if nu <= 2:
        raise ValueError("nu > 2 (skończona wariancja)")
    z = dystans_w_sigmach(dzwignia, mmr, sigma_dzien, strona, dni)
    ogon = float(student_t.sf(z * math.sqrt(nu / (nu - 2.0)), nu))
    return min(1.0, 2.0 * ogon) if dotkniecie else ogon


def es_straty(sigma_dzien: float, p: float, nu: float) -> tuple[float, float]:
    """(VaR, ES) dziennej straty na jednostkę ekspozycji, t_ν o wariancji σ²; dodatnie liczby."""
    q, es = var_es_t(_dodatnia(sigma_dzien, "sigma_dzien"), p, nu)
    return -q, -es


def skala_limitu_es(wagi, es, limit: float) -> tuple[np.ndarray, float]:
    """
    Wagi przeskalowane tak, by Σ|w_i|·ES_i ≤ `limit` (bez dywersyfikacji); nigdy nie zwiększa wag.
    Zwraca (nowe wagi, współczynnik skali ∈ (0, 1]). `es` — dodatnie straty na jednostkę ekspozycji.
    """
    w = np.asarray(wagi, dtype=float)
    e = np.asarray(es, dtype=float)
    limit = _dodatnia(limit, "limit")
    if w.ndim != 1 or w.shape != e.shape or len(w) == 0:
        raise ValueError("wagi i es: wektory 1-D tej samej niezerowej długości")
    if not (np.isfinite(w).all() and np.isfinite(e).all() and (e >= 0).all()):
        raise ValueError("wagi skończone, es skończone i ≥ 0")
    ryzyko = float(np.sum(np.abs(w) * e))
    skala = 1.0 if ryzyko <= limit else limit / ryzyko
    return w * skala, skala
