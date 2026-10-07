"""Kod rejestrowy vs całkowanie numeryczne: kwantyl i ES ogona t_ν oraz mnożniki par „dokładnie zerowych”.

Uruchamianie z korzenia repo: PYTHONPATH=. python runs/2026-10-07_lv2-var-es-estymowane/weryfikacja/stale_vs_rejestr.py
Porównuje `miara.var_es.var_es_t` i `symulacje.porownanie_lv2.mnoznik_zerowy` (kod rejestrowy)
z całkowaniem `scipy.integrate.quad` z `indep_lv2.py` (kod niezależny). Skrypt dopisano po przebiegu.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import indep_lv2 as ind

from miara.var_es import var_es_t
from symulacje.porownanie_lv2 import mnoznik_zerowy

print("# Kwantyl i ES ogona t_ν (wariancja 1): var_es_t(1, p, ν) vs całkowanie numeryczne")
maks_q = maks_es = 0.0
for p in (0.01, 0.05):
    for nu in (5.0, 8.0):
        q_r, es_r = (float(x) for x in var_es_t(1.0, p, nu))
        q_c, es_c = ind.ogon_t_calka(p, nu)
        maks_q = max(maks_q, abs(q_r - q_c))
        maks_es = max(maks_es, abs(es_r - es_c))
        print(f"p={p:.2f} ν={nu:.0f}: VaR {q_r:.10f} vs {q_c:.10f}; ES {es_r:.10f} vs {es_c:.10f}")
print(f"maks. |różnica| kwantyla {maks_q:.2e}, ES {maks_es:.2e}")

print("\n# Mnożniki c_B (ν = 5): mnoznik_zerowy vs quad + brentq")
maks_m = 0.0
for p in (0.01, 0.05):
    for strata in ("fz0", "pinb"):
        for c_a in (0.9, 0.8):
            m_r = mnoznik_zerowy(c_a, p, 5.0, strata)
            m_c = ind.mnoznik_calka(c_a, p, ind.NU, strata)
            maks_m = max(maks_m, abs(m_r - m_c))
            print(f"p={p:.2f} {strata:<5} c_A={c_a}: {m_r:.6f} vs {m_c:.6f}")
print(f"maks. |różnica| mnożników {maks_m:.2e}")
