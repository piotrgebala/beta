---
id: 016
tytul: laboratorium LV2 — testy VaR/ES dla prognoz ESTYMOWANYCH (okno, EWMA, GARCH) przed rundą na danych
typ: badawcze
status: do_przegladu
zlecil: orkiestrator
decyzja_uzytkownika: "2026-10-06: „LV1: poprawiona, 011: a, E0: zamknij” — wniosek z LV1 i STOP F2-1b (F2 → ryzyko ogona)"
utworzono: 2026-10-06
zalezy_od: [008, 009]
budzet: "Opus, 1 sesja, 16 procesów"
---

# 016 — LV2

## Po co

LV1 (MIERZALNA) mierzyła rozmiar testów tylko dla prognozy-wyroczni (prawdziwa σ). Realistyczne prognozy
z estymowaną σ (okno 60 dni, EWMA 0,94) przy poprawnym ogonie t5 miały za dużo trafień (1,28–1,39 % zamiast
1 %) i test zbiorczy odrzucał je w 78–98 % paneli. Zanim jakakolwiek runda VaR/ES dotknie prawdziwych danych
(licznik „ryzyko 2021+”), trzeba wiedzieć, jakie pytanie da się uczciwie zadać prognozie estymowanej.

## Zakres

- Pre-rejestracja w `runs/2026-10-07_lv2-var-es-estymowane/` przed przebiegiem; ten sam generator i test
  zbiorczy co LV1 (`symulacje/moc_var_es.py`), komórka n = 1 600 (i 1 700 z F2-1b), ρ = 0,8.
- Prognozy estymowane: okno 60, EWMA 0,94, GARCH(1,1)-t dopasowany walk-forward (rozgrzewka, refit co 30 dni),
  HAR jako opis; ogon: t5 stały i kwantyl empiryczny standaryzowanych reszt.
- Pytania do rozstrzygnięcia: (a) rozmiar testu zbiorczego, gdy model jest „dobrze wyspecyfikowany, ale
  estymowany” (np. GARCH-t na danych GARCH-t); (b) moc testu PORÓWNAWCZEGO (np. funkcja straty kwantylowej /
  FZ dla VaR i ES, DM między prognozami) zamiast „odrzuć/nie odrzuć”; (c) reguła MIERZALNA/NIEMIERZALNA dla
  pierwszej rundy na danych.
- Bez prawdziwych danych (licznik 0).

## Czego NIE robić

Żadnych prognoz VaR/ES na prawdziwych danych; nie zmieniać `miara/var_es.py` (zamrożony po KV1) — nowe
statystyki w `symulacje/`.

## Kryteria odbioru (dowody)

README rundy z werdyktem, `raw_output.txt`, wiersz w `runs/INDEX.md`; niezależna weryfikacja liczb.

## Postęp (stan na 2026-10-07)

**Zrobione:** kod i testy — commit `009204b` (`symulacje/garch_t.py`, `prognozy_lv2.py`, `porownanie_lv2.py`,
`run_lv2.py`, `tests/test_lv2.py`); pre-rejestracja — commit `73fff28`; przegląd przed przebiegiem (3 recenzentów,
mutacje, architektura) — commit `24c8863` (131 funkcji / 241 przypadków w `tests/test_lv2.py`, 1115 w całym repo,
ruff i black czyste). **Potem zrobione (2026-10-07):** przebieg rejestrowy z ziarnem `20261016` — commit `eb1e0fc`;
niezależne przeliczenie — `6d71b5e`; README z werdyktem — patrz „Wynik”. Licznik „ryzyko 2021+” = 0.

**Ustalenia projektu (już w kodzie, przypięte testem `test_konfiguracja_progi_i_prognozy_zgodne_z_pre_rejestracja`;
nie zmieniać bez wpisu w README):** 5 000 paneli, bootstrap 999, panel 2 100 dni (historia 400), komórki
(20 monet, 1 600 dni) i (15, 1 700), ρ = 0,8. Dwa pytania z osobnymi regułami: **K** (bezwzględne: zbiorczy test LV1 na
GARCH-t estymowanym) i **P** (porównawcze: DM na stracie FZ0). Runda jest MIERZALNA, gdy K albo P daje TAK.
Kontrola rozmiaru testu DM (K6) ma dwie bramki jednostronne: K6a (za liberalny) wstrzymuje tylko wniosek TAK,
K6b (za zachowawczy) tylko wniosek NIE — uzasadnienie wpisać do pre-rejestracji.

**Pilotaż (poza rejestrem; ziarno 777, 480 paneli; oznaczyć w README jako nie-ślepy):** K raczej TAK (K-a 7,9 % przy
progu 10 %, blisko); P raczej NIE (MDE ≈ 0,13–0,14 przy progu 0,10; moc pary ewma94 → garch_tnu 35 % przy 1 %, 76 % przy 5 %).

**Plan (wykonany w całości, po kolei; commit i push po każdym kroku):**

1. Pre-rejestracja `runs/2026-10-07_lv2-var-es-estymowane/README.md` (format jak LV1): zdanie o wnioskach skumulowanych
   (LV1: realistyczne prognozy odrzucane w 78–98 % paneli; F2-1b: NIEPOZYTYWNY 11/15 → STOP → ryzyko ogona), R1, rachunek
   mierzalności (R3), projekt, kryteria K1/K2/K-a/K-b i K4/K5/K6a/K6b/P-a/P-b/K7a–d, reguła rundy i STOP, przewidywania
   W1–W4, ograniczenia, liczniki. Commit, potem hash wpisany do README.
