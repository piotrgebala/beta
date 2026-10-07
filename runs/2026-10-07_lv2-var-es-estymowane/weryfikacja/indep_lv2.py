"""
indep_lv2.py — NIEZALEŻNE przeliczenie kluczowych liczb LV2 (krok 4 planu).

Uruchamianie z korzenia repo: PYTHONPATH=. python runs/2026-10-07_lv2-var-es-estymowane/weryfikacja/indep_lv2.py {panele|zbiorczo|stale} ...

Niezależność względem kodu rejestrowego (symulacje/*.py, miara/*.py):
  • prognozy: okno 60 i EWMA 0,94 własnymi pętlami; GARCH(1,1)-t przez pakiet `arch` (nie przez
    `symulacje.garch_t`), rekurencja σ² własną pętlą; ogon t_ν przez scipy.stats.t (nie `var_es_t`);
  • test zbiorczy A/B/C własnym kodem (pętle po replikacjach, rolling pandas dla grupowania);
  • FZ0 i pinball własnym wzorem; HAC przez statsmodels (nie `miara.dm.hac_variance`);
  • mnożniki par „dokładnie zerowych” przez scipy.integrate.quad + brentq (nie wzory zamknięte).
Wspólne: definicja świata (generator panelu — w trybie `panele` ten sam panel; w trybie `zbiorczo`
własny generator z docstringu garch_panel) i indeksy bootstrapu w trybie `panele`.
"""

from __future__ import annotations

import argparse
import math
import multiprocessing as mp
import os
import sys
import time

import numpy as np
import pandas as pd
import statsmodels.api as sm
from arch import arch_model
from scipy import integrate, optimize
from scipy import stats as st

RHO, NU = 0.8, 5.0
POZIOMY = (0.01, 0.05)
ALFA = 0.05
START, KROK = 400, 30

# --- ogon t_ν o wariancji 1 -------------------------------------------------------------------


def ogon_t(p: float, nu: float) -> tuple[float, float]:
    """(Q, ES) dolnego ogona innowacji t_ν znormalizowanej do wariancji 1 (scipy, wzór na ES t)."""
    s = math.sqrt((nu - 2.0) / nu)
    tp = st.t.ppf(p, nu)
    es_std = -(st.t.pdf(tp, nu) / p) * (nu + tp * tp) / (nu - 1.0)
    return s * tp, s * es_std


def ogon_t_calka(p: float, nu: float) -> tuple[float, float]:
    """To samo przez całkowanie numeryczne (sprawdzian wzoru)."""
    s = math.sqrt((nu - 2.0) / nu)
    tp = st.t.ppf(p, nu)
    calka = integrate.quad(lambda x: x * st.t.pdf(x, nu), -np.inf, tp, epsabs=1e-13, epsrel=1e-13)[
        0
    ]
    return s * tp, s * calka / p


# --- generator panelu (własny, z docstringu `garch_panel`) -------------------------------------


def gen_panel(n_days: int, k: int, seed: int, nu=NU, rho=RHO, vol=0.04, a=0.08, b=0.90, burn=500):
    rng = np.random.default_rng(seed)
    T = n_days + burn
    f = rng.standard_normal(T)
    e = rng.standard_normal((T, k))
    m = (nu - 2.0) / rng.chisquare(nu, size=(T, k))
    z = math.sqrt(rho) * f[:, None] + math.sqrt(1.0 - rho) * e
    omega = vol**2 * (1.0 - a - b)
    r = np.empty((T, k))
    s2 = np.empty((T, k))
    v = np.full(k, vol**2)
    for t in range(T):
        s2[t] = v
        r[t] = np.sqrt(v * m[t]) * z[t]
        v = omega + a * r[t] ** 2 + b * v
    return r[burn:], s2[burn:]


# --- prognozy σ̂ ---------------------------------------------------------------------------------


def sigma_okno(r: np.ndarray, w: int = 60, start: int = START) -> np.ndarray:
    T, k = r.shape
    out = np.empty((T - start, k))
    for t in range(start, T):
        out[t - start] = np.sqrt(np.mean(r[t - w : t] ** 2, axis=0))
    return out


