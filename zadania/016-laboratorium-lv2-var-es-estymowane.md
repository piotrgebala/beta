---
id: 016
tytul: laboratorium LV2 — testy VaR/ES dla prognoz ESTYMOWANYCH (okno, EWMA, GARCH) przed rundą na danych
typ: badawcze
status: nowe
zlecil: orkiestrator
decyzja_uzytkownika: "2026-10-06: „LV1: poprawiona, 011: a, E0: zamknij” — wniosek z LV1 i STOP F2-1b (F2 → ryzyko ogona)"
utworzono: 2026-10-06
zalezy_od: [008, 009]
budzet: "Opus, 1 sesja, 16 procesów"
---

# 016 — LV2

## Po co

LV1 (MIERZALNA) mierzyła rozmiar testów tylko dla prognozy-wyroczni (prawdziwa σ). Realistyczne prognozy
z estymowaną σ (okno 60 dni, EWMA 0,94) przy poprawnym ogonie t5 miały za dużo trafień (1,28–1,39 % zamiast
1 %) i test zbiorczy odrzucał je w 78–98 % paneli. Zanim jakakolwiek runda VaR/ES dotknie prawdziwych danych
(licznik „ryzyko 2021+”), trzeba wiedzieć, jakie pytanie da się uczciwie zadać prognozie estymowanej.

## Zakres

- Pre-rejestracja w `runs/RRRR-MM-DD_lv2-var-es-estymowane/` przed przebiegiem; ten sam generator i test
  zbiorczy co LV1 (`symulacje/moc_var_es.py`), komórka n = 1 600 (i 1 700 z F2-1b), ρ = 0,8.
- Prognozy estymowane: okno 60, EWMA 0,94, GARCH(1,1)-t dopasowany walk-forward (rozgrzewka, refit co 30 dni),
  HAR jako opis; ogon: t5 stały i kwantyl empiryczny standaryzowanych reszt.
- Pytania do rozstrzygnięcia: (a) rozmiar testu zbiorczego, gdy model jest „dobrze wyspecyfikowany, ale
  estymowany” (np. GARCH-t na danych GARCH-t); (b) moc testu PORÓWNAWCZEGO (np. funkcja straty kwantylowej /
  FZ dla VaR i ES, DM między prognozami) zamiast „odrzuć/nie odrzuć”; (c) reguła MIERZALNA/NIEMIERZALNA dla
  pierwszej rundy na danych.
- Bez prawdziwych danych (licznik 0).

## Czego NIE robić

Żadnych prognoz VaR/ES na prawdziwych danych; nie zmieniać `miara/var_es.py` (zamrożony po KV1) — nowe
statystyki w `symulacje/`.

## Kryteria odbioru (dowody)

README rundy z werdyktem, `raw_output.txt`, wiersz w `runs/INDEX.md`; niezależna weryfikacja liczb.

## Wynik

(dopisuje orkiestrator)
