# beta — status (plan, decyzje, ryzyka, backlog)

## Decyzje użytkownika

- **2026-09-30** — D1: „osobne repo”; D5: „niech nazywa się beta” (`docs/PRD.md` §15, ADR [0001](docs/adr/0001-osobne-repo.md)).

- **2026-09-30** — „Rób co chcesz, ma działać”: przyjęte jako zgoda na rekomendacje **D2** (F0 → F1 → F2,
  F3 równolegle) i **D4** (dane 5m top-20 od 2021). D3 i D6 nadal otwarte.

- **2026-10-05** — **D6: tak** — DVOL (Deribit) jako źródło dla modeli zmienności, tylko DVOL (pełne opcje
  dopiero, gdy F2 pokaże wartość); zadanie 006. Nowa zasada 28 w `CLAUDE.md`: commit i push po każdej
  większej zmianie.

- **2026-10-05** — „stwórz wszystkie repa na bundle oraz uzupełnij w nich README oraz CLAUDE.md”: bundle
  zaprojektowany (ADR `bundle/docs/adr/0001`), lokalnie założone `~/bundle`, `~/miara`, `~/kolektory`,
  `~/wykonanie` (szkielety). Na GitHubie zakłada je użytkownik (instrukcja w `bundle/README.md`).

- **2026-10-06** — „LV1: poprawiona, 011: a, E0: zamknij”: **E0 zamknięty**; w LV1 obowiązuje reguła
  poprawiona (x\* = 0,10 przy obu p, ii-a tylko przy 1 %); **011 = (a) F2-1b** (monety z pełną historią).

- **2026-10-07** — **Delegacja:** „miejsca w których potrzebna jest moja decyzja sam sobie odpowiedz wedługo
  swojej najlepszej wiedzy”. To nie jest Twoja decyzja w żadnej z poniższych spraw, tylko zgoda, żebym je
  rozstrzygnął sam. Co rozstrzygnąłem — w następnej sekcji.

- **2026-10-07** — **Koszyk: „rób tylko prognozy na eth btc sol, bnb”.** Zinterpretowałem jako: prognozy
  zmienności i ryzyka (VaR/ES), jedyne prognozy w programie, i tylko dla BTC, ETH, SOL, BNB (4 monety zamiast 15).
  To Twoja decyzja i wyprzedza pkt 2 i 9 poniżej oraz „15 monet” w kartach 017–019. Dane są (od 2021-01-01 do
  2026-09-30: BTC, ETH, BNB 2 099 wierszy, SOL 2 094), ale liczby z LV1/LV2 dotyczą 20 i 15 monet. Dla K = 4 moc
  testu zbiorczego jest niezmierzona (LV1: pojedyncza moneta wykrywa zaniżenie σ tylko w 10–17 % przypadków), więc
  przed jakąkolwiek rundą na danych potrzebny jest rachunek mierzalności K = 4 (R3). Kierunek ceny nie wchodzi w
  grę (alpha zamknęła go dowodem braku); gdyby chodziło o niego, napisz. Plan: karta 020 (opis 4 monet), potem 019
  przeliczona na K = 4, potem 018.

## Decyzje podjęte przez Claude na delegację (2026-10-07)

Każdą z nich możesz zmienić jednym zdaniem. Przy każdej: powód i jak ją cofnąć. Nie podjąłem żadnej decyzji
nieodwracalnej ani dotyczącej kapitału; rzeczy, których nie mogę zrobić z założenia (scalenie do `main`, konto
GitHub i klucze), zostały po Twojej stronie.

