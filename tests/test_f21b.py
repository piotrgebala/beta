"""F2-1b — dobór monet po długości, dni ważne, brak przecieku, kontrola pozytywna (syntetyczne)."""

from __future__ import annotations

import inspect
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from dane.dni import dni_wazne
from miara.dm import diebold_mariano
from modele import run_f21
from modele import run_f21b as b
from symulacje.garch_panel import generuj_panel

START = "2021-01-01"
T0 = pd.Timestamp(START, tz="UTC")


def _u(n_dni: int, **kw) -> b.Ustawienia:
    """Ustawienia na krótki okres syntetyczny (reszta jak w pre-rejestracji, o ile nie podano)."""
    return replace(b.Ustawienia(), okres_do=T0 + (n_dni - 1) * b.DZIEN, **kw)


def _swiece(n_dni: int, seed: int = 0, skala: float = 1.0) -> pd.DataFrame:
    p = generuj_panel(n_dni, 1, seed=seed)
    return b.swiece_syntetyczne(p["rv"].iloc[:, 0].to_numpy() * skala, START, seed=seed)


def _usun_dni(df: pd.DataFrame, od: int, ile: int) -> pd.DataFrame:
    """Dziura archiwum: `ile` dni bez żadnej świecy od dnia numer `od`."""
    t = df["timestamp"]
    out = (t >= T0 + od * b.DZIEN) & (t < T0 + (od + ile) * b.DZIEN)
    return df.loc[~out].reset_index(drop=True)


# ------------------------------------------------- dobór monet


def test_miesiace_top20_od_2021():
    sklad = {"2020-12-01": ["A"], "2021-01-01": ["A", "B"], "2021-02-01": ["B"]}
    assert b.miesiace_top20(sklad) == {"A": 1, "B": 2}


def _dostep(pierwszy: str, ostatni: str, udzial: float) -> dict:
    return {
        "pierwszy": pd.Timestamp(pierwszy, tz="UTC"),
        "ostatni": pd.Timestamp(ostatni, tz="UTC"),
        "dni_okresu": 2099,
        "wazne_w_okresie": int(udzial * 2099),
        "udzial": udzial,
    }


def test_dobierz_monety_progi_remis_i_limit():
    u = b.Ustawienia()
    pelny = _dostep("2021-01-02", "2026-09-30", 0.99)
    mies = {"AAA": 30, "BBB": 30, "CCC": 12, "DDD": 11, "EEE": 40, "FFF": 50, "GGG": 50, "HHH": 50}
    dostep = {
        "AAA": pelny,
        "BBB": pelny,
        "CCC": pelny,
        "DDD": pelny,  # < 12 miesięcy w top-20
        "EEE": _dostep("2021-02-01", "2026-09-30", 0.99),  # start po 2021-01-31
        "FFF": _dostep("2021-01-02", "2026-09-29", 0.99),  # koniec przed 2026-09-30
        "GGG": _dostep("2021-01-02", "2026-09-30", 0.949),  # udział < 95 %
        "HHH": None,  # brak danych
    }
    assert b.dobierz_monety(mies, dostep, u) == ["AAA", "BBB", "CCC"]
    assert b.dobierz_monety(mies, dostep, replace(u, k_max=2)) == ["AAA", "BBB"]
    assert b.dobierz_monety({"ZZZ": 12}, {}, u) == []


def test_dobor_wg_miesiecy_nie_alfabetu_i_granice_wlacznie():
    """Kolejność wg miesięcy (nie alfabetycznie); start = 2021-01-31 i udział = 95 % przechodzą."""
    u = b.Ustawienia()
    pelny = _dostep("2021-01-02", "2026-09-30", 0.99)
    mies = {"AAA": 20, "ZZZ": 40, "MMM": 30}
    dostep = {"AAA": pelny, "ZZZ": pelny, "MMM": pelny}
    assert b.dobierz_monety(mies, dostep, u) == ["ZZZ", "MMM", "AAA"]
    assert b.dobierz_monety(mies, dostep, replace(u, k_max=1)) == ["ZZZ"]
    graniczny = _dostep("2021-01-31", "2026-09-30", 0.95)
    assert b.kwalifikuje(graniczny, u)
    assert b.dobierz_monety({"GGG": 12}, {"GGG": graniczny}, u) == ["GGG"]


