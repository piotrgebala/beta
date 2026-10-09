"""
Karta 024, krok 1 (R3): prognozy σ̂/ν̂ walk-forward dla koszyka i rachunek mierzalności — liczba zdarzeń
likwidacji, której MODEL oczekuje przy dźwigniach 3×/5×/8×. Nie wczytuje cen high/low ani nie liczy trafień.

    PYTHONPATH=. python -m modele.run_lq024_mierzalnosc
"""

from __future__ import annotations

import numpy as np
from scipy.stats import poisson

from dane.zwroty_dzienne import panel_wspolny
from modele.likwidacja_model import START, p_model, sigma_nu_walk_forward

KOSZYK = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT")
DZWIGNIE, MMR, DNI, STRONY = (3.0, 5.0, 8.0), 0.01, 7, ("long", "short")
VR = 2.264  # z karty 020 (K = 4): jedna „niezależna” obserwacja ≈ VR trafień z czterech monet
WYJSCIE = "data/lq024_prognozy.npz"


def moc_poissona(e: float, ratio: float, alpha: float = 0.05) -> float:
    """Moc jednostronnego testu Poissona H0: średnia e, gdy prawdziwa średnia = ratio·e."""
    krytyczne = int(poisson.isf(alpha, e)) + 1  # najmniejsze k z P(X ≥ k) ≤ α
    return float(poisson.sf(krytyczne - 1, ratio * e))


def wymagane_e(ratio: float, moc: float = 0.8) -> float:
    for e in np.arange(0.5, 200.0, 0.5):
        if moc_poissona(float(e), ratio) >= moc:
            return float(e)
    return float("inf")


def main() -> None:
    panel, _, wyciete = panel_wspolny(KOSZYK, do="2026-09-30")
    daty = panel.index
    print(f"Panel wspólny: {len(panel)} dni, wycięte przez dziury: {len(wyciete)}, START = {START}")
    wyniki, brzeg_udzial = {}, {}
    for m in KOSZYK:
        s, nu, brzeg = sigma_nu_walk_forward(panel[m].to_numpy())
        wyniki[m] = (s, nu)
        brzeg_udzial[m] = float(brzeg.mean())
    # pozycja wpisu i = START − 1 … n − 2; okno [i, i + DNI] musi leżeć w kolejnych dniach kalendarza
    n = len(panel)
    wpisy = np.arange(START - 1, n - 1)
    ok = np.array([i + DNI < n and (daty[i + DNI] - daty[i]).days == DNI for i in wpisy])
    print(f"Wpisów: {len(wpisy)}, z pełnym oknem {DNI} kolejnych dni: {int(ok.sum())}")
    np.savez(
        WYJSCIE,
        wpisy=wpisy,
        ok=ok,
        daty=daty.values.astype("datetime64[D]"),
        **{f"{m}_sigma": wyniki[m][0] for m in KOSZYK},
        **{f"{m}_nu": wyniki[m][1] for m in KOSZYK},
    )
    print(
        "Udział dni z dopasowaniem przy granicy/niezbieżnym:",
        {m: round(v, 3) for m, v in brzeg_udzial.items()},
    )
    print(
        "\nMierzalność (oczekiwane liczby zdarzeń z MODELU; okna 7-dniowe, 4 monety, nakładające się):"
    )
    print(f"{'L':>3} {'strona':>6} {'E okien':>9} {'E bloki 7d':>11} {'E niezal.':>10}")
    wyniki_e = {}
    for L in DZWIGNIE:
        for strona in STRONY:
            e_okna = e_blok = 0.0
            for m in KOSZYK:
                s, nu = wyniki[m]
                p = p_model(s[ok], nu[ok], L, MMR, strona, DNI)
                e_okna += float(p.sum())
                e_blok += float(p[::DNI].sum())
            e_niezal = e_blok / VR
            wyniki_e[(L, strona)] = e_niezal
            print(f"{L:>3g} {strona:>6} {e_okna:>9.1f} {e_blok:>11.2f} {e_niezal:>10.2f}")
    print("\nWymagane E (niezależne) dla mocy 80 % jednostronnego testu Poissona α = 5 %:")
    for ratio in (1.5, 2.0, 3.0):
        print(f"  ratio {ratio}: E ≥ {wymagane_e(ratio):.1f}")
    print(
        "\nMierzalne (E niezal. ≥ próg dla ratio 2):",
        [(L, s) for (L, s), e in wyniki_e.items() if e >= wymagane_e(2.0)],
    )


if __name__ == "__main__":
    main()
