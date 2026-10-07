"""Tabela kryteriów (K/P/runda) i siatka mocy do README LV2 — WYŁĄCZNIE z raw_output.txt."""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "raw_output.txt"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT.mkdir(parents=True, exist_ok=True)
linie = RAW.read_text(encoding="utf-8").splitlines()

KRYT = re.compile(r"^    (K1|K2|K7a|K7b|K7c|K7d|K-a|K-b|K4|K5|K6a|K6b|P-a|P-b)\s+(\S.*)$")
HDR_C1 = "KRYTERIA z pre-rejestracji — komórka C1"
HDR_C2 = "WARUNEK ZAKRESU (b)"
P_LINIA = re.compile(r"^ p = (\d+)%$")

dane: dict[tuple[str, int], dict] = {}
komorka = None
p = None
sekcja = None
for t in linie[:124]:
    if t.startswith(HDR_C1):
        komorka, p, sekcja = "C1", None, None
        continue
    if t.startswith(HDR_C2):
        komorka, p, sekcja = "C2", None, None
        continue
    m = P_LINIA.match(t)
    if m and komorka:
        p = int(m.group(1))
        dane[(komorka, p)] = {"krit": {}, "kryt_sek": {}, "wynik": {}, "runda": None}
        continue
    if komorka is None or p is None:
        continue
    d = dane[(komorka, p)]
    if t.startswith("  Reguła K"):
        sekcja = "K"
        continue
    if t.startswith("  Reguła P"):
        sekcja = "P"
        continue
    k = KRYT.match(t)
    if k:
        kod, reszta = k.groups()
        m2 = re.match(r"^(.*): ([\d.]+(?: %)?) — (.*)$", reszta)
        assert m2, t
        wartosc, prawa = m2.group(2).strip(), m2.group(3)
        wyn = re.search(r": (TAK|NIE)(\s|$)", prawa)
        assert wyn, t
        flaga = "w granicach 2 SE od progu" in prawa
        d["krit"][(sekcja, kod)] = (wartosc, wyn.group(1), flaga)
        continue
    w = re.match(r"^    WYNIK reguły: (\S+)$", t)
    if w:
        d["wynik"][sekcja] = w.group(1)
        continue
    r = re.match(
        r"^  REGUŁA (?:PIERWSZEJ RUNDY|RUNDY W C2)[^:]*: (\S+) — dozwolone pytania: (.*)$", t
    )
    if r:
        d["runda"] = (r.group(1), r.group(2))

assert len(dane) == 4, list(dane)
BLOKI = [("C1", 1), ("C1", 5), ("C2", 1), ("C2", 5)]
assert all(dane[b]["runda"] and set(dane[b]["wynik"]) == {"K", "P"} for b in BLOKI)


def pl(s: str) -> str:
    return s.replace(".", ",")


def kom(b, sekcja, kod) -> str:
    wart, wyn, flaga = dane[b]["krit"][(sekcja, kod)]
    return f"{pl(wart)} — {wyn}" + (" †" if flaga else "")


# K7a–d identyczne w obu regułach i we wszystkich komórkach (jedna diagnoza estymatora)
for kod in ("K7a", "K7b", "K7c", "K7d"):
    wart = {dane[b]["krit"][("K", kod)][:2] for b in BLOKI} | {
        dane[b]["krit"][("P", kod)][:2] for b in BLOKI
    }
    assert len(wart) == 1, (kod, wart)

WIERSZE = [
    ("K", "K1", "K1 — rozmiar na wyroczni (2,5–7,5 %)"),
    ("K", "K2", "K2 — moc wobec σ − 30 % (≥ 95 %)"),
    ("K", "K7a", "K7a — średnia ν̂ (4,0–6,5; prawda 5)"),
    ("K", "K7b", "K7b — średnia α̂ + β̂ (0,95–0,995; prawda 0,98)"),
    ("K", "K7c", "K7c — dopasowania bez zbieżności (≤ 2 %)"),
    ("K", "K7d", "K7d — dopasowania przy granicy zakresu (≤ 5 %)"),
    ("K", "K-a", "**K-a — rozmiar, GARCH-t estymowany (≤ 10 %)**"),
    ("K", "K-b", "**K-b — moc, GARCH-t estymowany ze σ − 10 % (≥ 80 %)**"),
    ("W", "K", "**reguła K**"),
    ("P", "K4", "K4 — rozmiar DM, pary zerowe, najgorsza (2,5–7,5 %)"),
    ("P", "K5", "K5 — moc DM, σ wyroczni − 30 % (≥ 95 %)"),
    ("P", "K6a", "K6a — rozmiar DM po wyśrodkowaniu, pary realistyczne, największy (≤ 7,5 %)"),
    ("P", "K6b", "K6b — jw., najmniejszy (≥ 2,5 %)"),
    ("P", "P-a", "**P-a — MDE zaniżenia σ, DM-FZ0 (≤ 0,10)**"),
    ("P", "P-b", "**P-b — moc DM-FZ0, ewma94 → garch_tnu (≥ 80 %)**"),
    ("W", "P", "**reguła P**"),
    ("R", "", "**reguła rundy**"),
]
w = [
    "| kryterium (próg) | C1, p = 1 % | C1, p = 5 % | C2, p = 1 % | C2, p = 5 % |",
    "|---|---:|---:|---:|---:|",
]
for sek, kod, opis in WIERSZE:
    kol = [opis]
    for b in BLOKI:
        if sek == "W":
            kol.append(f"**{dane[b]['wynik'][kod]}**")
        elif sek == "R":
            kol.append(f"**{dane[b]['runda'][0]}** ({dane[b]['runda'][1]})")
        else:
            kol.append(kom(b, sek, kod))
    w.append("| " + " | ".join(kol) + " |")