def test_dobor_korzysta_tylko_ze_skladu_i_dni_waznych():
    """Inne ceny i skala zmienności, ten sam wzór dni ważnych → ta sama dostępność i dobór."""
    n = 120
    u = _u(n, najpozniej_start=T0 + 30 * b.DZIEN)
    a = _usun_dni(_swiece(n, seed=1), 50, 2)
    c = _usun_dni(_swiece(n, seed=9, skala=25.0), 50, 2)
    da = b.dostepnosc(dni_wazne(a, wyklucz_po_dziurze=True), u)
    dc = b.dostepnosc(dni_wazne(c, wyklucz_po_dziurze=True), u)
    assert da == dc
    assert da["wazne_w_okresie"] == n - 1 - 2 - 1  # 1. dzień bez RV, 2 dni dziury, dzień po dziurze
    mies = {"AUSDT": 12, "CUSDT": 12}
    assert b.dobierz_monety(mies, {"AUSDT": da, "CUSDT": dc}, u) == ["AUSDT", "CUSDT"]
    assert list(inspect.signature(b.dobierz_monety).parameters) == ["miesiace", "dostep", "u"]


def test_dostepnosc_martwy_ogon_i_braki_poza_danymi():
    n = 100
    df = _swiece(n, seed=2)
    df.loc[df["timestamp"] >= T0 + 80 * b.DZIEN, "close"] = float(df["close"].iloc[80 * 288 - 1])
    df.loc[df["timestamp"] >= T0 + 80 * b.DZIEN, "volume"] = 0.0
    u = _u(n + 10)  # okres dłuższy niż dane: brakujące dni liczą się jako nieważne
    d = b.dostepnosc(dni_wazne(df, wyklucz_po_dziurze=True), u)
    assert d["ostatni"] == T0 + 79 * b.DZIEN
    assert d["dni_okresu"] == n + 10 and d["wazne_w_okresie"] == 79
    assert not b.kwalifikuje(d, u)


# ------------------------------------------------- dni ważne, obcięcie, dni OOS


def test_martwy_dzien_poza_maska_i_rv():
    """Dzień z wolumenem 0 przy RV > 0 (`martwy`) nie jest ważny i nie ma RV w szeregu."""
    df = _swiece(60, seed=11)
    dzien = T0 + 30 * b.DZIEN
    df.loc[(df["timestamp"] >= dzien) & (df["timestamp"] < dzien + b.DZIEN), "volume"] = 0.0
    dni = dni_wazne(df, wyklucz_po_dziurze=True)
    assert bool(dni.loc[dzien, "martwy"]) and not bool(b.maska_dni(dni)[dzien])
    rv, _ = b.szeregi_monety(df, _u(60))
    assert np.isnan(rv[dzien]) and rv[dzien - b.DZIEN] > 0


def test_parytet_z_f21_bez_flagi():
    """R2: bez `wyklucz_po_dziurze` straty F2-1b = `run_f21.straty_monety` (dziura, dzień niepełny,
    martwy ogon z RV = 0) — ta sama logika strat, inna tylko populacja monet."""
    n = 520
    df = _usun_dni(_swiece(n, seed=12), 300, 3)
    t = df["timestamp"]
    df = df.loc[~((t >= T0 + 350 * b.DZIEN) & (t < T0 + 350 * b.DZIEN + pd.Timedelta(hours=3)))]
    df = df.reset_index(drop=True)
    tail = df["timestamp"] >= T0 + 490 * b.DZIEN
    df.loc[tail, "close"] = float(df.loc[~tail, "close"].iloc[-1])
    df.loc[tail, "volume"] = 0.0
    u = _u(n, min_trening=120, wyklucz_po_dziurze=False)
    a = b.straty_monety_b(df, u)
    f = run_f21.straty_monety(df, min_trening=120, co_ile=30)
    assert len(a) > 200
    pd.testing.assert_frame_equal(a[f.columns], f)


def test_dzien_po_dziurze_wykluczony_z_rv():
    df = _usun_dni(_swiece(60, seed=3), 40, 1)
    u = _u(60)
    rv, r = b.szeregi_monety(df, u)
    po = T0 + 41 * b.DZIEN
    assert np.isnan(rv[po]) and np.isfinite(r[po])
    rv0, _ = b.szeregi_monety(df, replace(u, wyklucz_po_dziurze=False))
    assert rv0[po] > 0
    assert (T0 + 40 * b.DZIEN) not in rv.index  # dzień bez świec nie jest wierszem (jak F2-1)


