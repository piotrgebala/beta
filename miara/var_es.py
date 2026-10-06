"""
var_es.py — przyrząd do oceny prognoz VaR i ES (testy wsteczne): pokrycie Kupca, niezależność
i pokrycie warunkowe Christoffersena, test ogona Acerbiego–Szekelya (Z2). Cel G2 i reguła STOP F2-1
(`docs/PRD.md` FR-32). Kontrole R8: `symulacje/run_kv1.py`.

KONWENCJA (zwroty, nie straty; tablice 1-D numpy albo pandas Series, po pozycji, zero I/O):
    r_t   zwrot dzienny;
    q_t   prognozowany p-kwantyl zwrotu, zwykle ujemny, znany w t − 1 (VaR = −q_t);
    es_t  prognozowane E[r | r < q_t], es_t ≤ q_t < 0;
    I_t   trafienie 1{r_t < q_t} (nierówność ostra: r_t = q_t nie jest trafieniem).
NaN, ±inf i różne długości wejść = ValueError. Brak jest świadomy: ciche pominięcie NaN psuje
testy niezależności (zmienia sąsiedztwo dni) i pokrycia (zmienia n).

Testy:
    Kupiec (1995), LR_uc ~ χ²(1): H0: P(I_t = 1) = p.
    Christoffersen (1998), LR_ind ~ χ²(1): H0: trafienia tworzą łańcuch Markowa 1. rzędu
        z π01 = π11 (po trafieniu nie jest ani częściej, ani rzadziej trafienie).
    Christoffersen, LR_cc = LR_uc + LR_ind ~ χ²(2): H0: π01 = π11 = p (pokrycie i niezależność).
        UWAGA: LR_uc w LR_cc liczone jest na I_2 … I_n (n − 1 trafień), nie na całych n, więc
        LR_cc ≠ kupiec_uc(h)["LR"] + christoffersen_ind(h)["LR"] (tak bywa w podręcznikach
        i bibliotekach); nasze LR_cc to dokładny iloraz wiarygodności łańcucha Markowa.
    Acerbi–Szekely (2014), test 2: Z2 = 1 − Σ_t r_t I_t / (n p es_t). Pod H0 E[Z2] = 0.
        ZNAK: Z2 < 0 = prognoza NIEDOSZACOWAŁA ogon (zwroty po przekroczeniu są głębsze niż es_t,
        iloraz r_t / es_t > 1); Z2 > 0 = ogon przeszacowany. Odrzucamy dla małego Z2 (test lewy).
        Wzór A–S to Σ X_t I_t / (T α ES_t) + 1 dla ES > 0 (stratowego); w konwencji zwrotów
        es_t < 0, więc znak ilorazu odwracamy i wynik jest ten sam co u autorów.

Ograniczenie asymptotyki χ²: LR_ind (i LR_cc) potrzebuje wielu przejść 1→1, czyli n p² ≳ 20.
Przy mniejszej liczbie rozmiar testu jest nieregularny (dla p = 1 % i n = 5 000–50 000 wychodzi od
1,8 % do 8,8 % zamiast 5 %, bo rozkład n11 jest dyskretny). Przy 1 % i ~2 000 dniach na monetę
(21 trafień) test niezależności nie ma więc ani rozmiaru, ani mocy — trzeba wtedy p-wartości
z symulacji. To właściwość przybliżenia, nie błąd kodu (kontrola: `symulacje/run_kv1.py`).

Przypadki zdegenerowane Christoffersena. Test niezależności porównuje π01 i π11, więc potrzebuje
obu wierszy tabeli przejść 2×2 (stan „wczoraj” 0 i 1) oraz obu kolumn (stan „dziś” 0 i 1). Gdy
któryś brzeg tabeli ma sumę 0 (brak trafień, same trafienia, jedyne trafienie na końcu, n = 1),
wiarygodności obu modeli są równe, więc formalnie LR = 0 — ale to brak informacji, nie dowód
niezależności. Dlatego `christoffersen_ind` zwraca wtedy LR = nan, p = nan i niezdefiniowany = True;
kontrole liczą to jako „brak odrzucenia”, ale raportują liczbę takich serii. Zwykły przypadek
n11 = 0 przy niezerowych brzegach NIE jest zdegenerowany (0·ln 0 = 0, LR liczy się normalnie).
W LR_cc część niezależności wchodzi wtedy jako 0: test łączny ma moc z samego pokrycia, więc
zostaje określony (niezdefiniowany tylko dla n < 2).

p-wartość Z2 pochodzi z symulacji pod H0 (nie ma wzoru). Dla prognoz typu położenie–skala
(q_t = σ_t a, es_t = σ_t b, r_t = σ_t ε_t) iloraz r_t I_t / es_t = ε_t 1{ε_t < a} / b nie zależy
od σ_t, więc rozkład zerowy Z2 wystarczy zasymulować RAZ dla (n, p, rodziny), a nie dla każdej
ścieżki: `as_z2_h0_polozenie_skala`. Wersja ogólna `as_z2_h0` przyjmuje dowolny sampler.
Uwaga: ten test (jak A–S test 2) łączy błąd VaR i ES — przy p = 5 % normalne q/es kontra
prawdziwe t5 dają E[Z2] ≈ +0,015, bo rzadsze trafienia i głębszy ogon znoszą się; Z2 nie wykrywa
tego błędu (przy p = 1 % E[Z2] ≈ −0,75). Kupiec wykrywa go przez częstość trafień.

DWA API rozkładu zerowego Z2 NIE są równoważne dla każdej prognozy. Równoważne są tylko wtedy, gdy
raportowane (q, es) = σ_t (a, b) dla (a, b) rodziny (`czy_polozenie_skala`). Różnią się, gdy es nie
jest ES rodziny (np. es za niskie przy dobrym q):
    `as_z2_h0_polozenie_skala` liczy rozkład zerowy z (a, b) rodziny (wzory zamknięte), a Z2 danych
        z RAPORTOWANYM es — więc wykrywa es niespójne z rodziną (kontrola POZYTYWNA 3 w KV1);
    `as_z2_h0` (ogólny) liczy rozkład zerowy z RAPORTOWANYM es i dowolnym samplerem; sampler
        i (q, es) muszą być jednym modelem (es = ES rozkładu samplera), bo przy niespójnym es dane
        z samplera mają ten sam błąd i rozkład zerowy przesuwa się razem z nim (moc znika).
Ziarno (R19): jawne, `int` albo `SeedSequence`; None, bool i Generator są odrzucane (TypeError).
"""

