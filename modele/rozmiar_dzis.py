"""
rozmiar_dzis.py — tabela „na dziś” dla koszyka: prognoza σ z GARCH-t, dźwignia z celu zmienności, dystans do
likwidacji i limit ES. Kalkulator stanu bieżącego, NIE ocena prognozy: niczego nie testuje na historii,
nie liczy zwrotu strategii i nie podbija żadnego licznika (`docs/PRD.md` §11.4). Prognoza σ nie przeszła
jeszcze testu kalibracji na danych (karty 018/022), więc tabela pokazuje też wrażliwość na σ × zapas.

    python -m modele.rozmiar_dzis [--do 2026-09-30] [--cele 0.18,0.35] [--sufit 3] [--mmr 0.005]
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from dane.zwroty_dzienne import panel_wspolny
from modele.ryzyko_pozycji import dystans_w_sigmach, dzwignia_konc, es_straty, p_likwidacji
from symulacje.garch_t import dopasuj_garch_t, filtr_sigma2

KOSZYK = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT")
P_ES = 0.05
ZAPASY = (1.0, 1.25, 1.5)


def prognoza_sigma_nu(r: np.ndarray) -> tuple[float, float, float, bool]:
    """(σ na następny dzień, ν̂, α̂ + β̂, czy dopasowanie bez uwag) z GARCH-t na całej serii r."""
    r = np.asarray(r, dtype=float)
    f = dopasuj_garch_t(r)
    s2 = filtr_sigma2(r * r, f.omega, f.alpha, f.beta, f.backcast)
    return (
        float(np.sqrt(s2[-1])),
        float(f.nu),
        float(f.alpha + f.beta),
        bool(f.zbiezny and not f.brzeg),
    )


def tabela_dzis(
    panel: pd.DataFrame,
    cele: tuple[float, ...] = (0.18, 0.35),
    sufit: float = 3.0,
    mmr: float = 0.005,
    zapasy: tuple[float, ...] = ZAPASY,
) -> pd.DataFrame:
    """Jeden wiersz na (moneta, zapas σ): σ, ES5, dźwignia dla każdego celu, dystans i P likwidacji."""
    wiersze = []
    for moneta in panel.columns:
        sigma, nu, trwalosc, czysty = prognoza_sigma_nu(panel[moneta].to_numpy())
        for zapas in zapasy:
            s = sigma * zapas
            _, es = es_straty(s, P_ES, nu)
            wiersz = {
                "moneta": moneta,
                "zapas": zapas,
                "sigma_dzien_%": 100 * s,
                "sigma_rok_%": 100 * s * np.sqrt(365),
                "nu": nu,
                "trwalosc": trwalosc,
                "dopasowanie_ok": czysty,
                "ES5_dzien_%": 100 * es,
            }
            for cel in cele:
                wiersz[f"dzwignia_cel_{cel:.0%}"] = dzwignia_konc(s, cel, sufit)
            for dzw in (2.0, 3.0):
                wiersz[f"dystans_{dzw:g}x_sigm"] = dystans_w_sigmach(dzw, mmr, s)
                wiersz[f"P_likw_{dzw:g}x_7d_%"] = 100 * p_likwidacji(dzw, mmr, s, nu, dni=7)
            wiersze.append(wiersz)
    return pd.DataFrame(wiersze)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--do", default="2026-09-30")
    ap.add_argument("--cele", default="0.18,0.35", help="roczne cele zmienności po przecinku")
    ap.add_argument("--sufit", type=float, default=3.0)
    ap.add_argument("--mmr", type=float, default=0.005)
    a = ap.parse_args()
    panel, _, wyciete = panel_wspolny(KOSZYK, do=a.do)
    cele = tuple(float(x) for x in a.cele.split(","))
    tab = tabela_dzis(panel, cele, a.sufit, a.mmr)
    print(
        f"Stan na {panel.index[-1].date()}, {len(panel)} wspólnych dni, wycięte przez dziury: {len(wyciete)}"
    )
    print(
        f"Sufit dźwigni {a.sufit:g}×, mmr {a.mmr:.2%}, ES na p = {P_ES:.0%}. Zapas = mnożnik prognozy σ."
    )
    pd.set_option("display.width", 250, "display.max_columns", 30)
    print(tab.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
