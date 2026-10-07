"""Generuje tabele markdown do README LV2 WYŁĄCZNIE z raw_output.txt (bez ręcznego przepisywania).

Wypisuje też liczby pochodne (ρ_h, zapasy w SE, stosunki SD/se), żeby tekst README
korzystał z liczb policzonych, a nie z pamięci.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "raw_output.txt"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT.mkdir(parents=True, exist_ok=True)

linie = RAW.read_text(encoding="utf-8").splitlines()

BLOK = re.compile(r"^=== (C1|C2)[^:]*: K = (\d+), n = (\d+), p = (\d+)% ===$")
WIERSZ_P = re.compile(
    r"^(\S+)\s+([\d.]+)\s+([\d.]+) \|\s+([\d.]+)\s+([\d.]+)\s+([\d.]+) \|\s+([\d.]+) ± ([\d.]+) \|"
    r"\s+([\d.]+)\s+([\d.]+)$"
)
WIERSZ_DM = re.compile(
    r"^(\S+)\s+([\d.]+)\s+([\d.]+) \|\s+([+-][\d.]+)\s+([\d.]+) \|\s+([\d.]+)\s+([+-][\d.]+)$"
)

prog: dict[tuple[str, int], dict[str, dict]] = {}
dm: dict[tuple[str, int], dict[str, dict]] = {}
tryb = None
klucz = None
for t in linie:
    m = BLOK.match(t)
    if m:
        klucz = (m.group(1), int(m.group(4)))
        tryb = None
        continue
    if klucz is None:
        continue
    if t.startswith("prognoza "):
        tryb = "p"
        prog[klucz] = {}
        continue
    if t.startswith("porównanie A"):
        tryb = "dm"
        dm[klucz] = {}
        continue
    if tryb == "p":
        w = WIERSZ_P.match(t)
        if w:
            n, hit, u, a, b, c, agg, se, a0, vr = w.groups()
            prog[klucz][n] = {
                "hit": hit,
                "u": u,
                "a": a,
                "b": b,
                "c": c,
                "agg": agg,
                "se": se,
                "a0": a0,
                "vr": vr,
            }
        elif t.strip() == "" or t.startswith("  niezdef"):
            pass
    if tryb == "dm":
        w = WIERSZ_DM.match(t)
        if w:
            n, ba, ab, d, sd, se, tt = w.groups()
            dm[klucz][n] = {"ba": ba, "ab": ab, "d": d, "sd": sd, "se": se, "t": tt}

assert len(prog) == 4 and len(dm) == 4, (len(prog), len(dm))
assert all(len(v) in (16, 19) for v in prog.values()), {k: len(v) for k, v in prog.items()}
assert all(len(v) in (34, 36) for v in dm.values()), {k: len(v) for k, v in dm.items()}


def pl(s: str) -> str:
    return s.replace(".", ",")


BLOKI = [("C1", 1), ("C1", 5), ("C2", 1), ("C2", 5)]
NAZWY_P = [
    "wyr_t5",
    "zan05",
    "zan10",
    "zan15",
    "zan20",
    "zan30",
    "okno60_t5",
    "ewma94_t5",
    "garch_t5",
    "garch_tnu",
    "garch_tnu_zan10",
    "garch_tnu_zan20",
    "har_t5",
    "okno60_ep",
    "ewma94_ep",
    "garch_ep",
    "okno60_ec",
    "ewma94_ec",
    "garch_ec",
]

# --- tabela: odsetek odrzuceń testu zbiorczego po prognozach -------------------------------------
w = [
    "| prognoza | trafienia C1 p=1 % [%] | C1, p = 1 % | C1, p = 5 % | C2, p = 1 % | C2, p = 5 % |",
    "|---|---:|---:|---:|---:|---:|",
]
for n in NAZWY_P:
    kol = [n and f"`{n}`", pl(prog[("C1", 1)][n]["hit"])]
    for b in BLOKI:
        r = prog[b].get(n)
        kol.append("—" if r is None else f"{pl(r['agg'])} ± {pl(r['se'])}")
    w.append("| " + " | ".join(kol) + " |")
(OUT / "tab_agg.md").write_text("\n".join(w) + "\n", encoding="utf-8")

# --- tabela: składniki A/B/C dla wybranych prognoz, C1 -------------------------------------------
w = [
    "| prognoza | p | A (pokrycie) | B (skupienie) | C (dotkliwość) | zbiorczy |",
    "|---|---|---:|---:|---:|---:|",
]
for n in [
    "wyr_t5",
    "garch_t5",
    "garch_tnu",
    "ewma94_t5",
    "okno60_t5",
    "okno60_ep",
    "ewma94_ep",
    "har_t5",
]:
    for p in (1, 5):
        r = prog[("C1", p)][n]
        w.append(
            f"| `{n}` | {p} % | {pl(r['a'])} | {pl(r['b'])} | {pl(r['c'])} | {pl(r['agg'])} ± {pl(r['se'])} |"
        )
(OUT / "tab_abc.md").write_text("\n".join(w) + "\n", encoding="utf-8")

# --- tabela: DM, koszt estymacji i pary realistyczne (C1) ----------------------------------------
KOSZT = ["okno60_t5", "ewma94_t5", "garch_t5", "garch_tnu", "har_t5"]
PARY = [
    ("okno60_t5__ewma94_t5", "okno60 → ewma94"),
    ("ewma94_t5__garch_tnu", "ewma94 → garch_tnu (para główna P-b)"),
    ("okno60_t5__garch_tnu", "okno60 → garch_tnu"),
    ("garch_tnu__garch_t5", "garch_tnu → garch_t5"),
    ("ewma94_t5__har_t5", "ewma94 → har"),
    ("ewma94_t5__ewma94_ep", "ewma94 → ewma94_ep"),
]
w = [
    "| porównanie (strata FZ0) | p = 1 %: B lepsza / A lepsza [%] | d̄ | t | p = 5 %: B lepsza / A lepsza [%] | d̄ | t |",
    "|---|---:|---:|---:|---:|---:|---:|",
]
w.append("| **koszt estymacji** (prognoza estymowana A wobec wyroczni B) | | | | | | |")
for n in KOSZT:
    kol = [f"`{n}` wobec wyroczni"]
    for p in (1, 5):
        r = dm[("C1", p)][f"wyr_fz0_{n}"]
        kol += [f"{pl(r['ba'])} / {pl(r['ab'])}", pl(r["d"]), pl(r["t"])]
    w.append("| " + " | ".join(kol) + " |")
w.append("| **pary realistyczne** (A → B) | | | | | | |")
for k, nazwa in PARY:
    kol = [nazwa]
    for p in (1, 5):
        r = dm[("C1", p)][f"real_fz0_{k}"]
        kol += [f"{pl(r['ba'])} / {pl(r['ab'])}", pl(r["d"]), pl(r["t"])]
    w.append("| " + " | ".join(kol) + " |")
(OUT / "tab_dm.md").write_text("\n".join(w) + "\n", encoding="utf-8")

# --- tabela: pary zerowe (rozmiar DM, kierunki) --------------------------------------------------
w = [
    "| para zerowa | C1 p = 1 %: B / A [%] | C1 p = 5 %: B / A [%] | C2 p = 1 %: B / A [%] | C2 p = 5 %: B / A [%] |",
    "|---|---:|---:|---:|---:|",
]
for k in ["zero_fz0_90", "zero_pinb_90", "zero_fz0_80", "zero_pinb_80"]:
    kol = [f"`{k}`"]
    for b in BLOKI:
        r = dm[b][k]
        kol.append(f"{pl(r['ba'])} / {pl(r['ab'])}")
    w.append("| " + " | ".join(kol) + " |")
(OUT / "tab_zero.md").write_text("\n".join(w) + "\n", encoding="utf-8")

# --- liczby pochodne ----------------------------------------------------------------------------
pochodne = []


def vr(b, n):
    return float(prog[b][n]["vr"])


for c, p in BLOKI:
    k = 20 if c == "C1" else 15
    for n in ("wyr_t5", "garch_tnu"):
        v = vr((c, p), n)
        pochodne.append(f"rho_h {c} p={p}% {n}: VR {v} -> {(v - 1) / (k - 1):.4f}")

for c, p in BLOKI:
    r = prog[(c, p)]["garch_tnu"]
    agg, se = float(r["agg"]), float(r["se"])
    pochodne.append(
        f"K-a {c} p={p}%: {agg} ± {se}; zapas do 10 %: {10 - agg:.1f} pp = {(10 - agg) / se:.1f} SE; "
        f"do 7,5 %: {7.5 - agg:+.1f} pp"
    )
    kb = prog[(c, p)]["garch_tnu_zan10"]
    pochodne.append(
        f"K-b {c} p={p}%: {kb['agg']} ± {kb['se']}; zapas do 80 %: {float(kb['agg']) - 80:.1f} pp"
    )
    k1 = prog[(c, p)]["wyr_t5"]
    pochodne.append(
        f"K1 {c} p={p}%: {k1['agg']} ± {k1['se']}; do dolnej granicy 2,5: {(float(k1['agg']) - 2.5):.1f} pp = "
        f"{(float(k1['agg']) - 2.5) / float(k1['se']):.1f} SE"
    )

for c, p in BLOKI:
    for k in ("ewma94_t5__garch_tnu", "okno60_t5__ewma94_t5"):
        r = dm[(c, p)][f"real_fz0_{k}"]
        sd, se, d = float(r["sd"]), float(r["se"]), float(r["d"].replace("+", ""))
        z = d / sd
        moc_b = 0.5 * math.erfc((1.959964 - z) / math.sqrt(2) * -1) if False else None
        # P(z_norm > 1,96 − d/SD) przy dokładnym se = SD
        from math import erf, sqrt

        def sf(x):
            return 0.5 * (1 - erf(x / sqrt(2)))

        pochodne.append(
            f"HAC {c} p={p}% {k}: SD/se = {sd / se:.3f}; d̄/SD = {z:.3f}; orient. moc (norm., se=SD) "
            f"= {100 * sf(1.959964 - z):.0f} %; moc zmierzona B>A = {r['ba']} %"
        )

for c, p in BLOKI:
    r = dm[(c, p)]["moc_fz0_zan10"]
    pochodne.append(
        f"P-a {c} p={p}%: moc DM-FZ0 przy x=0,10: {r['ba']} % (80 − {float(r['ba']):.1f} = {80 - float(r['ba']):.1f} pp; "
        f"SE ≈ {100 * math.sqrt(float(r['ba']) / 100 * (1 - float(r['ba']) / 100) / 5000):.2f} pp)"
    )

for c, p in BLOKI:
    a = float(prog[(c, p)]["garch_tnu"]["agg"])
    g5 = float(prog[(c, p)]["garch_t5"]["agg"])
    w0 = float(prog[(c, p)]["wyr_t5"]["agg"])
    pochodne.append(
        f"rozbicie nadwyżki {c} p={p}%: wyrocznia {w0} -> garch_t5 {g5} (+{g5 - w0:.1f}, σ̂) -> garch_tnu {a} (+{a - g5:.1f}, ν̂)"
    )

(OUT / "pochodne.txt").write_text("\n".join(pochodne) + "\n", encoding="utf-8")
print("\n".join(pochodne))
print("OK: tab_agg.md tab_abc.md tab_dm.md tab_zero.md pochodne.txt ->", OUT)