from __future__ import annotations

import math
import numbers
from collections.abc import Callable

import numpy as np
from scipy.special import xlog1py, xlogy
from scipy.stats import chi2, norm
from scipy.stats import t as student_t

Ziarno = int | np.random.SeedSequence
Sampler = Callable[[np.random.Generator, int], np.ndarray]

_MAX_KOMOREK = 2_000_000  # ile liczb naraz w symulacji Z2 (limit pamięci)


# --- walidacja wejść ---------------------------------------------------------------------------


def _wektor(x, nazwa: str) -> np.ndarray:
    """Tablica float 1-D, niepusta, bez NaN i ±inf."""
    a = np.asarray(x, dtype=float)
    if a.ndim != 1 or a.size == 0:
        raise ValueError(f"{nazwa}: oczekiwano niepustej tablicy 1-D")
    if not np.isfinite(a).all():
        raise ValueError(f"{nazwa}: NaN albo nieskończoność w danych")
    return a


def _hity(x, nazwa: str = "trafienia") -> np.ndarray:
    """Tablica bool 1-D z trafień (bool albo 0/1); wszystko inne = ValueError."""
    a = np.asarray(x)
    if a.ndim != 1 or a.size == 0:
        raise ValueError(f"{nazwa}: oczekiwano niepustej tablicy 1-D")
    if a.dtype == bool:
        return a
    if a.dtype.kind not in "iuf":  # napisy "0"/"1" i obiekty odpadają, nie są cicho rzutowane
        raise ValueError(f"{nazwa}: wartości muszą być bool albo 0/1")
    f = a.astype(float)
    if np.isnan(f).any():
        raise ValueError(f"{nazwa}: NaN w danych")
    if not np.isin(f, (0.0, 1.0)).all():
        raise ValueError(f"{nazwa}: wartości muszą być bool albo 0/1")
    return f.astype(bool)


