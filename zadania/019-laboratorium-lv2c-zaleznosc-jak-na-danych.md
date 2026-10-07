---
id: 019
tytul: LV2c — laboratorium z zależnością trafień i trwałością zmienności na wzór prawdziwych danych (rozmiar i moc testu K)
typ: badawcze
status: nowe
zlecil: orkiestrator
decyzja_uzytkownika: "2026-10-07: delegacja — „miejsca w których potrzebna jest moja decyzja sam sobie odpowiedz wedługo swojej najlepszej wiedzy”; zlecenie LV2c rozstrzygnął Claude po wyniku karty 017 (README rundy 017, „Decyzje wykonawcy”); na tym punkcie unieważnia decyzję 5 z STATUS.md"
utworzono: 2026-10-07
zalezy_od: [016, 017]
budzet: "Opus, 1–2 sesje (pre-rejestracja, kalibracja generatora na ziarnach pilotażowych, przebieg rejestrowy jak w LV2)"
---

# 019 — LV2c: laboratorium bliższe prawdziwym danym

## Po co

Karta 017 zmierzyła na prawdziwych danych 15 monet (2021–2026), że trafienia VaR 5 % prognozy `garch_tnu` są
bardziej zsynchronizowane niż w laboratorium LV2: VR **7,997** wobec 4,95 w komórce C2 (ρ̂ 0,50 wobec 0,282;
ρ̂ + 2 SE = 0,64), a w 27 % dopasowań (227 z 855) GARCH-t dochodzi do granicy persystencji 0,9999 (w LV2: 2,2 %).
Warunek przeniesienia nr 2 z LV2 nie jest spełniony, więc karta 018 (pierwsza runda VaR/ES na danych) czeka. Ta karta
sprawdza, **czy reguła K (pytanie bezwzględne) pozostaje mierzalna w laboratorium o takiej zależności i takiej
trwałości zmienności**. Nie wiemy z góry, czy test zbiorczy się psuje; to właśnie mierzymy.

## Zakres

1. **Pre-rejestracja w gicie PRZED przebiegiem rejestrowym** (R1–R4, zasada 26), w `runs/RRRR-MM-DD_LV2c-…/README.md`:
   R1 mechanizm jednym zdaniem, R2 zbiór × formuła × target × horyzont, R3 rachunek mierzalności, R4 jedna zmienna
   (siła zależności i trwałości w generatorze), licznik i reguła STOP; przewidywanie zapisane przed wynikiem.
2. **Generator** w NOWYCH plikach (np. `symulacje/garch_panel_wspolny_szok.py`); istniejące pliki zamrożone od `24c8863`
   (`garch_panel.py`, `garch_t.py`, `prognozy_lv2.py`, `moc_var_es.py`, `run_lv2.py`) bez zmian. Dwa nowe elementy
   względem LV2:
   (i) **wspólny szok zmienności** (np. czynnik wspólny w σ_t lub wspólny proces zmienności), tak by dni krachu były
   bardziej synchroniczne niż przy samym czynniku gaussowskim ρ = 0,8;
   (ii) **trwałość bliska granicy** (α + β do 0,9999 dla części monet), tak by odsetek dopasowań przy granicy w
   laboratorium był rzędu 27 % (±5 pp), nie 2 %.
3. **Cel kalibracji zapisany z góry:** VR dla `garch_tnu` przy VaR 5 % w komórce C2 (15 monet × 1 700 dni oceny po
   400 historii) = 7,997 ± 0,35 (ok. ±½ SE z 017), oraz odsetek dopasowań przy granicy 26,5 % ± 5 pp. Kalibracja na
   ziarnach pilotażowych **rozłącznych** od ziaren przebiegu rejestrowego; liczba pilotaży i reguła zatrzymania w
   pre-rejestracji. Z prawdziwych danych wolno użyć wyłącznie tych liczb z 017 (VR, odsetek przy granicy) — nie
   odsetka trafień (karta 017 go nie mierzyła i nie wolno go liczyć).
   Generator ma też zapisać (opis, nie kryterium) rozrzut ρ̂ między panelami i SE bootstrapu blokowego L = 20 (moduł
   `modele/pomiar_rho_h.py`, bez zmian): to dane do kryterium zgodności dla powtórki 017. Obecna bramka 017
   (ρ̂ + 2 SE ≤ 0,282) nie przechodzi nawet przy zależności jak w LV2 (0 z 10 paneli, README 017, sekcja 3), więc kryterium
   zgodności dla 018 trzeba zapisać tak, by przy zależności z LV2c MOGŁO przejść.
