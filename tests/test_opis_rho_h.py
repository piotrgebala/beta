"""opis_rho_h (karta 020) — wydruk bez bramki, bez okna C2 i bez odsetka trafień; kryteria kontroli; kontrola spójności."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

from modele import opis_rho_h as o
from modele import pomiar_rho_h as m
from symulacje.garch_panel import generuj_panel
from symulacje.prognozy_lv2 import START


@pytest.fixture(scope="module")
def katalog_swiec(tmp_path_factory):
    kat = tmp_path_factory.mktemp("swiece_1d_020")
    r = generuj_panel(560, 3, seed=6, m_intraday=24)["r"].to_numpy()
    dni = pd.date_range("2021-01-01", periods=560, freq="D", tz="UTC")
    for j, sym in enumerate(("AAA", "BBB", "CCC")):
        close = 100.0 * np.exp(np.cumsum(r[:, j]))
        pd.DataFrame({"timestamp": dni, "close": close}).to_parquet(kat / f"{sym}.parquet")
    return kat, str(dni[-1].date())


def test_stale_zgodne_z_pre_rejestracja():
    assert o.MONETY_020 == ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT")
    assert o.K_020 == 4
    assert o.OCZEKIWANE_ROZLOGI == (4 * 57, 117)
    assert list(o.ZIARNA_DODATNIEJ) == list(range(1, 41))
    assert list(o.ZIARNA_UJEMNEJ) == list(range(101, 141))
    assert o.ROZNICA_DODATNIEJ == 0.03 and o.PROG_UJEMNEJ == 0.02
    assert m.PROG_RHO == 0.282 and m.P == 0.05 and m.BLOK == 20 and m.B_BOOT == 2000
    assert m.ZIARNO == 20261007
    assert set(o.ZIARNA_DODATNIEJ).isdisjoint(range(5001, 5021))
    assert set(o.ZIARNA_UJEMNEJ).isdisjoint(range(5101, 5121))
    assert len(o.ZIARNA_DODATNIEJ) == len(o.ZIARNA_UJEMNEJ) == 40


def test_main_drukuje_opis_bez_bramki_okna_i_odsetka_trafien(katalog_swiec, capsys):
    kat, do = katalog_swiec
    monety = ("AAA", "BBB", "CCC")
    przed = sorted(p.name for p in kat.iterdir())
    kod = o.main(
        ["--katalog", str(kat), "--do", do, "--monety", ",".join(monety), "--bez-kontroli"]
    )
    wyjscie = capsys.readouterr().out
    assert kod == 0
    assert (
        "Inwentarz świec 1d" in wyjscie and "ρ̂ ± 2 SE" in wyjscie and "Spójność z 017" in wyjscie
    )
    for zakazane in ("Bramka", "Okno C2", "próg", "Kupiec", "Christoffersen", "odsetek trafień"):
        assert zakazane not in wyjscie
    assert sorted(p.name for p in kat.iterdir()) == przed

    ceny = [pd.read_parquet(kat / f"{s}.parquet").set_index("timestamp")["close"] for s in monety]
    r = np.log(pd.concat(ceny, axis=1)).diff().dropna().to_numpy()
    q, _ = m.prognoza_garch_tnu(r)
    odsetek = float((r[START:] < q).mean())
    liczby = set(re.findall(r"-?\d+(?:[.,]\d+)?", wyjscie))
    zakazane_liczby = {f"{odsetek:.{d}f}" for d in (2, 3, 4)} | {
        f"{100 * odsetek:.{d}f}" for d in (1, 2)
    }
    assert not (zakazane_liczby & liczby)
    assert "0.282" not in wyjscie  # próg pojawia się tylko w wydruku kontroli


def test_pomiar_w_wydruku_zgadza_sie_z_funkcja_017(katalog_swiec, capsys):
    kat, do = katalog_swiec
    o.main(["--katalog", str(kat), "--do", do, "--monety", "AAA,BBB,CCC", "--bez-kontroli"])
    wyjscie = capsys.readouterr().out
    ceny = [
        pd.read_parquet(kat / f"{s * 3}.parquet").set_index("timestamp")["close"] for s in "ABC"
    ]
    r = np.log(pd.concat(ceny, axis=1)).diff().dropna().to_numpy()
    pom = m.pomiar(r)
    assert f"VR = Var(S_t) / (K p (1 − p)) = {pom.vr:.3f}" in wyjscie
    assert f"ρ̂ = (VR − 1) / (K − 1) = {pom.rho:.4f}" in wyjscie
    assert "NIEZGODNA" in wyjscie  # K = 3 i krótka próba: liczby dopasowań inne niż w 017


def test_kontrole_wymagaja_k_4(katalog_swiec):
    kat, do = katalog_swiec
    with pytest.raises(ValueError, match="K = 4"):
        o.main(["--katalog", str(kat), "--do", do, "--monety", "AAA,BBB,CCC"])


def test_tekst_kontroli_ocenia_kryteria():
    t = o.tekst_kontroli([0.28] * 40, [0.0] * 40)
    assert t.count("ZALICZONA") == 2 and "NIEZALICZONA" not in t
    t = o.tekst_kontroli([0.20] * 40, [0.1] * 40)
    assert t.count("NIEZALICZONA") == 2
    t = o.tekst_kontroli([0.282 + o.ROZNICA_DODATNIEJ - 1e-9] * 40, [o.PROG_UJEMNEJ - 1e-9] * 40)
    assert t.count("ZALICZONA") == 2 and "NIEZALICZONA" not in t
    t = o.tekst_kontroli([0.282 - 0.03 + 1e-9] * 40, [-0.02 + 1e-9] * 40)
    assert t.count("ZALICZONA") == 2 and "NIEZALICZONA" not in t
    t = o.tekst_kontroli([0.282 + 0.05] * 40, [0.04] * 40)
    assert t.count("NIEZALICZONA") == 2
    t = o.tekst_kontroli([0.282 - 0.05] * 40, [-0.5] * 40)
    assert t.count("NIEZALICZONA") == 2


def _pom(brzeg=117, nie_zbiezne=0, **kw):
    return m.Pomiar(
        k=kw.get("k", 4),
        n_oos=1691,
        vr=kw.get("vr", 2.26),
        rho=kw.get("rho", 0.42),
        se={m.BLOK: 0.09, 10: 0.1, 40: 0.11},
        diag={
            "dopasowania": 228,
            "nie_zbiezne": nie_zbiezne,
            "brzeg": brzeg,
            "persystencja": 0.97,
            "nu": 4.1,
        },
    )


def test_kontrola_spojnosci_zgodna_przy_oczekiwanych_liczbach():
    assert "→ ZGODNA" in o.tekst_opisu(_pom())
    assert "NIEZGODNA" in o.tekst_opisu(_pom(brzeg=118))


def test_przedzialy_rho_i_vr_w_wydruku():
    t = o.tekst_opisu(_pom())
    assert "ρ̂ ± 2 SE = [0.2400; 0.6000]" in t
    assert "VR odpowiadające ρ̂ ± 2 SE = [1.720; 2.800]" in t
    assert "L = 10: 0.1000, L = 40: 0.1100" in t


@pytest.fixture(scope="module")
def katalog_4(tmp_path_factory):
    kat = tmp_path_factory.mktemp("swiece_1d_020_k4")
    r = generuj_panel(520, 4, seed=7, m_intraday=24)["r"].to_numpy()
    dni = pd.date_range("2021-01-01", periods=520, freq="D", tz="UTC")
    for j, sym in enumerate(("AAA", "BBB", "CCC", "DDD")):
        close = 100.0 * np.exp(np.cumsum(r[:, j]))
        pd.DataFrame({"timestamp": dni, "close": close}).to_parquet(kat / f"{sym}.parquet")
    return kat, str(dni[-1].date())


def test_main_kontrole_dostaja_rejestrowe_argumenty(katalog_4, monkeypatch, capsys):
    kat, do = katalog_4
    wywolania, wiersze = [], []

    def falszywa_kontrola(rho, ziarna, k, n):
        wywolania.append((rho, list(ziarna), k, n))
        return [0.282] * 40 if rho else [0.0] * 40

    def falszywy_pomiar(r):
        wiersze.append(r.shape)
        return _pom()

    monkeypatch.setattr(m, "kontrola", falszywa_kontrola)
    monkeypatch.setattr(m, "pomiar", falszywy_pomiar)
    kod = o.main(
        ["--katalog", str(kat), "--do", do, "--monety", "AAA,BBB,CCC,DDD", "--ostatnie", "300"]
    )
    wyjscie = capsys.readouterr().out
    assert kod == 0
    assert wiersze == [(300, 4)]
    assert wywolania == [
        (0.8, list(range(1, 41)), 4, 300),
        (0.0, list(range(101, 141)), 4, 300),
    ]
    assert "Okno pomiaru: ostatnie 300 wierszy" in wyjscie
    assert wyjscie.count("ZALICZONA") == 2 and "NIEZALICZONA" not in wyjscie
    for zakazane in ("Bramka", "Okno C2", "próg", "Kupiec", "Christoffersen", "odsetek trafień"):
        assert zakazane not in wyjscie


def test_main_zatrzymuje_sie_przy_niezbieznym_dopasowaniu(katalog_4, monkeypatch, capsys):
    kat, do = katalog_4
    monkeypatch.setattr(m, "pomiar", lambda r: _pom(nie_zbiezne=1))
    with pytest.raises(RuntimeError, match="STOP"):
        o.main(["--katalog", str(kat), "--do", do, "--monety", "AAA,BBB,CCC,DDD", "--bez-kontroli"])
    assert "Pomiar zależności" not in capsys.readouterr().out
