# beta — instrukcje projektowe (Claude Code)

## Projekt

Program badawczy: modele matematyczne i ML na perpetualach krypto (Binance, BTC i koszyk top-20/50).
Następca metodologii CLAS-5 z repo `alpha`. **Nie przewidujemy kierunku ceny z cech wykresu** — alpha
zamknęła to dowodem braku (p = 50,27 %, n = 7 687; WF1; AU2). Filary: przyrząd (`miara`), laboratorium
symulacji, zmienność i ryzyko ogona, dowody sekwencyjne dla dziennika alpha, portfel, tor ML na nowe dane.
Pełny plan: `docs/PRD.md`. Stan prac i decyzje: `STATUS.md`. Wyniki rund: `runs/INDEX.md`.

## Zasady nienaruszalne

Trzon z alpha (uzasadnienia: `docs/PRD.md` §3; pełne brzmienie w `alpha/docs/rag/08`):

1. **R1 Mechanizm jednym zdaniem przed danymi** („kto traci po drugiej stronie i dlaczego”).
2. **R2 Hipoteza = zbiór informacyjny × formuła × target × horyzont** — te same pola = ten sam wariant.
3. **R3 Rachunek mierzalności PRZED uruchomieniem** — NIEMIERZALNA = runda nie startuje.
4. **R4 Pre-rejestracja + licznik wariantów + reguła STOP**, zapisane przed obejrzeniem wyniku.
5. **R5 Korekta na liczbę prób (DSR) jest częścią przyrządu.**
6. **R6 Walk-forward z purgingiem i embargo; żadnego strojenia na całym zbiorze.**
7. **R7 Test leakage każdej cechy przed modelem.**
8. **R8 Kontrola pozytywna i negatywna każdego silnika.**
9. **R9 Werdykt kierunkowy ma dwa warunki:** t_neff > 1,96 zwrotu netto ORAZ ci_low(p) > p*.
10. **R10 N_eff ≤ n zawsze.**
11. **R11 Reguły kalendarzowe = średnia wszystkich faz startu.**
12. **R12 Więcej transakcji ≠ więcej informacji; 20 monet ≠ 20 obserwacji.**
13. **R13 Zielony backtest to nie dowód** — o kapitale decyduje drabina dowodów (alpha ADR-09).
14. **R14 Skrypt jest neutralnym reporterem; werdykt podpisuje Claude w README rundy.**
15. **R15 LLM nigdy w ścieżce decyzji handlowych.**
16. **R16 Dane tylko od 2021-01-01** — filtr w `config/settings.yaml` (`data.min_start`), jedna funkcja ładująca.

Reguły ML (nowe w beta):

17. **R17 Baseline = najprostszy model.** Złożony wchodzi tylko, gdy bije baseline testem na OOS.
18. **R18 Przeszukiwanie hiperparametrów liczy się do licznika** albo odbywa się wyłącznie w foldzie
    treningowym z siatką zamrożoną w pre-rejestracji.
19. **R19 Model deterministyczny albo z jawnym ziarnem;** „stabilność na seedach” nie jest dowodem.
20. **R20 Ważność cech (SHAP, importance) to filtr, nie dowód.**
21. **R21 Deep learning dopiero, gdy prostszy model przejdzie bramkę i zabraknie mu pojemności.**

Zasady współpracy z alpha:

22. **Wspólny rejestr odczytów.** Każdy odczyt ZWROTU strategii na historii 2021–2026 podbija rejestr
    `alpha/runs/odczyty_historii.csv` (dziś N = 40 → próg t ≈ 3,84). Nowe repo nie daje nowego budżetu.
    Pytania o prognozę zmienności/ryzyka i nowe źródła danych mają własne liczniki (`docs/PRD.md` §11.4).
23. **Alpha tylko do odczytu.** Dziennik papierowy, zamrożone skrypty i dane alpha się czyta, nie zmienia.
    Wpięcie czegokolwiek do dziennika = Poprawka w alpha + decyzja użytkownika.
24. **Parytet przyrządu.** `miara/` daje te same liczby co przyrząd alpha na wektorach testowych
    (`tests/test_parytet_alpha.py`); zmiana przyrządu w jednym repo = ta sama zmiana w drugim.
25. **Commit „zrobiony” = testy jednostkowe + (jeśli dotyczy) leakage + (jeśli dotyczy) `hypothesis`.**
26. **Każda runda we własnym katalogu `runs/RRRR-MM-DD_<id>-<slug>/`** jak w alpha (zasada 11):
    README (pre-rejestracja, wynik, „Co na plus / na minus”, werdykt Ready/Caveats/Revision, użyte skille)
    + `raw_output.txt` + wiersz w `runs/INDEX.md`.
27. **Rozmowa i raporty prostym językiem** (alpha zasada 17).

## Skille

Jak alpha zasada 19: `clas5-quant` (metodologia), `quant-strategy-catalog` (nowa hipoteza), `dataviz`
(wykres), `data:statistical-analysis` / `data:validate-data` (bramki), `engineering:code-review` (przed
scaleniem). Skille żyją w chmurze konta; `.claude/skills/` zostaje puste.

## Podział ról

**Użytkownik:** decyzje bramkowe etapów E0–E6, jakikolwiek kapitał, wszystko nieodwracalne.
**Claude:** autonomia badawcza w ramach zasad; tablica zadań `zadania/`; raport tygodniowy.

## Komendy

```
python -m pytest -q
python -m ruff check . && python -m black --check .
```
