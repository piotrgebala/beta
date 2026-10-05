"""
tydzien.py — zadanie 007 (FR-40): raport tygodniowy, jedna strona prostym językiem.

Generator składa FAKTY z repo: commity tygodnia, nowe wiersze `runs/INDEX.md`, statusy kart `zadania/`,
otwarte decyzje ze `STATUS.md`, stan dziennika alpha (`dowody.raport`). Zdania „co z tego wynika”, karty
decyzji i plan pisze Claude w bloku komentarza (R14: skrypt jest neutralnym reporterem) — przy ponownym
generowaniu blok zostaje nietknięty.

    python -m raporty.tydzien                 # bieżący tydzień ISO (UTC)
    python -m raporty.tydzien --data 2026-10-05
"""

from __future__ import annotations

import argparse
import contextlib
import io
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "raporty" / "tygodnie"
KOM_START, KOM_KONIEC = "<!-- komentarz -->", "<!-- /komentarz -->"
KOM_PUSTY = (
    "_(Claude: 3–5 zdań — co się wydarzyło i co z tego wynika; karty decyzji: pytanie, opcje, "
    "rekomendacja, ścieżka odwrotu; plan na następny tydzień.)_"
)
KOLEJNOSC = ("czeka_na_decyzje", "do_przegladu", "w_toku", "nowe", "zrobione", "odrzucone")


@dataclass(frozen=True)
class Tydzien:
    rok: int
    nr: int
    od: date  # poniedziałek
    do: date  # niedziela

    @property
    def etykieta(self) -> str:
        return f"{self.rok}-W{self.nr:02d}"


def tydzien_iso(d: date) -> Tydzien:
    rok, nr, dzien = d.isocalendar()
    od = d - timedelta(days=dzien - 1)
    return Tydzien(rok, nr, od, od + timedelta(days=6))


def commity(t: Tydzien, repo: Path = ROOT) -> list[tuple[str, str, str]]:
    """(hash, data, temat) commitów z tygodnia, od najstarszego."""
    out = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "log",
            "--reverse",
            f"--since={t.od.isoformat()} 00:00:00",
            f"--until={t.do.isoformat()} 23:59:59",
            "--date=short",
            "--format=%h%x09%ad%x09%s",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [tuple(line.split("\t", 2)) for line in out.splitlines() if line.strip()]


def nowe_rundy(index_md: str, t: Tydzien) -> list[list[str]]:
    """Wiersze tabeli rund (`| ID | data | ...`) z datą w tygodniu."""
    rows = []
    for line in index_md.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        jest_data = len(cells) >= 6 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[1])
        if jest_data and t.od <= date.fromisoformat(cells[1]) <= t.do:
            rows.append(cells)
    return rows


def karty(zadania_dir: Path) -> list[dict]:
    """Front matter kart `NNN-*.md`: id, tytul, status."""
    out = []
    for p in sorted(zadania_dir.glob("[0-9][0-9][0-9]-*.md")):
        txt = p.read_text(encoding="utf-8")
        m = re.match(r"---\n(.*?)\n---", txt, re.DOTALL)
        if not m:
            continue
        linie = [line.split(":", 1) for line in m.group(1).splitlines() if ":" in line]
        pola = {k.strip(): v.strip().strip('"') for k, v in linie}
        out.append(
            {
                "id": pola.get("id", p.name[:3]),
                "tytul": pola.get("tytul", ""),
                "status": pola.get("status", "?"),
            }
        )
    return out


def otwarte_decyzje(status_md: str) -> list[str]:
    """Punkty z sekcji „## Otwarte decyzje” w STATUS.md."""
    m = re.search(
        r"^## Otwarte decyzje[^\n]*\n(.*?)(?=^## |\Z)", status_md, re.DOTALL | re.MULTILINE
    )
    if not m:
        return []
    return [line for line in m.group(1).splitlines() if line.startswith("- ")]


def dziennik_alpha() -> str:
    """Wydruk reportera F3 (`dowody.raport`) albo informacja, czemu go nie ma."""
    from dowody import raport

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            raport.main([])
    except (OSError, ValueError, KeyError) as e:
        return f"(reporter F3 niedostępny: {type(e).__name__}: {e})"
    return buf.getvalue().rstrip()


def komentarz(stary: str | None) -> str:
    """Blok komentarza Claude z poprzedniej wersji pliku albo pusty szablon."""
    if stary and KOM_START in stary and KOM_KONIEC in stary:
        return stary[stary.index(KOM_START) : stary.index(KOM_KONIEC) + len(KOM_KONIEC)]
    return f"{KOM_START}\n{KOM_PUSTY}\n{KOM_KONIEC}"


def zbuduj(
    t: Tydzien,
    commits: list[tuple[str, str, str]],
    rundy: list[list[str]],
    zadania: list[dict],
    decyzje: list[str],
    dziennik: str,
    kom: str,
) -> str:
    L = [
        f"# Raport tygodniowy {t.etykieta} ({t.od} → {t.do})",
        "",
        "## W skrócie",
        "",
        kom,
        "",
        "## 1. Co się zmieniło",
        "",
        f"**Commity:** {len(commits)}.",
        "",
    ]
    L += [f"- `{h}` {d} — {s}" for h, d, s in commits] or ["- (brak)"]
    L += ["", f"**Rundy w tym tygodniu:** {len(rundy)}.", ""]
    if rundy:
        L += ["| ID | data | licznik | wynik |", "|---|---|---|---|"]
        L += [f"| {r[0]} | {r[1]} | {r[-2]} | {r[-1]} |" for r in rundy]
    else:
        L += ["- (brak)"]
    L += ["", "**Zadania według statusu:**", ""]
    po = {s: [z for z in zadania if z["status"] == s] for s in KOLEJNOSC}
    inne = [z for z in zadania if z["status"] not in KOLEJNOSC]
    for s, lista in [*po.items(), ("inne", inne)]:
        if lista:
            L.append(f"- `{s}`: " + "; ".join(f"{z['id']} {z['tytul']}" for z in lista))
    L += [
        "",
        "## 2. Dziennik alpha (reporter F3 — opis, nie wiąże)",
        "",
        "```",
        dziennik,
        "```",
        "",
    ]
    L += ["## 3. Decyzje czekające na Ciebie", ""]
    L += decyzje or ["- (brak otwartych decyzji w STATUS.md)"]
    czeka = po["czeka_na_decyzje"]
    L += [f"- Zadanie {z['id']}: {z['tytul']} (karta w `zadania/`)" for z in czeka]
    if po["do_przegladu"]:
        L.append("- Do przeglądu: " + ", ".join(z["id"] for z in po["do_przegladu"]))
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Raport tygodniowy (FR-40).")
    ap.add_argument("--data", type=date.fromisoformat, default=datetime.now(UTC).date())
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    a = ap.parse_args(argv)
    t = tydzien_iso(a.data)
    path = a.out / f"{t.etykieta}.md"
    stary = path.read_text(encoding="utf-8") if path.is_file() else None
    txt = zbuduj(
        t,
        commity(t),
        nowe_rundy((ROOT / "runs" / "INDEX.md").read_text(encoding="utf-8"), t),
        karty(ROOT / "zadania"),
        otwarte_decyzje((ROOT / "STATUS.md").read_text(encoding="utf-8")),
        dziennik_alpha(),
        komentarz(stary),
    )
    a.out.mkdir(parents=True, exist_ok=True)
    path.write_text(txt, encoding="utf-8")
    print(f"raport: {path}")


if __name__ == "__main__":
    main()
