"""Przeliczenie niezależne wyniku rejestrowego 021: liczby z wydruku odtworzone z surowych tablic paneli
(`data/lv2d_wyniki_paneli.npz`) zwykłym numpy, bez importu `run_lv2d`, `run_lv2c`, `run_lv2`,
`ocen_komorke` i bez zamrożonego `_werdykt`. Układ kolumn przepisany ręcznie (z asercją kształtu).

    python runs/2026-10-08_021-lv2d-regimy-wariancji/przeliczenie_niezalezne.py data/lv2d_wyniki_paneli.npz
"""

from __future__ import annotations

import sys

import numpy as np

PROGNOZY = (
    "wyr_t5",
    "zan30",
    "garch_x1.00",
    "garch_x0.95",
    "garch_x0.90",
    "garch_x0.85",
    "garch_x0.80",
    "garch_x0.70",
    "zan10",
    "zan20",
)
STAT = ("hit", "u_sr", "zb_a", "zb_b", "zb_c", "zb_bonf", "zb_a_prawa", "vr", "niezdef")
DIAG = ("dopasowania", "nie_zbiezne", "brzeg", "persystencja", "nu")
K, N_OCENY, P = 4, 1691, 0.05
KRYT = 2.3939  # kwantyl normalny dla Bonferroniego α/3 = 1,667 % dwustronnie
CELE_VR = {"A0": 1.846, "B1": 1.717, "B2": 2.264, "B3": 2.811}


def srednia_se(x: np.ndarray, mnoznik: float = 1.0) -> str:
    return f"{x.mean() * mnoznik:.3f} ± {x.std(ddof=1) / np.sqrt(len(x)) * mnoznik:.3f}"


