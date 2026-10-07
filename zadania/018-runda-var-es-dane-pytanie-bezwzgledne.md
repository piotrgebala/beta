---
id: 018
tytul: pierwsza runda VaR/ES na prawdziwych danych — pytanie bezwzględne, GARCH-t, p = 5 %
typ: badawcze
status: czeka_na_decyzje
zlecil: orkiestrator
decyzja_uzytkownika: "2026-10-07: delegacja — „miejsca w których potrzebna jest moja decyzja sam sobie odpowiedz wedługo swojej najlepszej wiedzy”; otwarcie rundy rozstrzygnął Claude (STATUS.md, „Decyzje podjęte przez Claude”, pkt 1–4); uruchomienie dopiero po 017 i po zapisaniu pre-rejestracji w gicie"
utworzono: 2026-10-07
zalezy_od: [016, 017, 019]
budzet: "Opus, 1–2 sesje"
---

# 018 — pierwsza runda VaR/ES na danych

## Po co

Pytanie, na które LV2 pozwoliła odpowiedzieć: **czy prognoza VaR 5 % z modelu GARCH(1,1)-t, dopasowywanego
na bieżąco do dziennych zwrotów 15 monet, jest skalibrowana na prawdziwych danych 2021–2026** (przekroczenia pojawiają
się z właściwą częstością i bez wspólnych skupisk). To pytanie o jakość pomiaru ryzyka, nie o zysk, więc leży w
liczniku „ryzyko 2021+” (PRD §11.4), nie w rejestrze zwrotów alpha. Odrzucenie znaczy „nie jest skalibrowana”, a nie
„jest bezużyteczna”; brak odrzucenia nie znaczy „jest dobra”.

## Zakres

1. **Nie ruszać, dopóki karta 017 nie powie „018 może ruszyć”** (okno 2 100 dni domknięte dla wszystkich 15 monet,
   ρ̂ + 2 SE ≤ 0,282). Jeśli 017 powie inaczej, ta karta przechodzi na `czeka_na_decyzje` i wracam do użytkownika.
2. **Pre-rejestracja w gicie PRZED uruchomieniem** (R1–R4, zasada 26): `runs/RRRR-MM-DD_018-…/README.md` z
   - R1: mechanizm jednym zdaniem („kto traci po drugiej stronie i dlaczego”): kto liczy kapitał na zaniżonym VaR,
     ten traci w dniach ogona; więc zaniżone ryzyko ma koszt i da się je wykryć po częstości przekroczeń;
   - R2: zbiór informacyjny (dzienne zwroty 15 monet do dnia t − 1) × formuła (`dopasuj_garch_t`, zerowa średnia,
     refit co 30 dni, okno rosnące od ≥ 400 dni, ogon t_ν̂, wariancja początkowa z próby) × target (przekroczenie
     VaR 5 % w dniu t) × horyzont 1 dzień;
   - R3: rachunek mierzalności = LV2 (reguła K w C2: K-a 5,0 %, K-b 99,6 %) plus wynik karty 017; NIEMIERZALNA = nie startuje;
   - R4: jedna zmienna (poziom p = 5 %), lista monet i kolejność z góry, **jeden przebieg**, reguła STOP: brak
     powtórek, brak zmiany p, progu ani okna po obejrzeniu wyniku; licznik „ryzyko 2021+” 0 → 1 w chwili uruchomienia;
   - test: ten sam test zbiorczy (składniki A/B/C, Bonferroni α/3), co w LV2 dla `garch_tnu` (kod `symulacje/` bez zmian,
     zamrożony od `24c8863`), nominalny poziom 5 %; odrzucenie czytane względem 5,0–5,5 % fałszywych alarmów z LV2;
   - raport obok p: odsetek trafień i VR (warunek 6 LV2); R9/R13: wynik nie wpina niczego do dziennika alpha (R23);
   - przewidywanie zapisane przed wynikiem (co oczekuję i dlaczego); kontrola pozytywna i negatywna silnika (R8):
     odesłanie do KV1/LV1/LV2 plus przebieg tego samego skryptu na danych syntetycznych o tej samej konfiguracji
     (15 monet × 2 100 dni), gdzie wynik jest znany z góry.
3. **Hash commita pre-rejestracji** w README, potem przebieg (deterministyczny, R19), `raw_output.txt` zatwierdzony bez
   interpretacji, dopiero potem opis wyniku.
4. **Niezależne przeliczenie** wyniku drugą drogą (jak w LV2: inny kod dla prognoz bez dopasowania, `arch` dla GARCH
   w granicach szumu) i „Kogo NIE ma w zbiorze”.
5. Werdykt Ready/Caveats/Revision podpisuje Claude w README (R14); wiersz w `runs/INDEX.md`; licznik „ryzyko 2021+” = 1;
   użyte skille. Testy jednostkowe + leakage + `hypothesis` tam, gdzie dotyczy (zasada 25).

## Czego NIE robić

- Nie zadawać pytań porównawczych (EWMA vs GARCH, DM) — reguła P jest NIEMIERZALNA przy tym n.
- Nie oceniać okna 60 dni ani EWMA testem bezwzględnym (odrzucane w 77–97 % paneli z założenia).
- Nie używać innej konwencji startu GARCH (w pakiecie `arch` domyślna zmienia fałszywy alarm przy 1 % z 7,25 % na 10,75 %).
- Nie dodawać drugiego poziomu p (wymagałby α/2) ani ES w tej rundzie.
- Nie dosypywać danych ani nie powtarzać po obejrzeniu wyniku. Nie uruchamiać bez zatwierdzonej pre-rejestracji.
- Nie dotykać dziennika papierowego alpha ani rejestru `odczyty_historii.csv`.

## Kryteria odbioru (dowody)

- Commit pre-rejestracji poprzedza przebieg (hash w README); `raw_output.txt` zatwierdzony przed opisem wyniku.
- README z wynikiem, „Co na plus / Co na minus”, weryfikacją niezależną, werdyktem i użytymi skillami.
- `python -m pytest -q` i `python -m ruff check . && python -m black --check .` zielone; commit i push.
- Licznik „ryzyko 2021+” w `runs/INDEX.md` = 1 i spójny z README.

## Wynik

**Nie uruchomiona (2026-10-07).** Karta 017 dała wynik „bramka zależności NIE PRZECHODZI” (ρ̂ + 2 SE = 0,639 > 0,282;
okno C2 ma 2 091 z 2 100 wierszy), więc zgodnie z pre-rejestracją 017 ta runda nie startuje. Żadnych odsetków trafień
na prawdziwych danych nie policzono.

Wznowienie wymaga łącznie:

1. karta 019 (LV2c) pokazuje, że reguła K (rozmiar ≤ 10 %, moc ≥ 80 %) jest MIERZALNA w laboratorium o VR ≈ 8
   i trwałości blisko granicy;
2. dane za październik 2026 domykają okno 2 100 wierszy;
3. powtórka 017 na ostatecznym oknie jest zgodna z założeniami LV2c;
4. własna pre-rejestracja 018 zapisana w gicie przed przebiegiem.

Dopiero wtedy status wraca na `nowe` (decyzja orkiestratora; licznik „ryzyko 2021+” rośnie z 0 do 1 dopiero przy
przebiegu).