| # | sprawa | decyzja | dlaczego | jak cofnąć |
|---|---|---|---|---|
| 1 | 016(a): czy otwierać pierwszą rundę VaR/ES na danych | **Tak, ale etapami.** Karta 017 (opisowa, bez oceny prognozy, licznik zostaje 0) → karta 018 (pre-rejestracja zapisana i zatwierdzona w gicie PRZED uruchomieniem). Dopiero uruchomienie 018 podbija licznik „ryzyko 2021+” 0 → 1. | Laboratorium LV2 mówi, że pytanie bezwzględne da się zmierzyć. Licznik ryzyka jest osobny od rejestru zwrotów alpha (PRD §11.4), więc nie zużywa budżetu strategii. Testy VaR/ES należą do etapu E2, który jest już otwarty rundami F2-1/F2-1b, więc to nie jest nowa bramka E. Bez rundy na danych program ryzyka stoi. | Przed uruchomieniem 018: napisz „nie”, a ustawię 018 na `odrzucone`. Po uruchomieniu licznik zostaje 1 (tego nie da się cofnąć), dlatego uruchomienie poprzedzi osobna pre-rejestracja. |
| 2 | 016(b): odczytanie Zakresu (b), 15 monet × 1 700 dni | **Przyjmuję odczytanie z README rundy, pkt 10:** zakres (b) jest otwarty tylko dla pytania bezwzględnego K. | Trzy flagi leżą na kontrolach reguły porównawczej P, której nie używamy; w regule K (komórka C2) flag nie ma. Surowsze odczytanie zamknęłoby jedyny dostępny zakres bez realnego powodu. **Uwaga:** odczytanie zaproponowałem ja i ja je zatwierdzam, więc to słabsza kontrola niż Twoja. | Odrzuć: 018 na `odrzucone`; pierwsza runda czeka na ≥ 20 monet z ≥ 1 600 dniami (np. top-50). |
| 3 | 016(c): próg K-a ≤ 10 % | **Przyjmuję.** | Przy jedynym poziomie p = 5 % nie rozstrzyga: fałszywy alarm 5,5 % (C1) i 5,0 % (C2). Próg wybrany po pilotażu zostaje w README jako jeden z powodów werdyktu Caveats. | Zmiana progu po fakcie to ścieżka rozwidlenia; jeśli chcesz inny, zapisz go przed 018. |
| 4 | 016(d): poziom VaR | **Jedyny poziom: p = 5 %.** | Fałszywy alarm 5,5 % zamiast 8,2 %; mała wrażliwość na konwencję startu GARCH (6,0 % wobec 6,75 %); jedno p nie wymaga korekty α/2. | Zmiana na 1 % albo dwa poziomy: przed pre-rejestracją 018; dwa poziomy wymagają α/2. |
| 5 | 016(e): czy zlecić LV2c | **Nie zlecam.** Trafia do Backlogu z wyzwalaczami (niżej). **Unieważniona pkt. 9 (2026-10-07, po wyniku 017): wyzwalacz (i) zadziałał.** | Do pierwszej rundy bezwzględnej nie jest potrzebne; pytanie porównawcze (reguła P) jest NIEMIERZALNE i nikt go teraz nie zadaje. | Napisz „zleć LV2c”, a założę kartę. |
| 6 | D3: rola oceny sekwencyjnej wobec ADR-09 alpha | **(a) tylko reporter obok z = 2,31** (rekomendacja PRD §15). | Dziennik alpha jest tylko do odczytu (R23), a nowy test nie powinien zmieniać kryterium, na którym stoi kapitał (R13). | Zmiana na (b) musi być zapisana przed 2026-12-24. |
| 7 | 013: cztery repo na GitHubie (bundle, miara, kolektory, wykonanie) | **Odkładam** (status `odrzucone` = „nie teraz”, karta zostaje do wznowienia). | Praca leży w `beta`, push działa, a cztery puste repo niczego nie odblokowują; migracja `miara` jest po E2 (ADR `bundle/0001` pkt 3). Zakładanie wymaga Twojego konta i kluczy, których Claude nie tworzy. Ryzyko: szkielety bundla (po jednym commicie) mają jedną kopię, na serwerze. | Zmień status karty 013 na `nowe` i załóż puste repo wg `~/bundle/README.md`. |
| 8 | Skład top-20 po 2026-06 | **Odkładam.** | Aktualizacja listy to Poprawka w alpha (R23, karta 015 w alpha). Pierwsza runda używa 15 monet z pełną historią od 2021, których zmiana składu nie dotyczy. | Wyzwalacz w Backlogu. |
| 9 | Po wyniku 017: czy zlecić LV2c i co z 018 | **Zlecam LV2c jako kartę 019** (laboratorium z VR ≈ 8 i trwałością zmienności blisko granicy 0,9999; tylko p = 5 %, komórka C2, reguła K bez zmian); **018 → `czeka_na_decyzje`** (nie uruchamiam). Szerszego koszyka nie wybieram. Licznik „ryzyko 2021+” zostaje 0. | 017 pokazała na prawdziwych danych VR = 8,0 wobec 4,95 w laboratorium (ρ̂ 0,50, dolny koniec 0,36 > 0,282), 27 % dopasowań GARCH-t przy granicy persystencji (lab.: 2,2 %) i okno 2 091 z 2 100 wierszy. Wyzwalacz (i) z pkt. 5 zadziałał; LV2c to dane syntetyczne, bez licznika. Szerszy koszyk nie pomaga: ρ̂ jest własnością rynku, a młodsze monety nie mają 2 100 dni. | Karta 019 → `odrzucone`; wtedy 018 zostaje wstrzymana (albo `odrzucone`, jeśli nie chcesz rundy VaR/ES na danych). Wznowienie 018: warunki w karcie 018. |
| 10 | Po wyniku 020: co z 019 przy K = 4 | **019 przeliczona na K = 4 z celem VR = 2,26 (ρ̂ 0,42) i drugim scenariuszem LV2 (ρ = 0,8, bez wspólnego szoku, VR ≈ 1,85).** Moc reguły K przy K = 4 nie jest dziedziczona z LV2. 018 zostaje wstrzymana. Licznik „ryzyko 2021+” zostaje 0. | 020: ρ̂ = 0,42, SE 0,09, przedział 0,24–0,60 obejmuje laboratorium (0,282); reguły z pre-rejestracji 020 dają dokładnie ten krok. Cztery monety niosą dziennie ok. 1,8 niezależnej monety, więc moc trzeba zmierzyć, a nie zakładać. Dane syntetyczne, bez licznika. | Karta 019 → `odrzucone`; 018 zostaje wstrzymana (albo `odrzucone`, jeśli nie chcesz rundy VaR/ES na danych). |
| 11 | Projekt pre-rejestracji 019 (2026-10-08) | **(i)** α jako pokrętło odsetka dopasowań przy granicy (karta mówiła tylko „α + β do 0,9999”); **(ii)** trzy scenariusze zależności A0/A1/A2 i dwie komórki opisowe A3/A4 zamiast jednego punktu; **(iii)** K7b i K7d nie bramkują w komórkach z trwałością przy granicy (bramkuje KAL); **(iv)** krzywa mocy `garch_tnu` jako opis. | Rozpoznanie (112 paneli) pokazało nasycenie odsetka przy α = 0,08 na ≈ 40 %; 020 dała SE ρ̂ = 0,091 z dolnym końcem poniżej LV2, a tabela decyzji z 020 wymaga scenariusza LV2 dla K = 4; K7b/K7d są sprzeczne z celem 27 → 51 % przy granicy. Dane syntetyczne, bez licznika. | (i) zostać przy α = 0,08 i uznać cel odsetka za nieosiągalny; (ii) werdykt tylko z A1; (iii) raportować K7b/K7d jako opis; (iv) pominąć. Szczegóły: README rundy 019. |
| 12 | Po STOP 1 w 019 (2026-10-08): co dalej | **019 zamknięta z werdyktem Revision** (reguła STOP 1 z pre-rejestracji; przebiegu rejestrowego nie ma, runner odmawia). **Otwieram kartę 021** (nowa pre-rejestracja: generator z przesunięciami poziomu wariancji + komórka A0), **nie wykonuję jej w tej sesji.** **Nie luzuję** progu 46,3 % po fakcie. 018 zostaje wstrzymana. Licznik „ryzyko 2021+” zostaje 0. | Najlepszy punkt kalibracji 44,5 % ± 1,3 pp < 46,3 % (druga droga: 37–44 %), płaskowyż od α = 0,12; VR w tolerancji. Pre-rejestracja zabrania zmiany generatora i progów po STOP 1, a przesunięcie progu po obejrzeniu wyniku byłoby przesunięciem słupków. Mechanizm (przesunięcia poziomu wariancji) to hipoteza, jeszcze niemierzona. Dane syntetyczne, bez licznika. | Kartę 021 zmienić na `odrzucone` albo wskazać inny kierunek: (a) luzowanie celu odsetka (jawnie jako przesunięcie słupków), (b) generator z reżimami, (c) sama komórka A0; 018 zostaje wstrzymana (albo `odrzucone`). |
| 13 | Projekt pre-rejestracji 021 (2026-10-08) | **(i)** mechanizm = wspólny poziom wariancji w reżimach (średnia długość *D* = 300 dni, zapasowo 150) nałożony na bazę LV2 (α + β = 0,98), **nie** na trwałość 0,9999 z 019; **(ii)** okno celu odsetka dopasowań przy granicy [41,3; 61,3] % zamiast [46,3; 56,3] % (jawnie po fakcie, środek celu 51,3 % bez zmian); **(iii)** komórki A0 (scenariusz LV2 dla K = 4) i B1/B2/B3 (dół/środek/góra przedziału VR z 020, B2 główna); **(iv)** K7a bramkuje tylko w A0; **(v)** kolumny wyroczni `zan10`/`zan20` jako opis; **(vi)** 1 000 paneli na punkt kalibracji, kalibracja dwuetapowa (odsetek, potem VR); **(vii)** nowe ziarna; poprawki z przeglądu 019 w nowym runnerze `run_lv2d.py`. Karta 021 → `w_toku`. Licznik „ryzyko 2021+” zostaje 0. | Przegląd 019 pokazał, że przy trwałości 0,9999 panel jest „zapadniętym IGARCH” (mediana |r| ≈ 0,12 %), a SD pojedynczego panelu odsetka to ok. 26 pp, więc okno ± 5 pp było fałszywie dokładne. Okno luzuję jawnie, bo mechanizm ma być sprawdzony na realistycznej bazie; jeśli B2 przejdzie tylko dolną częścią okna, wniosek brzmi „poziom wariancji nic nie dodał do LV2c”. Dane syntetyczne, bez licznika. | (i) komórki B z α + β = 0,9999 jak w 019; (ii) stare okno i próg STOP 1 = 46,3 %; (iii) werdykt tylko z B2 i A0; (iv) bramka K7a także w B; (vi) 400 paneli jak w 019. Szczegóły: README rundy 021. |
| 14 | Po wyniku 021 (2026-10-08): co dalej | **021 zamknięta z werdyktem Caveats** (A0 TAK; B1–B3 NIE przez K-a 28,7 / 20,3 / 17,0 % > 10 %); karta → `do_przegladu`. **Reguły K nie zmieniam** (ani progów, ani estymatora). **018 zostaje wstrzymana** (przy zamrożonej K runda na danych byłaby NIEMIERZALNA w scenariuszu jak w danych, R3). **Otwieram kartę 022** (propozycja: K′ z bootstrapem blokowym jako diagnostyka, potem ewentualnie prognoza widząca poziom wariancji) jako `czeka_na_decyzje`, **nie wykonuję jej** — zmiana zamrożonej reguły po obejrzeniu wyniku należy do Ciebie. Szerszego koszyka nie proponuję. Licznik „ryzyko 2021+” zostaje 0. | Test ma moc przy K = 4 (wyrocznia 85,5–98,1 %), a zawodzi K-a: rozrzut odsetka trafień GARCH-t jest 1,40–1,64 raza większy niż zakłada błąd dla niezależnych dni, a sam średni błąd (5,2 % zamiast 5,0 %) dałby tylko 2,5–3,2 % odrzuceń; źródło mieszane (małe prawdziwe zaniżenie + za wąski błąd testu), nierozdzielone. Zmiana reguły po fakcie byłaby przesunięciem słupków, więc idzie przez Ciebie i nową pre-rejestrację. Poziom wariancji jest wspólny dla monet, więc więcej monet nie leczy (R12). Dane syntetyczne, bez licznika. | Kartę 022 zmienić na `odrzucone` (018 zostaje wstrzymana albo `odrzucone`), albo wskazać kierunek: (a′) K′ z bootstrapem blokowym, (d) prognoza z poziomem wariancji, (b) zamknięcie rundy VaR/ES na danych. Szczegóły: README rundy 021. |

