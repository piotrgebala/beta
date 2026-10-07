"""zwroty_dzienne — zwrot tylko z dwóch kolejnych dni, panel wspólny, obcięcie `do`, R16."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dane.zwroty_dzienne import (
    log_zwroty_1d,
    ostatnie_wiersze,
    panel_wspolny,
)

T0 = pd.Timestamp("2021-01-01", tz="UTC")


def _swiece(close, start: pd.Timestamp = T0, usun: tuple[int, ...] = ()) -> pd.DataFrame:
    """Świece 1d: dzień i ma cenę close[i]; dni z `usun` (indeksy) nie mają wiersza."""
    dni = [start + pd.Timedelta(days=i) for i in range(len(close))]
    df = pd.DataFrame({"timestamp": dni, "close": np.asarray(close, dtype=float)})
    return df.drop(index=list(usun)).reset_index(drop=True)


def _zapisz(katalog, symbol: str, df: pd.DataFrame) -> None:
    df.to_parquet(katalog / f"{symbol}.parquet")


def test_zwrot_to_logarytm_ilorazu_kolejnych_dni():
    r = log_zwroty_1d(_swiece([100.0, 110.0, 99.0]), T0 + pd.Timedelta(days=2))
    assert np.isnan(r.iloc[0])
    np.testing.assert_allclose(r.iloc[1:], [np.log(1.1), np.log(0.9)], rtol=1e-14)


def test_dziura_jednego_dnia_unieważnia_zwrot_tego_dnia_i_nastepnego():
    r = log_zwroty_1d(_swiece(np.arange(1, 11) * 10.0, usun=(4,)), T0 + pd.Timedelta(days=9))
    assert list(r.index[r.isna()]) == [T0, T0 + pd.Timedelta(days=4), T0 + pd.Timedelta(days=5)]


def test_obciecie_do_ignoruje_swiece_po_dacie():
    r = log_zwroty_1d(_swiece([1.0, 2.0, 3.0, 4.0]), T0 + pd.Timedelta(days=1))
    assert len(r) == 2 and r.index[-1] == T0 + pd.Timedelta(days=1)


def test_swiece_konczace_sie_przed_do_daja_nan_na_koncu():
    r = log_zwroty_1d(_swiece([1.0, 2.0, 3.0]), T0 + pd.Timedelta(days=4))
    assert len(r) == 5 and r.iloc[3:].isna().all()


@pytest.mark.parametrize(
    "close", [[1.0, 0.0, 2.0], [1.0, -1.0, 2.0], [1.0, np.nan, 2.0], [1.0, np.inf, 2.0]]
)
def test_zla_cena_to_blad(close):
    with pytest.raises(ValueError, match="cena"):
        log_zwroty_1d(_swiece(close), T0 + pd.Timedelta(days=2))


def test_duplikat_dnia_to_blad():
    df = _swiece([1.0, 2.0, 3.0])
    with pytest.raises(ValueError, match="duplikaty"):
        log_zwroty_1d(pd.concat([df, df.iloc[[1]]]), T0 + pd.Timedelta(days=2))


def test_r16_swiece_sprzed_2021_nie_wchodza(tmp_path):
    start = pd.Timestamp("2020-12-29", tz="UTC")
    for m in ("A", "B"):
        _zapisz(tmp_path, m, _swiece(np.linspace(10, 20, 10), start=start))
    panel, inw, _ = panel_wspolny(["A", "B"], tmp_path, "2021-01-05")
    assert panel.index.min() == pd.Timestamp("2021-01-02", tz="UTC")
    assert inw[0].pierwsza == T0


def test_panel_wspolny_wycina_daty_z_dziurami_i_podaje_je(tmp_path):
    n = 30
    cena = np.exp(np.cumsum(np.full(n, 0.01)))
    _zapisz(tmp_path, "A", _swiece(cena))
    _zapisz(tmp_path, "B", _swiece(cena, usun=(10, 11, 12, 20, 21)))
    _zapisz(tmp_path, "C", _swiece(cena))
    do = str((T0 + pd.Timedelta(days=n - 1)).date())
    panel, inw, wyciete = panel_wspolny(["A", "B", "C"], tmp_path, do)
    # dziura 3 dni → 4 daty zwrotu, dziura 2 dni → 3 daty zwrotu, plus pierwszy dzień bez poprzednika
    assert len(wyciete) == 7
    assert len(panel) == n - 1 - 7
    assert list(panel.columns) == ["A", "B", "C"]
    assert panel.notna().all().all()
    b = next(m for m in inw if m.symbol == "B")
    assert b.swiec == n - 5 and len(b.brakujace_dni) == 5 and b.zwroty_wazne == n - 1 - 7
    a = next(m for m in inw if m.symbol == "A")
    assert a.swiec == n and a.brakujace_dni == () and a.zwroty_wazne == n - 1


def test_kolejnosc_kolumn_zgodna_z_lista_monet(tmp_path):
    for m in ("A", "B", "C"):
        _zapisz(tmp_path, m, _swiece(np.linspace(10, 20, 8)))
    panel, _, _ = panel_wspolny(["C", "A", "B"], tmp_path, "2021-01-08")
    assert list(panel.columns) == ["C", "A", "B"]


@pytest.mark.parametrize("monety", [["A"], ["A", "A"], []])
def test_potrzeba_dwoch_roznych_monet(tmp_path, monety):
    with pytest.raises(ValueError, match="różnych"):
        panel_wspolny(monety, tmp_path, "2021-01-08")


def test_ostatnie_wiersze():
    df = pd.DataFrame({"x": range(10)})
    assert len(ostatnie_wiersze(df, 0)) == 10
    assert list(ostatnie_wiersze(df, 3)["x"]) == [7, 8, 9]
    with pytest.raises(ValueError, match="potrzeba"):
        ostatnie_wiersze(df, 11)


@settings(max_examples=60, deadline=None)
@given(
    n=st.integers(min_value=5, max_value=60),
    braki=st.sets(st.integers(min_value=1, max_value=58), max_size=12),
)
def test_wazne_zwroty_to_pary_kolejnych_dni(n, braki):
    braki = {i for i in braki if i < n - 1}
    cena = np.exp(np.cumsum(np.full(n, 0.02)))
    r = log_zwroty_1d(_swiece(cena, usun=tuple(braki)), T0 + pd.Timedelta(days=n - 1))
    oczekiwane = [i for i in range(1, n) if i not in braki and (i - 1) not in braki]
    assert [(d - T0).days for d in r.index[r.notna()]] == oczekiwane
    np.testing.assert_allclose(r.dropna().to_numpy(), 0.02, rtol=1e-12)
