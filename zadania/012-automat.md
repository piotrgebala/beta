---
id: 012
tytul: automat — DVOL codziennie, Binance co miesiąc, raport w niedzielę
typ: infra
status: do_przegladu
zlecil: uzytkownik
decyzja_uzytkownika: "2026-10-05: „rozpisz sobie kolejne taski, zaplanuj i zacznij realizować” + akceptacja planu (007–012)"
utworzono: 2026-10-05
zalezy_od: [007]
budzet: "Sonnet, część sesji"
---

# 012 — automat (PRD §6)

## Zakres

- `narzedzia/automat.sh` z trybami: `codziennie` (DVOL), `miesiac` (Binance top-20 + manifest, 3. dnia
  miesiąca), `niedziela` (raport tygodniowy); log do `~/beta_logi/`, kod wyjścia ≠ 0 przy błędzie.
- Commit + push manifestów i raportu (zasada 28) — wymaga działającego klucza do GitHuba (jest od 2026-10-05).
- Linię crona dodaje użytkownik (zabezpieczenie Claude Code nie pozwala Claude'owi ustawiać zadań stałych;
  tak samo jak w alpha). Gotowa linia w karcie.

## Kryteria odbioru (dowody)

Każdy tryb uruchomiony ręcznie raz z sukcesem; linia crona w karcie.

## Wynik

2026-10-05/06: `narzedzia/automat.sh` (tryby `codziennie`, `miesiac`, `niedziela`; blokada flock, log
`~/beta_logi/<data>_<tryb>.log` + `ostatni_status_<tryb>.txt`, commit tylko plików wyniku, push na bieżącą gałąź
bez wymuszania, odmowa na main/master) + `tests/test_automat.py`. Każdy tryb uruchomiony ręcznie raz z sukcesem:

| tryb | kiedy | czas | wynik |
|---|---|---|---|
| `codziennie` | 2026-10-05 20:19 UTC | 5 s | DVOL BTC/ETH do 2026-10-04, 0 dziur; commit `55cfcdb`, push |
| `miesiac` | 2026-10-05 20:20 UTC | 32 min | 196 symboli 5m/1d do 2026-09; pliki w `data/` identyczne z kopią sprzed biegu (0 różnic); manifest zmienił 2 linie; commit `56fedc3`, push |
| `niedziela` | 2026-10-06 06:50 UTC | 3 s | raport `2026-W41` (komentarz zachowany); commit `18b4a5a`, push |

**Linie crona — ustawiasz Ty** (Claude nie instaluje zadań stałych). W katalogu repo, jeden raz:

```
(crontab -l 2>/dev/null | grep -v 'narzedzia/automat.sh'; grep -v '^#' narzedzia/crontab.txt) | crontab -
```

Wstawia: DVOL codziennie 06:10, Binance 3. dnia miesiąca 06:30, raport w niedzielę 18:00 (czas serwera = UTC).
Sprawdzenie: `crontab -l`; awarie: `~/beta_logi/cron_stderr.log`.

**Do wiedzy:** tryb `miesiac` pobiera całą historię od nowa (32 min, zapis nieatomowy) i bierze skład top-20
z `alpha/.../universe_full`, który kończy się na 2026-06 → karta 015 (pobieranie przyrostowe). Push odpada, gdy
origin jest przed lokalną gałęzią (automat nie scala sam). Commity automatu pojawiają się w historii gałęzi PR #1.