(OUT / "tab_kryteria.md").write_text("\n".join(w) + "\n", encoding="utf-8")

# --- siatka mocy ---------------------------------------------------------------------------------
i0 = next(i for i, t in enumerate(linie) if t.startswith("MOC NA SIATCE"))
blok = re.compile(r"^(C1 główna|C2 populacja F2-1b), p = (\d+)%:$")
wiersz = re.compile(
    r"^  (test zbiorczy \(wyrocznia × \(1 − x\)\)|DM-FZ0: wyrocznia × \(1 − x\) wobec wyroczni|DM-PINB: wyrocznia × \(1 − x\) wobec wyroczni)\s+((?:[\d.]+\s+){5}[\d.]+)\s+MDE ([\d.]+|>[\d.]+)$"
)
siatka = {}
cur = None
for t in linie[i0 : i0 + 40]:
    m = blok.match(t)
    if m:
        cur = ("C1" if m.group(1).startswith("C1") else "C2", int(m.group(2)))
        siatka[cur] = {}
        continue
    r = wiersz.match(t)
    if r and cur:
        siatka[cur][r.group(1)] = (r.group(2).split(), r.group(3))
assert len(siatka) == 4 and all(len(v) == 3 for v in siatka.values()), siatka
NAZ = {
    "test zbiorczy (wyrocznia × (1 − x))": "test zbiorczy",
    "DM-FZ0: wyrocznia × (1 − x) wobec wyroczni": "DM-FZ0",
    "DM-PINB: wyrocznia × (1 − x) wobec wyroczni": "DM-PINB",
}
w = [
    "| komórka | test | x = 0 (rozmiar) | 0,05 | 0,10 | 0,15 | 0,20 | 0,30 | MDE |",
    "|---|---|---:|---:|---:|---:|---:|---:|---:|",
]
for b in BLOKI:
    for klucz, (liczby, mde) in siatka[b].items():
        w.append(
            f"| {b[0]}, p = {b[1]} % | {NAZ[klucz]} | "
            + " | ".join(pl(x) for x in liczby)
            + f" | {pl(mde)} |"
        )
(OUT / "tab_siatka.md").write_text("\n".join(w) + "\n", encoding="utf-8")

# --- K6: rozmiar DM po wyśrodkowaniu, wszystkie pary realistyczne ---------------------------------
i6 = next(i for i, t in enumerate(linie) if t.startswith("OPIS (K6)"))
para6 = re.compile(r"^  (\S+) → (\S+): fz0\s+([\d.]+), pinb\s+([\d.]+)$")
k6: dict[tuple[str, int], dict[str, tuple[str, str]]] = {}
cur = None
for t in linie[i6:]:
    m = blok.match(t)
    if m:
        cur = ("C1" if m.group(1).startswith("C1") else "C2", int(m.group(2)))
        k6[cur] = {}
        continue
    r = para6.match(t)
    if r and cur:
        k6[cur][f"{r.group(1)} → {r.group(2)}"] = (r.group(3), r.group(4))
assert len(k6) == 4 and {len(v) for v in k6.values()} == {5, 6}, {b: len(v) for b, v in k6.items()}
PARY_K6 = [
    ("okno60_t5 → ewma94_t5", "okno60 → ewma94"),
    ("ewma94_t5 → garch_tnu", "ewma94 → garch_tnu (para główna P-b)"),
    ("okno60_t5 → garch_tnu", "okno60 → garch_tnu"),
    ("garch_tnu → garch_t5", "garch_tnu → garch_t5"),
    ("ewma94_t5 → har_t5", "ewma94 → har"),
    ("ewma94_t5 → ewma94_ep", "ewma94 → ewma94_ep (tylko C1)"),
]


def kom_k6(s: str) -> str:
    return f"**{pl(s)}**" if not 2.5 <= float(s) <= 7.5 else pl(s)


w = [
    "| para realistyczna (A → B) | C1, p = 1 % | C1, p = 5 % | C2, p = 1 % | C2, p = 5 % |",
    "|---|---:|---:|---:|---:|",
]
for klucz, nazwa in PARY_K6:
    kol = [nazwa]
    for b in BLOKI:
        fz0_pinb = k6[b].get(klucz)
        kol.append("—" if fz0_pinb is None else f"{kom_k6(fz0_pinb[0])} / {kom_k6(fz0_pinb[1])}")
    w.append("| " + " | ".join(kol) + " |")
(OUT / "tab_k6.md").write_text("\n".join(w) + "\n", encoding="utf-8")
print("OK: tab_kryteria.md tab_siatka.md tab_k6.md ->", OUT)
