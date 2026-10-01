# LD1 — laboratorium F3: e-procesy dla dziennika alpha przy codziennym zaglądaniu (2026-10-01)

> **STATUS: ZAMKNIĘTA — bramka 1 TAK, bramka 2 NIE → reporter tylko opisowy (D3-a).** e-procesy prawie
> nigdy nie dają fałszywego alarmu (≤ 0,9 %), ale też prawie nigdy nie widzą prawdziwego efektu w ciągu roku
> (moc ≤ 0,9 % wobec 3,4–10,9 % odczytów ADR-09). Pre-rejestracja `aea82dd`. 0 wariantów, poza licznikami.
> Poprzednio: **PRE-REJESTRACJA (przed przebiegiem).**

## W skrócie — prostym językiem

Dziennik alpha oceniamy dziś trzy razy (po 3, 6 i 12 miesiącach) progiem z = 2,31. Chcemy obok mieć
„licznik dowodu”, na który wolno patrzeć codziennie bez zawyżania fałszywych alarmów (e-proces). Na sztucznych
dziennikach sprawdzamy dwie rzeczy: czy licznik rzadko krzyczy bez powodu i czy widzi prawdziwy zysk co najmniej
tak dobrze jak trzy odczyty z ADR-09. To tylko REPORTER — o nodze dalej decyduje ADR-09.

## Metadane

- Zadanie 004 (etap E3). D3 nierozstrzygnięta — budujemy reporter, co jest zgodne z obiema opcjami D3
  (rekomendacja „tylko reporter”); żadne kryterium alpha się nie zmienia.
- Kod: `dowody/eproces.py` (mieszanka jednostronna po połówce N(0, τ²), postać zamknięta zgodna z całką
  numeryczną do 1e-8), `dowody/bayes.py`, `dowody/nogi.py` (μ, σ nóg = kopia alpha, test zgodności),
  `dowody/raport.py`; testy `tests/test_dowody.py`.
- Skrypt `symulacje/run_ld1.py`; komenda `python -m symulacje.run_ld1` → `raw_output.txt`.
- Dane: WYŁĄCZNIE syntetyczne; 20 000 ścieżek × 365 dni na komórkę, ziarno 20261001.

## Pre-rejestracja (zapisana przed przebiegiem)

- **Mechanizm (R1):** brak — kalibracja przyrządu.
- **e-procesy:** obalenie (H0: μ = zakładane, m0 = μ_d, strona −1), potwierdzenie (H0: μ ≤ 0, strona +1);
  σ zakładana z ADR-09; τ = μ_d / σ_d² (alternatywa: zero przewagi / zakładane μ); próg e ≥ 40 (α = 2,5 %,
  jak łączna jednostronna szansa fałszywego obalenia w ADR-09). Patrzymy CODZIENNIE przez 365 dni.
- **Porównanie:** ADR-09 — trzy odczyty po 92/182/365 dniach, z = Σ (x − m0) / (σ √n) < −2,31 (obalenie),
  analogicznie > 2,31 (potwierdzenie, tylko do porównania mocy).
- **Rozkłady dziennych zwrotów:** normalny; t₃ (grube ogony); t₃ + GARCH(1,1) (grupowanie zmienności).
  Nogi: TS1, CP1, R1, X1 z μ, σ z ADR-09.
- **Bramka 1 (PRD F3):** fałszywe alarmy obu e-procesów ≤ 5 % (górna granica Wilsona 95 %), dla każdej nogi
  i każdego rozkładu.
- **Bramka 2 (PRD F3):** moc potwierdzenia przy prawdziwym +15 %/rok ≥ mocy trzech odczytów z = 2,31
  (rozkład normalny, każda noga).
- **Opis:** fałszywe alarmy ADR-09, moc obalenia przy μ = 0 (e-proces vs ADR-09).
- **Werdykt:** bramka 1 i 2 → reporter gotowy jako kandydat na kryterium (opcja D3-b do rozważenia);
  tylko bramka 1 → reporter tylko opisowy (D3-a); bramka 1 nie → reporter niegotowy, poprawka przyrządu.