## Otwarte decyzje (z PRD §15)

Brak. D3 rozstrzygnięta na delegację (pkt 6 wyżej), D1, D2, D4, D5, D6 rozstrzygnięte wcześniej.

## Bieżące zadania

Tablica: [`zadania/`](zadania/). Stan na 2026-10-08.

**Nowe — do wykonania (`nowe`):** nic.

**Czekają na decyzję (`czeka_na_decyzje`):**

- **018** — pierwsza runda VaR/ES na danych: pytanie bezwzględne, `dopasuj_garch_t`, p = 5 %, od 2026-10-07 **4 monety** (BTC, ETH, SOL, BNB) × ok. 1 690 dni
  zamiast 15 × 1 700. **Wstrzymana** po wyniku 017 (zależność ponad laboratorium, okno 2 091 < 2 100). Wznowienie:
  LV2d dla K = 4 (021: reguła K odrzuca estymowany GARCH-t w B, więc przy zamrożonej K niemierzalna; dalej 022 — decyzja użytkownika) mierzalne przy VR ≈ 2,26 (020) + dane za październik 2026 + powtórka 020 na końcowym oknie +
  własna pre-rejestracja (licznik 0 → 1).
- **022** — po wyniku 021: (a′) reguła K′ z bootstrapem blokowym w teście A jako diagnostyka na laboratorium LV2d (zmiana zamrożonej reguły → Twoja zgoda
  i osobna pre-rejestracja), potem ewentualnie (d) prognoza widząca poziom wariancji. Propozycja, nie wykonana.

