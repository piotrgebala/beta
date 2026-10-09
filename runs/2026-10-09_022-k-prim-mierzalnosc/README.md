# 022 — czy reguła K′ (bootstrap blokowy) w ogóle może być mierzalna: górna granica mocy

**Status: ZAKOŃCZONA — K′ NIEMIERZALNA, runda K′ nie startuje; werdykt Ready.** Pre-rejestracja `bd11a21`, kod `37a73c9` (oba przed liczeniem). Typ: laboratorium (panele syntetyczne z 021, zero nowych
symulacji, zero danych rynkowych) — **poza licznikami** („ryzyko 2021+” zostaje 1, rejestr alpha nietknięty).

## Skąd ta runda

Karta 021 (Caveats): zamrożona reguła K odrzuca estymowany GARCH-t w komórkach B zbyt często (K-a 28,7 / 20,3 / 17,0 % wobec progu 10 %).
Rozbicie z 021: winne są składowe **A** (odsetek trafień: 16,8 / 11,7 / 10,1 %) i **C** (ES: 21,2 / 14,4 / 12,6 %), składowa B (skupianie) tylko 5,7 / 4,0 / 2,9 %.
Przyczyna: trafienia estymowanego GARCH-t są zależne w czasie (rozrzut odsetka trafień między panelami 1,40–1,64 raza większy niż błąd przy niezależnych dniach;
wyrocznia 1,00–1,01), a test A i C liczy błąd jak dla niezależnych dni. Karta 022 (a′) proponuje regułę K′: ten sam test, ale błąd z bootstrapu blokowego.

**Decyzja:** użytkownik 2026-10-09 („przejdź do aktualnych zadań i zacznij realizować”, po pytaniu, czy zamknąć 022, czy iść w (a′)) — przyjmuję jako zgodę na
rekomendację (a′). Pliki zamrożone nietknięte; K′ to nowy kod. Zgodnie z R3 zaczynam od mierzalności.

## Pomysł rachunku (jednym zdaniem)

Żaden test z **szacowanym** błędem (bootstrap blokowy, HAC) nie ma większej mocy niż ten sam test z **prawdziwym** błędem; prawdziwy błąd znamy z laboratorium —
to rozrzut statystyki między 4 000 paneli. Jeśli nawet z prawdziwym błędem moc wobec σ −10 % jest < 80 %, reguła K′ jest NIEMIERZALNA i runda K′ nie startuje.

## Procedura (zamrożona przed liczeniem)

- Źródło: `data/lv2d_wyniki_paneli.npz` (021, przebieg rejestrowy, 4 000 paneli × komórki A0, B1, B2, B3; kolumny `hit`, `u_sr`, `zb_b` na panel i prognozę).
- Dla prognozy f w komórce c: SE_A(f) = SD po panelach odsetka trafień, SE_C(f) = SD po panelach `u_sr` (średni wskaźnik ES).
  z_A = (hit − 0,05) / SE_A(f); z_C = (u_sr − 1) / SE_C(f).
- Test idealny K*: odrzuca, gdy |z_A| > 2,394 (dwustronnie α/3, jak „rowne”) **albo** z_C > 2,128 (prawostronnie α/3, jak „prawa”) **albo** zapisane `zb_b` = 1
  (składowa B bez zmian w K′; nie ma problemu z błędem — jej statystyka jest odporna na zależność przy H0). Wariant opisowy: bez B.
- K-a* = odsetek odrzuceń `garch_x1.00`, K-b* = odsetek odrzuceń `garch_x0.90`; progi bez zmian: **K-a ≤ 10 %, K-b ≥ 80 %**.
- Kontrola (R8): ten sam rachunek dla wyroczni `wyr_t5` (oczekiwane ok. 5 %: Bonferroni α/3 × 3) i `zan30` (oczekiwane ok. 100 %).
- Opis: K-b* dla `garch_x0.95 / 0.85 / 0.80 / 0.70` → najmniejsze zaniżenie σ wykrywalne z mocą ≥ 80 % (MDE).