- **Liczniki:** 0 wariantów, POZA licznikami (dane syntetyczne; dziennika nie czytamy w tej rundzie).

## Wynik

`raw_output.txt` (58 s). W nawiasach — trzy odczyty ADR-09 na tych samych ścieżkach.

| noga | fałszywe obalenie e (ADR) | fałszywe potwierdzenie e (ADR) | moc obalenia przy μ = 0 e (ADR) | moc potwierdzenia przy +15 % e (ADR) |
|---|---|---|---|---|
| TS1, normalny | 0,00 % (2,52 %) | 0,00 % (2,51 %) | 0,00 % (7,51 %) | 0,00 % (10,46 %) |
| CP1, normalny | 0,02 % (2,31 %) | 0,03 % (2,56 %) | 0,36 % (10,86 %) | 0,06 % (5,03 %) |
| R1, normalny | 0,01 % (2,54 %) | 0,01 % (2,48 %) | 0,12 % (10,39 %) | 0,10 % (8,19 %) |
| X1, normalny | 0,00 % (2,45 %) | 0,00 % (2,40 %) | 0,00 % (4,10 %) | 0,00 % (5,27 %) |
| najgorszy przypadek (CP1, t₃ + GARCH) | 0,54 % (2,15 %) | 0,50 % (2,44 %) | 0,86 % (6,25 %) | 0,64 % (3,42 %) |

Pełna tabela (t₃, t₃ + GARCH dla wszystkich nóg) w `raw_output.txt`.

- **Bramka 1 — TAK:** fałszywe alarmy e-procesów ≤ 0,54 % wszędzie (próg 5 %). ADR-09 trzyma swoje 2,5 %
  (2,1–2,8 %), także przy grubych ogonach.
- **Bramka 2 — NIE:** moc potwierdzenia przy +15 %/rok to 0,00–0,10 % wobec 5,0–10,5 % trzech odczytów.

## Co na plus (+) / Co na minus (−)

**(+)** Przyrząd jest poprawny: wzór zgodny z całką do 1e-8, średnia E pod H0 ≈ 1, fałszywe alarmy daleko
poniżej α także przy t₃ i GARCH. ADR-09 przy grubych ogonach i grupowaniu zmienności zachowuje ~2,5 %
fałszywych obaleń (to niezależne potwierdzenie doboru z = 2,31 w alpha).
**(−)** W horyzoncie roku e-proces jest praktycznie ślepy: efekty nóg to 0,3–0,9 błędu standardowego
rocznie, a e-wartość 40 wymaga dowodu rzędu √(2 ln 40) ≈ 2,7 SE plus „opłata” za mieszankę. Cena za prawo
codziennego zaglądania jest tu za wysoka. Moc samych odczytów ADR-09 też jest mała (3–11 %) — dziennik
w rok rozstrzyga mechanikę, nie przewagę (zgodnie z alpha `dziennik/README.md`). Model symulacji zakłada
stałą σ = zakładanej; inna prawdziwa σ zmienia oba przyrządy.

## Werdykt

**Ready (jako reporter opisowy).** Zgodnie z regułą z pre-rejestracji: tylko bramka 1 → F3 zostaje
reporterem obok ADR-09 (opcja D3-a). Opcja D3-b (e-proces jako kryterium) nie ma uzasadnienia — przy tej
długości danych byłby słabszy od obecnych trzech odczytów. Bardziej informacyjny w raporcie jest rozkład
a posteriori (`dowody/bayes.py`) — opis, nie decyzja.

## Wniosek

**Prostym językiem:** licznik dowodu, na który wolno patrzeć codziennie, działa poprawnie — nie krzyczy bez
powodu. Ale w ciągu roku dziennik daje za mało danych, żeby cokolwiek nim rozstrzygnąć; obecne trzy odczyty
z alpha są czulsze. Rekomendacja dla D3: **(a) tylko reporter**, bez zmiany kryterium ADR-09.

## Użyte skille

Brak wczytanych skilli w tej sesji — procedura rundy wzorowana na alpha NC1 i CLAUDE.md beta (zasady 25–26).