4. **Reguła K bez zmian:** test zbiorczy (składniki A/B/C, Bonferroni α/3, bootstrap-t po dniach) z `symulacje/`;
   K-a rozmiar ≤ 10 % na `garch_tnu`, K-b moc ≥ 80 % wobec `garch_tnu_zan10` (σ̂ × 0,90); tylko p = 5 %, tylko komórka C2;
   liczba paneli i ziarna w pre-rejestracji. Progi 10 % i 80 % nie zmieniają się po obejrzeniu wyniku.
5. **Odpowiedzi możliwe i ich konsekwencje (zapisać z góry):**
   - reguła K nadal MIERZALNA przy VR ≈ 8 → warunek przeniesienia nr 2 zastąpiony wartością z LV2c; 018 może być
     zlecona po danych za październik 2026 i powtórce 017;
   - rozmiar K-a > 10 % albo moc K-b < 80 % → NIEMIERZALNA: opcje do przedstawienia użytkownikowi (inna reguła K′ z
     osobną pre-rejestracją, szerszy koszyk, albo zamknięcie rundy VaR/ES na danych).
6. **Kontrole R8** generatora: ujemna (zależność zerowa → VR ≈ 1; wspólny szok wyłączony → wynik jak w LV2 C2) i dodatnia
   (znana zależność → oczekiwane VR); parytet z `generuj_panel` przy wyłączonych nowych elementach.
7. Testy jednostkowe + `hypothesis` (niezmienniki generatora: długości, dodatniość σ², kolejność ziaren, determinizm R19);
   test przecieku nie dotyczy generatora, ale dotyczy każdej nowej prognozy, jeśli powstanie.
8. Własny katalog rundy (zasada 26): README (pre-rejestracja, wynik, „Co na plus / Co na minus”, werdykt, użyte skille),
   `raw_output.txt`, wiersz w `runs/INDEX.md`. Licznik: **poza licznikami** (dane syntetyczne).

## Czego NIE robić

- Nie uruchamiać karty 018 ani nie liczyć odsetka trafień na prawdziwych danych.
- Nie zmieniać plików zamrożonych LV2, progów 10 % i 80 %, poziomu p ani komórki C2 po obejrzeniu wyniku.
- Nie strojenia generatora na wyniku reguły K (kalibracja tylko na VR i odsetku przy granicy, nigdy na odrzuceniach).
- Nie zmieniać estymatora `dopasuj_garch_t` ani granicy persystencji (LV2: „dokładnie `dopasuj_garch_t`”).
- Nie podbijać licznika „ryzyko 2021+” i nie dotykać rejestru alpha; `data/` nie do gita.

## Kryteria odbioru (dowody)

- Commit pre-rejestracji poprzedza przebieg rejestrowy (hash w README); `raw_output.txt` zatwierdzony bez interpretacji.
- README z wynikiem: VR i odsetek przy granicy w generatorze wobec celu, rozmiar K-a i moc K-b z przedziałami, kontrole R8,
  weryfikacja niezależna (druga droga), „Kogo NIE ma w zbiorze”, werdykt Ready/Caveats/Revision podpisany przez Claude.
- `python -m pytest -q` i `python -m ruff check . && python -m black --check .` zielone; commit i push.
- Wiersz w `runs/INDEX.md`; licznik „ryzyko 2021+” = 0.

## Wynik

(dopisuje orkiestrator)