def _poziom(p: float) -> float:
    if not (isinstance(p, int | float | np.floating) and 0.0 < p < 1.0):
        raise ValueError(f"p musi być w (0, 1), jest {p!r}")
    return float(p)


def _zgodne(**tablice: np.ndarray) -> None:
    dl = {k: len(v) for k, v in tablice.items()}
    if len(set(dl.values())) != 1:
        raise ValueError(f"różne długości wejść: {dl}")


def _calkowita(x, nazwa: str) -> int:
    """Liczba całkowita ≥ 1 (bez cichego obcinania 2,7 do 2 i bez bool)."""
    if isinstance(x, bool) or not isinstance(x, numbers.Integral) or x < 1:
        raise ValueError(f"{nazwa} musi być liczbą całkowitą ≥ 1, jest {x!r}")
    return int(x)


def _ziarno(seed) -> Ziarno:
    """R19: ziarno jawne — int (nie bool) albo SeedSequence; None i Generator = TypeError."""
    if isinstance(seed, bool) or not isinstance(seed, numbers.Integral | np.random.SeedSequence):
        raise TypeError(f"seed musi być int albo SeedSequence (jawne ziarno, R19), jest {seed!r}")
    return seed if isinstance(seed, np.random.SeedSequence) else int(seed)


def _stopnie_swobody(nu) -> float:
    """ν skończone i > 2 (skończona wariancja); None, NaN i ∞ = ValueError."""
    if nu is None or not (math.isfinite(nu) and nu > 2):
        raise ValueError(f"nu musi być skończone i > 2 (skończona wariancja), jest {nu!r}")
    return float(nu)


def _lr(x: float) -> float:
    """LR = 2·(różnica log-wiarygodności) ≥ 0; ujemna wartość poza błędem zaokrągleń = błąd wzoru."""
    if x < -1e-9:
        raise ArithmeticError(f"ujemny iloraz wiarygodności {x}: błąd wzoru")
    return max(x, 0.0)


# --- trafienia i testy pokrycia / niezależności -----------------------------------------------


def _trafienie(r, q):
    """Jedyna definicja trafienia (też dla Z2): r < q, nierówność ostra (r = q to nie trafienie)."""
    return r < q


def trafienia(r, q) -> np.ndarray:
    """Trafienia I_t = 1{r_t < q_t} jako tablica bool (nierówność ostra)."""
    r, q = _wektor(r, "r"), _wektor(q, "q")
    _zgodne(r=r, q=q)
    return _trafienie(r, q)


def _ll_bernoulli(x, n, p):
    """Log-wiarygodność x trafień w n próbach przy prawdopodobieństwie p (0·ln 0 = 0)."""
    return xlogy(x, p) + xlog1py(n - x, -p)


def kupiec_uc(trafienia, p: float) -> dict:
    """
    Test pokrycia bezwarunkowego Kupca (LR_uc, χ²(1)); zależy tylko od liczby trafień x i n.

    Returns:
        {x, n, odsetek = x/n, LR ≥ 0, p_wartosc (prawy ogon χ²(1))}. Dla x = 0 i x = n wiarygodność
        przy π̂ ∈ {0, 1} równa się 1 (0·ln 0 = 0), więc LR jest skończone.
    """
    h = _hity(trafienia)
    p = _poziom(p)
    n, x = len(h), int(h.sum())
    pi = x / n
    lr = _lr(2.0 * float(_ll_bernoulli(x, n, pi) - _ll_bernoulli(x, n, p)))
    return {"x": x, "n": n, "odsetek": pi, "LR": lr, "p_wartosc": float(chi2.sf(lr, 1))}


