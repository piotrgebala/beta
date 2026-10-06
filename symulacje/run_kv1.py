"""
KV1 — kontrole R8 przyrządu VaR/ES (`miara/var_es.py`): rozmiar testów na prawdziwych prognozach
(kontrola negatywna) i moc na prognozach znanych jako błędne (kontrole pozytywne).
Pre-rejestracja: `runs/2026-10-05_kv1-kontrola-var-es/README.md`. Neutralny reporter (R14).

    python -m symulacje.run_kv1 > runs/2026-10-05_kv1-kontrola-var-es/raw_output.txt
    python -m symulacje.run_kv1 --smoke      # małe n: TYLKO sprawdzenie, że kod działa

Wynik nie zależy od liczby procesów (`--workers`): ziarna rozdziela SeedSequence.spawn per zadanie.
Na stdout (raw_output.txt) idą tylko liczby odtwarzalne; czas przebiegu idzie na stderr.
Wymaga pandas 3 (indeks dat 200 000 dni w `generuj_panel` wychodzi poza zakres ns w pandas 2).
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

from miara.var_es import (
    as_z2,
    as_z2_h0_polozenie_skala,
    as_z2_pwartosc,
    christoffersen_cc,
    christoffersen_ind,
    czy_polozenie_skala,
    kupiec_uc,
    var_es_normal,
    var_es_t,
)
from symulacje.garch_panel import generuj_panel
from symulacje.run_lm1 import wilson

SEED = 20_261_005
NU = 5.0
SIGMA_STALA = 0.04  # bezwarunkowe σ generatora (daily_vol) — prognoza „stała”
POZIOMY = (0.01, 0.05)
ALFA = 0.05  # nominalny poziom testów: odrzucamy, gdy p-wartość < ALFA
ZAKRES_NEG = (0.025, 0.075)
MOC_MIN = 0.80
NIEZDEF_MAX = 0.01
B_H0 = 20_000
CHUNK_H0 = 500
TESTY = ("kupiec", "ind", "cc", "z2")
NAZWY_TESTOW = {
    "kupiec": "Kupiec LR_uc",
    "ind": "Christoffersen ind",
    "cc": "Christoffersen cc",
    "z2": "Acerbi–Szekely Z2",
}
PROGNOZY = ("prawdziwa", "normalna", "stala", "es_za_niski")
OPIS_PROGNOZ = {
    "prawdziwa": "prawdziwe q/es (σ wyroczni, kwantyl t5)",
    "normalna": "normalne q/es (σ wyroczni), prawda t5",
    "stala": "stałe σ = 4 % (t5), prawda GARCH",
    "es_za_niski": "q prawdziwe, es z ilorazu normalnego (za niskie)",
}

# n_dni: dni na serię; panele × monety = liczba niezależnych serii (ρ = 0) na poziom p.
# 1 %: n·p² = 20 oczekiwanych przejść 1→1 (zasada z README); 5 %: n·p² = 50.
KONFIG = {
    0.01: {"n_dni": 200_000, "panele": 200, "monety": 25},
    0.05: {"n_dni": 20_000, "panele": 100, "monety": 50},
}
KONFIG_SMOKE = {
    0.01: {"n_dni": 4_000, "panele": 2, "monety": 5},
    0.05: {"n_dni": 2_000, "panele": 2, "monety": 5},
}

_H0: dict = {}


def _init(h0: dict) -> None:
    _H0.update(h0)


def _ziarno_int(ss: np.random.SeedSequence) -> int:
    return int(ss.generate_state(1, dtype=np.uint64)[0])


def _chunk_h0(arg):
    n, p, rodzina, reps, ss = arg
    nu = NU if rodzina == "t" else None
    return as_z2_h0_polozenie_skala(n, p, rodzina, nu, reps, seed=ss)


def _prognozy(sigma2: np.ndarray, p: float) -> dict:
    """Cztery prognozy (q, es, rodzina rozkładu zerowego Z2) dla jednej monety."""
    n = len(sigma2)
    s = np.sqrt(sigma2)
    q_t, es_t = var_es_t(s, p, NU)
    q_n, es_n = var_es_normal(s, p)
    q_s, es_s = var_es_t(SIGMA_STALA, p, NU)
    qn1, en1 = var_es_normal(1.0, p)
    return {
        "prawdziwa": (q_t, es_t, "t"),
        "normalna": (q_n, es_n, "normal"),
        "stala": (np.full(n, q_s), np.full(n, es_s), "t"),
        "es_za_niski": (q_t, q_t * (en1 / qn1), "t"),
    }


def _panel(arg):
    p, n_dni, monety, ss = arg
    panel = generuj_panel(n_dni, monety, seed=_ziarno_int(ss), nu=NU, rho=0.0)
    r, s2 = panel["r"].to_numpy(), panel["sigma2"].to_numpy()
    out = {f: {k: [] for k in ("hit", *TESTY, "z2_stat")} for f in PROGNOZY}
    for j in range(monety):
        for nazwa, (q, es, rodzina) in _prognozy(s2[:, j], p).items():
            if nazwa != "es_za_niski" and not czy_polozenie_skala(
                q, es, p, rodzina, NU if rodzina == "t" else None
            ):  # skrót rozkładu zerowego Z2 wymaga prognozy σ_t (a, b); es_za_niski jest poza nią
                raise ValueError(f"prognoza {nazwa} nie jest typu położenie–skala")
            h = r[:, j] < q
            z2 = as_z2(r[:, j], q, es, p)
            ind = christoffersen_ind(h)
            o = out[nazwa]
            o["hit"].append(float(h.mean()))
            o["kupiec"].append(kupiec_uc(h, p)["p_wartosc"])
            o["ind"].append(ind["p_wartosc"])  # nan = niezdefiniowany
            o["cc"].append(christoffersen_cc(h, p)["p_wartosc"])
            o["z2"].append(as_z2_pwartosc(z2, _H0[(p, rodzina)]))
            o["z2_stat"].append(z2)
    return out


def _zbierz(czesci: list) -> dict:
    return {
        f: {k: np.array([x for c in czesci for x in c[f][k]]) for k in czesci[0][f]}
        for f in PROGNOZY
    }


def _kryterium(grupa, opis, wyn_p, test, wymaganie, ok):
    """Wiersz kryterium: liczba odrzuceń (p < ALFA; NaN = brak odrzucenia) z n serii."""
    k = int((wyn_p[test] < ALFA).sum())
    n = len(wyn_p[test])
    return {
        "grupa": grupa,
        "opis": opis,
        "k": k,
        "n": n,
        "wymaganie": wymaganie,
        "ok": ok(k / n),
    }


def _kryteria(wyn: dict) -> list[dict]:
    """19 kryteriów w kolejności numeracji z README (#1–19)."""
    lo, hi = ZAKRES_NEG
    txt_zakres = f"odsetek ∈ [{100 * lo:.1f}; {100 * hi:.1f}] %"
    txt_moc = f"odsetek ≥ {100 * MOC_MIN:.0f} %"

    def w_zakresie(x):
        return lo <= x <= hi

    def dosc_mocy(x):
        return x >= MOC_MIN

    kr = []
    for p in POZIOMY:  # #1–8
        for t in TESTY:
            opis = f"p = {p:.0%}, {NAZWY_TESTOW[t]}"
            kr.append(_kryterium("NEGATYWNA", opis, wyn[p]["prawdziwa"], t, txt_zakres, w_zakresie))
    for p in POZIOMY:  # #9–10
        w = wyn[p]["prawdziwa"]["ind"]
        k, n = int(np.isnan(w).sum()), len(w)
        kr.append(
            {
                "grupa": "NEGATYWNA",
                "opis": f"p = {p:.0%}, udział serii z niezdefiniowanym Christoffersen ind",
                "k": k,
                "n": n,
                "wymaganie": f"udział ≤ {100 * NIEZDEF_MAX:.0f} %",
                "ok": k / n <= NIEZDEF_MAX,
            }
        )
    for p in POZIOMY:  # #11–12
        opis = f"p = {p:.0%}, Kupiec, normalna vs t5"
        kr.append(_kryterium("POZYTYWNA 1", opis, wyn[p]["normalna"], "kupiec", txt_moc, dosc_mocy))
    opis = "p = 1%, Z2, normalna vs t5"  # #13
    kr.append(_kryterium("POZYTYWNA 1", opis, wyn[0.01]["normalna"], "z2", txt_moc, dosc_mocy))
    for p in POZIOMY:  # #14–15
        opis = f"p = {p:.0%}, Christoffersen ind, stałe σ vs GARCH"
        kr.append(_kryterium("POZYTYWNA 2", opis, wyn[p]["stala"], "ind", txt_moc, dosc_mocy))
    for p in POZIOMY:  # #16–17
        opis = f"p = {p:.0%}, Z2, q prawdziwe + es za niskie"
        kr.append(_kryterium("POZYTYWNA 3", opis, wyn[p]["es_za_niski"], "z2", txt_moc, dosc_mocy))
    for p in POZIOMY:  # #18–19: R8 dla cc — kontrola pozytywna (cc musi mieć składnik pokrycia)
        opis = f"p = {p:.0%}, Christoffersen cc, normalna vs t5"
        kr.append(_kryterium("POZYTYWNA 4", opis, wyn[p]["normalna"], "cc", txt_moc, dosc_mocy))
    return kr


def _wypisz_kryteria(kr: list[dict]) -> None:
    grupa = None
    for i, c in enumerate(kr, start=1):
        if c["grupa"] != grupa:
            grupa = c["grupa"]
            print(f"\n{grupa}")
        lo, hi = wilson(c["k"], c["n"])
        print(
            f"  #{i} {c['opis']}: {c['k']}/{c['n']} = {100 * c['k'] / c['n']:.2f} % "
            f"[Wilson {100 * lo:.2f}; {100 * hi:.2f}] — {c['wymaganie']}: "
            f"{'TAK' if c['ok'] else 'NIE'}"
        )


def _wypisz_opis(wyn: dict) -> None:
    print("\nOPIS (nie kryteria): odsetek odrzuceń na poziomie 5 % we wszystkich komórkach,")
    print("średni odsetek trafień, średnie Z2 (±błąd standardowy), niezdefiniowane ind")
    print(" p   | prognoza                                           | trafienia |", end="")
    print(" kupiec |   ind |    cc |    Z2 | śr. Z2 ± se       | niezdef. ind")
    for p in POZIOMY:
        for f in PROGNOZY:
            w = wyn[p][f]
            n = len(w["hit"])
            z = w["z2_stat"]
            odrz = [100 * (w[t] < ALFA).mean() for t in TESTY]
            print(
                f" {p:.0%}  | {OPIS_PROGNOZ[f]:50s} | {100 * w['hit'].mean():8.3f} % |"
                f" {odrz[0]:5.1f}% | {odrz[1]:4.1f}% | {odrz[2]:4.1f}% | {odrz[3]:4.1f}% |"
                f" {z.mean():+.4f} ± {z.std(ddof=1) / math.sqrt(n):.4f} |"
                f" {int(np.isnan(w['ind']).sum())}"
            )


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="KV1 — kontrole R8 przyrządu VaR/ES")
    ap.add_argument("--smoke", action="store_true", help="male n i reps; tylko test dzialania kodu")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    args = ap.parse_args(argv)
    konfig = KONFIG_SMOKE if args.smoke else KONFIG
    b_h0, chunk = (300, 150) if args.smoke else (B_H0, CHUNK_H0)
    t0 = time.time()

    print("KV1 — kontrole R8 przyrządu VaR/ES (Kupiec, Christoffersen ind/cc, Acerbi–Szekely Z2)")
    if args.smoke:
        print(
            "TRYB SMOKE: małe n i reps, TYLKO sprawdzenie działania kodu — wyniki nie są werdyktem."
        )
    print(
        f"Generator: GARCH(1,1)-t, ν = {NU:.0f}, ρ = 0 (serie niezależne), ziarno główne {SEED}; "
        f"poziom testów {100 * ALFA:.0f} %; rozkład zerowy Z2: {b_h0} symulacji."
    )
    for p in POZIOMY:
        c = konfig[p]
        print(
            f"  p = {p:.0%}: n = {c['n_dni']} dni na serię, {c['panele']} paneli × "
            f"{c['monety']} monet = {c['panele'] * c['monety']} serii; "
            f"oczekiwane trafienia {c['n_dni'] * p:.0f},"
            f" przejścia 1→1 {c['n_dni'] * p * p:.1f}"
        )

    ss_h0, ss_panele = np.random.SeedSequence(SEED).spawn(2)
    h0_poziomy = ss_h0.spawn(len(POZIOMY))
    panele_poziomy = ss_panele.spawn(len(POZIOMY))

    zadania_h0, klucze = [], []
    for i, p in enumerate(POZIOMY):
        for rodzina, ss_r in zip(("t", "normal"), h0_poziomy[i].spawn(2), strict=True):
            n_chunk = math.ceil(b_h0 / chunk)
            for j, ss in enumerate(ss_r.spawn(n_chunk)):
                reps = min(chunk, b_h0 - j * chunk)
                zadania_h0.append((konfig[p]["n_dni"], p, rodzina, reps, ss))
                klucze.append((p, rodzina))

    zadania_panele = []
    for i, p in enumerate(POZIOMY):
        c = konfig[p]
        for ss in panele_poziomy[i].spawn(c["panele"]):
            zadania_panele.append((p, c["n_dni"], c["monety"], ss))

    with Pool(args.workers) as pool:
        wyniki_h0 = pool.map(_chunk_h0, zadania_h0, chunksize=1)
        h0: dict = {}
        for k, z in zip(klucze, wyniki_h0, strict=True):
            h0.setdefault(k, []).append(z)
        h0 = {k: np.concatenate(v) for k, v in h0.items()}
        print(f"Rozkłady zerowe Z2 gotowe ({time.time() - t0:.0f} s)", file=sys.stderr)
        print("\nRozkłady zerowe Z2 gotowe:")
        for (p, rodzina), z in sorted(h0.items()):
            print(
                f"  p = {p:.0%}, {rodzina:6s}: średnia {z.mean():+.4f}, sd {z.std(ddof=1):.4f}, "
                f"5. percentyl {np.quantile(z, 0.05):+.4f}"
            )
    with Pool(args.workers, initializer=_init, initargs=(h0,)) as pool:
        czesci = pool.map(_panel, zadania_panele, chunksize=1)

    wyn = {}
    for p in POZIOMY:
        wyn[p] = _zbierz([c for c, z in zip(czesci, zadania_panele, strict=True) if z[0] == p])

    kr = _kryteria(wyn)
    print("\nKRYTERIA z pre-rejestracji (odrzucenie = p-wartość < 5 %; NaN = brak odrzucenia)")
    _wypisz_kryteria(kr)
    _wypisz_opis(wyn)

    zaliczona = all(c["ok"] for c in kr)
    print(f"\nKryteria spełnione: {sum(c['ok'] for c in kr)}/{len(kr)}")
    werdykt = "ZALICZONA" if zaliczona else "NIEZALICZONA"
    if args.smoke:
        print(f"[SMOKE — bez znaczenia] reguła dałaby: {werdykt}")
    else:
        print(f"Reguła z pre-rejestracji (wszystkie kryteria): {werdykt}")
    print(f"czas: {time.time() - t0:.0f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
