---
id: 012
tytul: automat — DVOL codziennie, Binance co miesiąc, raport w niedzielę
typ: infra
status: nowe
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

(dopisuje orkiestrator)