def sigma_ewma(r: np.ndarray, lam: float = 0.94, start: int = START) -> np.ndarray:
    """v_60 = średnia r² z dni 0–59 (start dowolny: wpływ po 340 dniach to 0,94^340 ≈ 1e-9)."""
    T, k = r.shape
    v = np.mean(r[:60] ** 2, axis=0)
    out = np.empty((T - start, k))
    for t in range(60, T):
        if t > 60:
            v = lam * v + (1.0 - lam) * r[t - 1] ** 2
        if t >= start:
            out[t - start] = np.sqrt(v)
    return out


def sigma_garch_arch(r: np.ndarray, start: int = START, krok: int = KROK, backcast: str = "probka"):
    """GARCH(1,1)-t przez `arch` na rosnącym oknie r[:b], rekurencja σ² z parametrami bloku.

    backcast: "probka" = σ²_0 = średnia r² z próby dopasowania (konwencja pre-rejestracji; ta sama w
    dopasowaniu i w rekurencji), "arch" = domyślny backcast pakietu (ważona wykładniczo średnia
    pierwszych 75 kwadratów). Zwraca (σ n_oos × k, ν̂ bloki × k, persystencja, nie_zbiezne, liczba_dopasowan).
    """
    T, k = r.shape
    bloki = list(range(start, T, krok))
    sig = np.empty((T - start, k))
    nus = np.empty((len(bloki), k))
    pers, niezb = [], 0
    for ib, b in enumerate(bloki):
        e = min(b + krok, T)
        for j in range(k):
            y = r[:b, j] * 100.0
            am = arch_model(y, mean="Zero", vol="GARCH", p=1, q=1, dist="t", rescale=False)
            if backcast == "probka":
                bc = float(np.mean(y * y))
                res = am.fit(disp="off", show_warning=False, backcast=bc)
            else:
                bc = float(am.volatility.backcast(y))
                res = am.fit(disp="off", show_warning=False)
            om, al, be, nu = (float(res.params[x]) for x in ("omega", "alpha[1]", "beta[1]", "nu"))
            niezb += int(res.convergence_flag != 0)
            pers.append(al + be)
            v = bc
            yy = r[:e, j] * 100.0
            s2 = np.empty(e)
            for t in range(e):
                s2[t] = v
                v = om + al * yy[t] ** 2 + be * v
            sig[b - start : e - start, j] = np.sqrt(s2[b:e]) / 100.0
            nus[ib, j] = nu
    return sig, nus, float(np.mean(pers)), niezb, len(bloki) * k


def tail_tnu(nus: np.ndarray, p: float, n_oos: int, krok: int = KROK):
    """(Q, ES) t_ν̂ rozwinięte na dni: nus (bloki × k) → (n_oos × k)."""
    qs = np.empty_like(nus)
    es = np.empty_like(nus)
    for i in range(nus.shape[0]):
        for j in range(nus.shape[1]):
            qs[i, j], es[i, j] = ogon_t(p, nus[i, j])
    return np.repeat(qs, krok, axis=0)[:n_oos], np.repeat(es, krok, axis=0)[:n_oos]


# --- test zbiorczy A/B/C (własny) --------------------------------------------------------------


def _t_a(S: np.ndarray, mu: float) -> float:
    n = len(S)
    sd = S.std(ddof=1)
    return (S.mean() - mu) / (sd / math.sqrt(n)) if sd > 0 else float("nan")


def _t_b(S: np.ndarray, lag: int = 10) -> float:
    c = pd.Series(S - S.mean())
    a = c.shift(1).rolling(lag).mean()  # średnia c_{t-1} … c_{t-lag}
    pr = (c * a).dropna().to_numpy()
    den = math.sqrt(float((pr * pr).sum()))
    return float(pr.sum() / den) if den > 0 else float("nan")


