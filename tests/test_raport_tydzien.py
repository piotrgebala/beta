"""Raport tygodniowy (007) na atrapie repo: tydzień ISO, rundy z INDEX, karty, decyzje, komentarz."""

from __future__ import annotations

from datetime import date

from raporty import tydzien as rt

INDEX = """| ID | data | katalog | opis | licznik | wynik |
|---|---|---|---|---|---|
| NC1B | 2026-09-30 | [x](x) | stara | 0 | Ready |
| F2-1 | 2026-10-05 | [y](y) | nowa | 0 | NIEMIERZALNA |
"""

STATUS = """# s

## Otwarte decyzje (z PRD §15)

- **D3** — rola F3; termin przed 2026-12-24.

## Bieżące zadania
- nie to
"""


def test_tydzien_iso():
    t = rt.tydzien_iso(date(2026, 10, 5))
    assert (t.etykieta, t.od, t.do) == ("2026-W41", date(2026, 10, 5), date(2026, 10, 11))
    assert rt.tydzien_iso(date(2026, 10, 11)).od == date(2026, 10, 5)
    assert rt.tydzien_iso(date(2021, 1, 3)).etykieta == "2020-W53"


def test_nowe_rundy_tylko_z_tygodnia():
    rows = rt.nowe_rundy(INDEX, rt.tydzien_iso(date(2026, 10, 7)))
    assert [r[0] for r in rows] == ["F2-1"] and rows[0][-1] == "NIEMIERZALNA"


def test_karty_i_decyzje(tmp_path):
    (tmp_path / "011-x.md").write_text(
        '---\nid: 011\ntytul: "krok F2"\nstatus: czeka_na_decyzje\n---\n# x\n'
    )
    (tmp_path / "007-y.md").write_text("---\nid: 007\ntytul: raport\nstatus: w_toku\n---\n")
    (tmp_path / "README.md").write_text("nie karta")
    k = rt.karty(tmp_path)
    assert [z["id"] for z in k] == ["007", "011"] and k[1]["tytul"] == "krok F2"
    assert rt.otwarte_decyzje(STATUS) == ["- **D3** — rola F3; termin przed 2026-12-24."]


def test_zbuduj_i_komentarz_przetrwa():
    t = rt.tydzien_iso(date(2026, 10, 5))
    zad = [{"id": "011", "tytul": "krok F2", "status": "czeka_na_decyzje"}]
    args = (
        [("abc1234", "2026-10-05", "F2-1: wynik")],
        rt.nowe_rundy(INDEX, t),
        zad,
        ["- **D3** — x"],
        "E ≈ 1",
    )
    txt = rt.zbuduj(t, *args, rt.komentarz(None))
    assert txt.startswith("# Raport tygodniowy 2026-W41 (2026-10-05 → 2026-10-11)")
    assert (
        "`abc1234` 2026-10-05 — F2-1: wynik" in txt
        and "| F2-1 | 2026-10-05 | 0 | NIEMIERZALNA |" in txt
    )
    assert "Zadanie 011: krok F2" in txt and "E ≈ 1" in txt and rt.KOM_PUSTY in txt
    moj = txt.replace(rt.KOM_PUSTY, "Mój komentarz.")
    txt2 = rt.zbuduj(t, *args, rt.komentarz(moj))
    assert "Mój komentarz." in txt2 and rt.KOM_PUSTY not in txt2