## Reguła decyzji (zapisana z góry)

- **B2 (komórka główna, VR jak w danych): K-b* < 80 % → K′ NIEMIERZALNA** → runda K′ na laboratorium nie startuje; rekomendacja (b): runda VaR/ES na danych
  (018) przy 4 monetach × 1 691 dni nie ma mocy wobec σ −10 % → 018 do zamknięcia albo do przeformułowania (inny cel mocy = zmiana zamrożonego progu → decyzja użytkownika).
- **B2: K-b* ≥ 80 % i K-a* ≤ 10 %** → K′ może być mierzalna → osobna pre-rejestracja K′ (długość bloku, nowe ziarna, przebieg na laboratorium).
- **B2: K-a* > 10 % przy prawdziwym błędzie** → problem nie leży w błędzie testu, tylko w samej prognozie (średnie zaniżenie ryzyka) → K′ nie pomoże; kierunek (d).
- B1, B3, A0 — opis.

## Przewidywanie (zapisane przed liczeniem)

Rachunek z n_eff w karcie 022 dawał moc K-b ok. 62–71 %. Przewiduję **K-b* w B2 = 60–75 % → NIEMIERZALNA** (pewność 75 %), K-a* w B2 ≤ 10 % (pewność 70 %).

## Wynik (`raw_output.txt`)

| komórka | K-a* (x1.00, próg ≤ 10 %) | **K-b* (σ −10 %, próg ≥ 80 %)** | σ −15 % | zapisane K z 021 (K-a / K-b) | werdykt |
|---|---|---|---|---|---|
| A0 (bez przesunięć poziomu) | 5,4 % | 93,2 % | 100 % | 5,4 / 96,9 % | mierzalna |
| B1 (VR 1,72) | 10,7 % | 68,0 % | 92,9 % | 28,7 / 93,7 % | NIEMIERZALNA |
| **B2 (VR 2,26, jak w danych)** | **8,7 %** | **65,0 %** | **91,9 %** | 20,3 / 90,2 % | **NIEMIERZALNA** |
| B3 (VR 2,81) | 7,4 % | 59,9 % | 88,7 % | 17,0 / 86,1 % | NIEMIERZALNA |

Kontrole (R8): wyrocznia odrzucana 4,3–4,9 % (oczekiwane ok. 5 %), `zan30` 100 %. W A0 test idealny daje te same liczby co zapisany (K-a 5,4 % = 5,4 %) — tam
błąd dla niezależnych dni jest dobry, więc rachunek nie „psuje” testu tam, gdzie nie trzeba.

**Druga droga** (`raw_druga_droga.txt`, wzór dla rozkładu normalnego z samego średniego przesunięcia z̄, bez liczenia panel po panelu): B2, σ −10 %:
moc A 53,6 % (po panelach 54,0 %), moc C 63,7 % (63,0 %); A i C są skorelowane 0,97, więc „A lub C” leży tuż nad mocą C — zgodne z 65,0 %.

Opis: najmniejsze zaniżenie σ wykrywalne z mocą 80 % przy idealnym błędzie (interpolacja między 0,90 a 0,85): ok. **12,4 % (B1), 12,8 % (B2), 13,5 % (B3)**.
Test z błędem szacowanym (bootstrap blokowy) będzie miał moc mniejszą, więc realnie raczej **ok. 15 %**. Potrzebna długość danych dla σ −10 % przy tym samym koszyku:
z̄ musiałoby urosnąć z 2,48 do ok. 2,97 (próg C 2,13 + 0,84), czyli dni oceny ×1,43 → ok. 2 420 zamiast 1 691, **ok. 2 lata więcej danych (2028)** — i to przy idealnym błędzie.

## Ocena przewidywań

