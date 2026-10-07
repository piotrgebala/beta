"""
pomiar_rho_h.py — karta 017: zależność trafień VaR 5 % między monetami (ρ_h), BEZ oceny prognozy.

Pre-rejestracja: `runs/2026-10-07_017-inwentarz-i-rho/README.md` (zapisana przed przebiegiem). Neutralny
reporter (R14): drukuje inwentarz, okno, VR, ρ̂, SE i wynik bramki ρ̂ + 2 SE ≤ 0,282; NIE drukuje odsetka
trafień ani statystyk testu zbiorczego, nie zapisuje macierzy trafień (wynik tylko na stdout).

Prognoza = pętla bloku GARCH z `symulacje.prognozy_lv2.zbuduj_zrodla` (kod `symulacje/` jest zamrożony od
`24c8863`), bez źródeł pobocznych; parytet pilnuje `tests/test_pomiar_rho_h.py`.

    python -m modele.pomiar_rho_h > runs/2026-10-07_017-inwentarz-i-rho/raw_output.txt
    python -m modele.pomiar_rho_h --do 2026-10-31 --ostatnie 2100   # końcowe okno C2 (karta 018)
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np
import pandas as pd

from dane.zwroty_dzienne import (
    KATALOG_1D,
    MONETY_F21B,
    InwentarzMonety,
    ostatnie_wiersze,
    panel_wspolny,
)
from miara.var_es import var_es_t
from symulacje.garch_panel import generuj_panel
from symulacje.garch_t import dopasuj_garch_t, filtr_sigma2
from symulacje.prognozy_lv2 import KROK, ROZGRZEWKA_RESZT, START

P = 0.05
PROG_RHO = 0.282  # ρ_h `garch_tnu`, C2, VaR 5 % (przebieg rejestrowy LV2)
BLOK = 20  # długość bloku bootstrapu użyta w bramce (dni)
BLOKI_OPIS = (10, 40)  # wrażliwość SE: opis, nie bramka
B_BOOT = 2000
ZIARNO = 20261007
N_C2 = START + 1700  # wiersze wspólne potrzebne do komórki C2 (400 historii + 1 700 oceny)
K_KONTROLI, N_KONTROLI = 15, 2100
ZIARNA_DODATNIEJ, ZIARNA_UJEMNEJ = range(1, 11), range(101, 111)
PRZEDZIAL_DODATNIEJ = (0.242, 0.322)  # wokół 0,282 z LV2
PROG_UJEMNEJ = 0.03


@dataclass(frozen=True)
class Pomiar:
    k: int
    n_oos: int
    vr: float
    rho: float
    se: dict[int, float]  # długość bloku -> SE ρ̂
    diag: dict

    @property
    def gorna(self) -> float:
        return self.rho + 2.0 * self.se[BLOK]

    @property
    def bramka(self) -> bool:
        return self.gorna <= PROG_RHO


def prognoza_garch_tnu(
    r: np.ndarray, p: float = P, start: int = START, krok: int = KROK
) -> tuple[np.ndarray, dict]:
    """
    (q, diag): VaR p dla dni start…n−1, GARCH(1,1)-t refitowany co `krok` dni na rosnącym oknie r[:b],
    σ̂²_t z filtra przepuszczonego przez r[:t] (ani jednego zwrotu z dnia ≥ t), ogon t_ν̂ z tego samego dopasowania.
    """
    r = np.asarray(r, dtype=float)
    if r.ndim != 2:
        raise ValueError("r musi być macierzą dni × monety")
    n, k = r.shape
    if start < ROZGRZEWKA_RESZT + 2 * krok or start >= n:
        raise ValueError("start poza zakresem panelu")
    if not np.isfinite(r).all():
        raise ValueError("NaN albo nieskończoność w zwrotach")
    s2, q0 = np.empty((n - start, k)), np.empty((n - start, k))
    poprzednie = [None] * k
    diag = {"dopasowania": 0, "nie_zbiezne": 0, "brzeg": 0, "persystencja": [], "nu": []}
    for b in range(start, n, krok):
        e = min(b + krok, n)
        for j in range(k):
            f = dopasuj_garch_t(r[:b, j], start=poprzednie[j])
            poprzednie[j] = f
            s2[b - start : e - start, j] = filtr_sigma2(
                r[: e - 1, j] ** 2, f.omega, f.alpha, f.beta, f.backcast
            )[b:e]
            q0[b - start : e - start, j] = float(var_es_t(1.0, p, f.nu)[0])
            diag["dopasowania"] += 1
            diag["nie_zbiezne"] += not f.zbiezny
            diag["brzeg"] += f.brzeg
            diag["persystencja"].append(f.alpha + f.beta)
            diag["nu"].append(f.nu)
    diag["persystencja"] = float(np.mean(diag["persystencja"]))
    diag["nu"] = float(np.mean(diag["nu"]))
    return np.sqrt(s2) * q0, diag


def vr_rho(s: np.ndarray, k: int, p: float = P) -> tuple[float, float]:
    """(VR, ρ̂) z dziennej liczby trafień s: VR = Var(s)/(K p (1 − p)), ρ̂ = (VR − 1)/(K − 1)."""
    vr = float(np.var(s, ddof=1)) / (k * p * (1.0 - p))
    return vr, (vr - 1.0) / (k - 1.0)


def rho_bootstrap(s: np.ndarray, k: int, p: float, blok: int, b: int, ziarno: int) -> np.ndarray:
    """ρ̂* z kołowego bootstrapu blokowego po dniach: ⌈n/blok⌉ losowych początków, bloki kołowe, skrócone do n."""
    n = len(s)
    if not 1 <= blok <= n:
        raise ValueError("blok poza zakresem 1…n")
    rng = np.random.default_rng(ziarno)
    starty = rng.integers(0, n, size=(b, -(-n // blok)))
    idx = ((starty[:, :, None] + np.arange(blok)) % n).reshape(b, -1)[:, :n]
    vr = s[idx].var(axis=1, ddof=1) / (k * p * (1.0 - p))
    return (vr - 1.0) / (k - 1.0)


def pomiar(r: np.ndarray, p: float = P, b: int = B_BOOT, ziarno: int = ZIARNO) -> Pomiar:
    """Prognoza GARCH-t → trafienia → S_t → VR, ρ̂, SE. Trafienia i S_t zostają wewnątrz funkcji."""
    r = np.asarray(r, dtype=float)
    q, diag = prognoza_garch_tnu(r, p)
    s = (r[START:] < q).sum(axis=1).astype(float)
    k = r.shape[1]
    vr, rho = vr_rho(s, k, p)
    se = {
        blok: float(np.std(rho_bootstrap(s, k, p, blok, b, ziarno), ddof=1))
        for blok in (BLOK, *BLOKI_OPIS)
    }
    return Pomiar(k=k, n_oos=len(s), vr=vr, rho=rho, se=se, diag=diag)


def kontrola(rho_gen: float, ziarna, k: int = K_KONTROLI, n: int = N_KONTROLI) -> list[float]:
    """ρ̂ na panelach syntetycznych (R8): ta sama funkcja pomiarowa, bez bootstrapu SE."""
    wyn = []
    for z in ziarna:
        r = generuj_panel(n, k, seed=int(z), rho=rho_gen)["r"].to_numpy()
        q, _ = prognoza_garch_tnu(r)
        wyn.append(vr_rho((r[START:] < q).sum(axis=1).astype(float), k)[1])
    return wyn


def _d(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m-%d")


def tekst_inwentarza(
    inw: list[InwentarzMonety], panel: pd.DataFrame, wyciete: list, do: str
) -> str:
    wiersze = [
        f"Inwentarz świec 1d (dane do {do} włącznie, R16: od 2021-01-01)",
        f"{'moneta':<10} | {'świec':>5} | {'pierwsza':<10} | {'ostatnia':<10} | {'zwroty':>6} | braki w kalendarzu",
    ]
    for m in inw:
        braki = ", ".join(_d(d) for d in m.brakujace_dni) or "-"
        wiersze.append(
            f"{m.symbol:<10} | {m.swiec:>5} | {_d(m.pierwsza)} | {_d(m.ostatnia)} | {m.zwroty_wazne:>6} | {braki}"
        )
    wiersze += [
        "",
        f"Daty wycięte z panelu wspólnego przez dziurę u którejś monety ({len(wyciete)}): "
        + (", ".join(_d(d) for d in wyciete) or "-"),
        f"Panel wspólny: {len(panel)} wierszy, {_d(panel.index[0])} … {_d(panel.index[-1])}, monet: {panel.shape[1]}",
    ]
    return "\n".join(wiersze)


def tekst_okna(n_wierszy: int) -> str:
    brak = N_C2 - n_wierszy
    stan = "DOMYKA SIĘ" if brak <= 0 else f"NIE DOMYKA SIĘ (brakuje {brak})"
    return (
        f"Okno C2: potrzeba {N_C2} wierszy wspólnych ({START} historii + {N_C2 - START} oceny), "
        f"jest {n_wierszy} → {stan}"
    )


def tekst_pomiaru(pom: Pomiar) -> str:
    d = pom.diag
    se = pom.se
    return "\n".join(
        [
            f"Pomiar zależności dziennej liczby przekroczeń VaR {100 * P:.0f} % (GARCH-t, refit co {KROK} dni, K = {pom.k})",
            f"  dni oceny: {pom.n_oos}",
            (
                f"  dopasowań GARCH: {d['dopasowania']}, niezbieżnych: {d['nie_zbiezne']}, "
                f"przy granicy: {d['brzeg']}, średnia persystencja α+β {d['persystencja']:.4f}, "
                f"średnie ν̂ {d['nu']:.2f}"
            ),
            f"  VR = Var(S_t) / (K p (1 − p)) = {pom.vr:.3f}",
            f"  ρ̂ = (VR − 1) / (K − 1) = {pom.rho:.4f}",
            f"  SE (bootstrap blokowy, L = {BLOK}, B = {B_BOOT}, ziarno {ZIARNO}) = {se[BLOK]:.4f}",
            "  wrażliwość SE (opis, nie bramka): "
            + ", ".join(f"L = {blok}: {se[blok]:.4f}" for blok in BLOKI_OPIS),
            f"  ρ̂ + 2 SE = {pom.gorna:.4f}; próg {PROG_RHO}",
            f"Bramka zależności (ρ̂ + 2 SE ≤ {PROG_RHO}): {'PRZECHODZI' if pom.bramka else 'NIE PRZECHODZI'}",
        ]
    )


def tekst_kontroli(dodatnia: list[float], ujemna: list[float]) -> str:
    sd, su = float(np.mean(dodatnia)), float(np.mean(ujemna))
    ok_d = PRZEDZIAL_DODATNIEJ[0] <= sd <= PRZEDZIAL_DODATNIEJ[1]
    ok_u = abs(su) <= PROG_UJEMNEJ
    wiersze = [
        f"Kontrole R8 ({len(dodatnia)} paneli syntetycznych po {K_KONTROLI} monet × {N_KONTROLI} dni, ta sama funkcja pomiarowa)",
        "  dodatnia (ρ = 0.8, oczekiwane ≈ 0.282): ρ̂ na panelach "
        + " ".join(f"{x:.3f}" for x in dodatnia),
        f"    średnia {sd:.4f}, kryterium [{PRZEDZIAL_DODATNIEJ[0]}; {PRZEDZIAL_DODATNIEJ[1]}] → {'ZALICZONA' if ok_d else 'NIEZALICZONA'}",
        "  ujemna (ρ = 0, monety niezależne, oczekiwane ≈ 0): ρ̂ na panelach "
        + " ".join(f"{x:.3f}" for x in ujemna),
        f"    średnia {su:.4f}, kryterium |średnia| ≤ {PROG_UJEMNEJ} → {'ZALICZONA' if ok_u else 'NIEZALICZONA'}",
    ]
    return "\n".join(wiersze)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--katalog", default=str(KATALOG_1D))
    ap.add_argument("--do", default="2026-09-30", help="ostatni dzień danych (włącznie)")
    ap.add_argument("--ostatnie", type=int, default=0, help="ostatnie N wierszy panelu (0 = cały)")
    ap.add_argument("--monety", default=",".join(MONETY_F21B))
    ap.add_argument("--bez-kontroli", action="store_true")
    a = ap.parse_args(argv)
    monety = [m for m in a.monety.split(",") if m]

    panel, inw, wyciete = panel_wspolny(monety, a.katalog, a.do)
    print(tekst_inwentarza(inw, panel, wyciete, a.do))
    panel = ostatnie_wiersze(panel, a.ostatnie)
    if a.ostatnie:
        print(
            f"Okno pomiaru: ostatnie {a.ostatnie} wierszy, {_d(panel.index[0])} … {_d(panel.index[-1])}"
        )
    print()
    print(tekst_okna(len(panel)))
    print()
    print(tekst_pomiaru(pomiar(panel.to_numpy())))
    if not a.bez_kontroli:
        print()
        print(tekst_kontroli(kontrola(0.8, ZIARNA_DODATNIEJ), kontrola(0.0, ZIARNA_UJEMNEJ)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