def _przejscia(h: np.ndarray) -> tuple[int, int, int, int]:
    """Liczby przejść (wczoraj → dziś): n00, n01, n10, n11 (n − 1 przejść)."""
    a, b = h[:-1], h[1:]
    return (
        int((~a & ~b).sum()),
        int((~a & b).sum()),
        int((a & ~b).sum()),
        int((a & b).sum()),
    )


def _ll_markow(n00: int, n01: int, n10: int, n11: int) -> float:
    """Maksymalna log-wiarygodność łańcucha 1. rzędu (π01, π11 dowolne), warunkowo na 1. dniu."""
    pi01 = n01 / (n00 + n01) if n00 + n01 > 0 else 0.0
    pi11 = n11 / (n10 + n11) if n10 + n11 > 0 else 0.0
    return float(_ll_bernoulli(n01, n00 + n01, pi01) + _ll_bernoulli(n11, n10 + n11, pi11))


def _niezdefiniowany(n00: int, n01: int, n10: int, n11: int) -> bool:
    """Tabela 2×2 z zerowym brzegiem (wiersz albo kolumna): test niezależności bez informacji."""
    return min(n00 + n01, n10 + n11, n00 + n10, n01 + n11) == 0


def christoffersen_ind(trafienia) -> dict:
    """
    Test niezależności trafień Christoffersena (LR_ind, χ²(1)), łańcuch Markowa 1. rzędu.

    Wiarygodność warunkowa na pierwszym dniu (n − 1 przejść). H1: π01 ≠ π11 szacowane z częstości,
    H0: π01 = π11 = π = (n01 + n11) / (n − 1).

    Returns:
        {n00, n01, n10, n11, LR, p_wartosc, niezdefiniowany}. Przy tabeli z zerowym brzegiem
        (patrz docstring modułu) LR = p_wartosc = nan i niezdefiniowany = True.
    """
    h = _hity(trafienia)
    n00, n01, n10, n11 = _przejscia(h)
    out = {"n00": n00, "n01": n01, "n10": n10, "n11": n11}
    if _niezdefiniowany(n00, n01, n10, n11):
        return out | {"LR": math.nan, "p_wartosc": math.nan, "niezdefiniowany": True}
    pi = (n01 + n11) / (n00 + n01 + n10 + n11)
    ll0 = _ll_bernoulli(n01 + n11, n00 + n01 + n10 + n11, pi)
    lr = _lr(2.0 * (_ll_markow(n00, n01, n10, n11) - float(ll0)))
    return out | {"LR": lr, "p_wartosc": float(chi2.sf(lr, 1)), "niezdefiniowany": False}


def christoffersen_cc(trafienia, p: float) -> dict:
    """
    Test pokrycia warunkowego Christoffersena: LR_cc = LR_uc + LR_ind ~ χ²(2).

    LR_uc jest liczone na próbie I_2 … I_n (n − 1 trafień — tej samej, na której stoi
    wiarygodność łańcucha, warunkowa na pierwszym dniu), nie na całych n; dzięki temu
    LR_cc = LR_uc + LR_ind jest dokładnym ilorazem wiarygodności (H0: π01 = π11 = p). Gdy część
    niezależności jest zdegenerowana (patrz moduł), wchodzi jako 0 i zostaje flaga
    `ind_niezdefiniowany`.

    Returns:
        {n, n_uc = n − 1, LR_uc, LR_ind, LR, p_wartosc, ind_niezdefiniowany, niezdefiniowany};
        dla n < 2 (brak przejść) LR = nan i niezdefiniowany = True.
    """
    h = _hity(trafienia)
    p = _poziom(p)
    n = len(h)
    if n < 2:
        return {
            "n": n,
            "n_uc": 0,
            "LR_uc": math.nan,
            "LR_ind": math.nan,
            "LR": math.nan,
            "p_wartosc": math.nan,
            "ind_niezdefiniowany": True,
            "niezdefiniowany": True,
        }
    n00, n01, n10, n11 = _przejscia(h)
    m, x = n00 + n01 + n10 + n11, n01 + n11
    pi = x / m
    ll_h0 = float(_ll_bernoulli(x, m, p))
    ll_pi = float(_ll_bernoulli(x, m, pi))
    ll_markow = _ll_markow(n00, n01, n10, n11)
    lr_uc = _lr(2.0 * (ll_pi - ll_h0))
    lr_ind = _lr(2.0 * (ll_markow - ll_pi))
    lr = _lr(2.0 * (ll_markow - ll_h0))
    return {
        "n": n,
        "n_uc": m,
        "LR_uc": lr_uc,
        "LR_ind": lr_ind,
        "LR": lr,
        "p_wartosc": float(chi2.sf(lr, 2)),
        "ind_niezdefiniowany": _niezdefiniowany(n00, n01, n10, n11),
        "niezdefiniowany": False,
    }