2. Przegląd przed przebiegiem: 3 niezależnych recenzentów + mutacje na kopii poza repo + `arxitect:architecture-review`;
   zmiany opisać w „Zmiany po przeglądzie, przed pełnym przebiegiem”.
3. Przebieg: `python -m symulacje.run_lv2 --workers 16 > runs/2026-10-07_lv2-var-es-estymowane/raw_output.txt`
   (ok. 30 min; bez innych równoległych przebiegów; czas idzie na stderr).
4. Niezależne przeliczenie ≥ 1 kluczowej liczby inną drogą (np. GARCH przez pakiet `arch`, osobna implementacja DM).
5. README: Wynik, Co na plus / na minus, Werdykt (Ready/Caveats/Revision, podpisuje Claude), Wniosek, Rekomendacja,
   Użyte skille. Wiersz w `runs/INDEX.md` (licznik 0, poza licznikami) i linia w „Stan wiedzy”; `STATUS.md`.
6. Karta: „Wynik”, status `do_przegladu`. Na końcu przypomnieć użytkownikowi o nowym PR (Claude nie wypycha na `main`).

## Wynik

Runda wykonana 2026-10-07 (przebieg rejestrowy, ziarno `20261016`, 5 000 paneli na komórkę). Pełny opis, tabele i
werdykt: [`runs/2026-10-07_lv2-var-es-estymowane/README.md`](../runs/2026-10-07_lv2-var-es-estymowane/README.md);
surowy wydruk: `raw_output.txt` w tym katalogu; wiersz w `runs/INDEX.md`. **Werdykt (podpisuje Claude): Caveats.**

- **(a) Rozmiar testu zbiorczego dla modelu poprawnego, ale estymowanego** (GARCH-t, refit co 30 dni): odrzuca go w
  8,2 % paneli przy VaR 1 % i 5,5 % przy VaR 5 % (C1: 20 monet × 1 600 dni; C2, 15 × 1 700: 8,0 % i 5,0 %); próg
  ≤ 10 % zachowany. Moc wobec σ zaniżonej o 10 %: 98,8 / 99,5 % (C2: 98,4 / 99,6 %). Reguła K: **MIERZALNE**.
- **(b) Moc testu porównawczego** (DM na stracie FZ0): wobec σ − 10 % tylko 49,1 / 59,6 % paneli; najmniejsze
  wykrywalne zaniżenie 0,139 / 0,130 (C2: 0,140 / 0,128) wobec wymaganych 0,10; para EWMA → GARCH-t 35,6 / 73,3 %
  (C2: 33,8 / 73,1 %) wobec wymaganych 80 %. Reguła P: **NIEMIERZALNE**.
- **(c) Reguła pierwszej rundy VaR/ES na danych:** MIERZALNA tylko dla **pytania bezwzględnego** (K), jednej klasy
  prognoz (`dopasuj_garch_t` w tej samej konwencji), jednego poziomu p (rekomendacja: 5 %) i na warunkach
  przeniesienia z README („Werdykt”): m.in. zakres 15 monet × 1 700 dni, ρ_h na danych ≤ 0,114 (1 %) / ≤ 0,282 (5 %)
  po uwzględnieniu błędu pomiaru. Pytań porównawczych na tych n nie zadawać.
- **Uwagi:** przy VaR 1 % uczciwy fałszywy alarm to ok. 8 %, nie 5 %; wynik zależy od konwencji startu GARCH
  (przy VaR 1 % 10,75 % zamiast 7,25 % w niezależnych 400 panelach; wskazówka, nie dowód); trzy kontrole reguły P
  oznaczone „blisko progu”; próg K-a wybrany po pilotażu.
- **Weryfikacja niezależna:** 1 470 liczb z wydruku przeliczono z zapisanych paneli (0 rozbieżności), 200 paneli
  policzono drugi raz bit w bit, prognozy bez dopasowywania i test DM przeliczono pakietami `arch` i `statsmodels`,
  osobna symulacja 400 paneli (21 z 24 wierszy w granicach 2 SE). Poza zakresem: niezależna reimplementacja HAR i
  ogonów empirycznych.
- **Licznik „ryzyko 2021+” = 0** (dane syntetyczne). LV2b nie było potrzebne (żadna reguła nie wyszła WSTRZYMANA).
- **Decyzje z tej rundy (2026-10-07):** użytkownik delegował je wykonawcy („sam sobie odpowiedz wedługo swojej najlepszej
  wiedzy”), więc rozstrzygnął je Claude (`STATUS.md`, „Decyzje podjęte przez Claude”, pkt 1–5): pierwsza runda na danych
  **tak**, ale etapami (karty 017 → 018, licznik 0 → 1 dopiero przy uruchomieniu 018 po zapisanej pre-rejestracji);
  Zakres (b) przyjęty w odczytaniu K-only; próg K-a ≤ 10 % przyjęty (przy p = 5 % nie rozstrzyga); jedyny poziom p = 5 %;
  LV2c niezlecone (Backlog z wyzwalaczami). Każdą możesz zmienić jednym zdaniem. Odczytanie Zakresu (b) zaproponował i
  zatwierdził ten sam wykonawca, więc to słabsza kontrola niż Twoja. Praca leży na gałęzi `claude/fervent-fermi-vfctk6`;
  na `main` trafia nowym PR (po Twojej stronie).