**Zrobione — czekają na Twój przegląd (`do_przegladu`):**

- **001** — fundament: przyrząd `miara` zgodny z alpha, loader z `min_start`, CI, NC1B zaliczona.
- **002** — dane: 196 symboli top-20 × 5m/1d od 2021, manifest, DQ1 (Ready).
- **003** — LM1: test porównania prognoz (DM) działa poprawnie.
- **004** — reporter F3 + LD1; rola rozstrzygnięta jako D3-a (reporter obok).
- **005** — F2-1: NIEMIERZALNA na progu (MDE 0,103 > 0,10), licznik 0 → 011.
- **006** — DVOL BTC/ETH od 2021-03-24.
- **007** — raport tygodniowy.
- **008** — przyrząd VaR/ES; kontrola KV1 **ZALICZONA 19/19** (Caveats: duże n, ρ = 0).
- **010** — rejestr cech + test przecieku (kontrola pozytywna łapie celowe przecieki).
- **012** — automat: wszystkie 3 tryby uruchomione z sukcesem; cron włączony 2026-10-06.
- **014** — `dane/dni.py::dni_wazne`: parytet z Poprawką 1 F2-1 20/20, martwe dni zgodne z DQ1.
- **009** — LV1: **MIERZALNA** przy p = 1 % i 5 % (Caveats; realistyczne prognozy odrzucane → LV2).
- **011** — F2-1b: MIERZALNA, **NIEPOZYTYWNY** (11/15 przy wymaganych 12); licznik „zmienność 2021+” = 1; HAR odłożony.
- **015** — pobieranie Binance przyrostowe: automat miesięczny pobiera tylko nowy miesiąc (bieg bez nowości 25 s).
- **017** — inwentarz 15 monet i zależność trafień ρ_h (karta opisowa, Caveats): VR = 8,0 wobec 4,95 w LV2
  (ρ̂ 0,50; dolny koniec 0,36 > 0,282), bramka zależności NIE PRZECHODZI (ostrożna: nie przechodzi też w laboratorium),
  okno C2 NIE DOMYKA SIĘ (2 091 z 2 100 wierszy), 27 % dopasowań GARCH-t przy granicy persystencji (lab.: 2,2 %).
  Licznik „ryzyko 2021+” = 0. Konsekwencja: 018 wstrzymana, zlecona 019.
