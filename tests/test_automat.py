"""
Automat (012): `narzedzia/automat.sh` na tymczasowym repo git z atrapą interpretera Pythona.

Bez sieci i bez prawdziwego remote: kroki pobierania zastępuje atrapa w `.venv/bin/python`,
a „zdalne” repo to lokalne repo bare w katalogu tymczasowym. Testy kluczowe: commit i push
obejmują WYŁĄCZNIE pliki wyniku (cudze zmiany w tych samych katalogach zostają), skrypt nie
pushuje cudzych commitów, nie commituje na zmienionej w trakcie gałęzi, ginie razem z krokiem
po sygnale i nie zatwierdza niekompletnego pobrania.
"""

from __future__ import annotations

import calendar
import fcntl
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from narzedzia import kontrola_miesiaca, ostatni_dzien_miesiaca, sprawdz_pobranie

KORZEN = Path(__file__).resolve().parents[1]
SKRYPT = KORZEN / "narzedzia" / "automat.sh"
CRONTAB = SKRYPT.with_name("crontab.txt")
TRYBY = ("codziennie", "miesiac", "niedziela")
DZIEN = "2026-10-06"  # wtorek
DZIEN_NIEDZIELI = "2026-10-11"  # niedziela tygodnia 2026-W41
GALAZ = "automat-test"
ZNACZNIK = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z \[(codziennie|miesiac|niedziela)\] ")
IZOLACJA_GITA = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}
WYNIKI_TRYBOW = {
    "codziennie": ["dane/manifest_deribit_dvol.json"],
    "miesiac": ["dane/manifest_binance_um.json", "dane/sklad_top20.json"],
    "niedziela": ["raporty/tygodnie/2026-W41.md"],
}

ATRAPA = r"""#!/usr/bin/env bash
# Atrapa interpretera: zapisuje wywołania i udaje kroki automatu (bez sieci).
katalog=$(dirname "$0")
echo "$*" >> "$katalog/wywolania.txt"
if [[ $1 == -c ]]; then
  if [[ $2 == "from narzedzia"* ]]; then # kontrola miesiąca: prawdziwy kod z repo
    PYTHONPATH="$ATRAPA_KORZEN" exec "$ATRAPA_PYTHON" "$@"
  fi
  if [[ ${ATRAPA_IMPORT_BLAD:-} == 1 ]]; then echo "ImportError: atrapa" >&2; exit 1; fi
  exit 0
fi
if [[ -n ${ATRAPA_SPANIE:-} ]]; then # krok, który się nie kończy (limit czasu, sygnał)
  if [[ ${ATRAPA_IGNORUJ_TERM:-} == 1 ]]; then trap '' TERM; fi # także potomek ignoruje TERM
  sleep "$ATRAPA_SPANIE" &
  echo $! > "$katalog/sen.pid"
  echo $$ > "$katalog/krok.pid"
  wait
  exit 0
fi
if [[ ${ATRAPA_ZABIJ:-} == 1 ]]; then kill -9 $$; fi
if [[ ${ATRAPA_KOD:-0} != 0 ]]; then echo "atrapa: krok zawiódł" >&2; exit "$ATRAPA_KOD"; fi
if [[ ${ATRAPA_PRZEL_GALAZ:-} == 1 ]]; then git checkout -q -b main; fi
if [[ ${ATRAPA_TLO:-} == 1 ]]; then # osierocony potomek, który przeżyje krok
  sleep 300 >/dev/null 2>&1 &
  echo $! > "$katalog/tlo.pid"
fi
if [[ ${ATRAPA_BEZ_WYNIKU:-} == 1 ]]; then echo "atrapa: bez wyniku"; exit 0; fi
tresc=${ATRAPA_TRESC:-stala}
case "$2" in
  dane.deribit_dvol)
    printf '{"tresc": "%s", "koniec": "%s"}\n' "$tresc" "$4" > dane/manifest_deribit_dvol.json
    echo "DVOL BTC: 10 dni"
    ;;
  dane.binance_vision)
    koniec=${!#} # ostatni argument: RRRR-MM
    swieca=${ATRAPA_SWIECA:-$(date -u -d "$koniec-01 +1 month -1 day" +%F)}
    printf '{"tresc": "%s", "do": "%s", "jakosc": {"BTCUSDT/5m": {"do": "%s 23:55:00+00:00"},
      "BTCUSDT/1d": {"do": "%s 00:00:00+00:00"}}}\n' \
      "$tresc" "${ATRAPA_DO:-$koniec}" "$swieca" "$swieca" > dane/manifest_binance_um.json
    printf '{"%s-01": ["BTCUSDT", "%s"]}\n' "${ATRAPA_SKLAD_DO:-$koniec}" "$tresc" \
      > dane/sklad_top20.json
    mkdir -p data/binance_um && echo x > data/binance_um/BTCUSDT.parquet
    echo "BTCUSDT 5m: 100 świec"
    ;;
  raporty.tydzien)
    plik="raporty/tygodnie/$(date -u -d "$4" +%G-W%V).md"
    kom=""
    if [[ -f $plik && ${ATRAPA_PSUJ:-} != 1 ]]; then
      kom=$(sed -n '/<!-- komentarz -->/,/<!-- \/komentarz -->/p' "$plik")
    fi
    if [[ -z $kom ]]; then kom=$'<!-- komentarz -->\n_(pusty)_\n<!-- /komentarz -->'; fi
    printf '# Raport tresc=%s\n\n%s\n' "$tresc" "$kom" > "$plik"
    echo "raport: $plik"
    ;;
esac
"""
RAPORT_START = (
    "# Raport tresc=start\n\n<!-- komentarz -->\nKomentarz Claude v1\n<!-- /komentarz -->\n"
)


@dataclass
class Srodowisko:
    korzen: Path

    @property
    def repo(self) -> Path:
        return self.korzen / "beta"

    @property
    def zdalne(self) -> Path:
        return self.korzen / "zdalne.git"

    @property
    def logi(self) -> Path:
        return self.korzen / "logi"

    @property
    def atrapa_dir(self) -> Path:
        return self.repo / ".venv" / "bin"

    def wywolania(self) -> list[str]:
        plik = self.atrapa_dir / "wywolania.txt"
        return plik.read_text(encoding="utf-8").splitlines() if plik.exists() else []

    def wywolania_krokow(self) -> list[str]:
        """Tylko uruchomienia kroków (`-m ...`), bez kontroli importu i kontroli miesiąca."""
        return [w for w in self.wywolania() if w.startswith("-m")]

    def pid(self, nazwa: str) -> int:
        return int((self.atrapa_dir / nazwa).read_text(encoding="utf-8").strip())

    def log(self, tryb: str, dzien: str = DZIEN) -> str:
        return (self.logi / f"{dzien}_{tryb}.log").read_text(encoding="utf-8")

    def status(self, tryb: str) -> str:
        return (self.logi / f"ostatni_status_{tryb}.txt").read_text(encoding="utf-8")


def git(katalog: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(katalog), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **IZOLACJA_GITA},
    )
    return out.stdout.rstrip("\n")


def zbuduj_srodowisko(korzen: Path) -> Srodowisko:
    s = Srodowisko(korzen)
    (korzen / "alpha" / "data" / "raw" / "universe_full").mkdir(parents=True)
    git(korzen, "init", "-q", "--bare", "-b", GALAZ, str(s.zdalne))
    (s.repo / "dane").mkdir(parents=True)
    (s.repo / "raporty" / "tygodnie").mkdir(parents=True)
    s.atrapa_dir.mkdir(parents=True)
    atrapa = s.atrapa_dir / "python"
    atrapa.write_text(ATRAPA, encoding="utf-8")
    atrapa.chmod(0o755)
    (s.repo / ".gitignore").write_text(".venv/\n", encoding="utf-8")  # data/ celowo NIE ignorowane
    for nazwa in ("manifest_deribit_dvol.json", "manifest_binance_um.json", "sklad_top20.json"):
        (s.repo / "dane" / nazwa).write_text('{"tresc": "start"}\n', encoding="utf-8")
    (s.repo / "raporty" / "tygodnie" / "2026-W41.md").write_text(RAPORT_START, encoding="utf-8")
    (s.repo / "notatki.txt").write_text("v1\n", encoding="utf-8")
    git(s.repo, "init", "-q", "-b", GALAZ)
    git(s.repo, "config", "user.name", "Test")
    git(s.repo, "config", "user.email", "test@example.com")
    git(s.repo, "config", "commit.gpgsign", "false")
    git(s.repo, "remote", "add", "origin", str(s.zdalne))
    git(s.repo, "add", "-A")
    git(s.repo, "commit", "-q", "-m", "start")
    git(s.repo, "push", "-q", "origin", GALAZ)
    return s


@pytest.fixture
def srodowisko(tmp_path: Path) -> Srodowisko:
    return zbuduj_srodowisko(tmp_path)


