"""Niezależne zestawienie kryteriów LV2 z zapisanych wyników paneli (npz) — krok 4, punkt iii.

Kryteria, kontrole i reguły są zaprogramowane NA NOWO z tekstu pre-rejestracji
(README rundy, sekcje „Kryteria” i „Reguła decyzji”), bez użycia ocen_k / ocen_p / liczby_k /
krzywa_dm / _werdykt z run_lv2. Z repo importowane są wyłącznie LISTY NAZW (kolejność osi tablic);
poprawność tej kolejności sprawdza porównanie z wydrukiem (całe tabele OPIS).

Wejście: data/lv2_wyniki_paneli.npz (zapis przebiegu rejestrowego) oraz raw_output.txt.
Wyjście: (1) tabela zgodności wszystkich liczb z wydruku, (2) kryteria i reguły przeliczone od zera.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from symulacje import run_lv2 as R  # tylko listy nazw

NPZ = sys.argv[1] if len(sys.argv) > 1 else str(REPO / "data" / "lv2_wyniki_paneli.npz")
RAW = (
    sys.argv[2]
    if len(sys.argv) > 2
    else str(REPO / "runs" / "2026-10-07_lv2-var-es-estymowane" / "raw_output.txt")
)

Z = 1.959964
z = np.load(NPZ)
A, D, G = z["abs"], z["dm"], z["diag"]
B = A.shape[0]
NAZWY = list(R.PROGNOZY)
FI = {n: i for i, n in enumerate(NAZWY)}
SI = {s: i for i, s in enumerate(R.STAT)}
KODY = [c["kod"] for c in R.POROWNANIA]
CI = {k: i for i, k in enumerate(KODY)}
POZ = (0.01, 0.05)
KOMORKI = {0: "C1 główna: K = 20, n = 1600", 1: "C2 populacja F2-1b: K = 15, n = 1700"}
assert A.shape[1:4] == (2, 2, len(NAZWY)) and D.shape[1:4] == (2, 2, len(KODY)), (A.shape, D.shape)
print(f"npz: {NPZ}\npaneli {B}, prognoz {len(NAZWY)}, porównań {len(KODY)}\n")


# --- agregaty z surowych tablic (własne) ----------------------------------------------------------
def stat(ic, ip, nazwa, s):
    return A[:, ic, ip, FI[nazwa], SI[s]]


def odsetek(ic, ip, nazwa, s):
    v = stat(ic, ip, nazwa, s)
    assert not np.isnan(v).any(), ("NaN w", ic, ip, nazwa, s)
    m = float(v.mean())
    return m, float(np.sqrt(m * (1 - m) / B))


def dm(ic, ip, kod, k):  # k: 0 = t, 1 = d̄, 2 = se
    return D[:, ic, ip, CI[kod], k]


def dm_odsetek(ic, ip, kod, rodzaj):
    t = dm(ic, ip, kod, 0)
    assert not np.isnan(t).any() and np.isfinite(t).all(), ("brak/NaN w t DM", ic, ip, kod)
    cond = {"prawa": t > Z, "lewa": t < -Z, "dwu": np.abs(t) > Z}[rodzaj]
    m = float(cond.mean())
    return m, float(np.sqrt(m * (1 - m) / B))


def dm_wysrodkowany(ic, ip, kod):
    d, se = dm(ic, ip, kod, 1), dm(ic, ip, kod, 2)
    tc = (d - d.mean()) / se
    m = float((np.abs(tc) > Z).mean())
    return m, float(np.sqrt(m * (1 - m) / B))


# --- 1. zgodność z wydrukiem: cała tabela OPIS (prognozy) i tabela DM ----------------------------
tekst = Path(RAW).read_text(encoding="utf-8").split("\n")
bloki = []  # (rodzaj, komórka, p, [wiersze])
i = 0
while i < len(tekst):
    m = re.match(r"=== (C[12]) .*: K = (\d+), n = (\d+), p = (\d+)% ===", tekst[i])
    if m:
        nag = tekst[i + 1]
        rodzaj = (
            "prog" if nag.startswith("prognoza") else "dm" if nag.startswith("porównanie") else "?"
        )
        ic = int(m.group(1)[1]) - 1
        ip = 0 if m.group(4) == "1" else 1
        wiersze = []
        j = i + 2
        while j < len(tekst) and tekst[j].strip() and not tekst[j].strip().startswith("niezdef"):
            wiersze.append(tekst[j])
            j += 1
        bloki.append((rodzaj, ic, ip, wiersze))
        i = j
    i += 1
print(
    f"bloki tabel w wydruku: {len(bloki)} ({sum(1 for b in bloki if b[0] == 'prog')} prognoz, "
    f"{sum(1 for b in bloki if b[0] == 'dm')} DM)"
)

liczby = r"[-+]?\d+\.\d+"
n_por = n_zle = 0
max_jedn = 0.0
niezgodne = []


def porownaj(opis, moje, wydruk, dec):
    global n_por, n_zle, max_jedn
    n_por += 1
    jedn = 10.0 ** (-dec)
    roz = abs(moje - wydruk) / jedn
    max_jedn = max(max_jedn, roz)
    if roz > 0.5 + 1e-6:
        n_zle += 1
        niezgodne.append((opis, moje, wydruk))


for rodzaj, ic, ip, wiersze in bloki:
    for w in wiersze:
        nazwa = w.split()[0]
        reszta = w[len(nazwa) :]
        wart = [float(x) for x in re.findall(liczby, reszta)]
        etyk = f"[{KOMORKI[ic][:2]} p={POZ[ip]:.2f}] {nazwa}"
        if rodzaj == "prog":
            # hit U | A B C | zbiorczy ± SE | A>0 VR
            hit, u, a, b, c, zb, se, apr, vr = wart
            porownaj(etyk + " hit", 100 * float(stat(ic, ip, nazwa, "hit").mean()), hit, 2)
            porownaj(etyk + " U", float(stat(ic, ip, nazwa, "u_sr").mean()), u, 3)
            for s, v, nm in (
                ("zb_a", a, "A"),
                ("zb_b", b, "B"),
                ("zb_c", c, "C"),
                ("zb_bonf", zb, "zbiorczy"),
                ("zb_a_prawa", apr, "A>0"),
            ):
                porownaj(etyk + " " + nm, 100 * odsetek(ic, ip, nazwa, s)[0], v, 1)
            porownaj(etyk + " SE", 100 * odsetek(ic, ip, nazwa, "zb_bonf")[1], se, 2)
            porownaj(etyk + " VR", float(stat(ic, ip, nazwa, "vr").mean()), vr, 2)
        elif rodzaj == "dm":
            ba, ab, dbar, sd, se, t = wart
            porownaj(etyk + " B>A", 100 * dm_odsetek(ic, ip, nazwa, "prawa")[0], ba, 1)
            porownaj(etyk + " A>B", 100 * dm_odsetek(ic, ip, nazwa, "lewa")[0], ab, 1)
            porownaj(etyk + " d̄", float(dm(ic, ip, nazwa, 1).mean()), dbar, 5)
            porownaj(etyk + " SD", float(dm(ic, ip, nazwa, 1).std(ddof=1)), sd, 5)
            porownaj(etyk + " se", float(dm(ic, ip, nazwa, 2).mean()), se, 5)
            porownaj(etyk + " t", float(dm(ic, ip, nazwa, 0).mean()), t, 2)

print(
    f"\nPORÓWNANIE Z WYDRUKIEM (tabele OPIS): porównanych liczb {n_por}, "
    f"niezgodnych (> pół jednostki ostatniej cyfry) {n_zle}, "
    f"maks. różnica = {max_jedn:.2f} jednostki ostatniej cyfry"
)
for o, m, w in niezgodne[:40]:
    print(f"  NIEZGODNE: {o}: moje {m:.6f}, wydruk {w}")

# VR ± SE z linii „VR dziennej sumy trafień”
vr_linie = [
    (m.group(1), float(m.group(2)), float(m.group(3)))
    for m in (
        re.match(r"\s+VR dziennej sumy trafień, (\w+): ([\d.]+) ± ([\d.]+)", ln) for ln in tekst
    )
    if m
]
print(f"\nLinie VR w wydruku: {len(vr_linie)} (kolejność C1 p=1,5; C2 p=1,5 × wyr_t5, garch_tnu)")
k = 0
for ic in (0, 1):
    for ip in (0, 1):
        for nazwa in ("wyr_t5", "garch_tnu"):
            v = stat(ic, ip, nazwa, "vr")
            nz, mv, ms = vr_linie[k]
            assert nz == nazwa
            ok = abs(v.mean() - mv) < 0.0051 and abs(v.std(ddof=1) / np.sqrt(B) - ms) < 0.0051
            print(
                f"  {KOMORKI[ic][:2]} p={POZ[ip]} {nazwa}: moje {v.mean():.3f} ± "
                f"{v.std(ddof=1)/np.sqrt(B):.3f}, wydruk {mv} ± {ms}: {'OK' if ok else 'NIEZGODNE'}"
            )
            k += 1

# --- 2. kryteria i reguły od zera (z tekstu pre-rejestracji) --------------------------------------
PARY_REALNE = [
    ("okno60_t5", "ewma94_t5"),
    ("ewma94_t5", "garch_tnu"),
    ("okno60_t5", "garch_tnu"),
    ("garch_tnu", "garch_t5"),
    ("ewma94_t5", "har_t5"),
    ("ewma94_t5", "ewma94_ep"),
]
X = [0.0, 0.05, 0.10, 0.15, 0.20, 0.30]
ZAN = ["zan05", "zan10", "zan15", "zan20", "zan30"]


def blisko(v, prog, se):
    return abs(v - prog) < 2 * se


def wynik_k7():
    dop, nz, br, pers, nu = (G[:, j] for j in range(5))
    return {
        "K7a": (float(nu.mean()), 4.0 <= nu.mean() <= 6.5),
        "K7b": (float(pers.mean()), 0.95 <= pers.mean() <= 0.995),
        "K7c": (float((nz / dop).mean()), (nz / dop).mean() <= 0.02),
        "K7d": (float((br / dop).mean()), (br / dop).mean() <= 0.05),
    }


def mde(moc):
    sm = np.maximum.accumulate(np.asarray(moc))
    if sm[0] >= 0.8:
        return 0.0
    for j in range(1, len(X)):
        if sm[j] >= 0.8:
            return X[j - 1] + (X[j] - X[j - 1]) * (0.8 - sm[j - 1]) / (sm[j] - sm[j - 1])
    return None


def werdykt(kontrole, kryteria):
    """kontrole: {kod: (ok, bramka, dotyczy)}; kryteria: {kod: ok}. bramka: obie|TAK|NIE; dotyczy: None|zbiór."""
    if all(kryteria.values()):
        return (
            "TAK"
            if all(ok for ok, br, _ in kontrole.values() if br in ("obie", "TAK"))
            else "WSTRZYMANE"
        )
    for c, ok_c in kryteria.items():
        if ok_c:
            continue
        rel = [
            ok
            for ok, br, dot in kontrole.values()
            if br in ("obie", "NIE") and (dot is None or c in dot)
        ]
        if all(rel):
            return "NIE"
    return "WSTRZYMANE"


def oceń(ic, ip):
    wyn, flagi = {}, []
    k7 = wynik_k7()
    # reguła K
    kk = {}
    v, se = odsetek(ic, ip, "wyr_t5", "zb_bonf")
    kk["K1"] = (0.025 <= v <= 0.075, "obie", None)
    wyn["K1"] = v
    if blisko(v, 0.025, se) or blisko(v, 0.075, se):
        flagi.append("K1")
    v, se = odsetek(ic, ip, "zan30", "zb_bonf")
    kk["K2"] = (v >= 0.95, "obie", None)
    wyn["K2"] = v
    for kod, (val, ok) in k7.items():
        kk[kod] = (ok, "obie", None)
        wyn[kod] = val
    va, sea = odsetek(ic, ip, "garch_tnu", "zb_bonf")
    vb, seb = odsetek(ic, ip, "garch_tnu_zan10", "zb_bonf")
    wyn["K-a"], wyn["K-b"] = va, vb
    if blisko(va, 0.10, sea):
        flagi.append("K-a")
    if blisko(vb, 0.80, seb):
        flagi.append("K-b")
    wk = werdykt(kk, {"K-a": va <= 0.10, "K-b": vb >= 0.80})
    # reguła P
    pp = {}
    zero = {
        (s, c): dm_odsetek(ic, ip, f"zero_{s}_{c}", "dwu")[0]
        for s in ("fz0", "pinb")
        for c in (90, 80)
    }
    najgorszy = max(zero, key=lambda key: abs(zero[key] - 0.05))
    v4 = zero[najgorszy]
    pp["K4"] = (0.025 <= v4 <= 0.075, "obie", {"P-a", "P-b"})
    wyn["K4"] = (v4, najgorszy)
    if blisko(v4, 0.025, np.sqrt(v4 * (1 - v4) / B)) or blisko(
        v4, 0.075, np.sqrt(v4 * (1 - v4) / B)
    ):
        flagi.append("K4")
    v5, _ = dm_odsetek(ic, ip, "moc_fz0_zan30", "prawa")
    pp["K5"] = (v5 >= 0.95, "obie", {"P-a", "P-b"})
    wyn["K5"] = v5
    pary = PARY_REALNE if ic == 0 else PARY_REALNE[:5]
    rozm = {f"{a}→{b}": dm_wysrodkowany(ic, ip, f"real_fz0_{a}__{b}") for a, b in pary}
    kmax = max(rozm, key=lambda q: rozm[q][0])
    kmin = min(rozm, key=lambda q: rozm[q][0])
    v6a, se6a = rozm[kmax]
    v6b, se6b = rozm[kmin]
    pp["K6a"] = (v6a <= 0.075, "TAK", {"P-b"})
    wyn["K6a"] = (v6a, kmax)
    pp["K6b"] = (v6b >= 0.025, "NIE", {"P-b"})
    wyn["K6b"] = (v6b, kmin)
    if blisko(v6a, 0.075, se6a):
        flagi.append("K6a")
    if blisko(v6b, 0.025, se6b):
        flagi.append("K6b")
    for kod, (val, ok) in k7.items():
        pp[kod] = (ok, "obie", {"P-b"})
    moc_dm = [float(dm_odsetek(ic, ip, f"zero_fz0_{c}", "dwu")[0]) for c in (90, 80)]
    krzywa = [float(np.mean(moc_dm))] + [
        dm_odsetek(ic, ip, f"moc_fz0_{n}", "prawa")[0] for n in ZAN
    ]
    mdp = mde(krzywa)
    pa = mdp is not None and mdp <= 0.10
    a, b = "ewma94_t5", "garch_tnu"
    vpb, sepb = dm_odsetek(ic, ip, f"real_fz0_{a}__{b}", "prawa")
    wyn["P-a"], wyn["P-b"] = mdp, vpb
    if blisko(vpb, 0.80, sepb):
        flagi.append("P-b")
    wp = werdykt(pp, {"P-a": pa, "P-b": vpb >= 0.80})
    runda = (
        "MIERZALNA"
        if "TAK" in (wk, wp)
        else "WSTRZYMANA" if "WSTRZYMANE" in (wk, wp) else "NIEMIERZALNA"
    )
    return wyn, wk, wp, runda, krzywa, flagi, rozm


def f(v):
    if isinstance(v, tuple):
        return f"{100*v[0]:.1f} %" if isinstance(v[0], float) and v[0] <= 1.5 else str(v)
    return "—" if v is None else f"{v:.4g}"


print("\n" + "=" * 100)
print("KRYTERIA I REGUŁY PRZELICZONE OD ZERA Z npz (kod własny, z tekstu pre-rejestracji)")
for ic in (0, 1):
    for ip in (0, 1):
        wyn, wk, wp, runda, krzywa, flagi, rozm = oceń(ic, ip)
        print(f"\n{KOMORKI[ic]}, p = {POZ[ip]:.0%}")
        print(
            f"  K1 {100*wyn['K1']:.1f} %  K2 {100*wyn['K2']:.1f} %  K7a {wyn['K7a']:.3f}  K7b {wyn['K7b']:.4f}  "
            f"K7c {100*wyn['K7c']:.2f} %  K7d {100*wyn['K7d']:.2f} %"
        )
        print(f"  K-a {100*wyn['K-a']:.1f} %  K-b {100*wyn['K-b']:.1f} %  → reguła K: {wk}")
        print(f"  K4 {100*wyn['K4'][0]:.1f} % (najgorsza {wyn['K4'][1]})  K5 {100*wyn['K5']:.1f} %")
        print(
            f"  K6a {100*wyn['K6a'][0]:.1f} % ({wyn['K6a'][1]})  K6b {100*wyn['K6b'][0]:.1f} % ({wyn['K6b'][1]})"
        )
        print(
            "  K6 wszystkie pary (FZ0): "
            + "; ".join(f"{q} {100*v[0]:.1f}" for q, v in rozm.items())
        )
        print(
            f"  P-a MDE {wyn['P-a']:.3f}  P-b {100*wyn['P-b']:.1f} %  (krzywa DM-FZ0: "
            + " / ".join(f"{100*x:.1f}" for x in krzywa)
            + f")  → reguła P: {wp}"
        )
        print(f"  RUNDA: {runda}   flagi „w granicach 2 SE od progu”: {flagi if flagi else 'brak'}")

# W1–W4 (opis, nie kryteria)
print("\nPRZEWIDYWANIA (liczone od zera):")
for ip in (0, 1):
    w1 = min(odsetek(0, ip, n, "zb_bonf")[0] for n in ("okno60_t5", "ewma94_t5"))
    f_okno = float(dm(0, ip, "wyr_fz0_okno60_t5", 1).mean())
    f_ewma = float(dm(0, ip, "wyr_fz0_ewma94_t5", 1).mean())
    f_gar = float(dm(0, ip, "wyr_fz0_garch_tnu", 1).mean())
    _, wk, wp, _, krzywa, _, _ = oceń(0, ip)
    mdp = mde(krzywa)
    pb = dm_odsetek(0, ip, "real_fz0_ewma94_t5__garch_tnu", "prawa")[0]
    print(
        f"  p={POZ[ip]:.0%}: W1 min odrzuceń {w1:.3f} (≥ 0,70: {w1 >= 0.70}); "
        f"W2 FZ0 ponad wyrocznię okno {f_okno:.4f} > ewma {f_ewma:.4f} > garch_tnu {f_gar:.4f}: "
        f"{f_okno > f_ewma > f_gar} (okno − garch = {f_okno - f_gar:.3f}); "
        f"W3 MDE {mdp:.3f} > 0,10: {mdp > 0.10}; W4 P-b {pb:.3f} < 0,80: {pb < 0.80}"
    )