- **020** — opis zależności trafień dla BTC, ETH, SOL, BNB (karta opisowa, Caveats): VR = 2,26, ρ̂ = 0,42 (SE 0,09, przedział
  0,24–0,60), nie do odróżnienia od laboratorium (0,282) ani od 15 monet (0,50); ok. 1,8 niezależnej monety dziennie;
  117 z 228 dopasowań przy granicy (te same co w 017); kontrole R8 ✓, druga droga ✓. Licznik „ryzyko 2021+” = 0.
  Konsekwencja: 019 na K = 4 z celem VR = 2,26, 018 wstrzymana.
- **019** — LV2c dla K = 4 (**Revision, STOP 1**): generator doszedł do celu VR (2,20–2,22 wobec 2,264 ± 0,14), ale nie do odsetka dopasowań
  przy granicy persystencji (max 44,5 % ± 1,3 pp przy progu 46,3 %; druga droga 37–44 %); przebiegu rejestrowego z regułą K nie było, więc
  mierzalność reguły K przy K = 4 pozostaje niezmierzona. K-gen-N ✓. Przegląd kodu (niezależny recenzent): bez błędu wysokiej wagi, żaden błąd nie zmienia
  liczb STOP 1; dopisane testy (14 + 2 znane braki `xfail`), poprawki runnera odłożone do 021. Ujawnione w README: wcześniejsza próba dymna `--smoke` (4 panele
  po 700 dni) wydrukowała szum odrzuceń testu K — bez wpływu na decyzje, ale 021 dostaje nowe ziarno. Licznik „ryzyko 2021+” = 0. Konsekwencja: karta 021, 018 wstrzymana.