def test_dni_oos_zgodne_ze_stratami():
    """Dni OOS z wzoru braków = dni strat; z dziurą, martwym ogonem i dniem niepełnym."""
    n = 500
    df = _usun_dni(_swiece(n, seed=4), 300, 3)
    t = df["timestamp"]
    df = df.loc[~((t >= T0 + 350 * b.DZIEN) & (t < T0 + 350 * b.DZIEN + pd.Timedelta(hours=3)))]
    df = df.reset_index(drop=True)
    tail = df["timestamp"] >= T0 + 470 * b.DZIEN
    df.loc[tail, "close"] = float(df.loc[~tail, "close"].iloc[-1])
    df.loc[tail, "volume"] = 0.0
    u = _u(n, min_trening=120)
    st = b.straty_monety_b(df, u)
    assert len(st) > 200
    assert st.index.equals(b.dni_oos(df, u))
    assert np.isfinite(st[["q_dz", "q_har", "m_dz", "m_har"]].to_numpy()).all()
    assert st.index.max() < T0 + 470 * b.DZIEN


def test_obciecie_na_okres_do():
    df = _swiece(400, seed=5)
    u = _u(350, min_trening=120)
    a = b.straty_monety_b(df, u)
    c = b.straty_monety_b(df.loc[df["timestamp"] < T0 + 350 * b.DZIEN], u)
    pd.testing.assert_frame_equal(a, c)
    assert a.index.max() == u.okres_do


# ------------------------------------------------- R7: brak przecieku


@pytest.mark.parametrize("k", [250, 333])
def test_bez_przecieku_zaklocenie_i_obciecie(k):
    """Prognozy dni ≤ k+1 nie zależą od świec po dniu k (zakłócenie) ani od ich istnienia."""
    n = 420
    df = _usun_dni(_swiece(n, seed=6), 200, 2)
    u = _u(n, min_trening=120)
    granica = T0 + (k + 1) * b.DZIEN
    po = df["timestamp"] >= granica
    lr = np.log(df["close"]).diff().fillna(0.0).to_numpy()
    rng = np.random.default_rng(7)
    lr2 = np.where(po, lr * rng.uniform(0.0, 5.0, len(lr)) + rng.normal(0, 0.01, len(lr)), lr)
    zak = df.assign(close=float(df["close"].iloc[0]) * np.exp(np.cumsum(lr2)))
    zak.loc[po, "volume"] = rng.uniform(0, 3, int(po.sum()))
    p = b.prognozy(*b.szeregi_monety(df, u), u)[["f_dz", "f_har"]]
    pz = b.prognozy(*b.szeregi_monety(zak, u), u)[["f_dz", "f_har"]]
    assert p.loc[:granica].notna().any().all()
    pd.testing.assert_frame_equal(p.loc[:granica], pz.loc[:granica])
    po_obc = b.prognozy(*b.szeregi_monety(df.loc[~po], u), u)[["f_dz", "f_har"]]
    pd.testing.assert_frame_equal(p.loc[: granica - b.DZIEN], po_obc)


# ------------------------------------------------- R8: kontrola pozytywna, determinizm


def test_kontrola_pozytywna_garch():
    """GARCH z trwałą zmiennością: pipeline F2-1b (5m → dni ważne → HAR vs EWMA 60), t > 1,96."""
    n = 2100
    df = _swiece(n, seed=8)
    st = b.straty_monety_b(df, _u(n))
    assert len(st) > 1600
    assert diebold_mariano(st["q_dz"], st["q_har"])["t"] > 1.96


def _katalog(tmp_path, n: int, syms: list[str], dziura: str | None = None) -> None:
    for j, s in enumerate(syms):
        df = _swiece(n, seed=20 + j)
        if s == dziura:
            df = _usun_dni(df, 100, 40)
        df.to_parquet(tmp_path / f"{s}.parquet")


