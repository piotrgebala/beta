# 026 — laboratorium K′ (bootstrap blokowy) przy celu mocy σ −15 %

**Status: PRE-REJESTRACJA (przed przebiegiem).** Typ: laboratorium na danych syntetycznych LV2d (K = 4) — **poza licznikami** („ryzyko 2021+” = 1, zwroty alpha N = 40).
Decyzja użytkownika 2026-10-17: cel mocy σ −15 % zamiast −10 % (pole `decyzja_uzytkownika` w `zadania/026-…`).

## Wnioski skumulowane, które dotyczą tej rundy (jedno zdanie)

022: przy 4 monetach × 1 691 dniach test z PRAWDZIWYM błędem ma moc 65 % wobec σ −10 %, ale 92 % wobec σ −15 %; zostaje pytanie, ile mocy zje szacowanie błędu z samych danych,
bo ograniczeniem jest liczba niezależnych faz poziomu wariancji (ok. 6 w 1 691 dniach), nie wzór testu — dlatego rozmiar i moc K′ trzeba zmierzyć, a nie założyć.

## R1 — mechanizm

Gdy poziom wariancji przesuwa się powoli i jest wspólny dla monet, trafienia VaR estymowanego GARCH-t skupiają się w fazach. Test, który liczy błąd jak dla niezależnych dni, jest za pewny siebie
(21: K-a 17–29 %). Bootstrap blokowy kołowy przestawia całe odcinki dni, więc zachowuje zależność wewnątrz bloku i daje szerszy, uczciwszy błąd. Kto traci: ten, kto ufa prognozie ryzyka,
która w fazie wysokiej wariancji zaniża ogon; test ma to wykryć, zanim prognoza posłuży do doboru dźwigni.

## R2 — pola hipotezy

Zbiór informacyjny: panele LV2d (4 monety, kalibracja 021), prognozy z przeszłości. Formuła: test zbiorczy VaR 5 % K′ — składowe A (pokrycie) i C (ogon ES) z bootstrapu blokowego kołowego
o długości L, składowa B (skupianie) bez zmian (iid dni), Bonferroni α/3. Target: odrzucenie H0 „prognoza dobrze skalibrowana”. Horyzont: 1 dzień, p = 5 %, ocena 1 691 dni.
Wariant = (L, komórka); L = 1 jest równoważne zapisanemu K (kontrola, nie nowy wariant).

## Projekt

- Komórki: A0, B1, B2 (główna, VR 2,264), B3 — kalibracja `runs/2026-10-08_021-lv2d-regimy-wariancji/kalibracja.json` (ta sama co 021). Generator i prognozy bez zmian.
- Prognozy: `wyr_t5` (kontrola ujemna), `zan30` (kontrola dodatnia), `garch_x1.00` (rozmiar, K-a), `garch_x0.90`, `garch_x0.85` (moc, K-b przy σ −15 %), `garch_x0.80`.
- Bootstrap: 999 powtórzeń; blok kołowy; długości z siatki **{1, 20, 60, 150}** (zamrożona; 150 ≈ połowa średniej fazy 300 dni).
- **Krok 1 — wybór (ziarno 20 262 601, 2 000 paneli/komórkę):** w komórce B2 spośród L > 1 spełniających K-a ≤ 10 % ORAZ K-b(σ −15 %) ≥ 80 % wybierz L z największym marginesem
  min(10 % − K-a, K-b − 80 %). Brak takiego L → STOP.
- **Krok 2 — potwierdzenie (ziarno 20 262 602, 4 000 świeżych paneli/komórkę):** tylko wybrane L. Strojenie na tych samych panelach wyklucza się tym, że werdykt wydaje WYŁĄCZNIE krok 2.
- Smoke (ziarno 20 269 998) nie jest przebiegiem.
- Rachunek mierzalności (R3): idealny test na tych samych kalibracjach daje K-a* 8,7 % i K-b*(−15 %) 91,9 % w B2 (022) — górna granica mocy K′ jest powyżej progu, więc runda startuje.
  Błąd binarnego odsetka przy 4 000 panelach: SE ≈ 0,5 pp (K-a) i 0,4 pp (K-b).

## Reguła decyzji (zapisana z góry)

Werdykt wydaje krok 2 w komórce **B2**:
- **K′ MIERZALNA** ⇔ K-a(garch_x1.00) ≤ 10 % ORAZ K-b(garch_x0.85) ≥ 80 % ORAZ kontrola ujemna `wyr_t5` ≤ 10 % ORAZ kontrola dodatnia `zan30` ≥ 95 %.
- Punkt w odległości < 2 SE od progu jest „graniczny” i traktowany jak niespełniony (ostrożnie), z adnotacją.
- B1, B3, A0: opis; jeśli K-a > 15 % w B1 lub B3 — zapisuję to jako zastrzeżenie (Caveats), nie jako zmianę werdyktu.
- Kontrola A0: K-a ≤ 10 % (rozmiar tam, gdzie bootstrap blokowy nie jest potrzebny, nie może się popsuć).
- Kontrola L = 1 w kroku 1 powinna odtworzyć zapisane K z 021 (K-a ok. 20 % w B2) w granicach 2 SE ze względu na inne ziarno i 2 000 paneli — jeśli nie, błąd w kodzie, przebieg do powtórzenia po naprawie.

**Reguła STOP:** brak L w kroku 1 ALBO niespełnienie reguły w kroku 2 → K′ NIEMIERZALNA dla zapisanej siatki; nie dodaję długości, nie powtarzam wyboru, nie obniżam progów.
Tor VaR/ES na danych (018) zamknięty do ok. 2028 (σ −10 % przy 2 420 dniach). MIERZALNA → karta 027 (osobna pre-rejestracja rundy na danych; licznik „ryzyko 2021+” 1 → 2 dopiero przy przebiegu).

## Przewidywania (zapisane przed przebiegiem)

- L = 1: K-a w B2 ok. 18–23 %, K-b(−15 %) ≥ 95 % (odtwarza K z 021).
- Bootstrap blokowy zjada moc: dla L = 60 K-b(−15 %) w B2 70–88 %, dla L = 150 65–85 %; K-a spada z ok. 20 % do 9–16 % (L = 20: 13–19 %).
- Szansa, że krok 1 wskaże jakiekolwiek L: **40 %**; że krok 2 potwierdzi: **30 %**. Najbardziej prawdopodobny wynik: K-a ok. 11–14 % przy mocy ok. 80 % — graniczny, czyli NIEMIERZALNA.
- Kontrole: `wyr_t5` ok. 4–6 %, `zan30` 100 %.

## Ograniczenia (z góry)

Dane syntetyczne; jeden mechanizm przesunięć poziomu (reżimy ~300 dni), wybrany w 021; jeden estymator GARCH-t; p = 5 %, horyzont 1 dzień; B2 odwzorowuje VR z danych, ale nie ich historię;
„MIERZALNA” w laboratorium nie znaczy, że prognoza przejdzie na danych — tylko że test miałby szansę ją uczciwie ocenić.

## Użyte skille

`data:statistical-analysis` (rozmiar/moc, SE odsetków, wielokrotne testy: Bonferroni, jedna siatka L), `engineering:code-review` (przed scaleniem).