# --- zamknięte wzory na VaR i ES -----------------------------------------------------------------


def _sigma(sigma) -> np.ndarray:
    s = np.asarray(sigma, dtype=float)
    if not np.isfinite(s).all() or (s <= 0).any():
        raise ValueError("sigma musi być skończona i > 0")
    return s


def var_es_normal(sigma, p: float):
    """
    (q, es) rozkładu normalnego N(0, σ²): q = σ Φ⁻¹(p), es = −σ φ(Φ⁻¹(p)) / p. Średnia zwrotu = 0.
    `sigma` skalar albo tablica (σ_t). Oba wyniki ujemne, es < q.
    """
    p = _poziom(p)
    s = _sigma(sigma)
    z = norm.ppf(p)
    return s * z, -s * norm.pdf(z) / p


def var_es_t(sigma, p: float, nu: float):
    """
    (q, es) ZNORMALIZOWANEGO rozkładu t_ν (wariancja 1, jak w `generuj_panel`) razy σ.

    Innowacja ε = T_ν √((ν − 2)/ν), T_ν ~ t Studenta; r = σ ε ma wariancję σ². Dla T_ν:
    q_T = t_ν⁻¹(p), ES_T = −g_ν(q_T)/p · (ν + q_T²)/(ν − 1) (g_ν = gęstość). Wymaga ν > 2.
    """
    p = _poziom(p)
    nu = _stopnie_swobody(nu)
    s = _sigma(sigma) * math.sqrt((nu - 2.0) / nu)
    tq = float(student_t.ppf(p, nu))
    es_t = -float(student_t.pdf(tq, nu)) / p * (nu + tq * tq) / (nu - 1.0)
    return s * tq, s * es_t


def losuj_innowacje(
    rng: np.random.Generator, size, rodzina: str, nu: float | None = None
) -> np.ndarray:
    """Innowacje o wariancji 1: rodzina "normal" albo "t" (znormalizowane t_ν, wymaga `nu` > 2)."""
    if rodzina == "normal":
        return rng.standard_normal(size)
    if rodzina == "t":
        nu = _stopnie_swobody(nu)
        return rng.standard_t(nu, size) * math.sqrt((nu - 2.0) / nu)
    raise ValueError(f"nieznana rodzina: {rodzina!r} (normal albo t)")


def _kwantyl_es_std(p: float, rodzina: str, nu: float | None) -> tuple[float, float]:
    """(a, b) = (kwantyl, ES) innowacji o wariancji 1 — wzory zamknięte dla σ = 1."""
    if rodzina == "normal":
        q, es = var_es_normal(1.0, p)
    elif rodzina == "t":
        q, es = var_es_t(1.0, p, nu)
    else:
        raise ValueError(f"nieznana rodzina: {rodzina!r} (normal albo t)")
    return float(q), float(es)


# --- test ES Acerbiego–Szekelya ---------------------------------------------------------------