def test_przebieg_koniec_w_koniec_i_determinizm(tmp_path, capsys):
    n = 520
    syms = ["AAAUSDT", "BBBUSDT", "CCCUSDT", "DDDUSDT"]
    _katalog(tmp_path, n, syms, dziura="DDDUSDT")
    sklad = {f"2021-{m:02d}-01": syms for m in range(1, 13)}
    u = _u(n, k_min=3, min_trening=120, reps=30)
    b.przebieg(sklad, tmp_path, u, tylko_monety=True)
    out1 = capsys.readouterr().out
    assert "K = min(20, 3) = 3" in out1 and "DDDUSDT" in out1
    assert "monety (3): AAAUSDT, BBBUSDT, CCCUSDT" in out1
    assert "Krok 1" not in out1 and "--tylko-monety: koniec" in out1
    b.przebieg(sklad, tmp_path, u, tylko_monety=True)
    assert capsys.readouterr().out == out1
    b.przebieg(sklad, tmp_path, u, tylko_monety=False)
    out2 = capsys.readouterr().out
    assert "dni OOS z wzoru braków u wszystkich monet: tak" in out2
    assert "Krok 1" in out2 and "MDE kryterium" in out2
    assert ("NIEMIERZALNA: test DM NIE" in out2) or ("Kryterium F2-1b" in out2)
    assert "zgodność z pre-rejestracją" not in out2  # bez `oczekiwane` (testy, smoke)


# ------------------------------------------------- reguła decyzji i gałęzie przebiegu


def test_werdykt_wektory():
    z = 2.0
    w = b.werdykt([z] * 12 + [0.0] * 3, 0.8)
    assert (w["k"], w["need"], w["good"], w["bad"], w["ok"]) == (15, 12, 12, 0, True)
    assert not b.werdykt([z] * 11 + [0.0] * 4, 0.8)["ok"]
    w = b.werdykt([z] * 12 + [0.0, 0.0, -2.0], 0.8)
    assert w["bad"] == 1 and not w["ok"]
    w = b.werdykt([b.Z] * 15, 0.8)  # dokładnie 1,96 nie jest „dobre”
    assert w["good"] == 0 and not w["ok"]
    assert b.werdykt([-b.Z] * 15, 0.8)["bad"] == 0
    assert b.werdykt([z] * 5, 0.8)["need"] == 4
    assert b.werdykt([z] * 20, 0.8)["need"] == 16
    assert b.werdykt([-z] * 15, 0.8)["good"] == 0  # znak: t < 0 = dziennik lepszy


def _g(mde: float) -> dict:
    return {
        "dni_kalendarza": 1, "dni_wspolne": 1, "n_mediana": 1, "neff_n": 1.0, "korel_D": 0.0,
        "mde_kryterium": mde, "mde_moneta": mde,
    }  # fmt: skip


@pytest.fixture
def maly_katalog(tmp_path):
    n = 520
    syms = ["AAAUSDT", "BBBUSDT", "CCCUSDT"]
    _katalog(tmp_path, n, syms)
    sklad = {f"2021-{m:02d}-01": syms for m in range(1, 13)}
    return sklad, tmp_path, _u(n, k_min=3, min_trening=120, reps=10)


def test_bramka_niemierzalna_konczy_bez_dm(maly_katalog, monkeypatch, capsys):
    sklad, dane, u = maly_katalog

    def dm_zakazany(st):
        raise AssertionError("test DM przy NIEMIERZALNEJ")

    monkeypatch.setattr(b, "test_dm", dm_zakazany)
    monkeypatch.setattr(b, "bramka_mde", lambda st, reps: _g(0.101))
    b.przebieg(sklad, dane, u, tylko_monety=False)
    out = capsys.readouterr().out
    assert "NIEMIERZALNA: test DM NIE" in out and "Krok 2" not in out


def test_bramka_rowna_progowi_uruchamia_krok_2(maly_katalog, monkeypatch, capsys):
    sklad, dane, u = maly_katalog
    wywolania = []

    def dm(st):
        wywolania.append(sorted(st))
        return [
            {"symbol": s, "n": 1, "od": "x", "t_qlike": t, "delta": 0.0, "t_mse_log": 0.0,
             "skala_rv_do_r2": 1.0}
            for s, t in zip(sorted(st), [2.5, 2.5, -2.5])
        ]  # fmt: skip

    monkeypatch.setattr(b, "test_dm", dm)
    monkeypatch.setattr(b, "bramka_mde", lambda st, reps: _g(0.10))
    b.przebieg(sklad, dane, u, tylko_monety=False)
    out = capsys.readouterr().out
    assert wywolania == [["AAAUSDT", "BBBUSDT", "CCCUSDT"]]
    assert "MIERZALNA: krok 2" in out
    assert "t > 1,96 w 2/3 monet (wymagane ≥ 3), t < −1,96: 1 → NIEPOZYTYWNY" in out