- „K-b* w B2 = 60–75 % → NIEMIERZALNA” (75 %): **trafione** (65,0 %).
- „K-a* w B2 ≤ 10 %” (70 %): **trafione** (8,7 %). W B1 K-a* = 10,7 % — nawet idealny błąd nie mieści estymowanego GARCH-t w progu; to głównie składowa B (5,7 %) i C (5,1 %).

## Co na plus (+)

- Rozstrzygnięcie bez nowej symulacji i bez danych rynkowych: 4 000 paneli × 4 komórki z 021, liczba policzona dwiema drogami.
- Górna granica jest konserwatywna w dobrą stronę: jeśli NIE wychodzi nawet z prawdziwym błędem, żadna sztuczka z błędem (blok, HAC, inna długość bloku) tego nie zmieni.
- Odpowiada wprost na pytanie z 022: K-a w komórkach B to w większości wada błędu testu (zapisane 17–29 % → 7–11 % przy idealnym błędzie), ale po naprawie błędu
  znika moc (90 % → 65 %). Naprawa błędu przenosi porażkę z K-a na K-b — dokładnie to, przed czym ostrzegała karta 022.

## Co na minus (−)

- Wszystko na laboratorium: generator z 021 (przesunięcia poziomu, D = 300) jest tylko jednym modelem danych; inny mechanizm zależności dałby inne liczby.
- „Prawdziwy błąd” to rozrzut między panelami tego samego generatora — test na danych tego błędu nie zna; dlatego to górna granica, nie przewidywanie mocy K′.
- Składowa B przyjęta z zapisu 021 (bootstrap dla niezależnych dni); w B1 sama B daje 5,7 % odrzuceń dobrego modelu.

## Wniosek (prostym językiem)

Mamy za mało danych, żeby sprawdzić prognozę ryzyka tak dokładnie, jak chcieliśmy. Na czterech monetach i ok. 4,6 roku historii test wychwyci zaniżenie zmienności
dopiero od ok. 13–15 %, a nie od 10 %. Poprawianie samego testu (K′) nic tu nie da. Praktycznie: prognozę σ trzeba traktować z zapasem co najmniej ok. 15 %
(tabela „na dziś” już pokazuje σ × 1,25 i × 1,5) i nie oczekiwać, że dane potwierdzą jej dokładność lepiej niż do tego poziomu.

## Werdykt: **Ready**

Rachunek z góry zapisany, wynik po złej stronie progu z dużym zapasem (65 % wobec 80 %), dwie drogi zgodne, kontrole zaliczone.

## Skutki

1. **Runda K′ na laboratorium nie startuje** (R3). Karta 022 → `do_przegladu`.
2. **018 (VaR/ES na danych, cel σ −10 %) → `odrzucone`** jako NIEMIERZALNA przy zamrożonym celu; dane za październik tego nie zmienią (+2 % dni).
   Wznowienie tylko przez: (i) cel mocy σ −15 % zamiast −10 % — to zmiana zamrożonego progu, **decyzja użytkownika**, i nowa pre-rejestracja z regułą K′ na laboratorium;
   albo (ii) ok. 2028 przy tym samym celu.
3. Kierunek (d) — prognoza widząca poziom wariancji — nie leczy mocy (moc zależy od liczby niezależnych faz, nie od prognozy); odkładam do backlogu.

## Użyte skille

- `clas5-runda` — procedura: rachunek mierzalności przed rundą, pre-rejestracja w gicie przed liczeniem, wiersz w INDEX i wniosek skumulowany.
- `data:statistical-analysis` — moc testu, Bonferroni, interpretacja „górnej granicy”.
- `data:validate-data` — druga droga (wzór dla normalnego), kontrole na wyroczni i `zan30`.
- `engineering:code-review` — przegląd `symulacje/k_prim.py` i testów: progi `isf(α/6)` dla A (dwustronnie α/3) i `isf(α/3)` dla C (prawostronnie) zgodne z `p_boot`
  („rowne” i „prawa”); SD z ddof = 1; wejścia sprawdzane. Bez uwag zmieniających liczby. Ready.
