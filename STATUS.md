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
| 5 | 016(e): czy zlecić LV2c | **Nie zlecam.** Trafia do Backlogu z wyzwalaczami (niżej). | Do pierwszej rundy bezwzględnej nie jest potrzebne; pytanie porównawcze (reguła P) jest NIEMIERZALNE i nikt go teraz nie zadaje. | Napisz „zleć LV2c”, a założę kartę. |
| 6 | D3: rola oceny sekwencyjnej wobec ADR-09 alpha | **(a) tylko reporter obok z = 2,31** (rekomendacja PRD §15). | Dziennik alpha jest tylko do odczytu (R23), a nowy test nie powinien zmieniać kryterium, na którym stoi kapitał (R13). | Zmiana na (b) musi być zapisana przed 2026-12-24. |
| 7 | 013: cztery repo na GitHubie (bundle, miara, kolektory, wykonanie) | **Odkładam** (status `odrzucone` = „nie teraz”, karta zostaje do wznowienia). | Praca leży w `beta`, push działa, a cztery puste repo niczego nie odblokowują; migracja `miara` jest po E2 (ADR `bundle/0001` pkt 3). Zakładanie wymaga Twojego konta i kluczy, których Claude nie tworzy. Ryzyko: szkielety bundla (po jednym commicie) mają jedną kopię, na serwerze. | Zmień status karty 013 na `nowe` i załóż puste repo wg `~/bundle/README.md`. |
| 8 | Skład top-20 po 2026-06 | **Odkładam.** | Aktualizacja listy to Poprawka w alpha (R23, karta 015 w alpha). Pierwsza runda używa 15 monet z pełną historią od 2021, których zmiana składu nie dotyczy. | Wyzwalacz w Backlogu. |

## Otwarte decyzje (z PRD §15)

Brak. D3 rozstrzygnięta na delegację (pkt 6 wyżej), D1, D2, D4, D5, D6 rozstrzygnięte wcześniej.

## Bieżące zadania

Tablica: [`zadania/`](zadania/). Stan na 2026-10-07.

**Nowe — do wykonania (`nowe`):**

- **017** — dane pod pierwszą rundę VaR/ES: inwentarz 15 monet × 2 100 dni zwrotów i zależność trafień ρ_h na
  prawdziwych danych (karta opisowa; nie ocenia żadnej prognozy; licznik „ryzyko 2021+” zostaje 0).
- **018** — pierwsza runda VaR/ES na danych: pytanie bezwzględne, `dopasuj_garch_t`, p = 5 %, 15 × 1 700 dni.
  Zależy od 017. Najpierw pre-rejestracja w gicie, potem uruchomienie (licznik 0 → 1).

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
- **016** — LV2: **MIERZALNA, ale tylko z pytaniem bezwzględnym** (Caveats). Dobry, lecz estymowany GARCH-t test
  zbiorczy odrzuca w 8,2 % / 5,5 % paneli (VaR 1 % / 5 %; próg 10 %), moc wobec σ − 10 % 98,8 / 99,5 %; test
  porównawczy DM jest za słaby (MDE 0,139 / 0,130 wobec 0,10). Licznik „ryzyko 2021+” = 0.

**Odłożone (`odrzucone`):** 013 — repo bundla na GitHubie (pkt 7 wyżej).

**W toku:** nic.

## Kolejka

1. **017** (opisowa, bez oceny prognozy) → **018** (pierwsza runda VaR/ES na danych; pre-rejestracja przed
   uruchomieniem; tylko pytanie bezwzględne, `dopasuj_garch_t`, 15 monet × 1 700 dni, p = 5 %). Jeśli 017 pokaże,
   że ρ̂ + 2 SE > 0,282 albo że okno 2 100 dni nie domyka się dla któreś z 15 monet, 018 nie startuje, a ja
   wracam do Ciebie z opcjami (LV2c z silniejszą zależnością albo szerszy koszyk).
2. Tor likwidacji (F5) bez zmian. HAR odłożony po F2-1b (bez F2-1c).
3. E3: reporter sekwencyjny gotowy przed 2026-12-24 (D3-a).

## Decyzje czekające na Ciebie

Z zasady po Twojej stronie (nie mogę ich podjąć za Ciebie):

1. **Scalenie do `main`** — praca leży na gałęzi `claude/fervent-fermi-vfctk6`; na `main` trafia nowym PR.
2. **Odbiór kart `do_przegladu`** (001–012, 014–016) — przegląd i przeniesienie na `zrobione`.
3. **Zmiana któregokolwiek z ośmiu wyborów wyżej**, jeśli się z nim nie zgadzasz — napisz numer.
4. **Konto GitHub i klucze** — tylko jeśli wznowisz 013.

Kapitał, dziennik papierowy alpha, nieodwracalne operacje: nic nie czeka i niczego nie ruszałem.

## Backlog (bez kart)

- **LV2c** (błąd standardowy testu DM, wrażliwość na konwencję startu GARCH parami, ewentualna reguła P′). Wyzwalacz:
  (i) 017 pokaże ρ̂ + 2 SE > 0,282, wtedy potrzebna nowa komórka z silniejszą zależnością; albo (ii) ktoś chce
  porównywać prognozy testem DM na n rzędu 1 700.
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

## Ryzyka

Pełna tabela: `docs/PRD.md` §14. Najważniejsze: traktowanie nowego repo jako „świeżego startu” licznika prób
(zasada 22) i oczekiwanie, że ML znajdzie przewagę tam, gdzie alpha zmierzyła jej brak. Dodatkowe, z delegacji
2026-10-07: osiem decyzji wyżej podjął ten sam wykonawca, który napisał badanie — nie ma przy nich drugiej pary
oczu poza Twoim przeglądem.
