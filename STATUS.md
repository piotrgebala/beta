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

## Otwarte decyzje (z PRD §15)

Brak. D3 rozstrzygnięta na delegację (pkt 6 wyżej), D1, D2, D4, D5, D6 rozstrzygnięte wcześniej.

## Bieżące zadania

Tablica: [`zadania/`](zadania/). Stan na 2026-10-07.

**Nowe — do wykonania (`nowe`):**

- **019** — LV2c dla K = 4: laboratorium z zależnością trafień jak na prawdziwych danych czwórki (cel VR = 2,26 z 020; drugi scenariusz: LV2 bez wspólnego szoku, VR ≈ 1,85) i trwałością zmienności blisko granicy (ok. 50 % dopasowań); pytanie: czy reguła K (rozmiar ≤ 10 %, moc ≥ 80 %) zostaje mierzalna. Dane syntetyczne, bez
  licznika. Najpierw pre-rejestracja w gicie. Zlecona pkt. 9 i 10 wyżej.

**Czekają na decyzję (`czeka_na_decyzje`):**

- **018** — pierwsza runda VaR/ES na danych: pytanie bezwzględne, `dopasuj_garch_t`, p = 5 %, od 2026-10-07 **4 monety** (BTC, ETH, SOL, BNB) × ok. 1 690 dni
  zamiast 15 × 1 700. **Wstrzymana** po wyniku 017 (zależność ponad laboratorium, okno 2 091 < 2 100). Wznowienie:
  LV2c dla K = 4 (019) mierzalne przy VR ≈ 2,26 (020) + dane za październik 2026 + powtórka 020 na końcowym oknie +
  własna pre-rejestracja (licznik 0 → 1).

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
- **016** — LV2: **MIERZALNA, ale tylko z pytaniem bezwzględnym** (Caveats). Dobry, lecz estymowany GARCH-t test
  zbiorczy odrzuca w 8,2 % / 5,5 % paneli (VaR 1 % / 5 %; próg 10 %), moc wobec σ − 10 % 98,8 / 99,5 %; test
  porównawczy DM jest za słaby (MDE 0,139 / 0,130 wobec 0,10). Licznik „ryzyko 2021+” = 0.

**Odłożone (`odrzucone`):** 013 — repo bundla na GitHubie (pkt 7 wyżej).

**W toku:** nic.

## Kolejka

0. ~~**020**~~ — zrobiona 2026-10-07 (`do_przegladu`).
1. **019** (LV2c dla K = 4: pre-rejestracja w gicie → kalibracja generatora na ziarnach pilotażowych → przebieg rejestrowy; cel VR = 2,26 i scenariusz LV2).
   Dalej, dopiero po jej wyniku i po danych za październik 2026 (spodziewane ok. 2026-11-01): powtórka 020 na
   końcowym oknie → decyzja o **018** (pierwsza runda VaR/ES na danych; pre-rejestracja przed uruchomieniem). Jeśli
   019 wyjdzie NIEMIERZALNA przy K = 4, wracam do Ciebie z opcjami (inna reguła K′, szerszy koszyk albo zamknięcie
   rundy VaR/ES na danych).
2. Tor likwidacji (F5) bez zmian. HAR odłożony po F2-1b (bez F2-1c).
3. E3: reporter sekwencyjny gotowy przed 2026-12-24 (D3-a).

## Decyzje czekające na Ciebie

Z zasady po Twojej stronie (nie mogę ich podjąć za Ciebie):

1. **Scalenie do `main`** — praca leży na gałęzi `claude/fervent-fermi-vfctk6`; na `main` trafia nowym PR.
2. **Odbiór kart `do_przegladu`** (001–012, 014–017, 020) — przegląd i przeniesienie na `zrobione`.
3. **Zmiana któregokolwiek z dziesięciu wyborów wyżej**, jeśli się z nim nie zgadzasz — napisz numer (szczególnie pkt. 9: zlecenie LV2c).
4. **Konto GitHub i klucze** — tylko jeśli wznowisz 013.

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
