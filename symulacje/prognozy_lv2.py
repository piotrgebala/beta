"""
prognozy_lv2.py — prognozy VaR/ES ESTYMOWANE na panelu symulacyjnym dla LV2 (okno, EWMA, GARCH-t, HAR)
z różnymi ogonami. Wszystko przyczynowe: prognoza dnia t używa wyłącznie zwrotów z dni < t.

Oś czasu panelu (N_DNI = 2 100): dni 0 … START − 1 to historia (rozgrzewka, trening), dni START … N_DNI − 1
to okres oceny (OOS). Estymowane elementy odświeżamy co KROK dni od dnia START (bloki):
  • σ̂²: okno 60 dni, EWMA 0,94 (bez parametrów — przyczynowe filtry całego panelu), GARCH(1,1)-t
    (refit na rosnącym oknie 0 … b − 1, filtr z parametrami bloku), HAR-RV (`modele.zmiennosc`, własny
    harmonogram refitów co 30 dni od dnia 395), wyrocznia σ (znana z generatora; tylko kontrola);
  • ogon standaryzowanej innowacji (kwantyl Q i ES poziomu p dla ε o wariancji 1):
      t5   stały, t_5 (prawdziwy ogon generatora),
      tnu  t_ν̂ z ν̂ z dopasowania GARCH-t danego bloku i monety,
      ec   empiryczny z reszt standaryzowanych r_s/σ̂_s, s ∈ [60, b), osobno dla każdej monety,
      ep   jak ec, ale reszty wszystkich monet razem (zbiorczo).
    Reszty dla okna/EWMA pochodzą z ich własnych prognoz σ̂_s, dla GARCH — z filtra z parametrami
    bloku b (reszty „w próbie”; filtr nadal widzi tylko dni < b).
Prognoza (q, es) = σ̂_t · (Q, ES) z ogonem stałym w bloku.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from miara.var_es import var_es_t
from modele.zmiennosc import prognoza_har
from symulacje.garch_panel import prognoza_ewma, prognoza_okno
from symulacje.garch_t import dopasuj_garch_t, filtr_sigma2

N_DNI = 2100
START = 400
KROK = 30
ROZGRZEWKA_RESZT = 60
POZIOMY = (0.01, 0.05)
NU = 5.0
EWMA_LAMBDA = 0.94
ZANIZENIA = {"zan05": 0.05, "zan10": 0.10, "zan15": 0.15, "zan20": 0.20, "zan30": 0.30}
# nazwa prognozy -> (źródło σ, mnożnik σ, ogon)
PROGNOZY = {
    "wyr_t5": ("wyr", 1.0, "t5"),
    **{k: ("wyr", 1.0 - x, "t5") for k, x in ZANIZENIA.items()},
    "okno60_t5": ("okno60", 1.0, "t5"),
    "ewma94_t5": ("ewma94", 1.0, "t5"),
    "garch_t5": ("garch", 1.0, "t5"),
    "garch_tnu": ("garch", 1.0, "tnu"),
    "garch_tnu_zan10": ("garch", 0.90, "tnu"),
    "garch_tnu_zan20": ("garch", 0.80, "tnu"),
    "har_t5": ("har", 1.0, "t5"),
    "okno60_ep": ("okno60", 1.0, "ep"),
    "ewma94_ep": ("ewma94", 1.0, "ep"),
    "garch_ep": ("garch", 1.0, "ep"),
    "okno60_ec": ("okno60", 1.0, "ec"),
    "ewma94_ec": ("ewma94", 1.0, "ec"),
    "garch_ec": ("garch", 1.0, "ec"),
}
# w podpanelu pierwszych k monet nie ma ogonów zbiorczych (liczone na wszystkich monetach panelu)
PROGNOZY_PODPANEL = tuple(n for n, (_, _, ogon) in PROGNOZY.items() if ogon != "ep")


@dataclass
class Zrodla:
    """Składniki prognoz na okresie OOS (n_oos × K) oraz diagnostyka dopasowań GARCH."""

    r: np.ndarray
    sigma: dict[str, np.ndarray]
    ogon: dict[tuple[str, str, float], tuple[np.ndarray, np.ndarray]]
    diag: dict = field(default_factory=dict)

    def pierwsze(self, k: int) -> Zrodla:
        """Podpanel pierwszych k monet (monety wymienne; bez ogonów zbiorczych `ep`)."""
        return Zrodla(
            r=self.r[:, :k],
            sigma={z: a[:, :k] for z, a in self.sigma.items()},
            ogon={
                key: (q[:, :k], es[:, :k]) for key, (q, es) in self.ogon.items() if key[1] != "ep"
            },
            diag=self.diag,
        )


def ogon_empiryczny(z: np.ndarray, p: float) -> tuple[np.ndarray, np.ndarray, float, float]:
    """(Q_moneta, ES_moneta, Q_zbiorczy, ES_zbiorczy): dolny kwantyl p i średnia reszt ≤ kwantyl."""
    qk = np.quantile(z, p, axis=0)
    esk = np.array([z[z[:, j] <= qk[j], j].mean() for j in range(z.shape[1])])
    qz = float(np.quantile(z, p))
    return qk, esk, qz, float(z[z <= qz].mean())


def _rozwin(w: np.ndarray, dlugosci: np.ndarray) -> np.ndarray:
    """Wartości bloków (bloków × K) → wiersze dni (n_oos × K)."""
    return np.repeat(w, dlugosci, axis=0)


def zbuduj_zrodla(panel: dict, start: int = START, krok: int = KROK) -> Zrodla:
    """Prognozy estymowane dla całego okresu OOS panelu (patrz docstring modułu)."""
    r_df = panel["r"]
    r = r_df.to_numpy()
    n, k = r.shape
    if start < ROZGRZEWKA_RESZT + 2 * krok or start >= n:
        raise ValueError("start poza zakresem panelu")
    sigma = {
        "wyr": np.sqrt(panel["sigma2"].to_numpy()[start:]),
        "okno60": np.sqrt(prognoza_okno(r_df, 60).to_numpy()),
        "ewma94": np.sqrt(prognoza_ewma(r_df, EWMA_LAMBDA).to_numpy()),
    }
    reszty = {z: r / sigma[z] for z in ("okno60", "ewma94")}
    sigma = {**sigma, **{z: sigma[z][start:] for z in ("okno60", "ewma94")}}
    har = np.column_stack(
        [prognoza_har(pd.Series(panel["rv"].to_numpy()[:, j])).to_numpy() for j in range(k)]
    )
    sigma["har"] = np.sqrt(har[start:])
    bloki = list(range(start, n, krok))
    dlugosci = np.array([min(b + krok, n) - b for b in bloki])
    tail = {
        (z, t, p): ([], [])
        for z in ("okno60", "ewma94", "garch")
        for t in ("ec", "ep")
        for p in POZIOMY
    }
    tnu = {p: ([], []) for p in POZIOMY}
    s2_garch, poprzednie = np.empty((n - start, k)), [None] * k
    diag = {"dopasowania": 0, "nie_zbiezne": 0, "brzeg": 0, "persystencja": [], "nu": []}
    for b in bloki:
        e = min(b + krok, n)
        zg, nu_blok = np.empty((b - ROZGRZEWKA_RESZT, k)), np.empty(k)
        for j in range(k):
            f = dopasuj_garch_t(r[:b, j], start=poprzednie[j])
            poprzednie[j] = f
            s2 = filtr_sigma2(r[: e - 1, j] ** 2, f.omega, f.alpha, f.beta, f.backcast)
            s2_garch[b - start : e - start, j] = s2[b:e]
            zg[:, j] = r[ROZGRZEWKA_RESZT:b, j] / np.sqrt(s2[ROZGRZEWKA_RESZT:b])
            nu_blok[j] = f.nu
            diag["dopasowania"] += 1
            diag["nie_zbiezne"] += not f.zbiezny
            diag["brzeg"] += f.brzeg
            diag["persystencja"].append(f.alpha + f.beta)
            diag["nu"].append(f.nu)
        z_src = {
            "okno60": reszty["okno60"][ROZGRZEWKA_RESZT:b],
            "ewma94": reszty["ewma94"][ROZGRZEWKA_RESZT:b],
            "garch": zg,
        }
        for p in POZIOMY:
            for src, z in z_src.items():
                qk, esk, qz, esz = ogon_empiryczny(z, p)
                tail[(src, "ec", p)][0].append(qk)
                tail[(src, "ec", p)][1].append(esk)
                tail[(src, "ep", p)][0].append(np.full(k, qz))
                tail[(src, "ep", p)][1].append(np.full(k, esz))
            qn, en = zip(*(var_es_t(1.0, p, nu) for nu in nu_blok))
            tnu[p][0].append(np.array(qn, dtype=float))
            tnu[p][1].append(np.array(en, dtype=float))
    sigma["garch"] = np.sqrt(s2_garch)
    ogon = {
        key: (_rozwin(np.array(q), dlugosci), _rozwin(np.array(es), dlugosci))
        for key, (q, es) in tail.items()
    }
    for p, (q, es) in tnu.items():
        ogon[("garch", "tnu", p)] = (
            _rozwin(np.array(q), dlugosci),
            _rozwin(np.array(es), dlugosci),
        )
    diag["persystencja"] = float(np.mean(diag["persystencja"]))
    diag["nu"] = float(np.mean(diag["nu"]))
    return Zrodla(r=r[start:], sigma=sigma, ogon=ogon, diag=diag)


def prognoza(zr: Zrodla, nazwa: str, p: float) -> tuple[np.ndarray, np.ndarray]:
    """(q, es) prognozy `nazwa` (klucz `PROGNOZY`) na okresie OOS: σ̂ · mnożnik · (Q, ES)."""
    zrodlo, mnoznik, ogon = PROGNOZY[nazwa]
    s = zr.sigma[zrodlo] * mnoznik
    if ogon == "t5":
        q0, e0 = (float(x) for x in var_es_t(1.0, p, NU))
        return s * q0, s * e0
    q0, e0 = zr.ogon[(zrodlo, ogon, p)]
    return s * q0, s * e0


def prognoza_wyrocznia_skala(zr: Zrodla, c: float, p: float) -> tuple[np.ndarray, np.ndarray]:
    """(q, es) prawdziwej prognozy (σ wyroczni, t5) pomnożonej przez c > 0 — pary „dokładnie zerowe”."""
    if c <= 0:
        raise ValueError("c > 0")
    q0, e0 = (float(x) for x in var_es_t(1.0, p, NU))
    s = zr.sigma["wyr"] * c
    return s * q0, s * e0