def _z2(r: np.ndarray, q: np.ndarray, es: np.ndarray, p: float) -> np.ndarray:
    """Z2 po ostatniej osi (r może być k × n, q i es długości n). Bez walidacji — dla symulacji."""
    n = r.shape[-1]
    hit = _trafienie(r, q)
    return 1.0 - (np.where(hit, r, 0.0) / es).sum(axis=-1) / (n * p)


def _prognoza_es(q, es) -> tuple[np.ndarray, np.ndarray]:
    """q i es jako wektory tej samej długości; es ujemne i ≤ q (konwencja zwrotów)."""
    q, es = _wektor(q, "q"), _wektor(es, "es")
    _zgodne(q=q, es=es)
    if (es >= 0).any():
        raise ValueError("es musi być ujemne (konwencja zwrotów: es_t ≤ q_t < 0)")
    if (es > q).any():
        raise ValueError("es musi być ≤ q (zamienione argumenty albo znak?)")
    return q, es


def _wejscie_as(r, q, es, p: float):
    r = _wektor(r, "r")
    q, es = _prognoza_es(q, es)
    _zgodne(r=r, q=q)
    return r, q, es, _poziom(p)


def as_z2(r, q, es, p: float) -> float:
    """
    Statystyka Z2 Acerbiego–Szekelya (2014, test 2): Z2 = 1 − Σ_t r_t I_t / (n p es_t).

    E[Z2] = 0 pod H0 (q_t = prawdziwy p-kwantyl, es_t = prawdziwy ES warunkowy). Z2 < 0 =
    niedoszacowany ogon (zwroty po przekroczeniu głębsze niż es_t); Z2 = 1 przy braku trafień.
    Niezmiennicze na pomnożenie (r, q, es) przez c > 0. Trafienie jak w `trafienia` (r < q).
    """
    r, q, es, p = _wejscie_as(r, q, es, p)
    return float(_z2(r, q, es, p))


def as_z2_pwartosc(z2: float, z2_h0) -> float:
    """
    Jednostronna p-wartość Monte Carlo (niedoszacowanie ogona): (1 + #{Z2* ≤ z2}) / (1 + B),
    gdzie Z2* to próbka rozkładu zerowego. Nigdy 0 (poprawka +1), więc nadaje się do reguł p < α.
    NaN i ±inf (w z2 albo w próbce) = ValueError — inaczej NaN dałoby najmniejszą możliwą p-wartość.
    """
    z2 = float(z2)
    if not math.isfinite(z2):
        raise ValueError("z2: NaN albo nieskończoność")
    z0 = _wektor(z2_h0, "z2_h0")
    return float((1 + np.count_nonzero(z0 <= z2)) / (1 + len(z0)))


def czy_polozenie_skala(q, es, p: float, rodzina: str, nu: float | None = None) -> bool:
    """
    Czy raportowane (q_t, es_t) = σ_t (a, b) dla (a, b) = (kwantyl, ES) rodziny i jakichś σ_t > 0.

    Tylko wtedy `as_z2_h0_polozenie_skala` i `as_z2_h0` (z samplerem σ_t ε_t) dają ten sam rozkład
    zerowy. Fałsz = prognoza spoza rodziny (np. es za niskie przy dobrym q): skrót liczy wtedy
    rozkład zerowy modelu rodziny, a ogólny z raportowanym es (patrz docstring modułu).
    """
    a, b = _kwantyl_es_std(_poziom(p), rodzina, nu)
    q, es = _wektor(q, "q"), _wektor(es, "es")
    _zgodne(q=q, es=es)
    sq, se = q / a, es / b
    return bool((sq > 0).all() and np.allclose(sq, se, rtol=1e-9, atol=0.0))


