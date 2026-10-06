"""
moc_var_es.py — laboratorium LV1: testy wsteczne VaR/ES ZBIORCZO po monetach (R12) i zestaw prognoz
do kontroli mocy (`docs/PRD.md` FR-32, cel G2). Instrument per moneta zostaje w `miara/var_es.py`
(zamrożony po KV1); tu jest tylko to, czego tamten nie ma: dzienne sumy po monetach.

Dlaczego dzienne sumy. Monety są skorelowane (czynnik rynkowy), więc 20·n trafień to NIE 20·n
niezależnych obserwacji (R12). Jednostką jest dzień t: S_t = Σ_i I_it. Pod H0 z prognozą
F_{t−1}-mierzalną E[S_t | przeszłość] = K·p (różnica martyngałowa), więc test dni nie zakłada
niezależności monet. Trzy statystyki zbiorcze (odpowiedniki Kupca, Christoffersena i
Acerbiego–Szekelya):

    A pokrycie       t-Studenta średniej S_t względem K·p, dwustronny z RÓWNYMI ogonami;
    B niezależność   studentyzowana kowariancja S_t ze średnią 10 poprzednich dni, dwustronny
                     z równymi ogonami;
    C ogon (Z2)      t-Studenta średniej d_t = Σ_i (U_it − 1), U_it = r_it I_it / (p es_it) ≥ 0,
                     jednostronny: odrzucamy, gdy średnia d_t > 0 (ogon niedoszacowany, Z2 < 0).

Test zbiorczy LV1 = „którykolwiek z A, B, C” z poprawką Bonferroniego (każdy na poziomie α/3).

p-wartości z bootstrapu-t po dniach (zwykłe losowanie dni ze zwracaniem). Test dwustronny ma
RÓWNE ogony: p = 2·min(P*(t* ≥ t), P*(t* ≤ t)). Powód (przegląd przed pełnym przebiegiem): t testu
A jest pod H0 skośne w lewo (S_t prawoskośne), więc symetryczne |t*| ≥ |t| oddawało prawie cały
rozmiar stronie „za mało trafień”, a strona „za dużo trafień” (zaniżone ryzyko) prawie nie
odrzucała. Równe ogony dają każdej stronie ok. α/6. Założenie bootstrapu: dni są wymienialne (jak
w generatorze: ε_it = r_it/σ_it iid po t); przy zmiennej w czasie korelacji monet to ograniczenie.
"""

from __future__ import annotations

import numpy as np

from miara.var_es import var_es_normal, var_es_t
from symulacje.garch_panel import prognoza_ewma, prognoza_okno

NU = 5.0
SIGMA_STALA = 0.04  # bezwarunkowe σ generatora (daily_vol) — prognoza „stała”
LAG_KLASTER = 10  # długość okna regresora w teście niezależności B (dni)
WARM = 60  # dni na rozgrzewkę okien i EWMA; wszystkie prognozy oceniamy na tych samych dniach
EWMA_LAMBDA = 0.94
CHUNK_BOOT = 100  # replikacji bootstrapu naraz: tablice mieszczą się w cache, wynik ten sam
ZANIZENIA = {
    "zanizenie_05": 0.05,
    "zanizenie_10": 0.10,
    "zanizenie_15": 0.15,
    "zanizenie_20": 0.20,
    "zanizenie_30": 0.30,
}
PROGNOZY = (
    "prawdziwa",
    "normalna",
    "stala",
    "okno10",
    "okno60",
    "ewma94",
    *ZANIZENIA,
    "es_za_niski",
)
OPIS_PROGNOZ = {
    "prawdziwa": "prawdziwa: σ wyroczni, t5 (H0)",
    "normalna": "normalna: σ wyroczni, kwantyl/ES normalny",
    "stala": "stała: σ = 4 %, t5",
    "okno10": "okno 10 dni na σ, t5 (zbyt krótkie)",
    "okno60": "okno 60 dni na σ, t5 (realistyczna)",
    "ewma94": "EWMA λ = 0,94 na σ, t5 (realistyczna)",
    **{k: f"σ wyroczni × (1 − {v:.2f}), t5" for k, v in ZANIZENIA.items()},
    "es_za_niski": "q prawdziwe, ES z ilorazu normalnego (za niskie)",
}
STAT = (
    "hit",  # średni odsetek trafień na monetę
    "z2",  # średnie Z2 na monetę
    "kupiec",  # odsetek monet odrzuconych przez Kupca (p < alfa)
    "cc",  # odsetek monet odrzuconych przez Christoffersena cc
    "z2_rej",  # odsetek monet odrzuconych przez Z2 (lewy ogon)
    "zb_a",  # zbiorczy test pokrycia odrzuca (0/1)
    "zb_b",  # zbiorczy test niezależności odrzuca (0/1)
    "zb_c",  # zbiorczy test ogona odrzuca (0/1)
    "zb_bonf",  # test zbiorczy „A lub B lub C” z poprawką Bonferroniego odrzuca (0/1)
    "zb_a_prawa",  # A odrzuca po stronie „za dużo trafień” (t_a > 0), opis
    "zb_ac",  # „A lub C” na α/2, bez testu B: opis wrażliwości (ii-b bez B)
    "vr",  # wariancja S_t / (K p (1 − p)): ile razy S_t zmienniejsze niż przy niezależnych monetach
    "naiwny",  # Kupiec na 20·n trafieniach jak na niezależnych (kontrola: zły z założenia)
    "niezdef",  # liczba niezdefiniowanych testów zbiorczych (t = NaN) w komórce, 0..3
)
IDX = {nazwa: i for i, nazwa in enumerate(STAT)}


