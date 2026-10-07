---
id: 017
tytul: dane pod pierwszą rundę VaR/ES — inwentarz 15 monet i zależność trafień ρ_h (karta opisowa)
typ: badawcze
status: nowe
zlecil: orkiestrator
decyzja_uzytkownika: "2026-10-07: delegacja — „miejsca w których potrzebna jest moja decyzja sam sobie odpowiedz wedługo swojej najlepszej wiedzy”; otwarcie rundy na danych rozstrzygnął Claude (STATUS.md, „Decyzje podjęte przez Claude”, pkt 1–4)"
utworzono: 2026-10-07
zalezy_od: [014, 016]
budzet: "Opus, 1 sesja"
---

# 017 — dane pod pierwszą rundę VaR/ES: inwentarz i ρ_h

## Po co

LV2 (karta 016) uznała pierwszą rundę VaR/ES na danych za MIERZALNĄ tylko pod warunkami przeniesienia (README
rundy, sekcja „Werdykt”, warunki 1 i 2): prawdziwe dane muszą domykać komórkę C2 (15 monet × 1 700 dni oceny po
400 dniach historii), a zależność trafień ρ_h na danych musi być nie większa niż w laboratorium. Ta karta sprawdza
te dwa warunki **bez oceniania jakiejkolwiek prognozy**, żeby pre-rejestracja karty 018 nie była pisana na ślepo.

## Zakres

1. **Inwentarz.** Lista i kolejność 15 monet z F2-1b (`python -m modele.run_f21b --tylko-monety`, tabela w
   `runs/2026-10-06_f21b-har-vs-dziennik-dlugie/README.md`) zapisana w README tej karty. Dla każdej monety: liczba dni z
   poprawnym dziennym zwrotem, pierwszy i ostatni dzień, dni brakujące i dlaczego.
2. **Czy okno się domyka.** Potrzeba 400 dni historii + 1 700 dni oceny = 2 100 dni zwrotów dla każdej z 15 monet.
   Dane obcięte na 2026-09-30 dają 2 099 dni kalendarzowych (≤ 2 098 zwrotów), więc **dwa dni brakuje już u BTC**;
   F2-1b ma ponadto tylko 1 636 dni oceny dla XRP, SOL, LTC, FIL i NEAR (przez dni nieważne w danych 5m). Karta ma
   rozstrzygnąć: (a) czy dzienne świece 1d, z których wystarczy liczyć zwrot, mają te dni; (b) czy „1 700 dni” da się
   domknąć dopiero po dopłynięciu danych za październik 2026 (automat miesięczny, po 2026-11-01); (c) jak zapisać okno
   oceny w 018 (np. ostatnie 1 700 dni, 400 poprzedzających jako historia). Rozstrzygnięcie idzie do README karty z
   uzasadnieniem. Jeśli okno nie domyka się dla którejś monety, **zatrzymuję się i wracam do użytkownika**
   (komórka C2 jest wymagana „dokładnie”); niczego nie zmieniam po cichu.
3. **Zależność trafień ρ_h.** Dla prognozy `symulacje.garch_t.dopasuj_garch_t` (zerowa średnia, refit co 30 dni, okno
   rosnące od ≥ 400 dni, ogon t_ν̂, wariancja początkowa z próby; dokładnie ta konwencja) przy p = 5 % policzyć na
   prawdziwych danych VR = Var(S_t)/(K p (1 − p)) i ρ_h = (VR − 1)/(K − 1), gdzie S_t to liczba monet z
   przekroczeniem VaR w dniu t. Błąd standardowy ρ̂ i sposób jego liczenia (np. bootstrap blokowy po dniach) zapisać w
   README **przed** uruchomieniem. Warunek 2 z LV2: **ρ̂ + 2 SE ≤ 0,282** (VaR 5 %).
4. **Wydruk bez odsetka trafień.** Skrypt drukuje inwentarz, VR, ρ̂, SE i wynik warunku; **nie drukuje** odsetka
   trafień, żadnej statystyki testu zbiorczego ani testów Kupca i Christoffersena i nie zapisuje macierzy trafień na
   dysk. Test pilnuje, że wydruk nie zawiera tych liczb.
5. Nowy kod w `modele/` albo `dane/` (nie w `symulacje/` i nie w `miara/`: kod badany LV2 jest zamrożony od commitu
   `24c8863`), z testami jednostkowymi, testem przecieku (prognoza na dzień t używa wyłącznie zwrotów z dni < t) i
   `hypothesis` tam, gdzie ma to sens. Dane przez `dane.ladowanie.wczytaj_swiece` (R16).
6. Własny katalog `runs/RRRR-MM-DD_017-…/` (zasada 26): README z pre-rejestracją (R1–R4 w zakresie, w jakim dotyczą
   karty opisowej), `raw_output.txt`, wiersz w `runs/INDEX.md` (licznik opisowy, **nie** „ryzyko 2021+”).

## Czego NIE robić

- Nie oceniać żadnej prognozy: ani trafień, ani testu zbiorczego, ani ES, ani porównań prognoz.
- Nie liczyć prognoz okna 60 dni, EWMA ani HAR (poza zakresem).
- Nie zmieniać `symulacje/`, `miara/` ani progów z README LV2 (0,282 zostaje).
- Nie podbijać licznika „ryzyko 2021+” (zostaje 0) i nie dotykać rejestru alpha.
- Nie wkładać `data/` do gita.

## Kryteria odbioru (dowody)

- README rundy z listą 15 monet (kolejność), tabelą dni na monetę, rozstrzygnięciem okna (2a–2c), VR, ρ̂, SE,
  ρ̂ + 2 SE wobec 0,282 i jednoznacznym zdaniem: „018 może ruszyć” albo „018 nie startuje, bo …”.
- `raw_output.txt`; w wydruku brak odsetka trafień (sprawdza test).
- `python -m pytest -q` i `python -m ruff check . && python -m black --check .` zielone; commit i push na bieżącą gałąź.
- Wiersz w `runs/INDEX.md`; licznik „ryzyko 2021+” = 0.

## Wynik

(dopisuje orkiestrator)
