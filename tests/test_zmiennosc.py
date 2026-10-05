"""RV z 5m, prognozy F2 (dziennik EWMA, HAR walk-forward) — testy bez danych rynkowych."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from dane.rv import rv_dzienna
from modele.zmiennosc import prognoza_dziennik, prognoza_har
from symulacje.garch_panel import generuj_panel


def _swiece5m(dni: int, seed: int = 0, sd5: float = 0.002) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = dni * 288
    ts = pd.date_range("2021-01-01", periods=n, freq="5min", tz="UTC")
    close = 100 * np.exp(np.cumsum(rng.normal(0, sd5, n)))
    return pd.DataFrame({"timestamp": ts, "close": close})


def test_rv_suma_kwadratow():
    df = _swiece5m(5)
    out = rv_dzienna(df)
    assert len(out) == 5 and (out["n_swiec"] == 288).all()
    lr = np.log(df["close"]).diff()
    day2 = df["timestamp"].dt.floor("D") == pd.Timestamp("2021-01-02", tz="UTC")
    assert out["rv"].iloc[1] == pytest.approx(float((lr[day2] ** 2).sum()))
    assert np.isnan(out["rv"].iloc[0])
    assert out["rv"].iloc[1:].mean() == pytest.approx(288 * 0.002**2, rel=0.15)


def test_rv_duplikaty_to_blad():
    df = _swiece5m(2)
    with pytest.raises(ValueError):
        rv_dzienna(pd.concat([df, df.iloc[:1]]))


def test_prognoza_dziennik_jak_alpha():
    """σ̂ alpha = √(365·EWMA(r²)); nasza prognoza dnia t+1 = EWMA(r²) z dnia t."""
    r = pd.Series(np.random.default_rng(1).normal(0, 0.03, 200))
    f = prognoza_dziennik(r)
    ref = (r**2).ewm(com=60, min_periods=30).mean()
    assert f.iloc[100] == pytest.approx(ref.iloc[99])
    assert f.iloc[:30].isna().all()


@pytest.mark.parametrize("fn", ["har", "dziennik"])
def test_bez_przecieku(fn):
    p = generuj_panel(900, 1, seed=3)
    rv = p["rv"].iloc[:, 0]
    r = p["r"].iloc[:, 0]
    k = 600
    rv2, r2 = rv.copy(), r.copy()
    rv2.iloc[k:] *= 10.0
    r2.iloc[k:] *= 3.0
    a = prognoza_har(rv) if fn == "har" else prognoza_dziennik(r)
    b = prognoza_har(rv2) if fn == "har" else prognoza_dziennik(r2)
    pd.testing.assert_series_equal(a.iloc[: k + 1], b.iloc[: k + 1])


def test_har_bije_dziennik_na_garch():
    """Kontrola pozytywna: na danych z trwałą zmiennością HAR ma niższą QLIKE niż EWMA com 60."""
    from miara.dm import diebold_mariano, qlike

    p = generuj_panel(10_000, 1, seed=4)
    rv, r = p["rv"].iloc[:, 0], p["r"].iloc[:, 0]
    h, e = prognoza_har(rv), prognoza_dziennik(r)
    ok = h.notna() & e.notna()
    res = diebold_mariano(qlike(rv[ok], e[ok]), qlike(rv[ok], h[ok]))
    assert res["t"] > 1.96


def test_wybierz_monety():
    from modele.run_f21 import wybierz_monety

    sklad = {"2021-01-01": ["A", "B", "C"], "2021-02-01": ["B", "C", "D"], "2021-03-01": ["C", "D"]}
    assert wybierz_monety(sklad, 2) == ["C", "B"]


def test_f21_koniec_w_koniec_na_atrapie(tmp_path, capsys):
    """Cały skrypt F2-1 na syntetycznych świecach 5m (3 monety × 460 dni, krótki trening)."""
    import json

    from modele import run_f21

    rng = np.random.default_rng(5)
    p = generuj_panel(460, 3, seed=6)
    syms = ["AAAUSDT", "BBBUSDT", "CCCUSDT"]
    (tmp_path / "5m").mkdir()
    for j, s in enumerate(syms):
        var = np.repeat(p["sigma2"].iloc[:, j].to_numpy(), 288) / 288
        n = len(var)
        lr = rng.standard_normal(n) * np.sqrt(var)
        ts = pd.date_range("2021-01-01", periods=n, freq="5min", tz="UTC")
        pd.DataFrame({"timestamp": ts, "close": 100 * np.exp(np.cumsum(lr))}).to_parquet(
            tmp_path / "5m" / f"{s}.parquet"
        )
    (tmp_path / "sklad.json").write_text(json.dumps({"2021-01-01": syms}))
    run_f21.main(
        [
            "--dane",
            str(tmp_path / "5m"),
            "--sklad",
            str(tmp_path / "sklad.json"),
            "--reps",
            "50",
            "--min-trening",
            "120",
        ]
    )
    out = capsys.readouterr().out
    assert "Krok 1" in out and "MDE kryterium" in out
    assert ("NIEMIERZALNA" in out) or ("Kryterium F2" in out)


def test_f21_poprawka1_martwe_dni_i_rozlaczne_okresy(tmp_path, capsys):
    """P1: martwy ogon (stała cena) nie psuje HAR; P2: monety bez wspólnych dni OOS — bramka liczy się."""
    import json

    from modele import run_f21

    rng = np.random.default_rng(7)
    p = generuj_panel(700, 3, seed=8)
    syms = ["AAAUSDT", "BBBUSDT", "CCCUSDT"]
    (tmp_path / "5m").mkdir()
    for j, s in enumerate(syms):
        var = np.repeat(p["sigma2"].iloc[:, j].to_numpy(), 288) / 288
        lr = rng.standard_normal(len(var)) * np.sqrt(var)
        ts = pd.date_range("2021-01-01", periods=len(var), freq="5min", tz="UTC")
        close = 100 * np.exp(np.cumsum(lr))
        df = pd.DataFrame({"timestamp": ts, "close": close})
        if s == "AAAUSDT":  # wycofana po 330 dniach: dalej świece, ale cena stoi (jak FTM)
            df.loc[330 * 288 :, "close"] = close[330 * 288 - 1]
        if s == "CCCUSDT":  # notowana dopiero od dnia 400 (jak WIF)
            df = df.iloc[400 * 288 :]
        df.to_parquet(tmp_path / "5m" / f"{s}.parquet")
        if s == "AAAUSDT":
            st = run_f21.straty_monety(df, min_trening=120)
            assert st.index.max() < pd.Timestamp("2021-01-01", tz="UTC") + pd.Timedelta(days=331)
            assert np.isfinite(st[["q_dz", "q_har"]].to_numpy()).all()
    (tmp_path / "sklad.json").write_text(json.dumps({"2021-01-01": syms}))
    run_f21.main(
        ["--dane", str(tmp_path / "5m"), "--sklad", str(tmp_path / "sklad.json"), "--reps", "30"]
        + ["--min-trening", "120"]
    )
    out = capsys.readouterr().out
    assert "wspólne wszystkim monetom 0" in out and "MDE kryterium" in out