def test_stop_gdy_dni_strat_rozne_od_oos(maly_katalog, monkeypatch, capsys):
    sklad, dane, u = maly_katalog
    oryg = b.straty_monety_b
    monkeypatch.setattr(b, "straty_monety_b", lambda df, u: oryg(df, u).iloc[1:])
    monkeypatch.setattr(b, "bramka_mde", lambda st, reps: pytest.fail("bramka po NIE"))
    b.przebieg(sklad, dane, u, tylko_monety=False)
    out = capsys.readouterr().out
    assert "u wszystkich monet: NIE" in out and "STOP przed Krokiem 1" in out
    assert "Krok 1 —" not in out


def test_zgodnosc_z_pre_rejestracja(maly_katalog, monkeypatch, capsys):
    """Różne monety / dni OOS / odcisk niż w pre-rejestracji → stop przed stratami."""
    sklad, dane, u = maly_katalog
    b.przebieg(sklad, dane, u, tylko_monety=True)
    out = capsys.readouterr().out
    odcisk = out.split("odcisk dni OOS ")[1].split()[0]
    n_oos = int(out.split("AAAUSDT ")[-1].split()[0])
    dobre = {
        "monety": ("AAAUSDT", "BBBUSDT", "CCCUSDT"),
        "dni_oos": {s: n_oos for s in ("AAAUSDT", "BBBUSDT", "CCCUSDT")},
        "odcisk": odcisk,
    }
    monkeypatch.setattr(b, "bramka_mde", lambda st, reps: _g(0.5))
    b.przebieg(sklad, dane, u, tylko_monety=False, oczekiwane=dobre)
    out = capsys.readouterr().out
    assert "zgodność z pre-rejestracją (monety, dni OOS, odcisk): tak" in out and "Krok 1" in out
    zle = [
        dobre | {"monety": ("AAAUSDT", "CCCUSDT", "BBBUSDT")},
        dobre | {"dni_oos": dobre["dni_oos"] | {"BBBUSDT": n_oos - 1}},
        dobre | {"odcisk": "0" * 16},
    ]
    monkeypatch.setattr(b, "straty_monety_b", lambda df, u: pytest.fail("straty po NIE"))
    for oczekiwane in zle:
        b.przebieg(sklad, dane, u, tylko_monety=False, oczekiwane=oczekiwane)
        out = capsys.readouterr().out
        assert "pre-rejestracją (monety, dni OOS, odcisk): NIE" in out
        assert "STOP przed stratami" in out and "Krok 1" not in out


def test_ustawienia_i_oczekiwane_z_pre_rejestracji():
    u = b.Ustawienia()
    assert (u.okres_od, u.okres_do, u.najpozniej_start) == (
        pd.Timestamp("2021-01-01", tz="UTC"),
        pd.Timestamp("2026-09-30", tz="UTC"),
        pd.Timestamp("2021-01-31", tz="UTC"),
    )
    assert (u.min_miesiecy, u.min_udzial, u.k_max, u.k_min) == (12, 0.95, 20, 12)
    assert (u.udzial_kryterium, u.wyklucz_po_dziurze) == (0.8, True)
    assert (u.min_trening, u.co_ile, u.reps) == (365, 30, 1000)
    assert u.udzial_kryterium == b.UDZIAL_BRAMKI
    assert len(b.OCZEKIWANE_MONETY) == 15 and set(b.OCZEKIWANE_DNI_OOS) == set(b.OCZEKIWANE_MONETY)
    assert sorted(b.OCZEKIWANE_DNI_OOS.values()) == [1636] * 5 + [1703] * 10


def test_smoke_kontrola_pozytywna(capsys):
    b.smoke()
    out = capsys.readouterr().out
    assert "→ MIERZALNA" in out and "→ POZYTYWNY" in out


def test_k_ponizej_minimum_to_niemierzalna(tmp_path, capsys):
    n = 200
    syms = ["AAAUSDT", "BBBUSDT"]
    _katalog(tmp_path, n, syms)
    sklad = {f"2021-{m:02d}-01": syms for m in range(1, 13)}
    b.przebieg(sklad, tmp_path, _u(n, min_trening=60), tylko_monety=False)
    out = capsys.readouterr().out
    assert "K = 2 < 12: runda NIEMIERZALNA z definicji" in out
    assert "Krok 1" not in out and "Dni OOS" not in out