def _t_a_vec(X: np.ndarray, mu) -> np.ndarray:
    n = X.shape[-1]
    sd = X.std(axis=-1, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return (X.mean(axis=-1) - mu) / (sd / math.sqrt(n))


def _t_b_vec(X: np.ndarray, lag: int = 10) -> np.ndarray:
    n = X.shape[-1]
    c = X - X.mean(axis=-1, keepdims=True)
    okna = np.lib.stride_tricks.sliding_window_view(c, lag, axis=-1)[..., : n - lag, :]
    a = okna.mean(axis=-1)  # a_t = średnia c_{t-lag} … c_{t-1}, t = lag … n-1
    pr = c[..., lag:] * a
    with np.errstate(divide="ignore", invalid="ignore"):
        return pr.sum(axis=-1) / np.sqrt((pr * pr).sum(axis=-1))


def _p(t_obs: float, tb: np.ndarray, strona: str) -> float:
    if not math.isfinite(t_obs):
        return float("nan")
    tb = tb[np.isfinite(tb)]
    B = len(tb)
    prawa = (1 + np.sum(tb >= t_obs)) / (B + 1)
    if strona == "prawa":
        return float(prawa)
    lewa = (1 + np.sum(tb <= t_obs)) / (B + 1)
    return float(min(1.0, 2.0 * min(prawa, lewa)))


def wklady(r, q, es, p):
    hit = r < q
    S = hit.sum(axis=1).astype(float)
    U = np.where(hit, r / (p * es), 0.0)
    d = (U - 1.0).sum(axis=1)
    return hit, S, d


def test_zbiorczy(r, q, es, p, idx, wektorowo=False):
    """Zwraca słownik statystyk i decyzji (α/3 każdy; bootstrap-t po dniach na indeksach `idx`)."""
    _, k = r.shape
    hit, S, d = wklady(r, q, es, p)
    ta, tb_, tc = _t_a(S, k * p), _t_b(S), _t_a(d, 0.0)
    mS, md = S.mean(), d.mean()
    if wektorowo:
        ta_b, tb_b, tc_b = _t_a_vec(S[idx], mS), _t_b_vec(S[idx]), _t_a_vec(d[idx], md)
    else:
        ta_b = np.empty(len(idx))
        tb_b = np.empty(len(idx))
        tc_b = np.empty(len(idx))
        for i, ix in enumerate(idx):  # pętla po replikacjach (celowo prosta)
            Sx, dx = S[ix], d[ix]
            ta_b[i] = _t_a(Sx, mS)
            tb_b[i] = _t_b(Sx)
            tc_b[i] = _t_a(dx, md)
    pa, pb, pc = _p(ta, ta_b, "rowne"), _p(tb_, tb_b, "rowne"), _p(tc, tc_b, "prawa")
    prog = ALFA / 3.0
    dec = [bool(x < prog) for x in (pa, pb, pc)]  # NaN < prog jest fałszem
    return {
        "hit": float(hit.mean()),
        "u_sr": float(1.0 + d.mean() / k),
        "vr": float(S.var(ddof=1) / (k * p * (1 - p))),
        "zb_a": float(dec[0]),
        "zb_b": float(dec[1]),
        "zb_c": float(dec[2]),
        "zb_bonf": float(any(dec)),
        "zb_a_prawa": float(dec[0] and ta > 0),
        "niezdef": float(sum(math.isnan(x) for x in (pa, pb, pc))),
        "t": (ta, tb_, tc),
        "p": (pa, pb, pc),
    }


# --- straty i DM (własne) -------------------------------------------------------------------------


def fz0_dzien(r, q, es, p):
    """Średnia po monetach z FZ0 (PZC 2019): −1/(p e)·1{r ≤ v}(v − r) + v/e + log(−e) − 1."""
    v, e = q, es
    s = -np.where(r <= v, v - r, 0.0) / (p * e) + v / e + np.log(-e) - 1.0
    return s.mean(axis=1)


def pinb_dzien(r, q, p, waga):
    s = (p - (r < q).astype(float)) * (r - q) / waga
    return s.mean(axis=1)


def dm_t_statsmodels(delta: np.ndarray, lag: int = 7) -> tuple[float, float, float]:
    """(t, średnia, se) z OLS(const) i kowariancją HAC Neweya–Westa (jądro Bartletta, lag)."""
    res = sm.OLS(delta, np.ones(len(delta))).fit(
        cov_type="HAC", cov_kwds={"maxlags": lag, "use_correction": False}
    )
    return float(res.tvalues[0]), float(res.params[0]), float(res.bse[0])


# --- mnożniki par „dokładnie zerowych” przez całkowanie numeryczne --------------------------------


def oczek_strata_calka(c: float, p: float, nu: float, strata: str) -> float:
    Q, ES = ogon_t(p, nu)
    v, e = c * Q, c * ES
    s = math.sqrt((nu - 2.0) / nu)
    f = lambda x: st.t.pdf(x / s, nu) / s  # gęstość ε o wariancji 1
    if strata == "fz0":
        ey = integrate.quad(lambda x: (v - x) * f(x), -np.inf, v, epsabs=1e-13, epsrel=1e-13)[0]
        return -ey / (p * e) + v / e + math.log(-e) - 1.0
    lewy = integrate.quad(lambda x: (p - 1.0) * (x - v) * f(x), -np.inf, v, epsabs=1e-13)[0]
    prawy = integrate.quad(lambda x: p * (x - v) * f(x), v, np.inf, epsabs=1e-13)[0]
    return lewy + prawy


def mnoznik_calka(c_a: float, p: float, nu: float, strata: str) -> float:
    cel = oczek_strata_calka(c_a, p, nu, strata)
    return float(
        optimize.brentq(lambda c: oczek_strata_calka(c, p, nu, strata) - cel, 1.0, 5.0, xtol=1e-12)
    )


# --- tryb „panele”: porównanie z kodem rejestrowym na tych samych panelach --------------------------

PROGNOZY_PAN = (
    "wyr_t5", "zan05", "zan10", "zan15", "zan20", "zan30", "okno60_t5", "ewma94_t5",
    "garch_t5", "garch_tnu", "garch_tnu_zan10", "garch_tnu_zan20",
)  # fmt: skip
ZAN = {"zan05": 0.05, "zan10": 0.10, "zan15": 0.15, "zan20": 0.20, "zan30": 0.30}


def prognozy_niezalezne(sig_wyr, sig_okno, sig_ewma, sig_garch, nus, p, n_oos, sufiks=""):
    """(q, es) każdej z `PROGNOZY_PAN` dla poziomu p (okres oceny n_oos dni); prognozy GARCH dostają
    `sufiks` w nazwie, a pozostałe są pomijane, gdy sufiks niepusty."""
    q5, e5 = ogon_t(p, NU)
    qn, en = tail_tnu(nus, p, sig_garch.shape[0])
    out = {"wyr_t5": (sig_wyr * q5, sig_wyr * e5)}
    for nazwa, x in ZAN.items():
        out[nazwa] = (sig_wyr * (1 - x) * q5, sig_wyr * (1 - x) * e5)
    out["okno60_t5"] = (sig_okno * q5, sig_okno * e5)
    out["ewma94_t5"] = (sig_ewma * q5, sig_ewma * e5)
    out["garch_t5"] = (sig_garch * q5, sig_garch * e5)
    out["garch_tnu"] = (sig_garch * qn, sig_garch * en)
    out["garch_tnu_zan10"] = (0.9 * sig_garch * qn, 0.9 * sig_garch * en)
    out["garch_tnu_zan20"] = (0.8 * sig_garch * qn, 0.8 * sig_garch * en)
    if sufiks:
        out = {k + sufiks: v for k, v in out.items() if k.startswith("garch")}
    return {k: (q[:n_oos], e[:n_oos]) for k, (q, e) in out.items()}


def jeden_panel_rejestr(arg):
    """Panel `i` z serii rejestrowej: wynik kodu rejestrowego vs wynik niezależny (C1: K = 20, n = 1600)."""
    i, ziarno = arg
    for zmienna in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(zmienna, "1")
    from symulacje import run_lv2 as R  # kod rejestrowy: tylko jako przedmiot porównania
    from symulacje.garch_panel import generuj_panel

    ss_a = np.random.SeedSequence(ziarno).spawn(i + 1)[i]
    abs_, dm, diag = R.przetworz_panel((ss_a, R.KONFIG))
    # niezależnie: ten sam panel i te same indeksy bootstrapu (świeże SeedSequence, bo spawn zmienia stan)
    ss_b = np.random.SeedSequence(ziarno).spawn(i + 1)[i]
    ss_gen, ss_boot = ss_b.spawn(2)
    panel = generuj_panel(
        R.KONFIG["n_dni"],
        R.KONFIG["k_panel"],
        seed=int(ss_gen.generate_state(1, dtype=np.uint64)[0]),
        nu=NU,
        rho=RHO,
    )
    gen = np.random.default_rng(ss_boot)
    idx = {
        n: gen.integers(0, n, size=(R.KONFIG["boot"], n))
        for n in sorted({n for _, n in R.KONFIG["komorki"]})
    }
    r_all = panel["r"].to_numpy()
    s2_all = panel["sigma2"].to_numpy()
    sig_wyr = np.sqrt(s2_all[START:])
    sig_ok, sig_ew = sigma_okno(r_all), sigma_ewma(r_all)
    sig_g, nus, pers, niezb, ndop = sigma_garch_arch(r_all)
    n = 1600
    r = r_all[START : START + n]
    wyniki = {"abs": {}, "dm": {}, "diag": (pers, niezb, ndop, float(nus.mean()))}
    straty = {}
    for ip, p in enumerate(POZIOMY):
        prog = prognozy_niezalezne(sig_wyr, sig_ok, sig_ew, sig_g, nus, p, n)
        waga = sig_ew[:n]
        straty[p] = {}
        for nazwa in PROGNOZY_PAN:
            q, es = prog[nazwa]
            wz = test_zbiorczy(r, q[:n], es[:n], p, idx[n])
            wyniki["abs"][(ip, nazwa)] = wz
            straty[p][nazwa] = {
                "fz0": fz0_dzien(r, q[:n], es[:n], p),
                "pinb": pinb_dzien(r, q[:n], p, waga),
            }
        # pary „dokładnie zerowe”: mnożnik własny (całkowanie)
        for s in ("fz0", "pinb"):
            for c_a in (0.9, 0.8):
                cb = mnoznik_calka(c_a, p, NU, s)
                q5, e5 = ogon_t(p, NU)
                qn_, en_ = sig_wyr[:n] * cb * q5, sig_wyr[:n] * cb * e5
                straty[p][f"nul_{s}_{round(100 * c_a)}"] = {
                    "fz0": fz0_dzien(r, qn_, en_, p),
                    "pinb": pinb_dzien(r, qn_, p, waga),
                }
        for por in R.POROWNANIA:
            a, b_, s = por["a"], por["b"], por["strata"]
            if a in straty[p] and b_ in straty[p]:
                delta = straty[p][a][s] - straty[p][b_][s]
                wyniki["dm"][(ip, por["kod"])] = dm_t_statsmodels(delta)
    return i, abs_, dm, diag, wyniki


def tryb_panele(args):
    ctx = mp.get_context("forkserver")
    zadania = [(i, args.ziarno) for i in range(args.M)]
    t0 = time.time()
    with ctx.Pool(args.workers) as pool:
        wyn = list(pool.imap(jeden_panel_rejestr, zadania, chunksize=1))
    print(
        f"czas: {time.time() - t0:.0f} s, panele: {args.M}, ziarno: {args.ziarno}", file=sys.stderr
    )
    from symulacje import run_lv2 as R

    print(
        f"# Porównanie kodu rejestrowego z przeliczeniem niezależnym; panele 0..{args.M - 1}, ziarno {args.ziarno}"
    )
    stat_pola = ("hit", "u_sr", "vr", "zb_a", "zb_b", "zb_c", "zb_bonf", "zb_a_prawa", "niezdef")
    print(
        "\n## Test zbiorczy (C1): maks. |różnica| hit/u_sr/vr, liczba niezgodnych decyzji (z liczby paneli × p)"
    )
    print(
        f"{'prognoza':<18}{'p':>5}{'max|Δhit|':>12}{'max|Δu_sr|':>12}{'max|Δvr|':>12}{'niezgodne A/B/C/bonf/prawa/niezdef':>40}{'odrz.rej':>10}{'odrz.nie':>10}"
    )
    for ip, p in enumerate(POZIOMY):
        for nazwa in PROGNOZY_PAN:
            roznice, rb, ib = [], [], []
            for _i, abs_, _dm, _diag, w in wyn:
                reg = abs_[0, ip, R.PROG_IDX[nazwa]]
                ind = w["abs"][(ip, nazwa)]
                roznice.append([reg[R.IDX[x]] - ind[x] for x in stat_pola])
                rb.append(reg[R.IDX["zb_bonf"]])
                ib.append(ind["zb_bonf"])
            rz = np.array(roznice)
            nz = [int(np.sum(np.abs(rz[:, k]) > 0.5)) for k in range(3, 9)]
            print(
                f"{nazwa:<18}{p:>5.2f}{np.abs(rz[:, 0]).max():>12.2e}{np.abs(rz[:, 1]).max():>12.2e}"
                f"{np.abs(rz[:, 2]).max():>12.2e}{'/'.join(map(str, nz)):>40}"
                f"{np.mean(rb):>10.3f}{np.mean(ib):>10.3f}"
            )
    print(
        "\n## DM (C1): maks. |Δt| rejestr vs statsmodels-HAC, po porównaniach z niezależnymi prognozami"
    )
    print(f"{'kod':<42}{'p':>5}{'max|Δt|':>12}{'max|Δśr|':>12}{'max|Δse|':>12}")
    for ip, p in enumerate(POZIOMY):
        for por in R.POROWNANIA:
            kod = por["kod"]
            if (ip, kod) not in wyn[0][4]["dm"]:
                continue
            dt, ds, dse = [], [], []
            for _i, _a, dm, _d, w in wyn:
                reg = dm[0, ip, R.POR_IDX[kod]]
                ind = w["dm"][(ip, kod)]
                dt.append(abs(reg[0] - ind[0]))
                ds.append(abs(reg[1] - ind[1]))
                dse.append(abs(reg[2] - ind[2]))
            print(
                f"{kod:<42}{p:>5.2f}{np.nanmax(dt):>12.2e}{np.nanmax(ds):>12.2e}{np.nanmax(dse):>12.2e}"
            )
    print("\n## Diagnostyka GARCH: kod rejestrowy vs arch (średnie po panelach)")
    reg_pers = np.mean([d[3][3] for d in wyn])
    reg_nu = np.mean([d[3][4] for d in wyn])
    ind_pers = np.mean([d[4]["diag"][0] for d in wyn])
    ind_nu = np.mean([d[4]["diag"][3] for d in wyn])
    ind_nz = np.sum([d[4]["diag"][1] for d in wyn]) / np.sum([d[4]["diag"][2] for d in wyn])
    print(
        f"persystencja: rejestr {reg_pers:.5f}, arch {ind_pers:.5f}; ν̂: rejestr {reg_nu:.4f}, arch {ind_nu:.4f}; "
        f"niezbieżne w arch: {100 * ind_nz:.3f} %"
    )
    if args.npz:
        z = np.load(args.npz)
        a_ok = all(np.array_equal(wyn[i][1], z["abs"][i], equal_nan=True) for i in range(args.M))
        d_ok = all(np.array_equal(wyn[i][2], z["dm"][i], equal_nan=True) for i in range(args.M))
        print(
            f"\n## Zgodność z zapisanym npz (panele 0..{args.M - 1}): abs identyczne co do bitu: {a_ok}; "
            f"dm identyczne co do bitu: {d_ok}; kształty abs {z['abs'].shape}, dm {z['dm'].shape}"
        )
    np.savez(args.out, ziarno=args.ziarno, M=args.M)


# --- tryb „zbiorczo”: całkiem niezależna symulacja (własny generator, własne ziarna) ---------------


def jeden_panel_zbiorczo(arg):
    j, ziarno = arg
    for zmienna in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(zmienna, "1")
    ss = np.random.SeedSequence(ziarno).spawn(j + 1)[j]
    ss_g, ss_b = ss.spawn(2)
    r_all, s2_all = gen_panel(2100, 20, seed=int(ss_g.generate_state(1, dtype=np.uint64)[0]))
    rng = np.random.default_rng(ss_b)
    n = 1600
    idx = rng.integers(0, n, size=(999, n))
    sig_wyr = np.sqrt(s2_all[START:])
    sig_ok, sig_ew = sigma_okno(r_all), sigma_ewma(r_all)
    sig_g, nus, pers, niezb, ndop = sigma_garch_arch(r_all)
    sig_g2, nus2, pers2, niezb2, _ = sigma_garch_arch(r_all, backcast="arch")
    r = r_all[START : START + n]
    wyn = {}
    for ip, p in enumerate(POZIOMY):
        prog = prognozy_niezalezne(sig_wyr, sig_ok, sig_ew, sig_g, nus, p, n)
        prog.update(
            prognozy_niezalezne(sig_wyr, sig_ok, sig_ew, sig_g2, nus2, p, n, sufiks="@arch")
        )
        for nazwa in prog:
            q, es = prog[nazwa]
            wz = test_zbiorczy(r, q[:n], es[:n], p, idx, wektorowo=True)
            wyn[(ip, nazwa)] = (wz["zb_bonf"], wz["hit"], wz["vr"])
    return wyn, (pers, niezb, ndop, float(nus.mean()), pers2, niezb2, float(nus2.mean()))


def tryb_zbiorczo(args):
    ctx = mp.get_context("forkserver")
    zadania = [(j, args.ziarno) for j in range(args.M)]
    t0 = time.time()
    with ctx.Pool(args.workers) as pool:
        wyn = list(pool.imap(jeden_panel_zbiorczo, zadania, chunksize=1))
    print(
        f"czas: {time.time() - t0:.0f} s, panele: {args.M}, ziarno: {args.ziarno}", file=sys.stderr
    )
    print(
        f"# Niezależna symulacja zbiorcza: własny generator, prognozy (arch dla GARCH), test A/B/C; "
        f"ziarno {args.ziarno}, paneli {args.M}"
    )
    print(f"{'prognoza':<18}{'p':>5}{'odrzucenia %':>14}{'SE pp':>8}{'trafienia %':>13}{'VR':>8}")
    for ip, p in enumerate(POZIOMY):
        for nazwa in (*PROGNOZY_PAN, *(k + "@arch" for k in PROGNOZY_PAN if k.startswith("garch"))):
            x = np.array([w[0][(ip, nazwa)][0] for w in wyn])
            h = np.array([w[0][(ip, nazwa)][1] for w in wyn])
            v = np.array([w[0][(ip, nazwa)][2] for w in wyn])
            se = 100 * x.std(ddof=1) / math.sqrt(len(x))
            print(
                f"{nazwa:<18}{p:>5.2f}{100 * x.mean():>14.2f}{se:>8.2f}{100 * h.mean():>13.4f}{v.mean():>8.3f}"
            )
    pers = np.mean([w[1][0] for w in wyn])
    nu = np.mean([w[1][3] for w in wyn])
    nz = np.sum([w[1][1] for w in wyn]) / np.sum([w[1][2] for w in wyn])
    print(
        f"GARCH (arch, backcast z próby): średnia persystencja {pers:.5f}, średnie ν̂ {nu:.4f}, niezbieżne {100 * nz:.3f} %"
    )
    pers2 = np.mean([w[1][4] for w in wyn])
    nu2 = np.mean([w[1][6] for w in wyn])
    nz2 = np.sum([w[1][5] for w in wyn]) / np.sum([w[1][2] for w in wyn])
    print(
        f"GARCH (arch, backcast domyślny pakietu): średnia persystencja {pers2:.5f}, średnie ν̂ {nu2:.4f}, niezbieżne {100 * nz2:.3f} %"
    )


def tryb_stale(args):
    print("# Ogon t_ν: wzór vs całkowanie numeryczne oraz mnożniki par zerowych przez całkowanie")
    for p in POZIOMY:
        for nu in (5.0, 8.0):
            a, b = ogon_t(p, nu), ogon_t_calka(p, nu)
            print(
                f"p={p:.2f} ν={nu:.0f}: Q wzór {a[0]:.10f} całka {b[0]:.10f}; ES wzór {a[1]:.10f} całka {b[1]:.10f}"
            )
    print("\nMnożniki c_B (ν = 5), całkowanie quad + brentq:")
    for p in POZIOMY:
        for s in ("fz0", "pinb"):
            print(
                f"p={p:.2f} {s:<5} c_A=0.9 → {mnoznik_calka(0.9, p, NU, s):.6f}   c_A=0.8 → {mnoznik_calka(0.8, p, NU, s):.6f}"
            )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tryb", choices=("panele", "zbiorczo", "stale"))
    ap.add_argument("--M", type=int, default=4)
    ap.add_argument("--ziarno", type=int, required=True)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--out", default="indep_out.npz")
    ap.add_argument(
        "--npz", default=None, help="tryb panele: zapisane wyniki przebiegu rejestrowego"
    )
    args = ap.parse_args()
    {"panele": tryb_panele, "zbiorczo": tryb_zbiorczo, "stale": tryb_stale}[args.tryb](args)


if __name__ == "__main__":
    main()
