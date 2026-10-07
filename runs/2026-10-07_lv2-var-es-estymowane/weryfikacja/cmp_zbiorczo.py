"""Porównanie: rejestr (C1, 5000 paneli) vs niezależna symulacja zbiorcza (M = 400, ziarno 424242).

Dane wejściowe: raw_output.txt (bloki C1) i zbiorczo_M400_output.txt. Liczy z-score różnicy
z SE pod hipotezą „prawdziwa wartość = rejestrowa" (SE niezależnego = sqrt(p(1-p)/M), a nie z próby,
żeby 100 % nie dawało SE = 0), oraz dokładne p dwustronne (dwumian) dla wartości przy brzegu.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

from scipy import stats

KATALOG = Path(__file__).resolve().parent
RAW = KATALOG.parent / "raw_output.txt"
IND = KATALOG / "zbiorczo_M400_output.txt"
M = 400

BLOK = re.compile(r"^=== (C1|C2)[^:]*: K = (\d+), n = (\d+), p = (\d+)% ===$")
WIERSZ_P = re.compile(
    r"^(\S+)\s+([\d.]+)\s+([\d.]+) \|\s+([\d.]+)\s+([\d.]+)\s+([\d.]+) \|\s+([\d.]+) ± ([\d.]+) \|"
    r"\s+([\d.]+)\s+([\d.]+)$"
)
reg: dict[tuple[int, str], tuple[float, float, float, float]] = {}
klucz = None
tryb = None
for t in RAW.read_text(encoding="utf-8").splitlines():
    m = BLOK.match(t)
    if m:
        klucz = (m.group(1), int(m.group(4)))
        tryb = None
        continue
    if klucz is None or klucz[0] != "C1":
        continue
    if t.startswith("prognoza "):
        tryb = "p"
        continue
    if t.startswith("porównanie A"):
        tryb = None
    if tryb == "p":
        w = WIERSZ_P.match(t)
        if w:
            n, hit, u, a, b, c, agg, se, a0, vr = w.groups()
            reg[(klucz[1], n)] = (float(agg), float(se), float(hit), float(vr))

ind: dict[tuple[int, str], tuple[float, float, float, float]] = {}
for t in IND.read_text(encoding="utf-8").splitlines():
    p = t.split()
    if len(p) == 6 and p[1] in ("0.01", "0.05"):
        nazwa, pp, odrz, se, hit, vr = p
        ind[(round(float(pp) * 100), nazwa)] = (float(odrz), float(se), float(hit), float(vr))

wiersze = []
print(
    f"{'prognoza':<22}{'p':>3} {'rejestr %':>11} {'niezal. %':>10} {'Δ pp':>7} {'SE_Δ pp':>8} {'z':>6} {'p dokł.':>9}"
)
nz = 0
zs = []
for (p, nazwa), (od, se, hit, vr) in sorted(
    ind.items(), key=lambda x: (x[0][0], list(ind).index(x[0]))
):
    base = nazwa.replace("@arch", "")
    if "@arch" in nazwa:
        continue
    if (p, base) not in reg:
        continue
    r_od, r_se, r_hit, r_vr = reg[(p, base)]
    pr = r_od / 100
    se_ind = math.sqrt(max(pr * (1 - pr), 1e-12) / M) * 100
    se_d = math.sqrt(se_ind**2 + r_se**2)
    d = od - r_od
    z = d / se_d if se_d > 1e-9 else float("nan")
    k = round(od / 100 * M)
    pe = stats.binomtest(k, M, min(max(pr, 1e-9), 1 - 1e-9)).pvalue if 0 < pr < 1 else float("nan")
    print(
        f"{nazwa:<22}{p:>3} {r_od:>11.2f} {od:>10.2f} {d:>+7.2f} {se_d:>8.2f} {z:>+6.2f} {pe:>9.3f}"
    )
    if not math.isnan(z):
        zs.append(z)
        nz += abs(z) > 2

print(
    f"\nwierszy z określonym z: {len(zs)}; |z| > 2: {nz}; średnie z {sum(zs)/len(zs):+.2f}; Σz² = {sum(z*z for z in zs):.1f}"
)
print("(wiersze tej samej próby paneli są skorelowane, więc Σz² to opis, nie test)")

print(
    "\nKonwencja startu GARCH (te same panele): pre-rejestracja (σ²_0 = średnia r² próby) vs domyślny backcast `arch`"
)
for p in (1, 5):
    for n in ("garch_t5", "garch_tnu", "garch_tnu_zan10", "garch_tnu_zan20"):
        a, b = ind[(p, n)], ind[(p, n + "@arch")]
        print(
            f"  p={p}% {n:<18} pre-rej. {a[0]:>6.2f} ± {a[1]:.2f}   arch-domyślny {b[0]:>6.2f} ± {b[1]:.2f}   Δ {b[0] - a[0]:+.2f} pp"
        )

print("\nTrafienia i VR (rejestr → niezależnie):")
for p in (1, 5):
    for n in ("wyr_t5", "okno60_t5", "ewma94_t5", "garch_t5", "garch_tnu", "zan30"):
        r = reg[(p, n)]
        i = ind[(p, n)]
        print(f"  p={p}% {n:<12} trafienia {r[2]:.2f} → {i[2]:.3f} %   VR {r[3]:.2f} → {i[3]:.3f}")
sys.exit(0)