def as_z2_h0(q, es, p: float, los: Sampler, reps: int, *, seed: Ziarno) -> np.ndarray:
    """
    Próbka rozkładu zerowego Z2 dla DOWOLNEGO modelu predykcyjnego (wersja ogólna).

    Z2* jest liczone z RAPORTOWANYM `es`, więc `los` i (q, es) muszą być jednym modelem
    (es = ES rozkładu, z którego losuje `los`). Przy es niespójnym z `los` rozkład zerowy przesuwa
    się razem z błędem i test nie ma mocy wobec niego; taką prognozę (przy rodzinie położenie–
    skala) bada `as_z2_h0_polozenie_skala`, bo liczy rozkład zerowy z (a, b) rodziny.

    Args:
        q, es: prognozy modelu (długość n), te same co w teście właściwym.
        los: `los(rng, k) -> tablica k × n` — k ścieżek zwrotów losowanych Z ROZKŁADU PREDYKCYJNEGO
            modelu (czyli pod H0, że model jest prawdziwy), z dostarczonego generatora.
            NaN i ±inf w ścieżkach = ValueError.
        reps: liczba ścieżek B (całkowita ≥ 1).
        seed: jawne ziarno (R19) — int albo SeedSequence; brak domyślnej wartości, None = TypeError.

    Returns:
        tablica B wartości Z2* pod H0. Ścieżki liczone partiami (limit pamięci).
    """
    ziarno = _ziarno(seed)
    q, es = _prognoza_es(q, es)
    p = _poziom(p)
    n, reps = len(q), _calkowita(reps, "reps")
    rng = np.random.default_rng(ziarno)
    partia = max(1, _MAX_KOMOREK // n)
    out = []
    zrobione = 0
    while zrobione < reps:
        k = min(partia, reps - zrobione)
        x = np.asarray(los(rng, k), dtype=float)
        if x.shape != (k, n):
            raise ValueError(f"los zwrócił kształt {x.shape}, oczekiwano {(k, n)}")
        if not np.isfinite(x).all():
            raise ValueError("los zwrócił NaN albo nieskończoność")
        out.append(_z2(x, q, es, p))
        zrobione += k
    return np.concatenate(out)


def as_z2_pwartosc_ogolna(r, q, es, p: float, los: Sampler, reps: int, *, seed: Ziarno) -> dict:
    """Z2 i jego jednostronna p-wartość z symulacji pod H0 (`as_z2_h0`): {z2, p_wartosc, reps}."""
    z2 = as_z2(r, q, es, p)
    z0 = as_z2_h0(q, es, p, los, reps, seed=seed)
    return {"z2": z2, "p_wartosc": as_z2_pwartosc(z2, z0), "reps": len(z0)}


def as_z2_h0_polozenie_skala(
    n: int, p: float, rodzina: str, nu: float | None, reps: int, *, seed: Ziarno
) -> np.ndarray:
    """
    Rozkład zerowy Z2 dla prognoz położenie–skala (zero, σ_t) — jedna symulacja na (n, p, rodzina).

    Z2 = 1 − Σ ε_t 1{ε_t < a} / (n p b), ε_t iid o wariancji 1, (a, b) = (kwantyl, ES) innowacji;
    σ_t się skraca, więc ta próbka jest rozkładem zerowym Z2 dla KAŻDEJ ścieżki σ_t. Równoważna
    `as_z2_h0` z samplerem σ_t ε_t i q_t = σ_t a, es_t = σ_t b (test: `tests/test_var_es.py`) —
    TYLKO dla takich prognoz (`czy_polozenie_skala`). Dla es spoza rodziny (np. za niskie przy
    dobrym q) rozkład zerowy nadal pochodzi z (a, b) rodziny, a Z2 danych z raportowanym es:
    to właśnie wykrywa kontrola POZYTYWNA 3 w KV1.
    """
    n = _calkowita(n, "n")
    a, b = _kwantyl_es_std(_poziom(p), rodzina, nu)
    q, es = np.full(n, a), np.full(n, b)

    def los(rng: np.random.Generator, k: int) -> np.ndarray:
        return losuj_innowacje(rng, (k, n), rodzina, nu)

    return as_z2_h0(q, es, p, los, reps, seed=seed)