# --- prognozy ------------------------------------------------------------------------------------


def sigmy_prognoz(panel: dict) -> dict[str, np.ndarray]:
    """σ_t (n × K, po rozgrzewce `WARM`) dla każdej prognozy; każda znana w t − 1.

    Okna i EWMA liczone na całym panelu (z rozgrzewką), dopiero potem obcinane — dzięki temu
    wszystkie prognozy są oceniane na tych samych dniach.
    """
    r = panel["r"]
    wyrocznia = np.sqrt(panel["sigma2"].to_numpy()[WARM:])
    okno = {
        k: np.sqrt(prognoza_okno(r, w).to_numpy()[WARM:])
        for k, w in (("okno10", 10), ("okno60", 60))
    }
    ewma = np.sqrt(prognoza_ewma(r, EWMA_LAMBDA).to_numpy()[WARM:])
    for s in (*okno.values(), ewma):
        if not np.isfinite(s).all() or (s <= 0).any():
            raise ValueError("σ̂ z okna/EWMA: NaN albo ≤ 0 po rozgrzewce")
    out = {
        "prawdziwa": wyrocznia,
        "normalna": wyrocznia,
        "stala": np.full_like(wyrocznia, SIGMA_STALA),
        **okno,
        "ewma94": ewma,
        "es_za_niski": wyrocznia,
    }
    out.update({k: wyrocznia * (1.0 - x) for k, x in ZANIZENIA.items()})
    return out


def rodzina_prognozy(nazwa: str) -> str:
    """Rodzina rozkładu zerowego Z2: „normal” tylko dla prognozy normalnej, reszta t5."""
    return "normal" if nazwa == "normalna" else "t"


def prognoza_q_es(sigma: np.ndarray, nazwa: str, p: float) -> tuple[np.ndarray, np.ndarray]:
    """(q, es) prognozy `nazwa` dla σ_t (dowolny kształt)."""
    if nazwa == "normalna":
        return var_es_normal(sigma, p)
    q, es = var_es_t(sigma, p, NU)
    if (
        nazwa == "es_za_niski"
    ):  # q prawdziwe, ES o ok. 13 % za niskie (iloraz ES/q rozkładu normalnego)
        qn, en = var_es_normal(1.0, p)
        return q, q * (en / qn)
    return q, es


# --- statystyki zbiorcze -------------------------------------------------------------------------