def env_biegu(s: Srodowisko, tryb: str, dzien: str | None, **env_extra: str | None) -> dict:
    """Środowisko biegu; wartość None w `env_extra` usuwa zmienną."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("AUTOMAT_", "ATRAPA_"))}
    dzien = dzien or (DZIEN_NIEDZIELI if tryb == "niedziela" else DZIEN)
    env.update(IZOLACJA_GITA)
    env.update(
        AUTOMAT_REPO=str(s.repo),
        AUTOMAT_LOG_DIR=str(s.logi),
        AUTOMAT_DATA=dzien,
        AUTOMAT_CZEKAJ_S="2",
        AUTOMAT_PONOW_S="0",  # w testach ponowienia git add/commit nie czekają
        ATRAPA_KORZEN=str(KORZEN),
        ATRAPA_PYTHON=sys.executable,
    )
    for k, v in env_extra.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    return env


def uruchom(s: Srodowisko, tryb: str, dzien: str | None = None, **env_extra: str | None):
    return subprocess.run(
        [str(SKRYPT), tryb],
        env=env_biegu(s, tryb, dzien, **env_extra),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def uruchom_w_tle(s: Srodowisko, tryb: str, **env_extra: str | None) -> subprocess.Popen:
    """Bieg w nowej sesji (bez terminala): sygnał idzie tylko do skryptu, jak z crona."""
    return subprocess.Popen(
        [str(SKRYPT), tryb],
        env=env_biegu(s, tryb, None, **env_extra),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )


def stan_git(s: Srodowisko) -> tuple[str, str]:
    return git(s.repo, "rev-parse", "HEAD"), git(s.repo, "status", "--porcelain")


def ostatnia_linia(log: str) -> str:
    return log.rstrip("\n").splitlines()[-1]


def zyje(pid: int) -> bool:
    """Czy proces działa (zombie, czyli proces zakończony, ale nieodebrany, nie liczy się)."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except OSError:
        return False
    return stat.rsplit(")", 1)[1].split()[0] not in ("Z", "X")