- **021** — LV2d dla K = 4 (**Caveats**): zamrożona reguła K ma moc (wyrocznia 85,5–98,1 % wobec σ − 10 %), ale rozmiar testu dla estymowanego GARCH-t (K-a) to 5,4 % w A0 (TAK)
  i 28,7 / 20,3 / 17,0 % w B1–B3 przy progu 10 % (NIE); diagnostyka po fakcie: rozrzut trafień 1,40–1,64 raza ponad błąd dla niezależnych dni, sam średni błąd dałby 2,5–3,2 %
  (źródło mieszane, nierozdzielone). Druga droga ✓ (granice niezależności opisane), przegląd kodu bez uwag krytycznych, przewidywania 23/33. Licznik „ryzyko 2021+” = 0.
  Konsekwencja: 018 wstrzymana (niemierzalna pod zamrożoną K), karta 022 czeka na decyzję.
- **016** — LV2: **MIERZALNA, ale tylko z pytaniem bezwzględnym** (Caveats). Dobry, lecz estymowany GARCH-t test
  zbiorczy odrzuca w 8,2 % / 5,5 % paneli (VaR 1 % / 5 %; próg 10 %), moc wobec σ − 10 % 98,8 / 99,5 %; test
  porównawczy DM jest za słaby (MDE 0,139 / 0,130 wobec 0,10). Licznik „ryzyko 2021+” = 0.

**Odłożone (`odrzucone`):** 013 — repo bundla na GitHubie (pkt 7 wyżej).

**W toku (`w_toku`):** nic.

## Kolejka

0. ~~**020**~~ — zrobiona 2026-10-07 (`do_przegladu`).
1. ~~**019**~~ — zrobiona 2026-10-08, werdykt Revision (STOP 1; `do_przegladu`). ~~**021**~~ — zrobiona 2026-10-08, werdykt Caveats (`do_przegladu`): reguła K ma moc, ale
   odrzuca estymowany GARCH-t w komórkach B (K-a 17–29 % > 10 %). Dalej czeka na **Twoją decyzję** karta **022** (K′ z bootstrapem blokowym jako diagnostyka albo prognoza
   widząca poziom wariancji, albo zamknięcie rundy VaR/ES na danych). **018** zostaje wstrzymana; po danych za październik 2026 (spodziewane ok. 2026-11-01) i po
   decyzji: powtórka 020 na końcowym oknie → decyzja o 018 (pre-rejestracja przed uruchomieniem).