def main() -> None:
    z = np.load(sys.argv[1])
    for komorka, cel in CELE_VR.items():
        stat, diag, vr_pom = z[f"{komorka}_stat"], z[f"{komorka}_diag"], z[f"{komorka}_vr_pom"]
        assert stat.shape == (4000, len(PROGNOZY), len(STAT)), stat.shape
        assert diag.shape == (4000, len(DIAG)), diag.shape
        assert np.isfinite(stat).all() and np.isfinite(diag).all() and np.isfinite(vr_pom).all()
        i = {n: j for j, n in enumerate(PROGNOZY)}
        j = {n: m for m, n in enumerate(STAT)}
        # kształt nie wyłapie zamiany kolumn; te niezmienniki wyłapią zamianę kolumn różnych rodzajów
        # (zamiany zb_a ↔ zb_b ↔ zb_c nie wyłapią — zob. README, „Przegląd kodu”)
        for n in ("zb_a", "zb_b", "zb_c", "zb_bonf", "zb_a_prawa"):
            assert set(np.unique(stat[:, :, j[n]])) <= {0.0, 1.0}, n
        assert (stat[:, :, j["zb_a_prawa"]] <= stat[:, :, j["zb_a"]]).all()
        assert ((stat[:, :, j["hit"]] > 0) & (stat[:, :, j["hit"]] < 0.5)).all()
        assert (stat[:, :, j["vr"]] > 0).all() and (stat[:, :, j["niezdef"]] >= 0).all()
        g1, g9, wyr, z30 = (
            stat[:, i[n]] for n in ("garch_x1.00", "garch_x0.90", "wyr_t5", "zan30")
        )
        print(f"\n=== {komorka} (4000 paneli; cel VR {cel}) ===")
        print(f"  K-a  rozmiar garch_x1.00 (zb_bonf), %: {srednia_se(g1[:, j['zb_bonf']], 100)} pp")
        print(f"  K-b  moc garch_x0.90 (zb_bonf), %:     {srednia_se(g9[:, j['zb_bonf']], 100)} pp")
        print(
            f"  K1   rozmiar wyr_t5, %:                {srednia_se(wyr[:, j['zb_bonf']], 100)} pp"
        )
        print(
            f"  K2   moc zan30, %:                     {srednia_se(z30[:, j['zb_bonf']], 100)} pp"
        )
        print(
            f"  moc zan10 / zan20, %: {stat[:, i['zan10'], j['zb_bonf']].mean() * 100:.1f} / "
            f"{stat[:, i['zan20'], j['zb_bonf']].mean() * 100:.1f}"
        )
        print(f"  VR garch_x1.00 (kolumna vr):           {srednia_se(g1[:, j['vr']])}")
        print(f"  VR z osobnej kolumny vr_pom:           {srednia_se(vr_pom)}")
        print(
            f"  max |vr − vr_pom|:                     {np.abs(g1[:, j['vr']] - vr_pom).max():.2e}"
        )
        print(f"  odsetek trafień garch_x1.00, %:        {srednia_se(g1[:, j['hit']], 100)} pp")
        print(f"  U (u_sr) garch_x1.00:                  {srednia_se(g1[:, j['u_sr']])}")
        brzeg = diag[:, DIAG.index("brzeg")] / diag[:, DIAG.index("dopasowania")]
        niezb = diag[:, DIAG.index("nie_zbiezne")] / diag[:, DIAG.index("dopasowania")]
        print(
            f"  przy granicy, %: {brzeg.mean() * 100:.2f}; niezbieżne, %: {niezb.mean() * 100:.2f}; "
            f"dopasowań na panel: {diag[:, 0].min():.0f}–{diag[:, 0].max():.0f}"
        )
        print(f"  persystencja {diag[:, 3].mean():.4f}, ν̂ {diag[:, 4].mean():.3f}")
        # spójność wewnętrzna: test zbiorczy odrzuca ⇔ którykolwiek z A/B/C poniżej α/3
        a, b, c, bonf = (stat[:, :, j[n]] for n in ("zb_a", "zb_b", "zb_c", "zb_bonf"))
        zgodne = (np.maximum(np.maximum(a, b), c) == bonf).all()
        print(f"  zb_bonf = max(zb_a, zb_b, zb_c) w każdym panelu i prognozie: {bool(zgodne)}")
        print(f"  niezdefiniowane p-wartości łącznie: {int(stat[:, :, j['niezdef']].sum())}")
        # rząd wielkości mocy z samej liczby niezależnych obserwacji (tylko trafienia, bez ES)
        vr = g1[:, j["vr"]].mean()
        n_eff = N_OCENY * K / vr
        se_hit = np.sqrt(P * (1 - P) / n_eff)
        hit90 = g9[:, j["hit"]].mean()
        z_hit = (hit90 - P) / se_hit
        print(
            f"  rząd wielkości (tylko trafienia): n_eff = n·K/VR = {n_eff:.0f}, SE odsetka = "
            f"{se_hit * 100:.2f} pp, nadwyżka x0.90 = {(hit90 - P) * 100:.2f} pp → z = {z_hit:.2f}"
        )
        # diagnostyka PO FAKCIE (opis, nie kryterium): czy rozrzut odsetka trafień między panelami
        # zgadza się z błędem standardowym, który zakłada niezależne dni (jak bootstrap-t testu A)
        for nazwa in ("wyr_t5", "garch_x1.00"):
            s = stat[:, i[nazwa]]
            hit, vr_p = s[:, j["hit"]], s[:, j["vr"]]
            se = np.sqrt(vr_p * P * (1 - P) / (N_OCENY * K))
            zn = (hit - P) / se
            print(
                f"  rozrzut odsetka trafień {nazwa}: SD po panelach {hit.std(ddof=1) * 100:.3f} pp, "
                f"SE przy niezależnych dniach {se.mean() * 100:.3f} pp, iloraz {hit.std(ddof=1) / se.mean():.2f}; "
                f"z naiwne: średnia {zn.mean():.2f}, SD {zn.std(ddof=1):.2f}, "
                f"P(z > {KRYT:.2f}) {np.mean(zn > KRYT) * 100:.1f} %, P(z < −{KRYT:.2f}) {np.mean(zn < -KRYT) * 100:.1f} %; "
                f"zapisane A: {s[:, j['zb_a']].mean() * 100:.1f} % (prawa {s[:, j['zb_a_prawa']].mean() * 100:.1f} %)"
            )


if __name__ == "__main__":
    main()