def t_srednia(x: np.ndarray, mu: float | np.ndarray) -> np.ndarray:
    """t = (średnia − mu) / (s/√n) po ostatniej osi (s z ddof = 1); NaN, gdy s = 0."""
    n = x.shape[-1]
    s = x.std(axis=-1, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return (x.mean(axis=-1) - mu) / (s / np.sqrt(n))


def t_klaster(x: np.ndarray, lag: int) -> np.ndarray:
    """Studentyzowana kowariancja c_t z średnią jej `lag` poprzednich dni (c = x − średnia).

    t = Σ c_t a_t / √Σ (c_t a_t)², a_t = (c_{t−1} + … + c_{t−lag}) / lag. Regresor a_t jest znany
    w t − 1, więc przy H0 (różnica martyngałowa) licznik ma średnią 0 bez założenia niezależności;
    c jest centrowane średnią próby, więc test nie reaguje na zły POZIOM trafień (to robi test A).
    """
    n = x.shape[-1]
    c = x - x.mean(axis=-1, keepdims=True)
    cs = np.concatenate([np.zeros_like(c[..., :1]), np.cumsum(c, axis=-1)], axis=-1)
    a = (cs[..., lag:n] - cs[..., : n - lag]) / lag
    pr = c[..., lag:] * a
    with np.errstate(divide="ignore", invalid="ignore"):
        return pr.sum(axis=-1) / np.sqrt((pr * pr).sum(axis=-1))


def p_boot(t_obs: float, t_boot: np.ndarray, strona: str) -> float:
    """p-wartość bootstrapu: „prawa” = (1 + #{t* ≥ t}) / (1 + B); „rowne” = dwustronna z równymi
    ogonami, 2·min(prawa, lewa) obcięte do 1. NaN w t* pomijane.

    Równe ogony, bo t bywa pod H0 skośne: każda strona ma wtedy ok. połowę rozmiaru.
    Zwraca NaN, gdy t_obs jest NaN (statystyka niezdefiniowana = brak odrzucenia).
    """
    if not np.isfinite(t_obs):
        return float("nan")
    tb = t_boot[np.isfinite(t_boot)]
    b = 1 + len(tb)
    prawa = (1 + np.count_nonzero(tb >= t_obs)) / b
    if strona == "prawa":
        return float(prawa)
    if strona == "rowne":
        lewa = (1 + np.count_nonzero(tb <= t_obs)) / b
        return float(min(1.0, 2.0 * min(prawa, lewa)))
    raise ValueError(f"strona: rowne albo prawa, jest {strona!r}")


def wklady_dzienne(r, q, es, p: float) -> tuple[np.ndarray, np.ndarray]:
    """Dzienne sumy po monetach (n × K na wejściu): S_t (liczba trafień) i d_t = Σ_i (U_it − 1)."""
    hit = r < q  # ta sama definicja co `miara.var_es._trafienie`
    u = np.where(hit, r / es, 0.0) / p
    return hit.sum(axis=1).astype(float), (u - 1.0).sum(axis=1)


def _t_boot(x: np.ndarray, idx: np.ndarray, stat) -> np.ndarray:
    """stat(x[idx]) po replikacjach, partiami `CHUNK_BOOT` (te same liczby, mniej pamięci)."""
    return np.concatenate(
        [stat(x[idx[i : i + CHUNK_BOOT]]) for i in range(0, len(idx), CHUNK_BOOT)]
    )


def testy_zbiorcze(r, q, es, p: float, idx: np.ndarray) -> dict:
    """
    Zbiorcze testy A, B, C po monetach na dziennych sumach (n × K), bootstrap-t po dniach.

    `idx` = indeksy dni (B × n) wspólne dla wszystkich komórek tego samego n; wynik zależy tylko od
    danych i `idx`. Zwraca statystyki t i p-wartości (NaN = niezdefiniowany, brak odrzucenia).
    """
    k = r.shape[1]
    s, d = wklady_dzienne(r, q, es, p)
    t_a, t_b, t_c = t_srednia(s, k * p), t_klaster(s, LAG_KLASTER), t_srednia(d, 0.0)
    ma, md = s.mean(), d.mean()
    tb_a = _t_boot(s, idx, lambda x: t_srednia(x, ma))
    tb_b = _t_boot(s, idx, lambda x: t_klaster(x, LAG_KLASTER))
    tb_c = _t_boot(d, idx, lambda x: t_srednia(x, md))
    return {
        "t_a": float(t_a),
        "t_b": float(t_b),
        "t_c": float(t_c),
        "p_a": p_boot(float(t_a), tb_a, "rowne"),
        "p_b": p_boot(float(t_b), tb_b, "rowne"),
        "p_c": p_boot(float(t_c), tb_c, "prawa"),
    }


def odrzuca_zbiorczo(pwartosci, alfa: float) -> bool:
    """Odrzuca, gdy któraś z m p-wartości < alfa/m (Bonferroni); LV1: m = 3 (A, B, C).

    NaN (statystyka niezdefiniowana) nie odrzuca — porównanie z NaN jest fałszywe.
    """
    pw = np.asarray(pwartosci, dtype=float)
    return bool(np.any(pw < alfa / len(pw)))


def mde(poziomy: np.ndarray, moc: np.ndarray, cel: float = 0.8) -> float:
    """Najmniejsze x z mocą ≥ cel (interpolacja liniowa; moc wygładzona maksimum narastającym).

    NaN, gdy cel jest nieosiągalny na siatce — to znaczy MDE większe niż największe x.
    """
    x = np.asarray(poziomy, dtype=float)
    m = np.maximum.accumulate(np.asarray(moc, dtype=float))
    trafione = np.nonzero(m >= cel)[0]
    if len(trafione) == 0:
        return float("nan")
    j = int(trafione[0])
    if j == 0:
        return float(x[0])
    x0, x1, m0, m1 = x[j - 1], x[j], m[j - 1], m[j]
    return float(x0 + (cel - m0) * (x1 - x0) / (m1 - m0)) if m1 > m0 else float(x1)