2. Tor likwidacji (F5) bez zmian. HAR odłożony po F2-1b (bez F2-1c).
3. E3: reporter sekwencyjny gotowy przed 2026-12-24 (D3-a).

## Decyzje czekające na Ciebie

Z zasady po Twojej stronie (nie mogę ich podjąć za Ciebie):

1. **Scalenie do `main`** — praca leży na gałęzi `claude/fervent-fermi-vfctk6`; na `main` trafia nowym PR.
2. **Odbiór kart `do_przegladu`** (001–012, 014–017, 019, 020, 021) — przegląd i przeniesienie na `zrobione`.
3. **Zmiana któregokolwiek z czternastu wyborów wyżej**, jeśli się z nim nie zgadzasz — napisz numer (szczególnie pkt. 14: co dalej po wyniku 021).
4. **Konto GitHub i klucze** — tylko jeśli wznowisz 013.
5. **Karta 022** — czy wolno zmienić zamrożoną regułę K (K′ z bootstrapem blokowym, jako diagnostyka z osobną pre-rejestracją i własnym licznikiem), czy pójść w prognozę widzącą poziom wariancji (d), czy zamknąć rundę VaR/ES na danych (b).

Kapitał, dziennik papierowy alpha, nieodwracalne operacje: nic nie czeka i niczego nie ruszałem.

## Backlog (bez kart)

- **LV2c — część porównawcza** (błąd standardowy testu DM, wrażliwość na konwencję startu GARCH parami, ewentualna
  reguła P′). Wyzwalacz (i) zadziałał (017: ρ̂ + 2 SE = 0,64 > 0,282) i dał kartę **019** (komórka z zależnością jak na
  danych, reguła K). Reszta zostaje tu z wyzwalaczem (ii): ktoś chce porównywać prognozy testem DM na n rzędu 1 700.
- **Trop z ogonem EWMA** (`ewma94_ep` odrzucana w 4,1 / 4,6 % paneli wobec 78,5 / 78,8 % z ogonem t5; README LV2).
  Karta opisowa na zapisanych panelach; wyzwalacz: gdy któraś runda zacznie używać prognozy EWMA.
- Skład top-20 po 2026-06 (pkt 8 wyżej) — wyzwalacz: runda wymagająca top-50 albo nowych wejść do top-20; wymaga
  Poprawki w alpha.
- Migracja `beta/miara` → pakiet `miara` — po E2 (ADR `bundle/0001` pkt 3; Poprawka w alpha).
- Migracja `beta/dane` → repo `kolektory` — po wznowieniu 013, osobną decyzją.
- Top-50 (FR-01) — gdy runda będzie tego potrzebować (`--top 50`).
- Tor F5 (likwidacje, Hyperliquid) — magazyn cech point-in-time; pierwszy odczyt najwcześniej 2027-09.
- F4 portfel — po E2.
- Wolumen 5m vs 1d różny w 600 dniach (161 symboli) — przyczyny nie badano (karta 014).
- Drobne uwagi do kodu LV2 (do poprawienia przy następnej zmianie kodu): etykieta „siatka X_GRID” w wydruku, zdublowane
  `POZIOMY`/`NU`, martwa stała `N_DNI`, kolejność argumentów `fz0`.
- Drobne uwagi do kodu 017 (przegląd, uwagi 6–7; poprawić przy następnej zmianie kodu, przed kartą 018): sprawdzenie
  `panel.index[-1] == do` w `panel_wspolny`, `do` bez strefy czasowej → czytelny błąd, walidacja cen po obcięciu do `do`,
  import listy monet z `run_f21b` zamiast kopii, jeden generator losowy dla wszystkich L.

## Ryzyka

Pełna tabela: `docs/PRD.md` §14. Najważniejsze: traktowanie nowego repo jako „świeżego startu” licznika prób
(zasada 22) i oczekiwanie, że ML znajdzie przewagę tam, gdzie alpha zmierzyła jej brak. Dodatkowe, z delegacji
2026-10-07: dziewięć decyzji wyżej podjął ten sam wykonawca, który napisał badanie — nie ma przy nich drugiej pary
oczu poza Twoim przeglądem.