def grupy_sesji(sid: int) -> dict[int, int]:
    """pid -> numer grupy procesów dla wszystkich procesów sesji `sid` (odczyt z /proc)."""
    wynik: dict[int, int] = {}
    for katalog in Path("/proc").iterdir():
        if not katalog.name.isdigit():
            continue
        try:
            pola = (katalog / "stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()
        except OSError:
            continue  # proces zdążył zniknąć
        if int(pola[3]) == sid:  # pola: stan, ppid, grupa, sesja
            wynik[int(katalog.name)] = int(pola[2])
    return wynik


def zabij_grupe(grupa: int) -> None:
    try:
        os.killpg(grupa, signal.SIGKILL)
    except ProcessLookupError:
        pass


def czekaj_na(warunek: Callable[[], bool], limit: float = 10.0) -> bool:
    koniec = time.monotonic() + limit
    while time.monotonic() < koniec:
        try:
            if warunek():
                return True
        except (OSError, ValueError):
            pass
        time.sleep(0.05)
    return False


def blokada_wolna(s: Srodowisko) -> bool:
    with open(s.logi / ".automat.lock", "a") as uchwyt:
        try:
            fcntl.flock(uchwyt, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
    return True


def zainstaluj_hak(s: Srodowisko, nazwa: str, tresc: str) -> Path:
    hak = s.repo / ".git" / "hooks" / nazwa
    hak.write_text(f"#!/bin/sh\n{tresc}\n", encoding="utf-8")
    hak.chmod(0o755)
    return hak


def polecenie_z_logu(log: str) -> list[str]:
    linia = next(w for w in log.splitlines() if "[DRY-RUN] polecenie:" in w)
    return shlex.split(linia.split("[DRY-RUN] polecenie:", 1)[1])


def cudzy_commit_na_origin(s: Srodowisko) -> str:
    """Inny klon dopisuje commit do zdalnej gałęzi; zwraca jej nowy SHA."""
    inny = s.korzen / "inny_klon"
    git(s.korzen, "clone", "-q", str(s.zdalne), str(inny))
    git(inny, "config", "user.name", "Inny")
    git(inny, "config", "user.email", "inny@example.com")
    (inny / "cudzy_plik.txt").write_text("z innego klona\n", encoding="utf-8")
    git(inny, "add", "cudzy_plik.txt")
    git(inny, "commit", "-q", "-m", "cudzy commit")
    git(inny, "push", "-q", "origin", GALAZ)
    return git(s.zdalne, "rev-parse", GALAZ)


# --- składnia i higiena skryptu ---


def test_skladnia_bash():
    subprocess.run(["bash", "-n", str(SKRYPT)], check=True)


def test_shellcheck():
    if shutil.which("shellcheck") is None:
        pytest.skip("shellcheck niedostępny w środowisku")
    subprocess.run(["shellcheck", "-x", str(SKRYPT)], check=True)


def test_skrypt_wykonywalny():
    assert os.access(SKRYPT, os.X_OK)


def kod_skryptu() -> str:
    linie = [w for w in SKRYPT.read_text(encoding="utf-8").splitlines() if w.lstrip()[:1] != "#"]
    return "\n".join(linie)


def test_skrypt_bez_wymuszania_pusha_i_szerokiego_add():
    tekst = kod_skryptu()
    for zakazane in ("--force", "--no-verify", "push -f", "push +", "reset --hard", "git clean"):
        assert zakazane not in tekst, zakazane
    assert not re.search(r"\badd\s+(-A|--all|-u|\.)(\s|$)", tekst)


def test_skrypt_push_i_commit_zawsze_ze_sciezkami():
    tekst = kod_skryptu()
    assert re.search(r'push origin "\$glowa:refs/heads/\$GALAZ"', tekst)  # po SHA, bez wymuszania
    assert re.search(r'\badd -- "\$\{WYNIKI\[@\]\}"', tekst)
    assert re.search(r'-m "\$OPIS_COMMITA" -- "\$\{WYNIKI\[@\]\}"', tekst)


def test_pomoc_konczy_sie_kodem_zero():
    for opcja in ("--help", "-h"):
        r = subprocess.run([str(SKRYPT), opcja], capture_output=True, text=True, check=False)
        assert r.returncode == 0 and "Użycie" in r.stdout, opcja


# --- argumenty ---


def test_brak_argumentu(srodowisko):
    r = subprocess.run([str(SKRYPT)], capture_output=True, text=True, check=False)
    assert r.returncode == 2
    assert "Użycie" in r.stderr


def test_nieznany_tryb(srodowisko):
    r = uruchom(srodowisko, "wtorek")
    assert r.returncode == 2
    assert "nieznany tryb" in r.stderr and "Użycie" in r.stderr
    assert not srodowisko.logi.exists() or not list(srodowisko.logi.glob("*.log"))


def test_zbyt_wiele_argumentow(srodowisko):
    r = subprocess.run(
        [str(SKRYPT), "codziennie", "miesiac"], capture_output=True, text=True, check=False
    )
    assert r.returncode == 2


@pytest.mark.parametrize(
    ("zmienna", "zla"),
    [
        ("AUTOMAT_DATA", "2026-02-30"),
        ("AUTOMAT_DATA", "jutro"),
        ("AUTOMAT_CZEKAJ_S", "x"),
        ("AUTOMAT_LIMIT_KROKU_S", "x"),
        ("AUTOMAT_LIMIT_PUSH_S", "-5"),
        ("AUTOMAT_PONOW_S", "1.5"),
    ],
)
def test_zla_wartosc_zmiennej(srodowisko, zmienna, zla):
    r = uruchom(srodowisko, "codziennie", **{zmienna: zla})
    assert r.returncode == 2
    assert "Błąd" in r.stderr
    assert srodowisko.wywolania() == []


def test_zly_katalog_repo(srodowisko):
    r = uruchom(srodowisko, "codziennie", AUTOMAT_REPO=str(srodowisko.korzen / "nie_ma"))
    assert r.returncode == 1
    assert "katalog repo nie istnieje" in r.stderr


# --- DRY RUN: nic nie pobiera, nic nie commituje ---


@pytest.mark.parametrize("tryb", TRYBY)
def test_dry_run_trybu(srodowisko, tryb):
    s = srodowisko
    przed = stan_git(s)
    zdalne_przed = git(s.zdalne, "rev-parse", GALAZ)
    r = uruchom(s, tryb, AUTOMAT_DRY_RUN="1")
    assert r.returncode == 0, r.stdout + r.stderr
    dzien = DZIEN_NIEDZIELI if tryb == "niedziela" else DZIEN
    log = s.log(tryb, dzien)
    assert "[DRY-RUN]" in log and f"origin refs/heads/{GALAZ}" in log
    assert ostatnia_linia(log).endswith("STATUS: OK")
    assert log.count("STATUS:") == 1
    assert all(w.startswith("-c import") for w in s.wywolania())  # tylko kontrola importu
    assert stan_git(s) == przed
    assert git(s.zdalne, "rev-parse", GALAZ) == zdalne_przed


@pytest.mark.parametrize("tryb", TRYBY)
def test_dry_run_pliki_wyniku_i_polecenie(srodowisko, tryb):
    """Plan z DRY-RUN to dokładnie to, co dostanie interpreter (pełne linie poleceń)."""
    s = srodowisko
    dzien = DZIEN_NIEDZIELI if tryb == "niedziela" else DZIEN
    assert uruchom(s, tryb, AUTOMAT_DRY_RUN="1").returncode == 0
    log = s.log(tryb, dzien)
    assert f"[DRY-RUN] pliki wyniku: {' '.join(WYNIKI_TRYBOW[tryb])}\n" in log
    python = str(Path(os.path.realpath(s.repo)) / ".venv" / "bin" / "python")
    uniwersum = str(Path(os.path.realpath(s.korzen)) / "alpha" / "data" / "raw" / "universe_full")
    oczekiwane = {
        "codziennie": [python, "-m", "dane.deribit_dvol", "--koniec", "2026-10-06"],
        "miesiac": [python, "-m", "dane.binance_vision", "--tf", "5m", "1d", "--uniwersum"]
        + [uniwersum, "--top", "20", "--watki", "16", "--przyrostowo", "--koniec", "2026-09"],
        "niedziela": [python, "-m", "raporty.tydzien", "--data", "2026-10-11"],
    }[tryb]
    assert polecenie_z_logu(log) == oczekiwane


def test_dry_run_importuje_tez_moduly_pomocnika_miesiaca(srodowisko):
    assert uruchom(srodowisko, "miesiac", AUTOMAT_DRY_RUN="1").returncode == 0
    assert srodowisko.wywolania() == ["-c import dane.binance_vision, yaml, narzedzia"]


@pytest.mark.parametrize(("tryb", "limit"), [("codziennie", 1800), ("miesiac", 21600)])
def test_dry_run_domyslne_limity(srodowisko, tryb, limit):
    r = uruchom(srodowisko, tryb, AUTOMAT_DRY_RUN="1", AUTOMAT_CZEKAJ_S=None, AUTOMAT_PONOW_S=None)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"limity: krok {limit} s, push 600 s, blokada 1800 s" in srodowisko.log(tryb)


def test_dry_run_limity_z_zmiennych(srodowisko):
    r = uruchom(
        srodowisko,
        "codziennie",
        AUTOMAT_DRY_RUN="1",
        AUTOMAT_LIMIT_KROKU_S="7",
        AUTOMAT_LIMIT_PUSH_S="8",
        AUTOMAT_CZEKAJ_S="9",
    )
    assert r.returncode == 0
    assert "limity: krok 7 s, push 8 s, blokada 9 s" in srodowisko.log("codziennie")


def test_dry_run_bez_gita_nie_wymaga_repo(srodowisko):
    shutil.rmtree(srodowisko.repo / ".git")
    r = uruchom(srodowisko, "codziennie", AUTOMAT_DRY_RUN="1", AUTOMAT_BEZ_GITA="1")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "git pominięty" in srodowisko.log("codziennie")


def test_dry_run_zly_import_to_blad(srodowisko):
    r = uruchom(srodowisko, "codziennie", AUTOMAT_DRY_RUN="1", ATRAPA_IMPORT_BLAD="1")
    assert r.returncode != 0
    log = srodowisko.log("codziennie")
    assert "ImportError" in log
    assert "STATUS: BLAD" in ostatnia_linia(log)


def test_dry_run_brak_pythona_to_blad(srodowisko):
    (srodowisko.repo / ".venv" / "bin" / "python").unlink()
    r = uruchom(srodowisko, "miesiac", AUTOMAT_DRY_RUN="1")
    assert r.returncode != 0
    assert "brak interpretera" in srodowisko.log("miesiac")


def test_dry_run_miesiac_wymaga_uniwersum_alpha(srodowisko):
    shutil.rmtree(srodowisko.korzen / "alpha")
    r = uruchom(srodowisko, "miesiac", AUTOMAT_DRY_RUN="1")
    assert r.returncode != 0
    assert "uniwersum" in srodowisko.log("miesiac")


@pytest.mark.parametrize("tryb", TRYBY)
def test_polecenia_automatu_uzywaja_tylko_flag_istniejacych_w_modulach(srodowisko, tryb):
    """Kontrakt: każda flaga z linii poleceń automatu jest w `--help` prawdziwego modułu."""
    assert uruchom(srodowisko, tryb, AUTOMAT_DRY_RUN="1").returncode == 0
    dzien = DZIEN_NIEDZIELI if tryb == "niedziela" else DZIEN
    polecenie = polecenie_z_logu(srodowisko.log(tryb, dzien))
    modul = polecenie[polecenie.index("-m") + 1]
    flagi = [x for x in polecenie if x.startswith("--")]
    assert flagi
    pomoc = subprocess.run(
        [sys.executable, "-m", modul, "--help"],
        cwd=KORZEN,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    ).stdout
    for flaga in flagi:
        assert flaga in pomoc, f"{modul} nie ma flagi {flaga}"


# --- odmowy przed pracą: nic nie pobieramy, gdy potem nie da się commitować i wypchnąć ---


def _bez_origin(s: Srodowisko) -> None:
    git(s.repo, "remote", "remove", "origin")


def _galaz_poza_origin(s: Srodowisko) -> None:
    git(s.repo, "checkout", "-q", "-b", "tylko-lokalna")


def _master(s: Srodowisko) -> None:
    git(s.repo, "checkout", "-q", "-b", "master")


def _main(s: Srodowisko) -> None:
    git(s.repo, "checkout", "-q", "-b", "main")


def _odlaczony(s: Srodowisko) -> None:
    git(s.repo, "checkout", "-q", "--detach")


def _zly_origin(s: Srodowisko) -> None:
    git(s.repo, "remote", "set-url", "origin", str(s.korzen / "nie_ma_takiego.git"))


def _trwa_operacja(nazwa: str, katalog: bool = False) -> Callable[[Srodowisko], None]:
    def przygotuj(s: Srodowisko) -> None:
        sciezka = s.repo / ".git" / nazwa
        if katalog:
            sciezka.mkdir()
        else:
            sciezka.write_text(git(s.repo, "rev-parse", "HEAD") + "\n", encoding="utf-8")

    return przygotuj


ODMOWY = [
    pytest.param(_bez_origin, "brak zdalnego repo", id="bez-origin"),
    pytest.param(_galaz_poza_origin, "nie istnieje na origin", id="galaz-poza-origin"),
    pytest.param(_zly_origin, "brak dostępu do origin", id="origin-nieosiagalny"),
    pytest.param(_master, "przez PR", id="master"),
    pytest.param(_main, "przez PR", id="main"),
    pytest.param(_odlaczony, "odłączony", id="odlaczony-head"),
    pytest.param(_trwa_operacja("MERGE_HEAD"), "MERGE_HEAD", id="trwa-merge"),
    pytest.param(_trwa_operacja("CHERRY_PICK_HEAD"), "CHERRY_PICK_HEAD", id="trwa-cherry-pick"),
    pytest.param(_trwa_operacja("REVERT_HEAD"), "REVERT_HEAD", id="trwa-revert"),
    pytest.param(_trwa_operacja("rebase-merge", True), "rebase-merge", id="trwa-rebase-merge"),
    pytest.param(_trwa_operacja("rebase-apply", True), "rebase-apply", id="trwa-rebase-apply"),
]


@pytest.mark.parametrize("dry_run", [None, "1"], ids=["bieg", "dry-run"])
@pytest.mark.parametrize(("przygotuj", "komunikat"), ODMOWY)
def test_odmowa_przed_krokiem(srodowisko, przygotuj, komunikat, dry_run):
    s = srodowisko
    przygotuj(s)
    zdalne = git(s.zdalne, "rev-parse", GALAZ)
    r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa", AUTOMAT_DRY_RUN=dry_run)
    assert r.returncode != 0, r.stdout + r.stderr
    log = s.log("codziennie")
    assert komunikat in log and "STATUS: BLAD" in ostatnia_linia(log)
    assert s.wywolania_krokow() == []  # odmowa PRZED pobieraniem
    assert git(s.zdalne, "rev-parse", GALAZ) == zdalne


def test_odmowa_gdy_repo_jest_podkatalogiem_cudzego_repo(srodowisko):
    s = srodowisko
    pod = s.repo / "pod"
    (pod / ".venv" / "bin").mkdir(parents=True)
    shutil.copy2(s.atrapa_dir / "python", pod / ".venv" / "bin" / "python")
    r = uruchom(s, "codziennie", AUTOMAT_REPO=str(pod))
    assert r.returncode != 0
    assert "nie jest korzeniem repo" in s.log("codziennie")
    assert s.wywolania_krokow() == []


def test_odmowa_na_main_bez_zgody_i_zgoda_na_zadanie(srodowisko):
    s = srodowisko
    git(s.repo, "checkout", "-q", "-b", "main")
    assert uruchom(s, "codziennie", ATRAPA_TRESC="nowa").returncode != 0
    assert uruchom(s, "codziennie", ATRAPA_TRESC="nowa", AUTOMAT_PUSH_MAIN="1").returncode != 0
    git(s.repo, "push", "-q", "origin", "main")  # gałąź musi istnieć na origin
    assert uruchom(s, "codziennie", ATRAPA_TRESC="nowa", AUTOMAT_PUSH_MAIN="1").returncode == 0
    assert git(s.zdalne, "rev-parse", "main") == git(s.repo, "rev-parse", "HEAD")


# --- dzienniki, status, alarm ---


def test_znaczniki_czasu_utc_mimo_innej_strefy(srodowisko):
    przed = datetime.now(UTC)
    r = uruchom(srodowisko, "codziennie", AUTOMAT_BEZ_GITA="1", TZ="Asia/Tokyo")
    po = datetime.now(UTC)
    assert r.returncode == 0, r.stdout + r.stderr
    linie = srodowisko.log("codziennie").splitlines()
    assert all(ZNACZNIK.match(w) for w in linie), linie
    start = datetime.strptime(linie[0][:20], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    assert przed.replace(microsecond=0) <= start <= po
    assert any(w.endswith("| DVOL BTC: 10 dni") for w in linie)  # wyjście kroku też ma znacznik


def test_domyslny_katalog_logow_to_beta_logi_w_home(srodowisko, tmp_path):
    dom = tmp_path / "home"
    dom.mkdir()
    r = uruchom(srodowisko, "codziennie", AUTOMAT_DRY_RUN="1", AUTOMAT_LOG_DIR=None, HOME=str(dom))
    assert r.returncode == 0, r.stdout + r.stderr
    assert (dom / "beta_logi" / f"{DZIEN}_codziennie.log").is_file()


def test_log_dopisuje_a_nie_nadpisuje(srodowisko):
    for _ in range(2):
        assert uruchom(srodowisko, "codziennie", AUTOMAT_DRY_RUN="1").returncode == 0
    assert srodowisko.log("codziennie").count("STATUS: OK") == 2


def test_udany_bieg_zapisuje_status_ok_i_nie_halasuje_na_stderr(srodowisko):
    s = srodowisko
    r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa")
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stderr == ""  # cron dopisuje stderr do cron_stderr.log: cisza = sukces
    status = s.status("codziennie").split()
    assert status[1:4] == ["codziennie", "OK", "kod=0"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", status[0])


def test_nieudany_bieg_zapisuje_status_blad_i_alarm_na_stderr(srodowisko):
    s = srodowisko
    r = uruchom(s, "codziennie", ATRAPA_KOD="3")
    assert r.returncode == 3
    assert "[beta automat] tryb codziennie: BŁĄD (kod 3)" in r.stderr
    assert str(s.logi / f"{DZIEN}_codziennie.log") in r.stderr
    assert s.status("codziennie").split()[1:4] == ["codziennie", "BLAD", "kod=3"]
    uruchom(s, "codziennie", ATRAPA_TRESC="nowa")  # kolejny udany bieg nadpisuje status
    assert "OK" in s.status("codziennie")


def test_status_kazdego_trybu_w_osobnym_pliku(srodowisko):
    s = srodowisko
    assert uruchom(s, "codziennie", AUTOMAT_DRY_RUN="1").returncode == 0
    assert uruchom(s, "miesiac", AUTOMAT_DRY_RUN="1", ATRAPA_IMPORT_BLAD="1").returncode != 0
    assert "OK" in s.status("codziennie") and "BLAD" in s.status("miesiac")


def test_przebieg_bez_home_i_path_jak_w_cronie(srodowisko):
    """Skrypt sam ustawia PATH i nie wymaga HOME (gdy dany jest katalog logów)."""
    s = srodowisko
    env = {
        k: v
        for k, v in env_biegu(s, "codziennie", None, ATRAPA_TRESC="nowa").items()
        if k.startswith(("AUTOMAT_", "ATRAPA_", "GIT_CONFIG_"))
    }
    r = subprocess.run(
        ["/bin/bash", str(SKRYPT), "codziennie"],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert git(s.zdalne, "rev-parse", GALAZ) == git(s.repo, "rev-parse", "HEAD")


def test_zamkniety_stdout_nie_psuje_biegu(srodowisko):
    s = srodowisko
    r = subprocess.run(
        ["bash", "-c", '"$0" "$@" >&-', str(SKRYPT), "codziennie"],
        env=env_biegu(s, "codziennie", None, ATRAPA_TRESC="nowa"),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    assert git(s.zdalne, "rev-parse", GALAZ) == git(s.repo, "rev-parse", "HEAD")
    assert ostatnia_linia(s.log("codziennie")).endswith("STATUS: OK")


def test_srodowisko_gita_i_locale_ustawia_skrypt(srodowisko):
    """Hak commita widzi środowisko, które skrypt ustawił jawnie (cron ma ubogie)."""
    s = srodowisko
    zrzut = s.korzen / "env_haka.txt"
    zainstaluj_hak(s, "pre-commit", f"env > '{zrzut}'")
    r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa", TZ="Asia/Tokyo", PATH="/usr/bin:/bin")
    assert r.returncode == 0, r.stdout + r.stderr
    linie = zrzut.read_text(encoding="utf-8").splitlines()
    for oczekiwana in ("LC_ALL=C.UTF-8", "TZ=UTC", "GIT_TERMINAL_PROMPT=0", "PYTHONUNBUFFERED=1"):
        assert oczekiwana in linie, oczekiwana
    # git dokłada na początek PATH własny katalog; ważny jest koniec, nie wartość z crona
    sciezka = next(w for w in linie if w.startswith("PATH="))
    assert sciezka.endswith(":/usr/local/bin:/usr/bin:/bin")


def test_nieprzewidziana_porazka_polecenia_zostawia_slad_w_logu(srodowisko, tmp_path):
    s = srodowisko
    r = uruchom(s, "niedziela", TMPDIR=str(tmp_path / "nie_ma_takiego_katalogu"))
    assert r.returncode != 0
    log = s.log("niedziela", DZIEN_NIEDZIELI)
    assert "polecenie zawiodło" in log and "mktemp" in log
    assert "STATUS: BLAD" in ostatnia_linia(log)
    assert s.wywolania_krokow() == []


# --- daty: poprzedni miesiąc i tydzień ISO ---


@pytest.mark.parametrize(
    ("tryb", "dzien", "oczekiwane"),
    [
        ("miesiac", "2026-10-03", "2026-09"),
        ("miesiac", "2026-01-03", "2025-12"),
        ("miesiac", "2024-03-03", "2024-02"),
        ("miesiac", "2026-03-31", "2026-02"),  # 31. dnia: bez „-01” data „-1 month” dałaby marzec
        ("miesiac", "2026-01-31", "2025-12"),
        ("miesiac", "2024-03-30", "2024-02"),
        ("miesiac", "2026-12-31", "2026-11"),
        ("miesiac", "2021-01-01", "2020-12"),
        ("niedziela", "2026-10-11", "raporty/tygodnie/2026-W41.md"),
        ("niedziela", "2027-01-03", "raporty/tygodnie/2026-W53.md"),
        ("niedziela", "2021-01-03", "raporty/tygodnie/2020-W53.md"),
    ],
)
def test_daty_trybow(srodowisko, tryb, dzien, oczekiwane):
    r = uruchom(srodowisko, tryb, dzien, AUTOMAT_DRY_RUN="1")
    assert r.returncode == 0, r.stdout + r.stderr
    log = srodowisko.log(tryb, dzien)
    if tryb == "miesiac":
        assert polecenie_z_logu(log)[-2:] == ["--koniec", oczekiwane]
    else:
        assert oczekiwane in log


@pytest.fixture(scope="module")
def srodowisko_wspolne(tmp_path_factory):
    return zbuduj_srodowisko(tmp_path_factory.mktemp("automat_wspolne"))


@settings(
    max_examples=15,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(d=st.dates(min_value=date(2021, 1, 1), max_value=date(2032, 12, 31)))
@example(d=date(2026, 3, 31))
@example(d=date(2024, 3, 30))
@example(d=date(2026, 12, 31))
@example(d=date(2021, 1, 1))
@example(d=date(2024, 2, 29))
def test_wlasnosc_daty_zgodne_z_pythonem(srodowisko_wspolne, d):
    """Poprzedni miesiąc i etykieta ISO ze skryptu = obliczenia Pythona dla dowolnej daty."""
    s, dzien = srodowisko_wspolne, d.isoformat()
    poprzedni = (d.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    rok, nr, _ = d.isocalendar()
    assert uruchom(s, "miesiac", dzien, AUTOMAT_DRY_RUN="1").returncode == 0
    assert f"--koniec {poprzedni}\n" in s.log("miesiac", dzien)
    assert uruchom(s, "niedziela", dzien, AUTOMAT_DRY_RUN="1").returncode == 0
    assert f"raporty/tygodnie/{rok}-W{nr:02d}.md" in s.log("niedziela", dzien)


# --- blokada ---


def test_blokada_zajeta_to_blad_z_komunikatem(srodowisko):
    s = srodowisko
    s.logi.mkdir()
    with open(s.logi / ".automat.lock", "w") as uchwyt:
        fcntl.flock(uchwyt, fcntl.LOCK_EX)
        r = uruchom(s, "codziennie", AUTOMAT_DRY_RUN="1", AUTOMAT_CZEKAJ_S="1")
    assert r.returncode == 75
    log = s.log("codziennie")
    assert "Blokada zajęta" in log and "rezygnuję" in log
    assert "STATUS: BLAD" in ostatnia_linia(log)
    assert s.wywolania() == []
    assert uruchom(s, "codziennie", AUTOMAT_DRY_RUN="1").returncode == 0  # po zwolnieniu działa


def test_blokada_inny_tryb_czeka_i_przechodzi(srodowisko):
    s = srodowisko
    s.logi.mkdir()
    env = env_biegu(s, "miesiac", DZIEN, AUTOMAT_DRY_RUN="1", AUTOMAT_CZEKAJ_S="20")
    with open(s.logi / ".automat.lock", "w") as uchwyt:
        fcntl.flock(uchwyt, fcntl.LOCK_EX)
        p = subprocess.Popen(
            [str(SKRYPT), "miesiac"], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        time.sleep(1.0)
        assert p.poll() is None  # czeka, nie odpuszcza
    out, _ = p.communicate(timeout=30)
    assert p.returncode == 0, out
    assert "czekam" in s.log("miesiac")


def test_osierocony_potomek_kroku_nie_trzyma_blokady(srodowisko):
    """Krok zostawia proces w tle; po śmierci skryptu następny bieg nie może na niego czekać."""
    s = srodowisko
    try:
        r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa", ATRAPA_TLO="1")
        assert r.returncode == 0, r.stdout + r.stderr
        assert zyje(s.pid("tlo.pid"))  # potomek przeżył koniec skryptu
        assert blokada_wolna(s)
    finally:
        if (s.atrapa_dir / "tlo.pid").exists():
            os.kill(s.pid("tlo.pid"), signal.SIGKILL)


# --- git: commit i push tylko plików wyniku ---


def test_commit_tylko_wskazane_sciezki_a_cudze_zmiany_zostaja(srodowisko):
    s = srodowisko
    (s.repo / "notatki.txt").write_text("v2 cudze, niezatwierdzone\n", encoding="utf-8")
    (s.repo / "staged.txt").write_text("w indeksie\n", encoding="utf-8")
    git(s.repo, "add", "staged.txt")
    (s.repo / "smieci.txt").write_text("nieśledzony\n", encoding="utf-8")
    r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa")
    assert r.returncode == 0, r.stdout + r.stderr
    assert git(s.repo, "show", "--name-only", "--format=", "HEAD").split() == [
        "dane/manifest_deribit_dvol.json"
    ]
    assert set(git(s.repo, "status", "--porcelain").splitlines()) == {
        " M notatki.txt",
        "A  staged.txt",
        "?? smieci.txt",
    }
    assert "(automat)" in git(s.repo, "log", "-1", "--format=%s")
    assert ostatnia_linia(s.log("codziennie")).endswith("STATUS: OK")


@pytest.mark.parametrize("tryb", TRYBY)
def test_cudze_zmiany_w_tych_samych_katalogach_nie_trafiaja_do_commita(srodowisko, tryb):
    """Sąsiedzi wyniku w dane/ i raporty/tygodnie/ (nieśledzeni i zmienieni) zostają w drzewie."""
    s = srodowisko
    (s.repo / "dane" / "inny.json").write_text("{}\n", encoding="utf-8")
    (s.repo / "raporty" / "tygodnie" / "2026-W42.md").write_text("cudzy raport\n", encoding="utf-8")
    sasiad = "manifest_binance_um.json" if tryb == "codziennie" else "manifest_deribit_dvol.json"
    (s.repo / "dane" / sasiad).write_text('{"tresc": "cudza zmiana"}\n', encoding="utf-8")
    r = uruchom(s, tryb, ATRAPA_TRESC="nowa")
    assert r.returncode == 0, r.stdout + r.stderr
    for ref in ("HEAD", f"origin/{GALAZ}"):
        assert sorted(git(s.repo, "show", "--name-only", "--format=", ref).split()) == sorted(
            WYNIKI_TRYBOW[tryb]
        )
    oczekiwane = {f" M dane/{sasiad}", "?? dane/inny.json", "?? raporty/tygodnie/2026-W42.md"}
    if tryb == "miesiac":
        oczekiwane.add("?? data/")
    assert set(git(s.repo, "status", "--porcelain").splitlines()) == oczekiwane
    assert git(s.zdalne, "rev-parse", GALAZ) == git(s.repo, "rev-parse", "HEAD")


def test_miesiac_zatwierdza_manifest_i_sklad_ale_nie_data(srodowisko):
    s = srodowisko
    r = uruchom(s, "miesiac", ATRAPA_TRESC="nowa")
    assert r.returncode == 0, r.stdout + r.stderr
    assert sorted(git(s.repo, "show", "--name-only", "--format=", "HEAD").split()) == [
        "dane/manifest_binance_um.json",
        "dane/sklad_top20.json",
    ]
    assert (s.repo / "data" / "binance_um" / "BTCUSDT.parquet").is_file()
    assert git(s.repo, "status", "--porcelain") == "?? data/"  # dane zostały poza commitem
    uniwersum = os.path.realpath(s.korzen / "alpha" / "data" / "raw" / "universe_full")
    assert s.wywolania_krokow() == [
        "-m dane.binance_vision --tf 5m 1d --uniwersum "
        + uniwersum
        + " --top 20 --watki 16 --przyrostowo --koniec 2026-09"
    ]
    assert any(w.endswith("dane/sklad_top20.json 2026-09") for w in s.wywolania())


def test_codziennie_i_niedziela_wolaja_krok_z_dokladnymi_argumentami(srodowisko):
    s = srodowisko
    assert uruchom(s, "codziennie", ATRAPA_TRESC="nowa").returncode == 0
    assert uruchom(s, "niedziela", ATRAPA_TRESC="nowa").returncode == 0
    assert s.wywolania_krokow() == [
        "-m dane.deribit_dvol --koniec 2026-10-06",
        "-m raporty.tydzien --data 2026-10-11",
    ]


def test_push_trafia_do_lokalnego_repo_bare(srodowisko):
    s = srodowisko
    assert uruchom(s, "codziennie", ATRAPA_TRESC="nowa").returncode == 0
    assert git(s.zdalne, "rev-parse", GALAZ) == git(s.repo, "rev-parse", "HEAD")
    assert git(s.zdalne, "log", "-1", "--format=%s", GALAZ).endswith("(automat)")
    assert "Wypchnięto" in s.log("codziennie")


def test_brak_zmian_brak_commita_i_kod_zero(srodowisko):
    s = srodowisko
    assert uruchom(s, "codziennie", ATRAPA_TRESC="nowa").returncode == 0
    head = git(s.repo, "rev-parse", "HEAD")
    (s.repo / "notatki.txt").write_text("v2 cudze\n", encoding="utf-8")  # brudne drzewo
    r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa")
    assert r.returncode == 0, r.stdout + r.stderr
    assert git(s.repo, "rev-parse", "HEAD") == head
    log = s.log("codziennie")
    assert "Brak zmian" in log and ostatnia_linia(log).endswith("STATUS: OK")
    assert git(s.repo, "status", "--porcelain") == " M notatki.txt"


def test_nieudany_push_haka_to_kod_niezerowy_i_commit_zostaje(srodowisko):
    s = srodowisko
    zainstaluj_hak(s, "pre-push", "exit 1")
    r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa")
    assert r.returncode != 0
    log = s.log("codziennie")
    assert "push nie powiódł się" in log and "STATUS: BLAD" in ostatnia_linia(log)
    assert "(automat)" in git(s.repo, "log", "-1", "--format=%s")  # commit lokalny zostaje


def test_niewypchniety_commit_jest_ponawiany_nawet_gdy_brak_nowych_zmian(srodowisko):
    """Nieudany push, potem bieg bez zmian: nie wolno raportować sukcesu, a po naprawie wypycha."""
    s = srodowisko
    zdalne_start = git(s.zdalne, "rev-parse", GALAZ)
    hak = zainstaluj_hak(s, "pre-push", "exit 1")
    assert uruchom(s, "codziennie", ATRAPA_TRESC="nowa").returncode != 0
    r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa")  # nic nowego do commita
    assert r.returncode != 0, r.stdout + r.stderr
    log = s.log("codziennie")
    assert "Brak zmian" in log and ostatnia_linia(log).endswith("(kod wyjścia 1)")
    assert git(s.zdalne, "rev-parse", GALAZ) == zdalne_start
    hak.unlink()
    r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa")
    assert r.returncode == 0, r.stdout + r.stderr
    assert git(s.zdalne, "rev-parse", GALAZ) == git(s.repo, "rev-parse", "HEAD")
    assert "Wypchnięto" in s.log("codziennie")


def test_limit_czasu_pusha(srodowisko):
    s = srodowisko
    zainstaluj_hak(s, "pre-push", "sleep 60")
    start = time.monotonic()
    r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa", AUTOMAT_LIMIT_PUSH_S="1")
    assert r.returncode == 124, r.stdout + r.stderr
    assert time.monotonic() - start < 30
    assert "push nie powiódł się (kod 124)" in s.log("codziennie")


def test_po_pushu_origin_musi_miec_ten_sam_commit_co_head(srodowisko):
    """Push zakończony kodem 0 nie wystarcza: skrypt czyta origin jeszcze raz i porównuje."""
    s = srodowisko
    start = git(s.zdalne, "rev-parse", GALAZ)
    hak = s.zdalne / "hooks" / "post-receive"  # zdalne repo cofa gałąź zaraz po przyjęciu pusha
    hak.write_text(f"#!/bin/sh\ngit update-ref refs/heads/{GALAZ} {start}\n", encoding="utf-8")
    hak.chmod(0o755)
    r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa")
    assert r.returncode != 0
    assert "po pushu origin" in s.log("codziennie")


def test_push_nigdy_nie_wymusza_gdy_zdalne_sie_rozeszlo(srodowisko):
    s = srodowisko
    cudzy = cudzy_commit_na_origin(s)
    r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa")
    assert r.returncode != 0
    assert "rozeszły" in s.log("codziennie")
    assert git(s.zdalne, "rev-parse", GALAZ) == cudzy  # zdalna gałąź nietknięta
    assert "(automat)" in git(s.repo, "log", "-1", "--format=%s")  # praca zostaje lokalnie


def test_zdalne_przed_lokalnym_bez_zmian_to_sukces_bez_pusha(srodowisko):
    s = srodowisko
    assert uruchom(s, "codziennie", ATRAPA_TRESC="nowa").returncode == 0
    cudzy = cudzy_commit_na_origin(s)
    r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "jest przed lokalną gałęzią" in s.log("codziennie")
    assert git(s.zdalne, "rev-parse", GALAZ) == cudzy


@pytest.mark.parametrize("plik", ["sekret.env", "data/dump.parquet", "dane/inny.json"])
def test_odmowa_pusha_cudzego_lokalnego_commita(srodowisko, plik):
    """Cudzy, niewypchnięty commit nie wyjdzie na GitHuba razem z wynikiem automatu."""
    s = srodowisko
    (s.repo / plik).parent.mkdir(parents=True, exist_ok=True)
    (s.repo / plik).write_text("cudze\n", encoding="utf-8")
    git(s.repo, "add", plik)
    git(s.repo, "commit", "-q", "-m", "cudzy lokalny commit")
    zdalne = git(s.zdalne, "rev-parse", GALAZ)
    r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa")
    assert r.returncode != 0
    log = s.log("codziennie")
    assert "spoza wyniku" in log and plik in log
    assert git(s.zdalne, "rev-parse", GALAZ) == zdalne


def test_wczesniejszy_commit_automatu_wychodzi_przy_nastepnym_biegu(srodowisko):
    s = srodowisko
    zdalne = git(s.zdalne, "rev-parse", GALAZ)
    plik = s.repo / "dane" / "manifest_deribit_dvol.json"
    plik.write_text('{"tresc": "wczoraj"}\n', encoding="utf-8")
    git(s.repo, "add", "--", "dane/manifest_deribit_dvol.json")
    git(s.repo, "commit", "-q", "-m", "Dane: manifest DVOL (automat)")
    r = uruchom(s, "niedziela", ATRAPA_TRESC="nowa")
    assert r.returncode == 0, r.stdout + r.stderr
    assert git(s.zdalne, "rev-parse", GALAZ) == git(s.repo, "rev-parse", "HEAD")
    assert git(s.zdalne, "rev-list", "--count", f"{zdalne}..{GALAZ}") == "2"


def test_odmowa_pusha_gdy_wsrod_commitow_jest_merge(srodowisko):
    s = srodowisko
    git(s.repo, "checkout", "-q", "-b", "boczna")
    (s.repo / "dane" / "manifest_binance_um.json").write_text('{"tresc": "b"}\n', encoding="utf-8")
    git(s.repo, "commit", "-q", "-am", "boczny")
    git(s.repo, "checkout", "-q", GALAZ)
    (s.repo / "dane" / "sklad_top20.json").write_text('{"tresc": "g"}\n', encoding="utf-8")
    git(s.repo, "commit", "-q", "-am", "gałęzi")
    git(s.repo, "merge", "-q", "--no-ff", "-m", "scalenie", "boczna")
    zdalne = git(s.zdalne, "rev-parse", GALAZ)
    r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa")
    assert r.returncode != 0
    assert "scalenie" in s.log("codziennie")
    assert git(s.zdalne, "rev-parse", GALAZ) == zdalne


def test_galaz_zmieniona_w_trakcie_kroku_nie_dostaje_commita(srodowisko):
    """Krok trwa godzinami; jeśli ktoś w tym czasie zmieni gałąź, wynik nie trafia na cudzą."""
    s = srodowisko
    start = git(s.repo, "rev-parse", "HEAD")
    r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa", ATRAPA_PRZEL_GALAZ="1")
    assert r.returncode != 0, r.stdout + r.stderr
    assert "gałąź zmieniła się" in s.log("codziennie")
    assert git(s.repo, "rev-parse", "main") == start  # żadnego nowego commita na main
    assert git(s.zdalne, "rev-parse", GALAZ) == start
    assert git(s.repo, "rev-parse", GALAZ) == start


def test_bez_gita_kroki_python_tak_commit_nie(srodowisko):
    s = srodowisko
    git(s.repo, "remote", "remove", "origin")
    head = git(s.repo, "rev-parse", "HEAD")
    r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa", AUTOMAT_BEZ_GITA="1")
    assert r.returncode == 0, r.stdout + r.stderr
    assert git(s.repo, "rev-parse", "HEAD") == head
    assert git(s.repo, "status", "--porcelain") == " M dane/manifest_deribit_dvol.json"
    assert "pomijam commit i push" in s.log("codziennie")


def test_odpiecie_wynikow_po_nieudanym_commicie(srodowisko):
    """Hak odrzuca commit: pliki wyniku nie zostają w indeksie, cudze zmiany w indeksie tak."""
    s = srodowisko
    (s.repo / "staged.txt").write_text("w indeksie\n", encoding="utf-8")
    git(s.repo, "add", "staged.txt")
    zainstaluj_hak(s, "pre-commit", "exit 1")
    r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa")
    assert r.returncode != 0
    log = s.log("codziennie")
    assert "git commit nie powiódł się" in log and "Cofnięto dodanie" in log
    assert git(s.repo, "diff", "--cached", "--name-only") == "staged.txt"
    assert " M dane/manifest_deribit_dvol.json" in git(s.repo, "status", "--porcelain")


def test_index_lock_znika_w_trakcie_ponowien(srodowisko):
    s = srodowisko
    blokada = s.repo / ".git" / "index.lock"
    blokada.write_text("", encoding="utf-8")
    zegar = threading.Timer(1.0, blokada.unlink)
    zegar.start()
    try:
        r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa", AUTOMAT_PONOW_S="2")
    finally:
        zegar.cancel()
        blokada.unlink(missing_ok=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Próba 1 z 3 nieudana" in s.log("codziennie")
    assert git(s.zdalne, "rev-parse", GALAZ) == git(s.repo, "rev-parse", "HEAD")


def test_trwala_blokada_indeksu_to_blad_i_nic_w_indeksie(srodowisko):
    s = srodowisko
    blokada = s.repo / ".git" / "index.lock"
    blokada.write_text("", encoding="utf-8")
    try:
        r = uruchom(s, "codziennie", ATRAPA_TRESC="nowa")
    finally:
        blokada.unlink(missing_ok=True)
    assert r.returncode != 0
    log = s.log("codziennie")
    assert "Próba 2 z 3 nieudana" in log and "git add nie powiódł się" in log
    assert git(s.repo, "diff", "--cached", "--name-only") == ""


def test_blad_kroku_pythona_to_kod_kroku_i_brak_commita(srodowisko):
    s = srodowisko
    head = git(s.repo, "rev-parse", "HEAD")
    r = uruchom(s, "codziennie", ATRAPA_KOD="3", ATRAPA_TRESC="nowa")
    assert r.returncode == 3
    log = s.log("codziennie")
    assert "atrapa: krok zawiódł" in log  # stderr kroku trafia do logu
    assert "STATUS: BLAD (kod wyjścia 3)" in ostatnia_linia(log)
    assert git(s.repo, "rev-parse", "HEAD") == head


def test_krok_zabity_sygnalem_kill_to_blad_i_brak_commita(srodowisko):
    s = srodowisko
    head = git(s.repo, "rev-parse", "HEAD")
    r = uruchom(s, "codziennie", ATRAPA_ZABIJ="1", ATRAPA_TRESC="nowa")
    assert r.returncode == 137
    assert "STATUS: BLAD (kod wyjścia 137)" in ostatnia_linia(s.log("codziennie"))
    assert git(s.repo, "rev-parse", "HEAD") == head


# --- sygnały i limity czasu: krok ginie w całości, blokada się zwalnia ---


@pytest.mark.parametrize(
    ("sygnal", "kod"),
    [(signal.SIGTERM, 143), (signal.SIGINT, 130), (signal.SIGHUP, 129)],
    ids=["TERM", "INT", "HUP"],
)
def test_sygnal_zabija_krok_i_jego_potomkow_i_zwalnia_blokade(srodowisko, sygnal, kod):
    s = srodowisko
    head = git(s.repo, "rev-parse", "HEAD")
    p = uruchom_w_tle(s, "codziennie", ATRAPA_SPANIE="60", ATRAPA_TRESC="nowa")
    try:
        assert czekaj_na(lambda: s.pid("sen.pid") > 0 and s.pid("krok.pid") > 0)
        sen, krok = s.pid("sen.pid"), s.pid("krok.pid")
        start = time.monotonic()
        p.send_signal(sygnal)
        p.communicate(timeout=30)
    finally:
        if p.poll() is None:
            p.kill()
    assert p.returncode == kod
    assert time.monotonic() - start < 20  # nie czeka na koniec 60-sekundowego kroku
    assert czekaj_na(lambda: not zyje(sen) and not zyje(krok), 5)
    assert blokada_wolna(s)
    log = s.log("codziennie")
    assert "Sygnał" in log and f"STATUS: BLAD (kod wyjścia {kod})" in ostatnia_linia(log)
    assert git(s.repo, "rev-parse", "HEAD") == head
    assert "BLAD" in s.status("codziennie")


def test_sygnal_zabija_tez_krok_ignorujacy_term(srodowisko):
    """Krok i jego potomek ignorują TERM: po 5 s idzie KILL na grupę, skrypt nie wisi 60 s."""
    s = srodowisko
    p = uruchom_w_tle(s, "codziennie", ATRAPA_SPANIE="120", ATRAPA_IGNORUJ_TERM="1")
    grupa = 0
    try:
        assert czekaj_na(lambda: s.pid("sen.pid") > 0 and s.pid("krok.pid") > 0)
        sen, krok = s.pid("sen.pid"), s.pid("krok.pid")
        grupa = os.getpgid(krok)
        start = time.monotonic()
        p.send_signal(signal.SIGTERM)
        p.wait(timeout=40)
    finally:
        if grupa:
            zabij_grupe(grupa)
        if p.poll() is None:
            p.kill()
    assert p.returncode == 143
    assert time.monotonic() - start < 30
    assert czekaj_na(lambda: not zyje(sen) and not zyje(krok), 5)
    assert blokada_wolna(s)


def test_krok_i_petla_logu_maja_wspolna_grupe_inna_niz_skrypt(srodowisko):
    """Sygnał ma zabić całą grupę kroku, razem z pętlą logu: skrypt nie może być w tej grupie."""
    s = srodowisko
    p = uruchom_w_tle(s, "codziennie", ATRAPA_SPANIE="60")
    try:
        assert czekaj_na(lambda: s.pid("sen.pid") > 0 and s.pid("krok.pid") > 0)
        grupy = grupy_sesji(p.pid)
        reszta = {pid: g for pid, g in grupy.items() if pid != p.pid}
        assert grupy[p.pid] == p.pid  # skrypt prowadzi sesję i własną grupę
        assert len(reszta) >= 4  # timeout, atrapa, jej sleep i pętla logu
        assert set(reszta.values()) == {os.getpgid(s.pid("krok.pid"))}
        assert p.pid not in set(reszta.values())
    finally:
        p.send_signal(signal.SIGTERM)
        p.wait(timeout=30)


def test_po_kill_skryptu_blokada_trwa_dopoki_zyje_krok(srodowisko):
    """Skrypt ubity przez OOM (`kill -9`): krok dalej biegnie, więc następny bieg ma czekać."""
    s = srodowisko
    p = uruchom_w_tle(s, "codziennie", ATRAPA_SPANIE="60")
    grupa = 0
    try:
        assert czekaj_na(lambda: s.pid("sen.pid") > 0 and s.pid("krok.pid") > 0)
        grupa = os.getpgid(s.pid("krok.pid"))
        p.kill()
        p.wait(timeout=10)
        assert zyje(s.pid("krok.pid"))
        assert not blokada_wolna(s)
        zabij_grupe(grupa)
        assert czekaj_na(lambda: blokada_wolna(s), 5)  # krok skończył, blokada wolna
    finally:
        if grupa:
            zabij_grupe(grupa)
        if p.poll() is None:
            p.kill()


def test_limit_czasu_kroku(srodowisko):
    s = srodowisko
    head = git(s.repo, "rev-parse", "HEAD")
    start = time.monotonic()
    r = uruchom(s, "codziennie", ATRAPA_SPANIE="60", AUTOMAT_LIMIT_KROKU_S="1")
    assert r.returncode == 124, r.stdout + r.stderr
    assert time.monotonic() - start < 30
    assert "przekroczył limit czasu" in s.log("codziennie")
    assert czekaj_na(lambda: not zyje(s.pid("sen.pid")), 5)  # potomek kroku też zabity
    assert git(s.repo, "rev-parse", "HEAD") == head
    assert blokada_wolna(s)


# --- miesiąc: czy pobranie jest kompletne ---


def test_miesiac_z_brakujacym_miesiacem_nie_zatwierdza_manifestu(srodowisko):
    """Downloader traktuje brak pliku miesiąca jak 404: manifest „do 2026-09” bez września."""
    s = srodowisko
    head = git(s.repo, "rev-parse", "HEAD")
    r = uruchom(s, "miesiac", ATRAPA_TRESC="nowa", ATRAPA_SWIECA="2026-08-31")
    assert r.returncode != 0
    log = s.log("miesiac")
    assert "niekompletne" in log and "ostatnia świeca 2026-08-31" in log
    assert git(s.repo, "rev-parse", "HEAD") == head
    assert git(s.zdalne, "rev-parse", GALAZ) == head
    assert " M dane/manifest_binance_um.json" in git(s.repo, "status", "--porcelain")


def test_miesiac_ze_starym_manifestem_nie_przechodzi(srodowisko):
    s = srodowisko
    r = uruchom(s, "miesiac", ATRAPA_TRESC="nowa", ATRAPA_DO="2026-08")
    assert r.returncode != 0
    assert "stary manifest" in s.log("miesiac")


def test_miesiac_ze_starym_skladem_top20_ostrzega_ale_przechodzi(srodowisko):
    s = srodowisko
    r = uruchom(s, "miesiac", ATRAPA_TRESC="nowa", ATRAPA_SKLAD_DO="2026-06")
    assert r.returncode == 0, r.stdout + r.stderr
    log = s.log("miesiac")
    assert "UWAGA" in log and "skład top-20 kończy się na 2026-06" in log
    assert "Pobranie do 2026-09 kompletne" in log
    assert git(s.zdalne, "rev-parse", GALAZ) == git(s.repo, "rev-parse", "HEAD")


# --- raport tygodniowy: komentarz Claude ---


def test_niedziela_zachowuje_komentarz_i_commituje_tylko_raport(srodowisko):
    s = srodowisko
    r = uruchom(s, "niedziela", ATRAPA_TRESC="nowa")
    assert r.returncode == 0, r.stdout + r.stderr
    tekst = (s.repo / "raporty" / "tygodnie" / "2026-W41.md").read_text(encoding="utf-8")
    assert "Komentarz Claude v1" in tekst and "tresc=nowa" in tekst
    assert git(s.repo, "show", "--name-only", "--format=", "HEAD").split() == [
        "raporty/tygodnie/2026-W41.md"
    ]
    assert git(s.repo, "log", "-1", "--format=%s") == "Raport tygodniowy 2026-W41 (automat)"


def test_niedziela_nowy_raport_trafia_do_repo(srodowisko):
    s = srodowisko
    r = uruchom(s, "niedziela", "2026-10-18", ATRAPA_TRESC="nowa")
    assert r.returncode == 0, r.stdout + r.stderr
    assert git(s.repo, "show", "--name-status", "--format=", "HEAD") == (
        "A\traporty/tygodnie/2026-W42.md"
    )


def test_niedziela_chroni_komentarz_gdy_generator_go_nadpisze(srodowisko):
    s = srodowisko
    plik = s.repo / "raporty" / "tygodnie" / "2026-W41.md"
    head = git(s.repo, "rev-parse", "HEAD")
    r = uruchom(s, "niedziela", ATRAPA_TRESC="nowa", ATRAPA_PSUJ="1")
    assert r.returncode != 0
    assert plik.read_text(encoding="utf-8") == RAPORT_START  # przywrócony
    assert git(s.repo, "rev-parse", "HEAD") == head
    assert "blok komentarza" in s.log("niedziela", DZIEN_NIEDZIELI)


def test_niedziela_odmawia_gdy_raport_ma_niezatwierdzone_zmiany(srodowisko):
    """Komentarz w trakcie pisania nie może zostać opublikowany ani nadpisany."""
    s = srodowisko
    plik = s.repo / "raporty" / "tygodnie" / "2026-W41.md"
    rozgrzebany = RAPORT_START.replace("v1", "v2 niezatwierdzony")
    plik.write_text(rozgrzebany, encoding="utf-8")
    przed, zdalne = stan_git(s), git(s.zdalne, "rev-parse", GALAZ)
    r = uruchom(s, "niedziela", ATRAPA_TRESC="nowa")
    assert r.returncode != 0
    assert "niezatwierdzone zmiany" in s.log("niedziela", DZIEN_NIEDZIELI)
    assert s.wywolania_krokow() == []  # generator nie ruszył
    assert plik.read_text(encoding="utf-8") == rozgrzebany
    assert stan_git(s) == przed and git(s.zdalne, "rev-parse", GALAZ) == zdalne


def test_niedziela_raport_bez_znacznikow_komentarza_przechodzi(srodowisko):
    """Poprzedni plik bez bloku komentarza nie ma czego chronić — generator wstawia szablon."""
    s = srodowisko
    plik = s.repo / "raporty" / "tygodnie" / "2026-W41.md"
    plik.write_text("# Raport stary, bez komentarza\n", encoding="utf-8")
    git(s.repo, "commit", "-q", "-am", "raport bez komentarza")
    r = uruchom(s, "niedziela", ATRAPA_TRESC="nowa")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "<!-- komentarz -->" in git(s.repo, "show", "HEAD:raporty/tygodnie/2026-W41.md")


def test_niedziela_generator_bez_pliku_to_blad(srodowisko):
    s = srodowisko
    r = uruchom(s, "niedziela", "2026-10-18", ATRAPA_BEZ_WYNIKU="1")
    assert r.returncode != 0
    assert "generator nie utworzył pliku" in s.log("niedziela", "2026-10-18")


# --- pomocnik narzedzia: kontrola kompletności pobrania ---


def zapisz_manifest(katalog: Path, do: str, ostatnie: dict[str, str]) -> Path:
    plik = katalog / "manifest.json"
    jakosc = {para: {"do": data} for para, data in ostatnie.items()}
    plik.write_text(json.dumps({"do": do, "jakosc": jakosc}), encoding="utf-8")
    return plik


def zapisz_sklad(katalog: Path, klucze: list[str]) -> Path:
    plik = katalog / "sklad.json"
    plik.write_text(json.dumps({k: ["BTCUSDT"] for k in klucze}), encoding="utf-8")
    return plik


KOMPLET = {"BTCUSDT/5m": "2026-09-30 23:55:00+00:00", "BTCUSDT/1d": "2026-09-30 00:00:00+00:00"}


@pytest.mark.parametrize(
    ("miesiac", "oczekiwany"),
    [
        ("2024-02", date(2024, 2, 29)),
        ("2026-02", date(2026, 2, 28)),
        ("2026-12", date(2026, 12, 31)),
    ],
)
def test_ostatni_dzien_miesiaca_przyklady(miesiac, oczekiwany):
    assert ostatni_dzien_miesiaca(miesiac) == oczekiwany


@given(rok=st.integers(2000, 2100), mies=st.integers(1, 12))
def test_wlasnosc_ostatni_dzien_miesiaca_zgodny_z_kalendarzem(rok, mies):
    wynik = ostatni_dzien_miesiaca(f"{rok}-{mies:02d}")
    assert wynik == date(rok, mies, calendar.monthrange(rok, mies)[1])


@pytest.mark.parametrize("zly", ["2026-13", "2026-00", "abc", "2026", "2026-1-1", ""])
def test_ostatni_dzien_miesiaca_zly_format(zly):
    with pytest.raises(ValueError):
        ostatni_dzien_miesiaca(zly)


def test_kontrola_kompletne_pobranie(tmp_path):
    manifest = zapisz_manifest(tmp_path, "2026-09", KOMPLET)
    sklad = zapisz_sklad(tmp_path, ["2026-06-01", "2026-09-01"])
    assert sprawdz_pobranie(manifest, sklad, "2026-09") == ([], [])


def test_kontrola_ostatnia_swieca_dokladnie_na_koncu_miesiaca_wystarcza(tmp_path):
    manifest = zapisz_manifest(tmp_path, "2026-09", {**KOMPLET, "BTCUSDT/1d": "2026-09-30"})
    sklad = zapisz_sklad(tmp_path, ["2026-09-01"])
    assert sprawdz_pobranie(manifest, sklad, "2026-09")[0] == []


@pytest.mark.parametrize(
    ("do", "ostatnie", "fragment"),
    [
        ("2026-08", KOMPLET, "stary manifest"),
        ("2026-09", {**KOMPLET, "BTCUSDT/5m": "2026-09-29 23:55:00+00:00"}, "BTCUSDT/5m"),
        ("2026-09", {**KOMPLET, "BTCUSDT/1d": "2026-08-31 00:00:00+00:00"}, "BTCUSDT/1d"),
        ("2026-09", {"BTCUSDT/5m": KOMPLET["BTCUSDT/5m"]}, "nie ma pary kontrolnej BTCUSDT/1d"),
        ("2026-09", {}, "nie ma pary kontrolnej BTCUSDT/5m"),
    ],
)
def test_kontrola_wykrywa_niekompletne_pobranie(tmp_path, do, ostatnie, fragment):
    manifest = zapisz_manifest(tmp_path, do, ostatnie)
    sklad = zapisz_sklad(tmp_path, ["2026-09-01"])
    bledy, _ = sprawdz_pobranie(manifest, sklad, "2026-09")
    assert bledy and any(fragment in b for b in bledy), bledy


@pytest.mark.parametrize("tresc", ["", "{nie json", "[1, 2]", '{"do": "2026-09", "jakosc": []}'])
def test_kontrola_nieczytelny_albo_dziwny_manifest_to_blad(tmp_path, tresc):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(tresc, encoding="utf-8")
    bledy, _ = sprawdz_pobranie(manifest, zapisz_sklad(tmp_path, ["2026-09-01"]), "2026-09")
    assert len(bledy) == 1


def test_kontrola_brak_pliku_manifestu_to_blad(tmp_path):
    bledy, _ = sprawdz_pobranie(
        tmp_path / "nie_ma.json", zapisz_sklad(tmp_path, ["2026-09-01"]), "2026-09"
    )
    assert len(bledy) == 1 and "nie mogę odczytać manifestu" in bledy[0]


@pytest.mark.parametrize("klucze", [["2026-06-01"], []])
def test_kontrola_stary_lub_pusty_sklad_to_tylko_ostrzezenie(tmp_path, klucze):
    manifest = zapisz_manifest(tmp_path, "2026-09", KOMPLET)
    bledy, ostrzezenia = sprawdz_pobranie(manifest, zapisz_sklad(tmp_path, klucze), "2026-09")
    assert bledy == [] and len(ostrzezenia) == 1 and "skład top-20" in ostrzezenia[0]


def test_kontrola_brak_pliku_skladu_to_tylko_ostrzezenie(tmp_path):
    manifest = zapisz_manifest(tmp_path, "2026-09", KOMPLET)
    bledy, ostrzezenia = sprawdz_pobranie(manifest, tmp_path / "nie_ma.json", "2026-09")
    assert bledy == [] and "nie mogę odczytać składu" in ostrzezenia[0]


def test_kontrola_miesiaca_drukuje_wynik_i_kod(tmp_path, capsys):
    manifest = zapisz_manifest(tmp_path, "2026-09", KOMPLET)
    sklad = zapisz_sklad(tmp_path, ["2026-06-01"])
    assert kontrola_miesiaca(str(manifest), str(sklad), "2026-09") == 0
    wyjscie = capsys.readouterr().out
    assert "UWAGA" in wyjscie and "Pobranie do 2026-09 kompletne" in wyjscie
    assert kontrola_miesiaca(str(manifest), str(sklad), "2026-10") == 1
    wyjscie = capsys.readouterr().out
    assert "BŁĄD" in wyjscie and "kompletne" not in wyjscie


def test_kontrola_miesiaca_zly_miesiac_to_kod_1(tmp_path, capsys):
    manifest = zapisz_manifest(tmp_path, "2026-09", KOMPLET)
    assert kontrola_miesiaca(str(manifest), str(zapisz_sklad(tmp_path, [])), "2026-13") == 1
    assert "zły miesiąc" in capsys.readouterr().out


def test_kontrola_na_prawdziwym_manifescie_binance():
    """Kontrakt formatu: pomocnik czyta to, co naprawdę zapisuje downloader (jeśli jest plik)."""
    manifest = KORZEN / "dane" / "manifest_binance_um.json"
    if not manifest.is_file():
        pytest.skip("brak dane/manifest_binance_um.json")
    miesiac = json.loads(manifest.read_text(encoding="utf-8"))["do"]
    bledy, _ = sprawdz_pobranie(manifest, KORZEN / "dane" / "sklad_top20.json", miesiac)
    assert bledy == []


# --- linie crona ---


def linie_crona() -> list[str]:
    return [w for w in CRONTAB.read_text(encoding="utf-8").splitlines() if w.strip()]


def test_crontab_ma_trzy_linie_z_pelnymi_sciezkami():
    linie = [w for w in linie_crona() if not w.startswith("#")]
    assert len(linie) == 3  # także: żadnych linii ze zmiennymi (CRON_TZ, MAILTO) poza komentarzem
    harmonogramy = {" ".join(w.split()[:5]) for w in linie}
    assert harmonogramy == {"10 6 * * *", "30 6 3 * *", "0 18 * * 0"}
    for w in linie:
        assert "/home/dantey1/beta/narzedzia/automat.sh " in w
        assert "2>>/home/dantey1/beta_logi/cron_stderr.log" in w
        assert ">/dev/null" in w and "/bin/mkdir -p /home/dantey1/beta_logi &&" in w
    assert [w.split("automat.sh ")[1].split()[0] for w in linie] == list(TRYBY)
    assert "UŻYTKOWNIK" in CRONTAB.read_text(encoding="utf-8")


def test_crontab_bez_cron_tz_ktorego_cron_ubuntu_nie_obsluguje():
    assert not [w for w in linie_crona() if w.lstrip().startswith("CRON_TZ")]
    assert "nie obsługuje CRON_TZ" in CRONTAB.read_text(encoding="utf-8")


def test_crontab_polecenie_instalacji_jest_idempotentne():
    tekst = CRONTAB.read_text(encoding="utf-8")
    assert (
        "grep -v 'narzedzia/automat.sh'" in tekst
    )  # stare linie automatu znikają przed dopisaniem
    assert "grep -v '^#' narzedzia/crontab.txt" in tekst
    assert "ostatni_status_" in tekst and "cron_stderr.log" in tekst  # gdzie szukać awarii


def test_crontab_wskazuje_istniejacy_skrypt_a_tryby_sa_obslugiwane():
    assert SKRYPT.is_file()
    for w in linie_crona():
        if not w.startswith("#"):
            assert w.split("automat.sh ")[1].split()[0] in TRYBY
