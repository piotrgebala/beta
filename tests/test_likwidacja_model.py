"""Walk-forward σ̂/ν̂ dla karty 024: brak podglądu przyszłości (R7) i zgodność z filtrem na ręcznym dopasowaniu."""

from __future__ import annotations

import numpy as np
import pytest

from modele.likwidacja_model import p_model, sigma_nu_walk_forward
from symulacje.garch_panel import generuj_panel
from symulacje.garch_t import dopasuj_garch_t, filtr_sigma2


def _r(n: int = 700, seed: int = 5) -> np.ndarray:
    return generuj_panel(n, 1, seed=seed)["r"].to_numpy()[:, 0]


def test_dlugosc_i_skonczonosc():
    r = _r()
    s, nu, brzeg = sigma_nu_walk_forward(r, start=300, krok=50)
    assert len(s) == len(nu) == len(brzeg) == len(r) - 300
    assert np.isfinite(s).all() and (s > 0).all() and (nu > 2).all()


def test_pierwsza_prognoza_zgodna_z_recznym_dopasowaniem():
    r = _r()
    s, nu, _ = sigma_nu_walk_forward(r, start=300, krok=50)
    f = dopasuj_garch_t(r[:300])
    s2 = filtr_sigma2(r[:300] ** 2, f.omega, f.alpha, f.beta, f.backcast)
    assert s[0] == pytest.approx(np.sqrt(s2[300]), rel=1e-9)
    assert nu[0] == pytest.approx(f.nu)


def test_brak_podgladu_przyszlosci():
    # zmiana zwrotów od dnia k wzwyż nie może zmienić σ̂ przed dniem k (leakage, R7)
    r = _r()
    k = 520
    r2 = r.copy()
    r2[k:] *= 3.0
    s1, nu1, _ = sigma_nu_walk_forward(r, start=300, krok=50)
    s2, nu2, _ = sigma_nu_walk_forward(r2, start=300, krok=50)
    do_k = k - 300  # σ̂[j] dotyczy dnia 300 + j; dzień k zależy od zwrotów < k
    assert np.array_equal(s1[:do_k], s2[:do_k]) and np.array_equal(nu1[:do_k], nu2[:do_k])
    assert not np.allclose(s1[do_k + 1 :], s2[do_k + 1 :])


def test_p_model_w_przedziale_i_rosnie_z_dzwignia():
    s, nu = np.full(5, 0.03), np.full(5, 4.0)
    p3, p8 = p_model(s, nu, 3.0, 0.01, "long", 7), p_model(s, nu, 8.0, 0.01, "long", 7)
    assert ((0 <= p3) & (p3 <= 1)).all() and (p8 > p3).all()
