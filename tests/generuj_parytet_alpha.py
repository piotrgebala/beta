"""
Generator wartości oczekiwanych parytetu: liczy wektory z `tests/wektory_parytetu.py` KODEM ALPHA
i zapisuje `tests/fixtures/parytet_alpha.json` z hashem commita alpha.

Alpha tylko do odczytu (zasada 23): moduły alpha importujemy z `data.alpha_repo`; zależności,
których przenoszone funkcje nie używają (talib, xgboost, ccxt…), zastępujemy pustymi atrapami.

    python -m tests.generuj_parytet_alpha
"""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
import types
from pathlib import Path

import yaml

from tests.wektory_parytetu import FUNKCJE, wykonaj

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "parytet_alpha.json"


def _alpha_root() -> Path:
    cfg = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    return (ROOT / cfg["data"]["alpha_repo"]).resolve()


class _Atrapa(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _Atrapa(f"{self.__name__}.{name}")

    def __call__(self, *a, **k):
        return _Atrapa(self.__name__ + "()")


def _importuj(modul: str):
    for _ in range(50):
        try:
            return importlib.import_module(modul)
        except ModuleNotFoundError as exc:
            brak = exc.name
            if brak is None or brak.split(".")[0] in ("backtest", "agents", "data", "tools"):
                raise
            sys.modules[brak] = _Atrapa(brak)
    raise RuntimeError(f"nie udało się zaimportować {modul}")


def main() -> None:
    sys.dont_write_bytecode = True  # żadnych plików __pycache__ w katalogu alpha
    alpha = _alpha_root()
    commit = subprocess.check_output(
        ["git", "-C", str(alpha), "rev-parse", "HEAD"], text=True
    ).strip()
    brudne = subprocess.check_output(["git", "-C", str(alpha), "status", "--porcelain"], text=True)
    if brudne.strip():
        raise SystemExit(
            "alpha ma niezatwierdzone zmiany — parytet liczymy tylko z czystego commita"
        )
    sys.path.insert(0, str(alpha))
    zrodla = {}
    for fn, (mod_alpha, _) in FUNKCJE.items():
        m = _importuj(mod_alpha)
        zrodla[fn] = getattr(m, fn)
        plik = Path(m.__file__)
        zrodla.setdefault("__pliki__", {})[plik.relative_to(alpha).as_posix()] = hashlib.sha256(
            plik.read_bytes()
        ).hexdigest()
    pliki = zrodla.pop("__pliki__")
    wyniki = wykonaj(lambda name: zrodla[name])
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(
        json.dumps(
            {
                "alpha_commit": commit,
                "alpha_pliki_sha256": dict(sorted(pliki.items())),
                "wyniki": wyniki,
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(wyniki)} przypadków, alpha {commit[:7]} → {FIXTURE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
