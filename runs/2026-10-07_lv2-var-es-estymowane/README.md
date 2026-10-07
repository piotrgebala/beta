# LV2 — laboratorium VaR/ES dla prognoz ESTYMOWANYCH: czy test zbiorczy i test porównawczy nadają się na pierwszą rundę na danych (2026-10-07)

> **STATUS: PRZEBIEG REJESTROWY WYKONANY — werdykt rundy: Caveats.** Przebieg z ziarnem `20261016` (5 000
> paneli × 2 100 dni, 16 procesów) trwał od 2026-10-07 10:21:45 do 10:53:19 UTC (1 894 s, kod zakończył
> się bez błędu) na kodzie z commitu `24c8863`; surowy wydruk jest w `raw_output.txt` (commit `eb1e0fc`,
> bez żadnej interpretacji). Wynik: reguła **K** (pytanie bezwzględne: czy prognoza GARCH-t dopasowana
> na danych przechodzi test zbiorczy) = **MIERZALNE** w obu komórkach i przy obu poziomach p; reguła **P**
> (pytanie porównawcze: czy test DM odróżni dwie prognozy) = **NIEMIERZALNE** w obu komórkach i przy obu
> poziomach p. Runda na danych jest więc **MIERZALNA tylko dla pytania bezwzględnego**. Progi, prognozy i
> reguły są te z pre-rejestracji po przeglądzie. Wynik nie był ślepy (przewidywania W1–W4 zapisano po
> pilotażu) i wszystkie 8 sprawdzeń W1–W4 wyszło zgodnie z przewidywaniem — to powód do ostrożności, nie
> do spokoju (sekcja „Co na plus (+) / Co na minus (−)”). Część od „W skrócie” do „Decyzje wykonawcy
> (poza zleceniem)” to pre-rejestracja, **w niezmienionym brzmieniu** (dodana jest tylko uwaga pod
> nagłówkiem „W skrócie”); wynik opisują sekcje „Wynik w skrócie” (na początku) oraz „Przebieg rejestrowy”,
> „Wynik”, „Weryfikacja niezależna”, „Kogo NIE ma w zbiorze”, „Co na plus (+) / Co na minus (−)”,
> „Werdykt”, „Wniosek”, „Rekomendacja”, „Decyzje wykonawcy — ciąg dalszy” i „Użyte skille” (na końcu).

## Wynik w skrócie — prostym językiem

**Co zrobiliśmy.** Wygenerowaliśmy 5 000 sztucznych „rynków” po 20 monet i 2 100 dni (400 dni historii do
uczenia, potem 1 600 dni oceny; osobno wariant z 15 monetami i 1 700 dniami oceny). Prawdziwą zmienność
znamy, bo sami ją ustawiliśmy. Na każdym rynku prognoza ryzyka musiała zmienność **oszacować z danych**,
tak jak będzie musiała na prawdziwych cenach. Ryzyko to **VaR** (strata, którą mamy przekraczać w 1 dniu na
100, albo w 5 dniach na 100) i **ES** (średnia strata w takich dniach). Potem dwa testy: **zbiorczy** („czy ta
prognoza jest dobra?”) i **porównawczy** (Diebold–Mariano, „czy ta prognoza jest lepsza od tamtej?”). Dla
każdego mierzymy **fałszywy alarm** (jak często test odrzuca prognozę, która jest dobra) i **moc** (jak często
wykrywa prognozę, o której wiemy, że jest zła). Skrót „pp” znaczy „punkt procentowy”.

**Wynik jednym zdaniem.** Na pytanie „czy prognoza GARCH-t dopasowana na danych jest dobra” da się na naszych
danych uczciwie odpowiedzieć, a na pytanie „która z dwóch prognoz jest lepsza” — nie. Pierwsza runda
VaR/ES na prawdziwych danych jest więc **MIERZALNA, ale tylko z pytaniem bezwzględnym**, i **tylko na warunkach
przeniesienia z pre-rejestracji** (punkt 3). LV1 sugerowała, że pytanie rundy na danych powinno być
„porównawcze albo dotyczyć kalibracji”; LV2 zamyka wariant porównawczy przy tych n i zostawia kalibrację.

**1. Pytanie bezwzględne — TAK (reguła K).**

- Dobry model, który sam musi oszacować parametry (`garch_tnu`: GARCH(1,1)-t, dopasowywany od nowa co 30 dni),
  jest odrzucany w **8,2 %** paneli przy VaR 1 % i w **5,5 %** przy VaR 5 % (próg: nie więcej niż 10 %). Ten
  sam model z prawdziwymi parametrami (wyrocznia) jest odrzucany w 3,9 % i 3,6 %.
- Prognozę zaniżoną o 10 % test wykrywa w **98,8 %** (VaR 1 %) i **99,5 %** (VaR 5 %) paneli (próg: co najmniej
  80 %). Wariant z 15 monetami i 1 700 dniami daje to samo: 8,0 % i 5,0 % fałszywych alarmów, moc 98,4 % i 99,6 %.
- **Warto zapamiętać: przy VaR 1 % uczciwy fałszywy alarm to ok. 8 %, nie 5 %.** Nadwyżkę ponad 3,9 % robią
  dwa błędy szacowania: zmienności (+1,1 pp) i, głównie, „grubości ogona” ν (+3,2 pp). Przy VaR 5 % nadwyżka
  jest mniejsza: 5,5 % wobec 3,6 % na wyroczni (+1,9 pp: zmienność +1,4, ogon +0,5); względem nominalnych 5 %
  to pół punktu.

**2. Pytanie porównawcze — NIE (reguła P).**

- Test porównawczy (Diebold–Mariano na stracie FZ0) widzi zaniżenie zmienności o 10 % względem prognozy
  idealnej tylko w **49,1 %** (VaR 1 %) i **59,6 %** (VaR 5 %) paneli; z mocą 80 % widzi dopiero zaniżenie rzędu
  0,139 i 0,130, a wymagaliśmy 0,10 lub mniej (kryterium P-a). To samo przesądza o wyniku NIE.
- Nie odróżnia też EWMA od GARCH-t: widzi różnicę w **35,6 %** (VaR 1 %) i **73,3 %** (VaR 5 %) paneli, a
  wymagane jest 80 % (kryterium P-b). Przy VaR 5 % to kryterium jest bliższe progu niż przy 1 % — o tym w
  punkcie 4; o wyniku NIE rozstrzyga i tak P-a.
- Sens: przy takich n nie wolno budować pierwszej rundy na pytaniu „czy model A jest lepszy od B”, bo
  brak istotnego wyniku niczego by nie znaczył.

**3. Co to znaczy dla pierwszej rundy na prawdziwych danych.**

- Wolno zadać tylko pytanie bezwzględne, dla jednej klasy prognoz: GARCH(1,1)-t dopasowany dokładnie tak jak
  w LV2 (`symulacje.garch_t.dopasuj_garch_t`, refit co 30 dni, okno rosnące od ≥ 400 dni, zerowa średnia).
  Okno 60 dni i EWMA, choć to rozsądne, popularne prognozy, test zbiorczy odrzuca w 97,1 / 93,4 % (okno) i
  78,5 / 78,8 % (EWMA) paneli, przy VaR 1 % / 5 %. Tym testem ich więc nie oceniamy.
- Zakres: 20 monet × 1 600 dni jest dziś nieosiągalne. Zostaje 15 monet × 1 700 dni; reguła K daje tam TAK bez
  flagi, więc otwieram ten zakres — **to moje odczytanie nieostrego zapisu, do Twojego przeglądu** (sekcja „Werdykt”).
- Przed rundą trzeba sprawdzić na danych, że trafienia monet są skorelowane nie silniej niż w laboratorium:
  ρ_h (średnia korelacja trafień dwóch monet w tym samym dniu) ≤ 0,114 przy 1 % i ≤ 0,282 przy 5 %,
  po uwzględnieniu błędu pomiaru. Inaczej potrzebna jest nowa komórka laboratorium.
- Odrzucenie prognozy tym testem znaczy „nie jest skalibrowana”, nie „jest bezużyteczna”. Przy pytaniu o
  oba poziomy VaR (1 % i 5 %) trzeba wskazać jeden z góry albo zastosować poprawkę α/2 (połowę progu
  istotności).

**4. Na co uważać.**

- **Przy VaR 1 % uczciwy fałszywy alarm to ok. 8 %, a nie 5 %.** Test zbiorczy ma poziom nominalny 5 %, ale
  dobry model z oszacowanymi parametrami odrzuca w 8,2 % paneli (przy VaR 5 %: 5,5 %). Odrzucenie na
  prawdziwych danych czytać więc względem tych liczb i nie pisać „odrzucono przy 5 %” bez tej uwagi.
- **Wynik przy VaR 1 % zależy od drobnego wyboru technicznego.** Model GARCH trzeba od czegoś zacząć
  (wariancja początkowa). Pre-rejestracja przyjęła średnią z kwadratów zwrotów próby. Ten sam model z domyślnym
  ustawieniem pakietu `arch` odrzucał przy VaR 1 % 10,75 ± 1,55 % paneli zamiast 7,25 ± 1,30 % (niezależna
  symulacja 400 paneli); przy VaR 5 %: 6,75 % zamiast 6,00 %. To wskazówka, nie dowód (różnicy liczonej parami
  nie policzyłem). Stąd warunek „dokładnie `dopasuj_garch_t`”.
- **Próg 10 % dla K-a nie wynika z teorii**; wybraliśmy go po pilotażu 64 paneli. Przy ostrzejszym progu 7,5 %
  reguła K dałaby przy VaR 1 % wynik NIE (8,2 % i 8,0 % to o 0,7 i 0,5 pp za dużo), a przy VaR 5 % nadal TAK
  (zapas 2,0 i 2,5 pp). Czy 10 % wystarcza, to Twoja decyzja.
- **EWMA zawodzi raczej przez ogon niż przez zmienność.** `ewma94_ep` (ta sama EWMA, ale z ogonem wyznaczonym
  z danych, a nie z rozkładu t5) jest odrzucana tylko w 4,1 / 4,6 % paneli, wobec 78,5 / 78,8 % z ogonem t5.
  To trop opisowy na osobną kartę, nie wynik rundy.
- **Test porównawczy ma własne kłopoty z błędem standardowym.** W parze okno 60 → EWMA daje po wyśrodkowaniu
  za dużo fałszywych alarmów (9,1 / 10,1 % zamiast ok. 5 %; próg kontrolny 7,5 %), bo jego błąd standardowy
  jest za mały (rzeczywisty rozrzut to 1,13 i 1,20 tego błędu). Zgadza się to z podejrzeniem z pre-rejestracji
  (West 1996), którego osobno nie badaliśmy. W parze głównej (EWMA → GARCH-t) jest odwrotnie: błąd jest za
  duży (rozrzut to 0,92 i 0,86 błędu), test jest zachowawczy i jego moc wychodzi niższa, niż byłaby przy
  dokładnym błędzie (orientacyjnie 44 / 81 % zamiast zmierzonych 35,6 / 73,3 %; to szacunek, nie wynik).
  Wyniku NIE reguły P to nie zmienia, bo trzyma go kryterium P-a, a w sprawdzonym wierszu (C1, VaR 1 %,
  zaniżenie 10 %) błąd jest dokładny (rozrzut 0,99 błędu).
- Wydruk oznaczył trzy kontrole reguły P jako „blisko progu” (K6b przy VaR 5 % w obu komórkach i K6a przy VaR 1 %
  w C2). Żadna kontrola ani kryterium reguły K nie ma flagi. Flagi obniżają werdykt najwyżej do Caveats.

**5. Weryfikacja niezależna** (szczegóły: sekcja „Weryfikacja niezależna”, skrypty w `weryfikacja/`).

- 1 470 liczb z wydruku przeliczono ponownie z zapisanych surowych wyników wszystkich 5 000 paneli: 0 rozbieżności
  (różnice nie większe niż pół jednostki ostatniej cyfry wydruku, czyli samo zaokrąglenie).
- 200 paneli policzono drugi raz na innej liczbie procesów (12 zamiast 16) i bez ograniczania wątków BLAS: wyniki
  identyczne co do bitu.
- Prognozy bez dopasowywania (okno, EWMA, zaniżenia) i test DM przeliczono innym kodem (`arch`, `statsmodels`):
  zero różnic w decyzjach. Prognozy GARCH zgodne w granicach szumu dopasowania (3 z 1 600 decyzji inne).
- Osobna symulacja 400 paneli (własny generator, ziarno 424242): 21 z 24 wierszy zgodnych w granicach 2 błędów
  standardowych; trzy odstające to wiersze mocy wobec zaniżenia o 10 %, w obu kierunkach.
- **Nie** przeliczono niezależnie prognozy HAR ani ogonów empirycznych (`*_ep`, `*_ec`); warstwę wydruku
  sprawdzono przeliczeniem z surowych wyników, a nie czytaniem kodu linia po linii.
- Strona niezależna (pakiet `arch`) daje przy GARCH wydruki różniące się w trzeciej cyfrze zależnie od liczby
  wątków BLAS; strona rejestrowa nie (wyniki identyczne co do bitu). Wniosków to nie zmienia.

**6. Werdykt: Caveats** (podpisuje Claude, R14). Nie Ready: trzy flagi, próg K-a wybrany po pilotażu, wrażliwość
na konwencję startu GARCH oraz to, że wszystkie 8 przewidywań W1–W4 wyszło zgodnie z oczekiwaniem (wynik
idealnie potwierdzający hipotezę zawsze wymaga ostrożności). Nie Revision: nie znaleziono błędu, a wszystkie
niezależne przeliczenia się zgadzają. Siedem warunków jest w sekcji „Werdykt”.

**7. Po Twojej stronie** (nic z tego nie jest zrobione bez Ciebie).

1. Czy otwierać pierwszą rundę VaR/ES na danych. Licznik „ryzyko 2021+” zostaje 0, aż ją otworzysz (0 → 1).
2. Czy akceptujesz odczytanie Zakresu (b): 15 monet × 1 700 dni, bo reguła K w C2 nie ma flagi.
3. Czy próg K-a ≤ 10 % jest do przyjęcia (przy 7,5 % wynik dla VaR 1 % to NIE).
4. Który poziom VaR. Rekomenduję **5 %** jako jedyny wskazany z góry: fałszywy alarm 5,5 % (nie 8,2 %) i
   mniejsza wrażliwość na konwencję startu GARCH. Pytanie o oba poziomy naraz wymaga poprawki α/2.
5. Czy zlecić LV2c (wyjaśnienie błędu standardowego testu DM, wrażliwość na konwencję startu GARCH, ewentualnie
   inna reguła dla pytania porównawczego) — nie jest potrzebne do pierwszej rundy bezwzględnej. Trop z ogonem EWMA
   (sekcja 4) to osobna karta opisowa, nie część LV2c.

## W skrócie — prostym językiem

> *Uwaga dopisana po przebiegu rejestrowym: wszystko poniżej, aż do sekcji „Przebieg rejestrowy (fakty
> wykonania)” na końcu pliku, jest tekstem **sprzed przebiegu**. Słowa „oczekujemy”, „jeszcze nie”, „może
> dać” opisują oczekiwania z tamtej chwili, nie wyniki. Wynik jest w sekcji „Wynik w skrócie” powyżej i w
> sekcjach na końcu pliku.*

LV1 pokazała, że test zbiorczy (liczenie po dniach, nie po monetach) wykrywa prognozę ryzyka zaniżoną o
ok. 8 %. Ale tylko dla prognozy-**wyroczni**, czyli takiej, w której znamy prawdziwą zmienność. Prawdziwa
prognoza musi zmienność oszacować z danych. I wtedy LV1 zobaczyła coś niepokojącego: nawet rozsądne,
codziennie liczone prognozy (okno 60 dni, EWMA) test zbiorczy odrzucał w 78–98 % sztucznych paneli,
choć ogon był dobry. Prawdopodobna przyczyna (hipoteza z LV1): sam błąd szacowania zmienności daje za
dużo przekroczeń VaR.

Zanim jakakolwiek runda VaR/ES dotknie prawdziwych danych, LV2 odpowiada — na sztucznych cenach, w
których prawdę znamy — na trzy pytania:

- **(a)** Czy test zbiorczy jest **uczciwy dla modelu poprawnego, ale oszacowanego z danych** (GARCH-t
  dopasowywany od nowa co 30 dni na danych, które naprawdę pochodzą z GARCH-t)? Jeśli taki model odrzuca
  częściej niż w ok. 10 % przypadków, to „odrzucono” na prawdziwych danych niczego nie znaczy.
- **(b)** Czy test **porównawczy** (miara straty FZ0 i test Diebolda–Mariano na dziennych średnich po
  monetach) odróżni od siebie dwie prognozy estymowane przy ok. 1 600 dniach i 20 monetach? To inne
  pytanie niż „czy prognoza jest dobra”: „czy ta jest lepsza od tamtej”.
- **(c)** Reguła: które z tych pytań (jeśli którekolwiek) wolno zadać w pierwszej rundzie na danych.

Dwa pytania mają dwie osobne reguły: **K** (bezwzględne, z (a)) i **P** (porównawcze, z (b)). Runda jest
MIERZALNA, gdy choć jedna z nich da TAK. Każda reguła ma kontrole samego laboratorium (rozmiar na prawdziwej
prognozie, moc wobec zaniżenia o 30 %, wiarygodność estymatora GARCH i błędu standardowego testu DM). Gdy
kontrola zawiedzie, wynik to WSTRZYMANE — to błąd laboratorium, nie wniosek o danych.

Uczciwie o oczekiwaniu: przed zapisem tej pre-rejestracji obejrzeliśmy pilotaż 480 paneli (poza rejestrem,
inne ziarno). Wygląda na to, że **K da TAK** (z małym zapasem przy 1 %), a **P da NIE** (test porównawczy
za słaby, by przy 1 600 dniach odróżnić EWMA od GARCH-t). Przewidywania W1–W4 zapisano po tym pilotażu, więc
**nie są ślepe**. Dokładna oś czasu — w sekcji „Co sprawdzono PRZED zapisem kryteriów”.

Po zapisie recenzenci uruchomili dwa małe pilotaże (100 i 60 paneli, inne ziarna, poza rejestrem). Razem z
pilotażem 480 (640 paneli) K-a przy 1 % wyszło **8,9 ± 1,1 %** wobec progu 10 %, czyli zapas jest mały i
niepewny. Dlatego wynik rejestrowy może być też inny, niż tu oczekujemy: K może dać NIE (wtedy przy 1 % runda
NIEMIERZALNA), a kontrola laboratorium może zawieść przypadkiem (wtedy WSTRZYMANE i najwyżej jedna runda
LV2b). Każdy z tych wyników jest uczciwym wynikiem rundy i zostanie opisany wprost.

## Metadane

- **Pre-rejestracja zapisana w commicie `73fff28`** (2026-10-07 07:02:44 UTC: README oraz zmiany tylko w
  dokumentacji kodu `symulacje/garch_t.py` i `symulacje/run_lv2.py` i w ścieżkach karty 016; kod i testy
  rundy pochodzą z `009204b`, 2026-10-06 17:56:29 UTC). Hash `73fff28` wpisał commit `c9419a3` (07:02:57
  UTC), bez zmian kodu ani progów. **Przebieg rejestrowy z commitu:** `24c8863` (stan po przeglądzie
  z kroku 2; hash wpisany osobnym commitem przed uruchomieniem, który zmienia tylko README, kartę i STATUS — kod i testy
  są dokładnie z `24c8863`; różnice względem `73fff28` wymienia sekcja
  „Zmiany po przeglądzie, przed pełnym przebiegiem”).
- Zadanie 016 (`zadania/016-laboratorium-lv2-var-es-estymowane.md`), kontynuacja LV1 (zadanie 009).
  Runda kalibracyjna, nie hipoteza rynkowa: **R1 — brak mechanizmu rynkowego** (nic nie przewidujemy,
  mierzymy własności przyrządu przy naszych n i dla prognoz estymowanych).
- Kod (commit `009204b`, poprawiony po przeglądzie): `symulacje/run_lv2.py` (przebieg, reguły K i P, wydruk), `symulacje/prognozy_lv2.py`
  (19 prognoz estymowanych na jednym panelu), `symulacje/garch_t.py` (własny estymator GARCH(1,1)-t
  metodą największej wiarygodności, sprawdzony niezależnie pakietem `arch` 8.0.0), `symulacje/porownanie_lv2.py`
  (strata FZ0, strata kwantylowa, wzory zamknięte na oczekiwane straty, test DM), testy `tests/test_lv2.py`
  (131 testów, 241 przypadków; w `009204b` było 88 i 159). **Nie zmieniane:** zamrożony `miara/var_es.py` (po KV1), `miara/dm.py`
  (HAC), `symulacje/moc_var_es.py` (test zbiorczy LV1: A lub B lub C, Bonferroni, bootstrap-t po dniach),
  `symulacje/garch_panel.py` (generator).
- Komenda: `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m symulacje.run_lv2 --workers 16
  --zapisz data/lv2_wyniki_paneli.npz > runs/2026-10-07_lv2-var-es-estymowane/raw_output.txt`. `--zapisz`
  zapisuje surowe wyniki wszystkich paneli (plik `.npz` w `data/`, poza gitem) zaraz po przebiegu, przed
  wydrukiem raportu, żeby awaria raportu nie kosztowała 30 minut liczenia; kod sam wymusza jeden wątek
  BLAS (zmienne w komendzie są dla porządku).
  `--smoke` sprawdza tylko, że kod działa (4 panele po 700 dni, 8 monet); `--panele` i `--ziarno` dają
  pilotaż z nagłówkiem „PILOTAŻ — NIE JEST PRZEBIEGIEM REJESTROWYM”. Na stdout idą tylko liczby
  odtwarzalne (oraz wersje pakietów z linii „Wersje: …”); czas i postęp idą na stderr.
- Dane: WYŁĄCZNIE syntetyczne (`symulacje.garch_panel.generuj_panel`: GARCH(1,1) α 0,08, β 0,90, szok
  dzienny t z ν = 5, zmienność bezwarunkowa 4 %/dzień, czynnik rynkowy ρ = 0,8). Nie czytamy `data/`;
  R16 (dane od 2021) nie dotyczy.
- Determinizm (R19): ziarno główne `20261016`; `SeedSequence.spawn` na panel, a w panelu osobno generator
  i bootstrap (po przeglądzie ziarna dzieci panelu liczy funkcja `_potomne`, która **nie zmienia stanu**
  `SeedSequence`: te same ziarna co `spawn` na świeżym obiekcie, przypięte w teście dla paneli 0, 1 i 4 999);
  kolejność wyników zachowuje `imap`, więc wynik **nie zależy od liczby procesów** (pilnują tego testy);
  kod sam ustawia jeden wątek BLAS. Ziarna pilotaży przed zapisem kryteriów były INNE (777 dla pilotaży 16
  i 480 paneli, 810000 dla pilotażu 64 paneli, własne ziarna dla pilotaży estymatora), pilotaże recenzentów
  po zapisie też (4711 i 424242). Ziarno rejestrowe użyto dotąd w teście działania `--smoke` (4 panele),
  w mikro-teście niezależności od liczby procesów (3 panele po 520 dni, 3 monety) i w teście przypięcia
  ziaren; **pełnej konfiguracji (5 000 paneli × 2 100 dni) nikt z tym ziarnem nie doprowadził do końca ani
  nie widział jej wyniku** (patrz incydent W14 w „Zmiany po przeglądzie”).
- Czas: pilotaż 480 paneli = 174 s na 16 procesach, czyli ok. 5,8 s na panel na rdzeń; 5 000 paneli ≈
  **30 min** na 16 procesach (zakres 20–60 min). Uruchamiać bez innych równoległych przebiegów.

## Pre-rejestracja (zapisana przed przebiegiem)

### Wnioski skumulowane, które dotyczą tej rundy (jedno zdanie)

LV1 (2026-10-06): realistyczne prognozy estymowane (okno 60, EWMA 0,94) przy poprawnym ogonie t5 są
odrzucane przez test zbiorczy w 78–98 % paneli, a rozmiar tego testu zmierzono tylko dla wyroczni,
natomiast F2-1b (2026-10-06, NIEPOZYTYWNY 11/15 → STOP → ryzyko ogona) i KV1 (19/19 przy bardzo dużych
n i ρ = 0) mówią, że następny krok to ryzyko ogona, ale dopiero po sprawdzeniu przyrządu na prognozie
estymowanej — stąd w LV2 H0 to model poprawny i dopasowany z danych (GARCH-t), obok pytania
bezwzględnego jest pytanie porównawcze, a komórką główną jest ta z LV1 (n = 1 600, 20 monet, ρ = 0,8).

### Pytanie i mechanizm (R1)

Nie przewidujemy rynku, tylko kalibrujemy przyrząd; „kto traci po drugiej stronie” nie dotyczy. Trzy
pytania: (a) rozmiar i moc testu zbiorczego LV1, gdy prognoza jest poprawnie określona, ale
estymowana (reguła K); (b) moc testu porównawczego FZ0 + Diebold–Mariano dla prognoz estymowanych (reguła P);
(c) która z reguł pozwala zacząć pierwszą rundę VaR/ES na danych. Mechanizm sprawdzanej hipotezy
(z LV1, tam niesprawdzanej): szum w σ̂ nie zeruje się w średniej — prognoza z zaniżonym σ̂ ma więcej
trafień, niż prognoza z zawyżonym σ̂ ich traci — więc test bezwzględny odrzuca nawet poprawny model
częściej niż nominalnie. Pytanie jest ilościowe: o ile częściej, i czy przy poprawnie określonym GARCH-t
mieści się to w progu.

### Konwencje

Zwrot dzienny r_it (moneta i, dzień t); q_it = kwantyl rzędu p (ujemny); es_it = E[r | r < q_it] (ujemny);
trafienie I_it = 1{r_it < q_it}, równość NIE jest trafieniem (zamrożony `miara/var_es.py`). Odrzucamy H0,
gdy p-wartość < 5 % (test zbiorczy: każdy ze składników A, B, C na α/3 = 1,67 %; DM: dwustronnie
|t| > 1,96, albo jednostronnie t > 1,96, gdy wskazano). Test z niezdefiniowaną statystyką (NaN) to **brak
odrzucenia**; liczymy je osobno (`niezdef`). Panel ma 2 100 dni: dni 0–399 to historia (rozgrzewka i
trening), dni 400–2099 to okres oceny (1 700 dni). **Każda prognoza dnia t używa wyłącznie zwrotów z dni
< t** (R6/R7; patrz testy poniżej). Komórki są **zagnieżdżone w jednym panelu**: C1 = pierwsze 20 monet i
pierwsze 1 600 dni oceny, C2 = pierwsze 15 monet i pierwsze 1 700 dni oceny; każda ma własne indeksy bootstrapu.

### Projekt

| element | wartość |
|---|---|
| generator | GARCH(1,1) α 0,08 β 0,90, t5, zmienność 4 %, czynnik rynkowy ρ = 0,8 (korelacja zwrotów ok. 0,62), K = 20 monet; bez zależności ogonowej i bez wspólnej zmienności |
| panel | 2 100 dni, generowany RAZ na panel; okres oceny 1 700 dni po 400 dniach historii |
| komórka główna **C1** | K = 20 monet, n = 1 600 dni oceny (jak w LV1); **tylko ona wchodzi do reguł i werdyktu** |
| komórka **C2** (warunek Zakresu (b)) | K = 15 monet, n = 1 700 dni oceny (populacja F2-1b); ta sama reguła drukowana w C2 jest **warunkiem Zakresu (b)** pierwszej rundy na danych, nie werdyktem rundy; w K6 pięć par realistycznych (bez `ewma94_t5 → ewma94_ep`: C2 nie ma ogonów `ep`), K7 liczone z 20 monet |
| poziomy | p ∈ {1 %, 5 %}, każdy osobno |
| panele | **5 000** (jedna wspólna seria paneli dla wszystkich prognoz, strat i komórek) |
| bootstrap testu zbiorczego | 999 replikacji po dniach (wspólne indeksy dla wszystkich prognoz i p w danym panelu i n) |
| test porównawczy | DM na dziennych średnich po monetach różnicy strat, wariancja HAC Newey–West (`miara.dm`, opóźnienie 7 dla n od 1 241 do 2 262 dni, czyli dla 1 600 i 1 700); bez poprawki Harveya–Leyborne'a–Newbolda |
| precyzja | SE odsetka ≤ **0,71 pp** (0,57 pp przy mocy 80 %, 0,31 pp przy 5 %) |
| okres treningu GARCH | rosnące okno od dnia 0 do początku bloku b ≥ 400; refit co 30 dni (57 bloków × 20 monet = 1 140 dopasowań na panel) |

**Dlaczego 5 000 paneli.** SE odsetka odrzuceń ma być wyraźnie mniejszy niż pasmo rozmiaru (±2,5 pp wokół
5 % to ok. 8 SE, bo SE rozmiaru wynosi 0,31 pp) i niż odstępy między progami a oczekiwanymi wartościami.
Przy K-a prawdziwy rozmiar nie jest znany: pilotaż 480 paneli dał 7,9 ± 1,2 % przy progu 10 %, a trzy
pilotaże razem (480 + 100 + 60 = 640 paneli, inne ziarna) 57/640 = 8,9 ± 1,1 %. SE ok. 0,4 pp przebiegu
rejestrowego opisuje tylko jego własną precyzję i **nie usuwa niepewności co do prawdziwego rozmiaru**: przy
niepewności 8,9 ± 1,1 % szansa, że wynik rejestrowy wyjdzie ≤ 10 %, to ok. 80–83 %, a nie pewność
(wcześniejsze sformułowanie „zapas ok. 5,5 SE” było przesadą). Panele
komórek C1 i C2 są zależne (ten sam panel), więc porównania między komórkami są opisowe.

### Rachunek mierzalności (R3)

Laboratorium jest mierzalne, jeśli (1) jego rozdzielczość jest dużo mniejsza niż marginesy kryteriów oraz
(2) każde kryterium może zawieść (inaczej reguła nic nie rozstrzyga).

1. **Rozdzielczość.** SE ≤ 0,71 pp przy 5 000 panelach. Pasma kontroli rozmiaru (K1, K4, K6) mają ±2,5 pp
   wokół 5 % (8 SE); próg mocy 95 % (K2, K5) leży daleko od wyników pilotażu (100 %); K-a: zapas ok. 1–2 pp
   (pilotaż 480: 7,9 %; trzy pilotaże razem 8,9 ± 1,1 %) wobec SE przebiegu rejestrowego ok. 0,4 pp — zapas
   jest realny, ale prawdziwy rozmiar jest niepewny (patrz „Dlaczego 5 000 paneli”); K-b: moc 99,4–99,6 %
   wobec progu 80 % (**K-b to w praktyce druga kontrola pozytywna, a nie kryterium, które realnie
   rozstrzyga; rozstrzyga K-a**). Rozdzielczość bootstrapu: B = 999 daje p-wartości na siatce 1/1 000, a próg
   α/3 = 1,67 % oznacza, że składnik jednostronny odrzuca przy co najwyżej 15 z 999 replikacji po dużej
   stronie (dwustronny: przy co najwyżej 7 po mniejszej stronie), więc test zbiorczy ma poziom nominalny co
   najwyżej 4,8 %, nie 5 % (testy
   `test_rozdzielczosc_bootstrapu_pozwala_testom_a_i_b_odrzucac_na_poziomie_alfa_przez_3` oraz
   `test_skladniki_i_zbiorczy_odrzucaja_dopiero_ponizej_alfa_przez_3`).
2. **Obalalność (kryteria mogą zawieść).** Gdyby K-a stosować do prognozy `ewma94_t5` (σ z EWMA, ogon t5),
   zawiodłoby ono z dużym zapasem: 77–86 % odrzuceń w pilotażach wobec progu 10 %. Gdyby K-b dotyczyło σ
   zaniżonego tylko o 5 %, zawiodłoby też (pilotaż 480: moc testu zbiorczego wobec wyroczni × 0,95 to
   47 % / 53 %, wobec progu 80 %). P-a i P-b w pilotażu **nie** są spełnione (patrz niżej): reguła P
   potrafi więc dać NIE, a reguła K w pilotażu daje TAK. Żadna reguła nie jest trywialnie spełniona;
   P-a i P-b nie są też niemożliwe z konstrukcji (moc DM rośnie z n i ze zbliżaniem się prognoz do
   wyroczni), tylko przy n = 1 600 pilotaż 480 pokazuje 35 % / 76 % mocy pary głównej (pilotaże
   recenzentów: 37–47 % przy 1 % i 78–84 % przy 5 %). Reguła K może też dać NIE: w pilotażach recenzentów
   K-a przy 1 % wyszło 12,0 % i 11,7 % (powyżej progu 10 %), w pilotażu 480 7,9 %.
3. **Koszt:** ok. 30 min na 16 procesach.

Werdykt rachunku: **przebieg może wystartować** — rozdzielczość jest dużo mniejsza niż marginesy
kryteriów, a każde kryterium może zawieść. To rachunek dla samego laboratorium; „MIERZALNA /
NIEMIERZALNA” w regule rundy (niżej) dotyczy dopiero pierwszej rundy na prawdziwych danych.

### Prognozy (19, wszystkie F_{t−1}-mierzalne)

Prognoza = (q, es) = σ̂_t · (Q, ES), gdzie (Q, ES) to kwantyl i ES poziomu p dla standaryzowanej innowacji
o wariancji 1; ogon jest stały w bloku 30 dni i odświeżany co blok.

| nazwa | σ̂ | ogon | rola |
|---|---|---|---|
| `wyr_t5` | σ_t wyroczni (z generatora) | t5 (prawdziwy) | **kontrola negatywna K1, K4** (H0 prawdziwa); druga strona każdego porównania z wyrocznią |
| `zan05` … `zan30` | wyrocznia × (1 − x), x ∈ {0,05; 0,10; 0,15; 0,20; 0,30} | t5 | krzywa mocy, MDE; `zan30` = **kontrola pozytywna K2, K5** |
| `okno60_t5` | okno 60 dni | t5 | opis, W1, W2, para realistyczna |
| `ewma94_t5` | EWMA λ = 0,94 | t5 | opis, W1, W2, **baseline pary głównej P-b** (R17) |
| `garch_t5` | GARCH(1,1)-t, refit co 30 dni na rosnącym oknie | t5 | opis, para realistyczna |
| `garch_tnu` | jw. | t_ν̂ (ν̂ z dopasowania danego bloku i monety) | **prognoza „poprawnie określona, estymowana”: K-a, K-b (w wersji ×0,90), P-b** |
| `garch_tnu_zan10`, `garch_tnu_zan20` | `garch_tnu` × 0,90 / × 0,80 | t_ν̂ | **K-b** (zan10), opis (zan20) |
| `har_t5` | HAR-RV (`modele.zmiennosc.prognoza_har`), własny harmonogram refitów co 30 dni od dnia 395 | t5 | opis (HAR odłożony po F2-1b; tu tylko jako opis), para realistyczna |
| `okno60_ep`, `ewma94_ep`, `garch_ep` | jak wyżej | empiryczny, reszty wszystkich monet razem | opis (nie w C2, bo C2 to podpanel) |
| `okno60_ec`, `ewma94_ec`, `garch_ec` | jak wyżej | empiryczny, reszty każdej monety osobno | opis |

Reszty standaryzowane do ogonów empirycznych: dla okna i EWMA z ich własnych σ̂_s (s ∈ [60, b)), dla GARCH
z filtra przepuszczonego z parametrami bloku b przez dni < b („reszty w próbie”: parametry widziały te
same dni, ale filtr nie widzi dni ≥ b). Bez żadnego zwrotu z dnia ≥ t w prognozie dnia t:
`test_prognozy_nie_zalezą_od_przyszlosci_obciecie_panelu` oraz
`test_zaburzenie_dnia_t_nie_zmienia_prognoz_na_dni_do_t_wlacznie`. Po przeglądzie testy poszerzono (pierwotnie
zaburzały tylko dzień w środku bloku):
`test_zwroty_od_dnia_t0_nie_zmieniaja_zadnej_z_19_prognoz_na_dni_do_t0_wlacznie` (t0 ∈ {400, 429, 430, 431,
489, 490, ostatni dzień} na mikro-panelu; wszystkie 19 prognoz i oba poziomy bez różnicy co do bitu dla dni ≤ t0),
`test_zmiana_zwrotu_dnia_t0_rusza_prognozy_estymowane_dopiero_od_dnia_t0_plus_1` (test czułości: zmiana
jednego dnia rusza σ̂ dnia następnego, we wszystkich monetach każdej prognozy estymowanej),
`test_zaburzenie_pierwszego_dnia_bloku_nie_zmienia_prognoz_tego_ani_poprzednich_blokow` (dzień początku bloku nie
wchodzi do parametrów GARCH ani do ogonów tego bloku) i
`test_zrodla_zgodne_z_odtworzeniem_od_zera_z_definicji_dnia_t_i_bloku` (każde σ̂ i każdy ogon przeliczone od nowa
z definicji, pętlami). Niezależnie recenzent kodu sprawdził panel o pełnej długości (2 100 dni, 5 monet):
zaburzenie zwrotów od dnia t0 ∈ {399, 400, 429, 430, 431, 1000, 2079, 2080} nie zmieniło ani jednego bitu
w 76 tablicach prognoz (19 prognoz × 2 poziomy p × kwantyl i ES) dla dni ≤ t0.

### Test zbiorczy (bez zmian względem LV1)

Jednostką jest dzień (R12). S_t = Σ_i I_it, d_t = Σ_i (U_it − 1), U_it = r_it I_it / (p es_it). A: pokrycie
(t-test średniej S_t względem K·p, dwustronny z równymi ogonami), B: grupowanie trafień (okno 10 dni,
dwustronny z równymi ogonami), C: ogon (średnia d_t, jednostronny). Zbiorczy = A lub B lub C, każdy na
α/3 (Bonferroni), p-wartości z bootstrapu-t po dniach (B = 999). Kod: `symulacje/moc_var_es.py`
(`testy_zbiorcze`, `odrzuca_zbiorczo`), bez żadnej zmiany względem LV1.

### Straty i test porównawczy

- **FZ0** (Patton–Ziegel–Chen 2019), dolny ogon, v = VaR, e = ES (obie ujemne): S = −1/(p e) · 1{r ≤ v}
  (v − r) + v/e + log(−e) − 1. Ocenia razem VaR i ES; różnica FZ0 dwóch prognoz nie zależy od wspólnej
  skali zwrotu. Jest to strata PRAWIDŁOWA (w oczekiwaniu najmniejsza dla prawdziwych (VaR, ES)); wzory
  zamknięte na oczekiwane straty pod t_ν dla σ wyroczni są w `oczekiwana_strata`.
- **PINB:** strata kwantylowa (p − 1{r < v})(r − v) samego VaR, dzielona przez wspólną wagę σ̂ (EWMA 0,94,
  znana w t − 1, więc strata nadal prawidłowa). Tylko opis i pary zerowe (K4).
- Strata dnia = **średnia po monetach** (R12: 20 monet to nie 20 obserwacji). Δ_t = strata_A − strata_B,
  t = średnia Δ / błąd HAC; **t > 0 oznacza, że B jest lepsza** (mniejsza strata).
- **Pary „dokładnie zerowe” (rozmiar DM pod prawdziwą H0):** prognoza A = wyrocznia × c_A (c_A ∈ {0,9; 0,8}),
  prognoza B = wyrocznia × c_B, gdzie c_B > 1 jest dobrane tak, by OCZEKIWANE straty A i B były równe
  (druga gałąź paraboli straty). Wtedy H0 „równe oczekiwane straty” jest prawdziwa, choć żadna prognoza nie
  jest prawdziwa. Mnożniki (ν = 5; wyliczone brentq, sprawdzone: oczekiwane straty A i B równe do 1e-8):

  | strata, p | c_A = 0,9 → c_B | c_A = 0,8 → c_B |
  |---|---|---|
  | FZ0, 1 % | 1,126683 | 1,344627 |
  | PINB, 1 % | 1,116078 | 1,276016 |
  | FZ0, 5 % | 1,120401 | 1,302395 |
  | PINB, 5 % | 1,109835 | 1,243453 |

- **K6 (rozmiar DM po wyśrodkowaniu na parach realistycznych):** t_c = (d̄ − średnia d̄ po panelach) / błąd
  HAC. Pary realistyczne to `okno60_t5 → ewma94_t5`, `ewma94_t5 → garch_tnu`, `okno60_t5 → garch_tnu`,
  `garch_tnu → garch_t5`, `ewma94_t5 → har_t5`, `ewma94_t5 → ewma94_ep`. Pod H0 „prawdziwa średnia
  różnica = jej średnia po panelach” odsetek |t_c| > 1,96 powinien wynosić ok. 5 %, jeśli błąd HAC jest
  wiarygodny. To kontrola błędu standardowego (opóźnienia HAC), nie rozmiar absolutny. W C2 jest pięć par (bez
  `ewma94_t5 → ewma94_ep`). Pilotaż 480 dał największy odsetek 7,3 % / 9,0 %, pilotaże recenzentów do
  12 %; prawdopodobna przyczyna to efekt estymacji (West 1996: różnica strat z estymowanych parametrów ma
  inną wariancję niż daje wzór HAC) — to **hipoteza, nie ustalenie**, a dłuższe opóźnienie HAC by jej nie
  naprawiło.

### Kryteria

Wszystkie liczone na **komórce głównej C1 (K = 20, n = 1 600, ρ = 0,8), osobno dla p = 1 % i p = 5 %**.
Kody są w kodzie (`ocen_k`, `ocen_p`) i w wydruku.

**Reguła K — pytanie bezwzględne (test zbiorczy LV1 na prognozie estymowanej).**

| kod | rola | co | wymaganie | bramkuje |
|---|---|---|---|---|
| **K1** | kontrola negatywna (R8) | rozmiar testu zbiorczego na `wyr_t5` | odsetek odrzuceń ∈ [2,5 %; 7,5 %] | każdy wniosek |
| **K2** | kontrola pozytywna (R8) | moc testu zbiorczego wobec `zan30` (σ wyroczni − 30 %) | ≥ 95 % | każdy wniosek |
| **K7a** | kontrola estymatora | średnia ν̂ GARCH-t po panelach (prawda 5) | ∈ [4,0; 6,5] | każdy wniosek |
| **K7b** | kontrola estymatora | średnia α̂ + β̂ (prawda 0,98) | ∈ [0,95; 0,995] | każdy wniosek |
| **K7c** | kontrola estymatora | odsetek dopasowań bez zbieżności | ≤ 2 % | każdy wniosek |
| **K7d** | kontrola estymatora | odsetek dopasowań przy granicy zakresu parametrów | ≤ 5 % | każdy wniosek |
| **K-a** | kryterium (kalibracja) | rozmiar testu zbiorczego na `garch_tnu` (poprawny model, estymowany) | odsetek odrzuceń ≤ **10 %** | — |
| **K-b** | kryterium (kalibracja) | moc testu zbiorczego na `garch_tnu_zan10` (σ̂ × 0,90) | ≥ **80 %** | — |

**Reguła P — pytanie porównawcze (DM na stracie FZ0).**

| kod | rola | co | wymaganie | bramkuje wniosek | dotyczy kryteriów |
|---|---|---|---|---|---|
| **K4** | kontrola negatywna (R8) | rozmiar DM (dwustronny) na 4 parach dokładnie zerowych {FZ0, PINB} × {c_A 0,9; 0,8}; liczy się NAJGORSZA z czterech | odsetek odrzuceń ∈ [2,5 %; 7,5 %] | każdy wniosek | P-a, P-b |
| **K5** | kontrola pozytywna (R8) | moc DM-FZ0 (jednostronnie t > 1,96): `zan30` wobec `wyr_t5` | ≥ 95 % | każdy wniosek | P-a, P-b |
| **K6a** | kontrola HAC | rozmiar DM-FZ0 po wyśrodkowaniu na parach realistycznych: NAJWIĘKSZY z sześciu (w C2 z pięciu) | ≤ 7,5 % | **tylko wniosek TAK** | P-b |
| **K6b** | kontrola HAC | jw.: NAJMNIEJSZY z sześciu (w C2 z pięciu) | ≥ 2,5 % | **tylko wniosek NIE** | P-b |
| **K7a–d** | kontrola estymatora | jak w regule K | jak wyżej | każdy wniosek | P-b |
| **P-a** | kryterium (mierzalność) | MDE zaniżenia σ testu DM-FZ0 wobec wyroczni (moc 80 %, siatka x ∈ {0; 0,05; 0,10; 0,15; 0,20; 0,30}) | MDE ≤ **0,10** (realizacja: moc po wygładzeniu maksimum narastającym przy x = 0,10 ≥ 80 %) | — | — |
| **P-b** | kryterium (mierzalność) | moc DM-FZ0 (t > 1,96, B lepsza) pary głównej `ewma94_t5 → garch_tnu` | ≥ **80 %** | — | — |

Kolumna „dotyczy kryteriów” mówi, przy którym niespełnionym kryterium reguły P dana kontrola musi przejść,
żeby wniosek NIE był wiarygodny (zmiana po przeglądzie, patrz niżej); w regule K każda kontrola dotyczy
obu kryteriów, a przy wniosku TAK (wszystkie kryteria spełnione) liczą się wszystkie kontrole „TAK”/„każdy”.

**Uzasadnienia progów.**

- **K1, K4, K6 [2,5 %; 7,5 %], K2, K5 ≥ 95 %:** jak w LV1 (pasmo ±2,5 pp = ok. 8 SE rozmiaru; kontrola
  pozytywna wobec σ − 30 % ma dawać ≈ 100 %, inaczej laboratorium jest głuche).
- **K-a ≤ 10 %:** dwukrotność poziomu nominalnego. Test zbiorczy dla modelu poprawnego, ale estymowanego,
  ma wolno być nieco liberalny (Escanciano–Olmo 2010: ryzyko estymacji zaburza rozmiar testów
  wstecznych), ale powyżej 10 % odrzucenie przestaje być sygnałem (co dziesiąty poprawny model wyglądałby
  na zły). **To nie jest próg wyprowadzony z teorii, tylko wybór po obejrzeniu pilotażu 64 paneli**
  (`garch_tnu`: 6,2 % przy 1 % i 4,7 % przy 5 %) — patrz „Co sprawdzono PRZED zapisem kryteriów”. Ma
  chronić przed dwukrotną nominalną liberalnością, nie wynika z żadnej funkcji straty użytkownika.
- **K-b ≥ 80 % przy x = 0,10:** ta sama kotwica co w LV1 (kryterium iii): zaniżenie σ o 10 % to „standardowy
  błąd modelu” (normalny kontra t5 przy 1 %: 2,326 vs 2,606); pozycja dobrana pod cel zmienności jest wtedy
  o ok. 11 % za duża. Przy estymowanym modelu pytamy, czy ta moc przeżyje szum estymacji.
- **K7 (zakresy):** sprawdzają estymator, nie rynek. Estymator ma odtwarzać generator w granicach
  błędu skończonej próby: ν̂ ∈ [4,0; 6,5] wokół 5 (ν̂ jest z natury skośne w prawo i niedoszacowuje
  ciężkości ogona), α̂ + β̂ ∈ [0,95; 0,995] wokół 0,98 (MLE zaniża persystencję w skończonej próbie),
  brak zbieżności ≤ 2 %, przy granicy ≤ 5 %. Zakresy są **szerokie celowo**: awaria oznacza zepsuty
  estymator, a nie niedokładność. Wybrane po pilotażach estymatora (nie ślepo, patrz wyżej).
- **P-a ≤ 0,10 i P-b ≥ 80 %:** P-a to ta sama kotwica x\* = 0,10 co w LV1, ale dla testu porównawczego
  wobec wyroczni (czy porównanie w ogóle widzi zaniżenie σ o 10 %). P-b pyta wprost: czy test odróżni
  najprostszy baseline (EWMA 0,94, t5; R17) od poprawnego modelu GARCH-t(ν̂), przy 1 600 dniach. Moc 80 % to
  zwykły standard mocy, jak w LM1 i LV1.
- **Dlaczego K6 ma dwie bramki jednostronne.** Błąd HAC (opóźnienie Newey–West) może być za mały (test
  liberalny: za często „istotnie”) albo za duży (test zachowawczy: za rzadko). Test **zbyt liberalny** może
  tylko zawyżać moc, więc wniosek NIE (moc za mała mimo zawyżenia) pozostaje ważny, a podważa tylko
  wniosek TAK → K6a bramkuje TAK. Test **zbyt zachowawczy** może tylko zaniżać moc, więc wniosek TAK pozostaje
  ważny, a podważa tylko wniosek NIE → K6b bramkuje NIE. Progi 2,5 % i 7,5 % bez zmian względem wersji
  pierwotnej (jedna kontrola dwustronna dla obu wniosków); zmiana zrobiona po pilotażu (patrz niżej).
- **Dlaczego K6 i K7 dotyczą tylko wniosku P-b (zmiana po przeglądzie, po fakcie).** P-a pyta o moc DM
  wobec wyroczni, a K6 (błąd HAC na parach realistycznych) i K7 (estymator GARCH) tej mocy nie dotyczą:
  wyrocznia nie jest estymowana, a pary realistyczne w ogóle w P-a nie występują. W wersji z `73fff28`
  zawiedzione K6a, K6b albo K7 wstrzymywało więc także wniosek „P-a niespełnione”, choć nic o nim nie mówi.
  Recenzent statystyczny pokazał to na własnym pilotażu przy p = 5 % (P-a: MDE 0,127, czyli niespełnione;
  K6b 2,0 % < 2,5 %; stara reguła dawała WSTRZYMANE zamiast NIE). Teraz każda kontrola ma jawną listę
  kryteriów (`dotyczy`): K4 i K5 — P-a i P-b; K6a, K6b i K7a–d — tylko P-b. **Skutek: nowa reguła zmienia
  wyłącznie wyniki WSTRZYMANE na NIE; nie tworzy TAK, nie odbiera NIE i nie zmienia reguły K** (własność
  sprawdza `test_werdykt_z_dotyczy_wlasnosci`; stara reguła jako szczególny przypadek bez `dotyczy`:
  `test_werdykt_bez_dotyczy_to_regula_sprzed_przegladu`). To zmiana po obejrzeniu pilotaży, więc **nie jest
  ślepa**; uzasadnienie jest logiczne, progi liczbowe bez zmian.

### Reguła decyzji (R4 / reguła STOP)

Dla każdego p osobno, na komórce głównej C1. Wynik każdej z dwóch reguł (K, P) to jedno z trzech:

- **TAK** (pytanie mierzalne) ⇔ wszystkie kryteria reguły są spełnione (K: K-a i K-b; P: P-a i P-b) ORAZ
  przeszły wszystkie kontrole o bramce „każdy wniosek” albo „tylko TAK” (K: K1, K2, K7a–d; P: K4, K5, K6a,
  K7a–d; K6b w TAK nie uczestniczy).
- **NIE** (pytanie niemierzalne) ⇔ dla co najmniej jednego niespełnionego kryterium przeszły wszystkie
  kontrole o bramce „każdy wniosek” albo „tylko NIE”, które to kryterium dotyczą (K: K1, K2, K7a–d; P przy
  niespełnionym P-a: K4 i K5; P przy niespełnionym P-b: K4, K5, K6b, K7a–d).
- **WSTRZYMANE** ⇔ każdy inny przypadek: zawiodła kontrola, od której zależy wyciągany wniosek. To błąd
  laboratorium, nie wniosek o danych.

Zmiana względem `73fff28`: wniosek NIE z P-a nie czeka już na K6b i K7a–d (nie dotyczą mocy wobec wyroczni).
Reguła zmienia więc wyłącznie wyniki WSTRZYMANE na NIE; TAK i reguła K są bez zmian (patrz „Zmiany po
przeglądzie”).

W wydruku wynik reguły K lub P nazywa się **MIERZALNE** (= TAK), **NIEMIERZALNE** (= NIE) albo
**WSTRZYMANE**; wynik rundy to **MIERZALNA / NIEMIERZALNA / WSTRZYMANA**. Każdą regułę i regułę rundy
wydruk podaje osobno dla C1 (werdykt rundy) i C2 (warunek Zakresu (b), nie werdykt rundy).

**Reguła rundy** (`regula_rundy`): runda pierwszej analizy VaR/ES na danych przy poziomie p jest

- **MIERZALNA(p)** ⇔ K albo P daje TAK; dozwolone są tylko pytania z wynikiem TAK;
- **WSTRZYMANA(p)** ⇔ żadne pytanie nie dało TAK i któreś jest WSTRZYMANE;
- **NIEMIERZALNA(p)** ⇔ ani K, ani P nie dało TAK i żadne nie jest WSTRZYMANE (obie NIE).

**WSTRZYMANA ⇒ STOP:** najpierw diagnoza, potem **najwyżej jedna** runda LV2b. W LV2b wolno zmienić
wyłącznie to, co diagnoza wskaże jako błąd laboratorium (np. opóźnienie HAC w DM, ustawienia estymatora);
NIE wolno zmieniać progów, prognoz, generatora, komórek ani liczby paneli. Druga WSTRZYMANA to
NIEMIERZALNA(p) i karta decyzji do użytkownika. LV2b używa **nowego ziarna `20261017`** (ziarno rejestrowe + 1):
poprawka nie może być dopasowana do już obejrzanych paneli. LV2b dotyczy tylko poziomów p, które były
WSTRZYMANE; wynik poziomu, który nie był WSTRZYMANY, przechodzi bez zmian i nie jest liczony ponownie. Reguły
są oceniane dla każdego p osobno, więc runda może być MIERZALNA przy p = 5 % i NIEMIERZALNA albo WSTRZYMANA
przy p = 1 %. (Ziarno LV2b to decyzja wykonawcy, odmienna od propozycji recenzenta „to samo ziarno”; do
przeglądu użytkownika.)

**MIERZALNA(p) ⇒ pierwsza runda VaR/ES na danych może wejść do pre-rejestracji** (osobna karta, licznik
„ryzyko 2021+”, PRD §11.4), ale tylko przy warunkach przeniesienia zapisanych TERAZ:

1. **Zakres.** (a) ≥ 20 monet, każda z ≥ 1 600 dniami OOS po ≥ 400 dniach historii (komórka C1), **albo**
   (b) populacja 15 monet × ≥ 1 700 dni OOS (komórka C2, jak F2-1b), ale tylko jeśli ta sama reguła
   (to samo pytanie, to samo p) daje TAK także w C2 **i wynik C2 nie ma flagi „w granicach 2 SE od progu”**
   — C2 jest warunkiem Zakresu (b), nie kryterium werdyktu rundy. **Dziś osiągalna jest tylko wersja (b)**
   (wg F2-1b pełną historię ma 15 monet); wersja (a) wymaga rozszerzenia koszyka. Przy mniejszym n lub K
   potrzebna jest nowa pre-rejestracja laboratorium. Komórka i lista monet rundy na danych (K, n, kolejność
   monet) muszą być zapisane z góry i być dokładnie komórką laboratorium.
2. **Zależność.** Współczynnik VR dziennej sumy trafień (VR = Var(S_t)/(K p (1 − p))) rośnie z liczbą monet
   K, więc porównujemy **ρ_h = (VR − 1)/(K − 1)** (średnia korelacja trafień dwóch monet w tym samym dniu;
   pilotaż: ρ_h ≈ 0,116 przy 1 % i ≈ 0,284 przy 5 %, w C1 i C2 prawie tak samo). ρ_h zmierzone na
   prawdziwych danych dla prognozy `garch_tnu`-podobnej (osobna karta, licznik opisowy; skrypt, który nie
   drukuje odsetka trafień) musi spełniać **ρ̂ + 2 SE ≤ ρ_h z laboratorium** (VR dla `garch_tnu` wydruk
   podaje przy każdym p, a ρ_h wylicza się z niego). Inaczej trzeba policzyć nową komórkę z silniejszą
   zależnością.
3. **Klasa prognozy.** Wniosek K dotyczy klasy „GARCH(1,1)-t dopasowany walk-forward (refit co 30 dni, rosnące
   okno ≥ 400 dni), ogon t_ν̂”. Okno 60 dni i EWMA mają W1 (odrzucane w ≥ 70 % paneli): test bezwzględny jest dla
   nich z założenia nieinformatywny i wolno je oceniać wyłącznie testem porównawczym (jeśli P = TAK) albo
   opisowo. Prognozę i ogon zapisuje pre-rejestracja rundy na danych; ma ona użyć dokładnie
   `symulacje.garch_t.dopasuj_garch_t`, zerowej średniej zwrotu i refitów co 30 dni od początku okresu oceny.
4. **Pytanie.** Wolno zadać wyłącznie pytania z wynikiem TAK; odrzucenie prognozy testem bezwzględnym
   znaczy „nie skalibrowana”, nie „bezużyteczna” (LV1).
5. **Dwa poziomy.** Runda na danych, która pyta o oba p (1 % i 5 %), zadaje dwa testy: albo wskazuje jedno p
   z góry, albo stosuje korektę (α/2). Zapisze to pre-rejestracja rundy na danych.

**NIEMIERZALNA(p)** ⇒ **żadna runda VaR/ES na prawdziwych danych przy tym poziomie nie startuje** (R3).
Alternatywy — niżej.

Skrypt jest neutralnym reporterem (R14): drukuje liczby, kryteria i wynik reguł; werdykt (Ready / Caveats
/ Revision) podpisuje Claude po przebiegu. Wydruk oznacza „[w granicach 2 SE od progu]” każde kryterium lub
kontrolę, której wartość leży bliżej progu niż 2 SE (przy takich werdykt jest wrażliwy na losowość), oraz
przy kontrolach „[bramkuje tylko wniosek …]” i „[dotyczy: …]” (które kryteria wniosek NIE bramkuje).

**Reguła flagi (dopisana po przeglądzie, przed przebiegiem).** Wynik mechaniczny reguł obowiązuje i flaga go
nie zmienia. Ale werdykt rundy (Ready / Caveats / Revision) jest przy wyniku z flagą co najwyżej Caveats;
nie wolno dosypywać paneli, zmieniać ziarna ani powtarzać przebiegu „bo blisko progu”; a TAK z flagą w C2 nie
otwiera Zakresu (b).

### Przewidywania (zapisane PO obejrzeniu pilotażu, więc nie ślepe; falsyfikowalne)

Sprawdzane w kodzie (`przewidywania`) dla komórki głównej, osobno dla p = 1 % i 5 %; **nie wchodzą do reguł**.

- **W1.** Test zbiorczy odrzuca `okno60_t5` i `ewma94_t5` w ≥ **70 %** paneli (LV1: 78–98 %; pilotaż 480:
  77,3 % / 80,6 %, czyli dla EWMA zapas jest mały).
- **W2.** Średnia strata FZ0 ponad wyrocznię jest ściśle malejąca: `okno60_t5` > `ewma94_t5` > `garch_tnu`
  (pilotaż: tak, przy 1 % i 5 %).
- **W3.** P-a **niespełnione** (MDE zaniżenia σ testu DM-FZ0 > 0,10; pilotaż: 0,140 / 0,131).
- **W4.** P-b **niespełnione** (moc DM-FZ0 pary `ewma94_t5 → garch_tnu` < 80 %; pilotaż: 35,2 % / 75,8 %).

**Oczekiwanie łączne (nie ślepe):** K = TAK (K-a przy 1 % blisko progu: 7,9 ± 1,2 % w pilotażu), P = NIE,
a więc runda MIERZALNA wyłącznie przez pytanie bezwzględne K. W razie niespełnienia któregoś z W1–W4 albo
takiego łącznego wyniku opisujemy to wprost. Po przeglądzie (pilotaże recenzentów, razem 640 paneli):
K-a przy 1 % ma zbiorczo 8,9 ± 1,1 %, więc **K = NIE (a przy 1 % runda NIEMIERZALNA) jest realnym wynikiem**;
kontrola, która zawiedzie przypadkiem (np. K1 8,0 % w pilotażu recenzenta), daje WSTRZYMANE; P-b przy 5 %
ma zbiorczo 77,3 ± 1,7 %, więc szansa, że W4 zostanie obalone (moc ≥ 80 %), to ok. 6–7 %; P-a jest
niespełnione z dużym zapasem (moc przy x = 0,10 ok. 50–59 % wobec 80 %), więc przy przechodzących K4 i K5
P = NIE. Przewidywania W3 i W4 program odczytuje po kodzie kryterium, nie po jego pozycji w liście.

### Co NIE jest kryterium (opis)

Wynik komórki C2 (jest warunkiem Zakresu (b), nie kryterium werdyktu rundy); wszystkie prognozy poza `wyr_t5`, `zan30`, `garch_tnu`, `garch_tnu_zan10` w regule K i
poza `wyr_t5`/`zan…` i parą główną w regule P; składniki A, B, C testu zbiorczego; test A po stronie „za
dużo trafień”; VR; strata PINB poza K4; ogony empiryczne (`ep`, `ec`), `garch_t5`, `har_t5`, `okno60_t5`,
`ewma94_t5` (z wyjątkiem pary głównej); „koszt estymacji” (średnia różnica straty prognozy estymowanej
względem wyroczni); pełna tabela odsetków odrzuceń testu DM dla wszystkich 36 porównań; kolumny
uśrednionych t. Odsetek odrzuceń testu zbiorczego dla okien i EWMA to **moc** (H0 dla nich fałszywa), nie
rozmiar.

### Co sprawdzono PRZED zapisem kryteriów (pełna jawność, R3)

Oś czasu (UTC, 2026-10-06; ustalona z zapisów sesji) i co z niej wynika dla ślepoty projektu:

**1. Estymator GARCH-t (17:07–17:09).** Własny estymator (`symulacje/garch_t.py`) porównano z pakietem `arch`
8.0.0 przy tej samej wartości backcastu (test `test_dopasowanie_zgodne_z_pakietem_arch_przy_tym_samym_backcast`;
konwencja startu filtra różni się: `arch` przyjmuje σ²₀ = ω + (α + β)·backcast, nasz estymator σ²₀ = backcast;
różnica logarytmu wiarygodności ≤ 0,04 na 10 seriach, α i β w granicach 3·10⁻⁴, ν w granicach 0,1),
sprawdzono odtwarzanie parametrów generatora na długich seriach, zgodność ciepłego i zimnego startu oraz
niezależność od jednostek zwrotu. Pilotaże estymatora na pojedynczych seriach miały własne ziarna.

**1a. Pilotaż samej wyroczni dla testu DM (17:09:59, skrypt poza repo, ziarna 900000 + numer powtórzenia).**
300 paneli po 20 monet × 1 700 dni; tylko pary „dokładnie zerowe” (c_A 0,9 i 0,8) i moc wobec wyroczni na
siatce x = 0,05–0,20, straty FZ0 i PINB, oba p. Pokazał, jak szybko rośnie moc DM; nie zawierał prognoz
estymowanych. Wynik był widziany przed zapisem kryteriów P.

**2. Pilotaż 64 paneli (17:11:45, skrypt poza repo, ziarno bazowe 810000; to NIE jest wynik rundy).** Odsetek
odrzuceń testu zbiorczego, p = 1 % / 5 %: `garch_tnu` 6,2 % / 4,7 %; `okno60_t5` 100 % / 93,8 %;
`ewma94_t5` 85,9 % / 79,7 %. Test DM-FZ0 pary `ewma94_t5 → garch_tnu`, odsetek t > 1,96 (B lepsza): 37,5 % /
68,8 %. **Progi K-a (≤ 10 %) i zakresy K7 zapisano w kodzie PO tym pilotażu (17:22:07)** — nie są ślepe.
SE pilotażu 64 paneli jest duży (ok. 3 pp przy 6 %). Pilotaż objął n = 1 700 dni oceny, 14 prognoz i 16 par DM, a
parę główną P-b i pary K6 wybrano **po** jego obejrzeniu. Wagą straty PINB była wtedy σ̂ prognozy A; po
pilotażu zmieniono ją na wspólną EWMA 0,94 znaną w t − 1 (17:20:54–17:21:00; waga musi być wspólna dla
obu prognoz pary, żeby strata pozostała prawidłowa; zmiana była zrobiona po obejrzeniu wyniku).

**3. Test działania i pilotaże 16 i 480 paneli (17:28–17:35, ziarno 777).** `--smoke` (17:28:36) sprawdził,
że kod działa. Pilotaż 16 paneli (17:28:49–17:29:02) to pierwsze 16 paneli tego samego ziarna; jego wynik też
był widziany. Pilotaż 480 paneli (17:29:08–17:32:03; 174 s na 16 procesach) pokazał: (komórka C1, p = 1 % /
p = 5 %; **to NIE jest wynik rundy**)

| wielkość | p = 1 % | p = 5 % | wymaganie |
|---|---|---|---|
| K1 rozmiar `wyr_t5` | 3,1 % | 4,8 % | [2,5; 7,5] % |
| K2 moc `zan30` | 100 % | 100 % | ≥ 95 % |
| K-a rozmiar `garch_tnu` | 7,9 ± 1,2 % | 5,0 ± 1,0 % | ≤ 10 % |
| K-b moc `garch_tnu_zan10` | 99,4 % | 99,6 % | ≥ 80 % |
| K4 najgorsza para zerowa | 6,0 % (FZ0, c_A 0,8) | 5,6 % | [2,5; 7,5] % |
| K5 moc DM-FZ0 `zan30` | 100 % | 100 % | ≥ 95 % |
| K6 DM-FZ0 wyśrodkowany: największy / najmniejszy z 6 par | 7,3 / 2,5 % | 9,0 / 2,9 % | ≤ 7,5 / ≥ 2,5 % |
| P-a MDE DM-FZ0 (moc przy x = 0,10) | 0,140 (50,0 %) | 0,131 (59,0 %) | ≤ 0,10 (≥ 80 %) |
| P-b moc `ewma94_t5 → garch_tnu` | 35,2 % | 75,8 % | ≥ 80 % |
| K7 (oba p razem): ν̂ / α̂+β̂ / bez zbieżności / przy granicy | 5,232 / 0,9722 / 0,00 % / 2,10 % | | [4,0; 6,5] / [0,95; 0,995] / ≤ 2 % / ≤ 5 % |
| opis: test zbiorczy, MDE zaniżenia σ (wyrocznia) | 0,082 | 0,079 | |
| opis: VR dziennej sumy trafień `garch_tnu` (`wyr_t5`) | 3,20 (3,03) | 6,36 (6,30) | |
| W1 (min z okno60, ewma94) / W2 (okno60 − garch_tnu, FZ0) | 0,773 / 0,080 | 0,806 / 0,058 | ≥ 0,70 / > 0 |
| opis C2: K-a / P-a / P-b | 9,4 % / 0,141 / 33,3 % | 4,4 % / 0,130 / 73,5 % | |

Moc DM-FZ0 wobec wyroczni (x = 0; 0,05; 0,10; 0,15; 0,20; 0,30): p = 1 %: 5,9; 14,4; 50,0; 87,3; 99,2; 100,0 %;
p = 5 %: 5,4; 19,6; 59,0; 93,1; 99,8; 100,0 %. Rozkład wyniku: K → TAK (K-a przy 1 % z małym zapasem; C2
przy 1 % jeszcze bliżej progu: 9,4 %), P → NIE (W3, W4 spełnione). Pilotaż pokazał też, że reguły potrafią dać
oba wyniki, czyli nie są trywialne (R3).

**4. Zmiany PO obejrzeniu pilotażu 480 (17:41–17:52; przed tą pre-rejestracją i przed przebiegiem rejestrowym).**

- **K6: jedna kontrola dwustronna → dwie bramki jednostronne (K6a, K6b)** (17:48). Pierwotnie wszystkie 6
  par realistycznych musiało mieścić się w [2,5; 7,5] %, a porażka wstrzymywała każdy wniosek. W pilotażu
  przy p = 5 % dwie pary (`okno60_t5 → ewma94_t5` i `garch_tnu → garch_t5`) dały 9,0 %, więc stara
  kontrola wstrzymałaby regułę P przy 5 %; nowa daje tam NIE (najmniejszy 2,9 % ≥ 2,5 %; K6a bramkuje
  tylko TAK). **Zmiana jest po fakcie** i przestawia przewidywany wynik reguły P przy 5 % z WSTRZYMANE na
  NIE; werdykt rundy (MIERZALNA przez K) się nie zmienia. Uzasadnienie logiczne — w „Uzasadnieniach progów”;
  progi liczbowe bez zmian. Przy p = 1 % obie nowe bramki leżą na krawędzi (7,3 % przy 7,5 %; 2,5 % przy
  2,5 %), więc w przebiegu rejestrowym K6a lub K6b może zawieść; skutek: P = WSTRZYMANE. Przy oczekiwanym
  P = NIE wniosku o rundzie to nie zmienia, o ile K = TAK.
- **P-a: realizacja przez moc przy x\* = 0,10 po wygładzeniu maksimum narastającym** (17:41), zamiast
  interpolowanego MDE (x\* leży na siatce, więc to to samo kryterium bez zaokrągleń interpolacji;
  wydruk nadal podaje MDE). W pilotażu bez wpływu na wynik (moc 50,0 / 59,0 %).
- **Panele 3 000 → 5 000** (17:51): zmniejsza SE, by zapas K-a był rozróżnialny (SE ≤ 0,71 pp).
- **Test przypięcia konfiguracji** (`test_konfiguracja_progi_i_prognozy_zgodne_z_pre_rejestracja`) zapisuje
  progi, ziarno, komórki i listę prognoz z tej pre-rejestracji; zmiana któregokolwiek w kodzie wymaga zmiany
  w README (oraz w teście).
- **Zmiana tylko w dokumentacji** `symulacje/porownanie_lv2.py` (17:48:49): docstring, bez zmiany kodu.

**5. Kod testów i commit.** Testy jednostkowe powstały równolegle z kodem (17:33–17:55); commit kodu
`009204b` (17:56:29). Testy pokrywają m.in.: wzory strat na liczbach ręcznych, wartości oczekiwane
(porównanie z całkowaniem), pary zerowe, DM na wzorze ręcznym i znak, estymator GARCH względem `arch`, brak
zaglądania w przyszłość (zaburzenie dnia t nie zmienia prognoz do t włącznie), podpanel = te same monety
i dni, okablowanie reguł (każdy próg domknięty na granicy, bramki K6, tabela prawdy reguły rundy),
determinizm niezależny od liczby procesów, przypięcie konfiguracji, znacznik pilotażu. Mikro kontrole R8
na małych panelach: wyrocznia ma poprawny rozmiar, `zan30` jest wykrywane, pary zerowe nie odrzucają zbyt
często. Mutacje na kopii poza repozytorium zrobiono po zapisie (sekcja „Zmiany po przeglądzie”).

**6. Czego nie sprawdzano.** Pełnego przebiegu rejestrowego (5 000 paneli, ziarno 20261016) nie
uruchamiano (poza jednym incydentem po zapisie, opisanym w „Zmiany po przeglądzie”: przerwany test
mutacyjny z konfiguracją rejestrową, którego wyniku nikt nie widział). Nie czytano żadnych prawdziwych danych. K-a na rozdzielczości rejestrowej (SE ok. 0,4 pp)
nie jest znane — pilotaż ma SE 1,2 pp. Nie badano zachowania estymatora przy zmianach reżimu, wspólnej
zmienności ani zależności ogonowej (generator ich nie ma).

### Zmiany po przeglądzie, przed pełnym przebiegiem

Zapisane po commicie `73fff28` i **przed** przebiegiem rejestrowym. Przegląd zrobiły **modele** (agenty
Claude), nie ludzie: inna „głowa” niż autor, ale możliwe wspólne ślepe plamy; dlatego po przebiegu dojdzie
jeszcze przeliczenie jednej kluczowej liczby drugą, niezależną drogą (krok 4 planu). Recenzenci dostali
pre-rejestrację i kod, nie moją analizę.

**Kto i co sprawdzał.**

- *Recenzent statystyczny:* progi, wzory strat i mnożniki par zerowych, reguły, tabelę prawdy reguły rundy i
  liczby pilotażu 480 (przeliczone od nowa); własny pilotaż 100 paneli (ziarno 4711, poza rejestrem).
- *Recenzent kodu:* przeciek z przyszłości (zero różnic co do bitu w 76 tablicach przy ośmiu punktach t0 na panelu
  o pełnej długości 2 100 dni, 5 monet), niezależne przeliczenie jednego panelu (kwantyle i ES do 7·10⁻¹⁶; trafienia, U i VR co do
  bitu; statystyka DM identyczna: 2,569250), determinizm (1 i 3 procesy, liczba wątków BLAS), estymator względem
  `arch` na 10 seriach, ciepły i zimny start (różnica NLL ≤ 5·10⁻¹²); własny pilotaż 60 paneli (ziarno 424242).
- *Recenzent mutacyjny:* zepsuł kod na kopii poza repozytorium na wiele sposobów (mutacje), żeby sprawdzić, czy
  testy to zauważą.
- *`arxitect:architecture-review`:* projekt obiektowy APPROVED, architektura APPROVED, interfejsy
  CHANGES_REQUESTED (0 ustaleń blokujących).

**Ustalenia i co z nimi zrobiono.**

| # | ustalenie | kto | działanie |
|---|---|---|---|
| 1 | **BLOKUJĄCE:** K6 i K7 bramkowały wniosek NIE z P-a, choć nic o nim nie mówią | statystyczny | `dotyczy` w regule P (zmiana reguły, po fakcie; patrz „Uzasadnienia progów”) |
| 2 | brak reguły na wynik „blisko progu” | statystyczny | reguła flagi (w „Reguła decyzji”) |
| 3 | C2 nazwana „opisem”, a jest jedynym osiągalnym Zakresem | statystyczny | C2 = warunek Zakresu (b) (README i wydruk) |
| 4 | warunki przeniesienia nieprecyzyjne (VR zależy od K; dwa p = dwa testy) | statystyczny | warunki 1–5 |
| 5 | luki w osi czasu | statystyczny, kod | sekcja „Co sprawdzono PRZED zapisem kryteriów” uzupełniona |
| 6 | K6a ≈ 9–12 % na parach realistycznych (hipoteza: efekt estymacji) | statystyczny | opisane, progi bez zmian; propozycję ograniczenia K6a/K6b do pary głównej **odrzucono** (opcja diagnozy w LV2b) |
| 7 | brak reguły ziarna dla LV2b | statystyczny | ziarno `20261017` (recenzent proponował to samo ziarno) |
| 8 | drobiazgi: opóźnienie NW 7 tylko do n = 2 262; „17 przekroczeń”; „z sześciu”; flaga P-a z surowej mocy; K-b w praktyce kontrola pozytywna; godzina commitu | statystyczny | poprawione w README i w kodzie (flaga P-a z mocy po wygładzeniu) |
| 9 | `przetworz_panel` zmieniał stan wspólnego `SeedSequence` | kod | `_potomne` (to samo, co `spawn`, bez zmiany stanu), test przypięcia ziaren |
| 10 | test przecieku zaburzał tylko środek bloku | kod | testy poszerzone (patrz „Prognozy”) |
| 11 | zbyt luźny strażnik `start` | kod | strażnik: prognoza HAR musi być określona od początku okresu oceny |
| 12 | błędny opis U w wydruku | kod | poprawiony |
| 13 | błędne zdania README o backcaście i o ziarnach | kod | poprawione |
| 14 | 53 luki w testach (mutanty, których nikt nie zauważył) | mutacyjny | 23 nowe funkcje testowe (42 przypadki) |
| 15 | okablowanie reguły rundy (W3/W4 po kodzie), kolejność kolumn STAT/DIAG, domyślne wartości cudzych funkcji, nieznana `bramka`, wersje środowiska, `--zapisz` | architektura | kod i testy |

**Co się zmieniło w regułach (po fakcie).** Tylko jedno: `dotyczy` w regule P (ustalenie 1). **Nie zmieniły się**:
progi liczbowe, prognozy, generator, komórki, liczba paneli, ziarno rejestrowe, reguła K, reguła rundy. Nowa
reguła P zamienia wyłącznie WSTRZYMANE na NIE (własność sprawdzona w teście). Doszły reguły operacyjne:
flaga „blisko progu”, ziarno LV2b, warunki przeniesienia 1–5, nazwa C2.

**Czego nie przyjęto.** (a) Ograniczenia K6a/K6b do pary głównej `ewma94_t5 → garch_tnu`: uczyniłoby K6a mniej
surowym po obejrzeniu pilotaży (zostaje jako opcja diagnozy w LV2b). (b) „To samo ziarno w LV2b”: wybrano nowe,
żeby poprawka nie była dopasowana do obejrzanych paneli. (c) Asercji NaN w `przetworz_panel`: zamiast tego
mikro-test i sprawdzenie NaN na zapisanych wynikach po przebiegu.

**Pilotaże recenzentów (poza rejestrem, inne ziarna, bez wpływu na jakikolwiek licznik).** Recenzent
statystyczny: 100 paneli, ziarno 4711; recenzent kodu: 60 paneli, ziarno 424242. Ziarno rejestrowe nie było
użyte. Komórka C1, p = 1 %:

| wielkość | pilotaż 480 | recenzent statystyczny (100) | recenzent kodu (60) |
|---|---|---|---|
| K1 rozmiar na wyroczni | 3,1 % | 8,0 % (powyżej 7,5 %) | 3,3 % |
| K-a rozmiar `garch_tnu` | 7,9 ± 1,2 % | 12,0 % | 11,7 ± 4,2 % |
| K-b moc | 99,4 % | 100 % | 100 % |
| P-a MDE | 0,140 | 0,141 | 0,134 |
| P-b moc | 35,2 % | 47,0 % | 36,7 % |
| wynik reguł K / P / rundy | TAK / NIE / MIERZALNA | WSTRZYMANE / WSTRZYMANE / WSTRZYMANA | NIE / WSTRZYMANE / WSTRZYMANA |

Wyniki reguł w tabeli pochodzą z kodu z `73fff28` (przed zmianą `dotyczy`); przy p = 1 % nowa reguła P dałaby
to samo, bo w obu pilotażach zawiodła K4 (8,0 % i 1,7 %). Przy p = 5 % K wyszło MIERZALNE w obu pilotażach recenzentów (K-a 7,0 % i 5,0 %); P-a MDE 0,127 i 0,130, P-b
84,0 % i 78,3 %. Trzy pilotaże razem (640 paneli): K-a przy 1 % **57/640 = 8,9 ± 1,1 %**; P-b przy 5 % **77,3 ± 1,7 %**.
Małe pilotaże mają duże SE (3–4 pp), więc pojedyncze porażki kontroli (K1 8,0 %; K4 1,7 %; K6b 0,0 %) to w
dużej mierze szum, ale pokazują, że w przebiegu rejestrowym kontrola może zawieść przypadkiem.

**Incydent W14 (błąd recenzenta mutacyjnego, ujawniony).** Jedna z mutacji sprawiła, że test działania
(`--smoke`) zaczął liczyć pełną konfigurację rejestrową (5 000 paneli, ziarno rejestrowe) na kopii poza
repozytorium, aż do przerwania po 420 s. Wynik nie został zapisany ani nigdy zobaczony; oryginalny kod nie
został ruszony. Od tego czasu test-strażnik (autouse) powoduje błąd w `uruchom` przy więcej niż 100 panelach
(mutacja W14 jest zabijana w 14 s). Jest to jedyny przypadek uruchomienia konfiguracji rejestrowej przed
przebiegiem rejestrowym i **żaden jej wynik nie został obejrzany**.

**Mutacje (kopia poza repozytorium).** Pierwsza seria: 216 mutantów względem testów z `73fff28`; 159 zabitych,
57 przeżyło (4 równoważne, czyli bez zmiany zachowania, i 53 prawdziwe luki w testach). Recenzent zaproponował
23 funkcje testowe (42 przypadki), które zabiły 53 z nich; wszystkie dodano. Ostatnia seria, na końcowym
kodzie: **249 mutantów; 243 zabite asercją, 2 zabite błędem (C16, D10), 4 przeżyły i są równoważne** (M01 i M06:
strata równa 0 przy r = v w obu zapisach; S08: dłuższy filtr dodaje tylko σ² dla dnia, którego nikt nie
czyta; D06: uporządkowane `imap` nie zależy od `chunksize`). Mutacje sprawdzają, czy testy zauważą zepsuty kod;
nie sprawdzają, czy wniosek statystyczny jest dobry.

**Stan testów po przeglądzie.** `tests/test_lv2.py`: 131 funkcji testowych, 241 przypadków (w
`009204b`: 88 i 159); cały zestaw repo: 1115 zebranych przypadków, z tego 1 pominięty (brak
`shellcheck` w środowisku), reszta zielona; ruff i black czyste. Uczciwie: w drugim pełnym
przebiegu jeden test czasowy spoza LV2 (`tests/test_automat.py`, sygnał zabijający krok automatu) przekroczył
limit 30 s pod obciążeniem maszyny; w izolacji jest zielony (3 z 3 przebiegów), a pierwszy pełny przebieg był
w całości zielony.

**Poprawki samego README** (stwierdzone przez recenzentów): godzina commitu kodu 17:56:29 (nie 17:56:28); „ok. 17
przekroczeń” → co najwyżej 15 (jednostronny) i 7 (dwustronny, po mniejszej stronie) z 999, poziom ≤ 4,8 %; „zapas 5,5 SE”
usunięty; zdanie o ziarnie rejestrowym (użyte też w mikro-teście i teście przypięcia ziaren); „z sześciu” (w C2 z
pięciu); opóźnienie NW 7 tylko dla n od 1 241 do 2 262; zdanie o backcaście (ta sama wartość liczbowa, inna
konwencja startu filtra); „kod i testy z `009204b`” (commit `73fff28` zmienił też dokumentację dwóch plików
kodu i ścieżki w karcie); luki w osi czasu; liczby testów.

**Odroczone drobiazgi (po przebiegu, bez wpływu na wynik):** zdublowane `POZIOMY` i `NU`; martwa stała `N_DNI`;
kolejność argumentów `fz0` i `straty_dzienne`; `Zrodla.pierwsze(k)` dla k większego niż liczba monet; definicja
trafienia w `fz0` (`r <= v`) kontra `r < q` w teście zbiorczym (różnią się tylko przy równości); podział
`run_lv2.py` (dziś ok. 990 linii).

**Czego przegląd nie pokrył.** Niezależnej reimplementacji testu zbiorczego i estymatora GARCH przez recenzenta
statystycznego; symulacji potwierdzającej efekt estymacji w DM (hipoteza z K6a); niezależnego przeliczenia C2,
testu B i HAR przez recenzenta kodu; warstwy wydruku i reguł w pełni (część zamknięta nowymi testami). Dlatego
po przebiegu: (i) przeliczenie niezależną drogą (krok 4), (ii) sprawdzenie NaN w C1 na zapisanych wynikach paneli.

### Co zrobić, gdy wynik jest NIEMIERZALNA albo WSTRZYMANA (alternatywy, nie ruchy tej rundy)

Każda alternatywa to nowe pytanie z własnym licznikiem (PRD §11.4) i własną pre-rejestracją:

1. **Raport opisowy bez werdyktu:** odsetek trafień, średni stosunek strat ponad VaR do ES, strata FZ0
   obok siebie dla prognoz, bez „zdał / nie zdał”.
2. **Dłuższa historia albo więcej monet** (top-50, FR-01): komórka C1 z większym n lub K; mapa z LV1/LV2 jako
   opis do planowania.
3. **Inna miara niż test zbiorczy:** np. test warunkowy z tzw. czynnikiem skalującym albo test oparty na
   oczekiwanym niedoborze na dłuższym horyzoncie — wymaga osobnego laboratorium.
4. **Tylko poziom, który przeszedł** (np. wyłącznie p = 1 %, jeśli 5 % jest NIEMIERZALNA), albo zmierzyć
   faktyczną zależność koszyka (VR) na prawdziwych danych i dopiero wtedy wybrać komórkę.

### Ograniczenia

- **Generator ma tylko zależność gaussowską przez wspólny czynnik** (stałe ρ; brak zależności ogonowej
  i wspólnej zmienności), więc VR dziennej sumy trafień to ok. 3,2 (1 %) i 6,4 (5 %); prawdziwe krachy są
  bardziej synchroniczne. Wynik to raczej górne oszacowanie mocy; stąd warunek „Zależność”.
- **Model poprawnie określony to najlepszy przypadek.** GARCH-t jest prawdziwą klasą modelu generatora, więc
  K-a mierzy tylko rozmiar testu przy błędzie estymacji parametrów, bez błędu specyfikacji. Na prawdziwych
  danych model jest zawsze w jakimś stopniu źle określony; TAK w K oznacza „test nie myli się, gdy model jest
  dobry” (warunek konieczny), nie „test wykryje każdy błąd specyfikacji”.
- **K1/K-a dotyczą klasy GARCH-t(ν̂) z refitem co 30 dni.** Rozmiar dla innych klas modeli (np. HAR jako prognoza
  VaR, modele z innymi innowacjami) jest nieznany.
- **Test DM bez poprawki HLN i z jednym opóźnieniem HAC (7).** K6 sprawdza błąd HAC na parach
  realistycznych, ale po wyśrodkowaniu na średniej po panelach (to nie jest rozmiar absolutny). Przy n = 1 600
  poprawka HLN jest pomijalna, ale to założenie, nie pomiar.
- **Reszty „w próbie” dla ogonów empirycznych GARCH** i ok. 16 trafień na monetę w ogonie 1 % → ogony
  empiryczne są szumne; to opis, nie kryterium.
- **Pilotaż nie był ślepy** (K-a, K7, K6, P-a i W1–W4 ustalono po jego obejrzeniu). Zmiana reguły P po przeglądzie
  (`dotyczy`) też jest po fakcie. Przegląd zrobiły modele, nie ludzie.
- **Efekt estymacji w DM (hipoteza).** K6a ≈ 9–12 % na parach realistycznych sugeruje, że błąd HAC jest za
  mały przy prognozach z estymowanymi parametrami (West 1996); nie zbadano tego symulacją. Dla wniosku NIE
  z reguły P to nie ma znaczenia (liberalny test tylko zawyża moc), dla TAK — bramkuje K6a.
- **C2 (15 monet) to warunek Zakresu (b), nie werdykt rundy.** W pilotażu K-a w C2 przy p = 1 % wyniosło 9,4 %, bliżej progu niż w C1. Jeśli
  w przebiegu rejestrowym C2 nie da TAK, populacja 15 monet (F2-1b) nie spełnia warunku „Zakres (b)”; wtedy
  pierwsza runda na danych wymaga ≥ 20 monet (np. top-50 z danymi od 2021).
- Panel ma 2 100 dni, a refit idzie od 400 dni; krótsza historia (np. monety z ok. 600 dniami) jest poza
  zakresem tego laboratorium.

### Liczniki

- **0 wariantów**, POZA licznikami: dane syntetyczne, kalibracja przyrządu.
- Wspólny rejestr odczytów alpha (`odczyty_historii.csv`, N = 40): **bez zmian** — żaden zwrot strategii nie
  jest odczytywany na historii.
- Licznik „ryzyko ogona (VaR/ES) 2021+” (PRD §11.4): **bez zmian (0)** — nie testujemy żadnej prognozy VaR/ES
  na prawdziwych danych. Licznik „zmienność 2021+”: bez zmian (1, F2-1b).
- R15: LLM nie występuje w żadnej ścieżce decyzyjnej; przyrząd i skrypt są deterministyczne (R19).

### Decyzje wykonawcy (poza zleceniem) — do przeglądu

1. **Dwie reguły (K i P) i reguła rundy „K albo P”.** Karta pytała o (a), (b), (c); wybrany podział daje
   odpowiedź na (c) bez mieszania pytania bezwzględnego z porównawczym.
2. **K-a ≤ 10 %** (karta nie podała progu), wybrane po pilotażu 64 paneli; patrz uzasadnienie.
3. **K6 jako dwie bramki jednostronne** (po pilotażu 480; zmienia przewidywany wynik P przy 5 % z
   WSTRZYMANE na NIE, nie zmienia werdyktu rundy).
4. **Komórki C1 i C2:** C1 decyduje o werdykcie rundy, C2 jest sprawdzianem populacji F2-1b i warunkiem
   „Zakres (b)” (karta: „n = 1 600 i 1 700 z F2-1b”); warunek „Zakres (b)” jest nowy, a po przeglądzie C2
   przestała być nazywana „opisem” (dziś to jedyny osiągalny Zakres).
5. **HAR i ogony empiryczne tylko jako opis** (karta: „HAR jako opis”, „ogon t5 i kwantyl empiryczny”).
6. **Własny estymator GARCH-t** (ok. 1 140 dopasowań na panel × 5 000 paneli; pakiet `arch` byłby za wolny),
   zwalidowany pakietem `arch` w testach.
7. **Data katalogu 2026-10-07** (karta wskazywała 2026-10-06 z dnia pisania kodu).
8. Żaden z punktów 2–4 nie zmienia werdyktu rundy w pilotażu 480 (MIERZALNA przez K), więc nie jest punktem
   decyzyjnym dla użytkownika; wszystkie są do przeglądu.
9. **Po przeglądzie, po fakcie:** (a) `dotyczy` w regule P (K6 i K7 bramkują tylko P-b; zmienia wyłącznie
   WSTRZYMANE → NIE); (b) C2 jako warunek Zakresu (b) zamiast „opisu”; (c) ziarno LV2b `20261017` (recenzent
   proponował to samo ziarno); (d) reguła flagi „blisko progu”; (e) warunki przeniesienia 1–5 (ρ_h zamiast VR,
   dokładna komórka, jedno p albo korekta); (f) opcjonalny `--zapisz` i wymuszenie jednego wątku BLAS; (g) `_potomne`
   zamiast `spawn` na stanie wspólnym. **Nie przyjęto:** ograniczenia K6a/K6b do pary głównej (zostaje jako
   opcja diagnozy w LV2b). Punkty 9a–9d zmieniają tylko to, co wolno z wyniku wnioskować; **do przeglądu użytkownika**.

## Przebieg rejestrowy (fakty wykonania)

Polecenie (skrypt startowy leży poza repozytorium; zmienne `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` i
`MKL_NUM_THREADS` ustawione na 1, żeby procesy nie dzieliły rdzeni):

```
.venv/bin/python -m symulacje.run_lv2 --workers 16 --zapisz data/lv2_wyniki_paneli.npz \
    > raw_output.txt 2> stderr_przebiegu.txt
```

| co | wartość |
|---|---|
| kod | commit `24c8863` (przegląd przed przebiegiem). Przy starcie HEAD był `9acb8b9`; od `24c8863` zmieniły się tylko README, karta i STATUS: `git diff 24c8863 9acb8b9 -- symulacje tests miara` jest puste (na HEAD tej pracy też) |
| ziarno | `20261016`; wynik nie zależy od liczby procesów (R19) |
| start / koniec | 2026-10-07 10:21:45 → 10:53:19 UTC |
| czas | 1 894 s (16 procesów, 6,1 s na panel na rdzeń); źródło: `stderr_przebiegu.txt` (dziennik postępu na stderr, poza wydrukiem wyniku) |
| kod wyjścia | 0 (odczytany z pliku z kodem wyjścia, nie z powiadomienia narzędzia) |
| wydruk | `raw_output.txt`, 466 wierszy, sha256 `5d10ea001a0933a96fb0cf560a9c2152f471f9e0da1de26062dcc4c4cd549d1c`; zatwierdzony bez zmian w commicie `eb1e0fc` (10:53:32 UTC), przed jakąkolwiek interpretacją |
| zapis wyników paneli | `data/lv2_wyniki_paneli.npz`, 24 254 902 B, sha256 `f0c140529e732d6db1f4bcd1e19db859f0726e5e5119280f461b39a9185c29d7`; poza gitem (`data/`) |
| wersje | Python 3.12.3, numpy 2.5.3, scipy 1.18.1, pandas 3.0.6 |
| prawdziwe dane | żadne; licznik „ryzyko 2021+” bez zmian (0) |

**Pierwszy start został przerwany (R4: jawność).** O 10:19:27 UTC, 13 s po commicie z hashem przeglądu,
uruchomiłem ten przebieg tym samym poleceniem jako zadanie w tle narzędzia powłoki. Jego limit czasu (10 minut)
mógł zabić pracę trwającą pół godziny, więc po ok. 30 s (10:19:57) sam przerwałem proces sygnałem SIGTERM i
uruchomiłem przebieg od nowa jako proces odłączony od powłoki: to samo polecenie, to samo ziarno (10:21:45).
Z pierwszego startu nikt nie widział żadnego wyniku: został wydruk z samym nagłówkiem, bez pliku z wynikami
paneli, a dziennik błędów miał 546 wierszy: 16 raportów `BrokenPipeError`, po jednym z każdego z 16 procesów
roboczych, które straciły proces nadrzędny, i ostrzeżenie o 6 niezwolnionych semaforach. Przebieg jest
deterministyczny i nic z pierwszego startu nie obejrzano, więc nie było wyboru „który przebieg wziąć”.
Po moim zabiciu narzędzie powłoki zgłosiło „zakończone (kod 0)”; to kończyła się powłoka opakowująca, więc nie
uznałem tego za wynik. Kod wyjścia pierwszego startu (143, czyli zabity sygnałem) odczytałem z pliku z kodem
wyjścia o 10:21:27, zanim drugi start go nadpisał; kod drugiego startu (0) odczytałem z tego samego pliku po
jego zakończeniu. Poza repozytorium zachowałem tylko dziennik błędów i znacznik czasu pierwszego startu; plik z
kodem 143 i wydruk z samym nagłówkiem nadpisał drugi start, więc kodu 143 nie da się dziś sprawdzić z pliku.

**Usterka kosmetyczna wydruku.** Etykieta kryterium P-a w wydruku zawiera nazwę stałej z kodu („siatka X_GRID”)
zamiast wartości siatki (4 wystąpienia: wiersze 34, 61, 90 i 117 `raw_output.txt`; źródło `symulacje/run_lv2.py`,
wiersz 611). Żadna liczba nie jest dotknięta, a siatka (0; 0,05; 0,10; 0,15; 0,20; 0,30) jest wypisana w sekcji
„MOC NA SIATCE” (wiersz 135 `raw_output.txt`); sekcja „OPIS” podaje tę samą siatkę jako mnożniki prognoz
zaniżonych (`zan05…zan30` = σ × 0,95 … 0,70). Kodu nie poprawiam: poprawka po przebiegu rejestrowym zmieniałaby
kod, który dał wynik; zostaje do następnej zmiany kodu.

## Wynik

Tabele poniżej są generowane skryptami `weryfikacja/tabele_wynik.py` i `weryfikacja/tabele_kryteria.py`
wyłącznie z `raw_output.txt` (bez ręcznego przepisywania). Przecinek jest znakiem dziesiętnym, „±” to błąd
standardowy (SE) odsetka paneli (przy 5 000 paneli i 5 % ok. 0,3 pp), „pp” to punkt procentowy. C1 = 20 monet ×
1 600 dni (komórka główna, werdykt rundy), C2 = 15 monet × 1 700 dni (warunek Zakresu (b)); p to poziom VaR.

### Kryteria z pre-rejestracji

| kryterium (próg) | C1, p = 1 % | C1, p = 5 % | C2, p = 1 % | C2, p = 5 % |
|---|---:|---:|---:|---:|
| K1 — rozmiar na wyroczni (2,5–7,5 %) | 3,9 % — TAK | 3,6 % — TAK | 3,8 % — TAK | 3,6 % — TAK |
| K2 — moc wobec σ − 30 % (≥ 95 %) | 100,0 % — TAK | 100,0 % — TAK | 100,0 % — TAK | 100,0 % — TAK |
| K7a — średnia ν̂ (4,0–6,5; prawda 5) | 5,24 — TAK | 5,24 — TAK | 5,24 — TAK | 5,24 — TAK |
| K7b — średnia α̂ + β̂ (0,95–0,995; prawda 0,98) | 0,972 — TAK | 0,972 — TAK | 0,972 — TAK | 0,972 — TAK |
| K7c — dopasowania bez zbieżności (≤ 2 %) | 0,0 % — TAK | 0,0 % — TAK | 0,0 % — TAK | 0,0 % — TAK |
| K7d — dopasowania przy granicy zakresu (≤ 5 %) | 2,2 % — TAK | 2,2 % — TAK | 2,2 % — TAK | 2,2 % — TAK |
| **K-a — rozmiar, GARCH-t estymowany (≤ 10 %)** | 8,2 % — TAK | 5,5 % — TAK | 8,0 % — TAK | 5,0 % — TAK |
| **K-b — moc, GARCH-t estymowany ze σ − 10 % (≥ 80 %)** | 98,8 % — TAK | 99,5 % — TAK | 98,4 % — TAK | 99,6 % — TAK |
| **reguła K** | **MIERZALNE** | **MIERZALNE** | **MIERZALNE** | **MIERZALNE** |
| K4 — rozmiar DM, pary zerowe, najgorsza (2,5–7,5 %) | 5,3 % — TAK | 4,7 % — TAK | 5,4 % — TAK | 4,2 % — TAK |
| K5 — moc DM, σ wyroczni − 30 % (≥ 95 %) | 100,0 % — TAK | 100,0 % — TAK | 100,0 % — TAK | 100,0 % — TAK |
| K6a — rozmiar DM po wyśrodkowaniu, pary realistyczne, największy (≤ 7,5 %) | 9,1 % — NIE | 10,1 % — NIE | 8,1 % — NIE † | 10,1 % — NIE |
| K6b — jw., najmniejszy (≥ 2,5 %) | 3,7 % — TAK | 2,7 % — TAK † | 3,9 % — TAK | 2,7 % — TAK † |
| **P-a — MDE zaniżenia σ, DM-FZ0 (≤ 0,10)** | 0,139 — NIE | 0,130 — NIE | 0,140 — NIE | 0,128 — NIE |
| **P-b — moc DM-FZ0, ewma94 → garch_tnu (≥ 80 %)** | 35,6 % — NIE | 73,3 % — NIE | 33,8 % — NIE | 73,1 % — NIE |
| **reguła P** | **NIEMIERZALNE** | **NIEMIERZALNE** | **NIEMIERZALNE** | **NIEMIERZALNE** |
| **reguła rundy** | **MIERZALNA** (K bezwzględne) | **MIERZALNA** (K bezwzględne) | **MIERZALNA** (K bezwzględne) | **MIERZALNA** (K bezwzględne) |

† = „w granicach 2 SE od progu” (flaga z pre-rejestracji). K7a–d to kontrola estymatora: jedna diagnoza ze
wszystkich dopasowań, więc jest taka sama w każdej komórce i przy każdym p.

**Wynik mechaniczny.** Reguła K: **MIERZALNE** we wszystkich czterech blokach (komórka × p). Reguła P:
**NIEMIERZALNE** we wszystkich czterech: P-a i P-b niespełnione, a kontrole K4 i K5, od których zależy to NIE,
przeszły. Reguła rundy: **MIERZALNA, tylko pytanie bezwzględne (K)**, we wszystkich czterech blokach.

**Zapasy do progów (wyliczone z wydruku; kolejność: C1 1 % / C1 5 % / C2 1 % / C2 5 %).**

- K-a (próg ≤ 10 %): 8,2 / 5,5 / 8,0 / 5,0 %, czyli zapas 1,8 / 4,5 / 2,0 / 5,0 pp, a w błędach standardowych
  4,6 / 14,1 / 5,3 / 16,1 SE. Gdyby próg wynosił 7,5 %, wynik przy 1 % byłby o 0,7 i 0,5 pp ponad progiem
  (NIE), a przy 5 % o 2,0 i 2,5 pp poniżej progu (TAK).
- K-b (próg ≥ 80 %): zapas 18,8 / 19,5 / 18,4 / 19,6 pp. K1 (dolna granica 2,5 %): zapas 1,4 / 1,1 / 1,3 / 1,1 pp,
  czyli 5,2 / 4,2 / 4,8 / 4,2 SE; wyrocznia odrzuca 3,6–3,9 %, czyli rzadziej niż nominalne 5 % (test zbiorczy
  łączy trzy składniki poprawką Bonferroniego, więc jest zachowawczy).
- P-a: moc DM-FZ0 przy zaniżeniu σ o 10 % wynosi 49,1 / 59,6 / 48,5 / 61,5 % wobec wymaganych 80 %; brakuje
  30,9 / 20,4 / 31,5 / 18,5 pp, przy SE ok. 0,7 pp. To NIE nie jest „na granicy”.
- P-b: 35,6 / 73,3 / 33,8 / 73,1 % wobec 80 %. Przy 1 % brakuje 44,4 i 46,2 pp, przy 5 % 6,7 i 6,9 pp (ok. 10
  SE; ale patrz uwaga o błędzie standardowym DM w punkcie o teście porównawczym).

**K6a zawodzi we wszystkich czterech blokach** (9,1 / 10,1 / 8,1 / 10,1 % wobec ≤ 7,5 %). To kontrola
laboratorium: w parze okno 60 → EWMA test DM po wyśrodkowaniu odrzuca zbyt często, czyli jego błąd standardowy
jest za mały. Według zapisu reguły K6a bramkuje tylko wynik TAK reguły P, więc nie zmienia wyniku NIE, który
opiera się na P-a (bramki K4 i K5). K6b przechodzi, ale przy 5 % z flagą (2,7 % wobec ≥ 2,5 %).

**Flagi.** Trzy: K6b przy C1 5 %, K6a przy C2 1 % i K6b przy C2 5 %; wszystkie na kontrolach reguły P, żadnej na
kryteriach ani kontrolach reguły K. Regułę flagi czytam ostrożnie: skoro wynik z flagą (nawet pomocniczy)
ogranicza werdykt do Caveats, to wydruk z flagami nie dostaje Ready. W tej rundzie nie ma to znaczenia dla
rozstrzygnięcia, bo werdykt jest Caveats także z innych powodów (sekcja „Werdykt”). Zgodnie z regułą nie
dosypywano paneli, nie zmieniano ziarna i nie powtarzano przebiegu.

### Test zbiorczy na prognozach

Liczby to odsetek paneli (z 5 000), w których test zbiorczy odrzuca daną prognozę; „±” to SE. Pierwsza kolumna
to średni odsetek trafień (dni, w których strata przekroczyła VaR) w C1 przy p = 1 %; cel to 1,00. Trzy wiersze
to prognozy poprawne, więc odsetek odrzuceń jest **fałszywym alarmem** (nominalnie 5 %): `wyr_t5` (prawdziwa
zmienność z generatora), `garch_t5` (zmienność oszacowana, ogon prawdziwy t5) i `garch_tnu` (zmienność i ogon
oszacowane, czyli kandydat do pierwszej rundy). Wiersze `zan…` i `garch_tnu_zan…` to prognozy celowo zaniżone
(`zan10` = σ × 0,90); odsetek odrzuceń to **moc**. Reszta wierszy jest opisowa (nie kryteria).

| prognoza | trafienia C1 p=1 % [%] | C1, p = 1 % | C1, p = 5 % | C2, p = 1 % | C2, p = 5 % |
|---|---:|---:|---:|---:|---:|
| `wyr_t5` | 1,00 | 3,9 ± 0,27 | 3,6 ± 0,26 | 3,8 ± 0,27 | 3,6 ± 0,26 |
| `zan05` | 1,21 | 46,8 ± 0,71 | 54,4 ± 0,70 | 45,8 ± 0,70 | 55,6 ± 0,70 |
| `zan10` | 1,46 | 97,9 ± 0,20 | 99,2 ± 0,13 | 97,7 ± 0,21 | 99,4 ± 0,11 |
| `zan15` | 1,77 | 100,0 ± 0,00 | 100,0 ± 0,00 | 100,0 ± 0,00 | 100,0 ± 0,00 |
| `zan20` | 2,16 | 100,0 ± 0,00 | 100,0 ± 0,00 | 100,0 ± 0,00 | 100,0 ± 0,00 |
| `zan30` | 3,26 | 100,0 ± 0,00 | 100,0 ± 0,00 | 100,0 ± 0,00 | 100,0 ± 0,00 |
| `okno60_t5` | 1,39 | 97,1 ± 0,24 | 93,4 ± 0,35 | 96,6 ± 0,25 | 94,0 ± 0,34 |
| `ewma94_t5` | 1,28 | 78,5 ± 0,58 | 78,8 ± 0,58 | 77,4 ± 0,59 | 80,0 ± 0,57 |
| `garch_t5` | 1,03 | 5,0 ± 0,31 | 5,0 ± 0,31 | 4,9 ± 0,31 | 5,0 ± 0,31 |
| `garch_tnu` | 1,04 | 8,2 ± 0,39 | 5,5 ± 0,32 | 8,0 ± 0,38 | 5,0 ± 0,31 |
| `garch_tnu_zan10` | 1,51 | 98,8 ± 0,16 | 99,5 ± 0,10 | 98,4 ± 0,18 | 99,6 ± 0,09 |
| `garch_tnu_zan20` | 2,23 | 100,0 ± 0,00 | 100,0 ± 0,00 | 100,0 ± 0,00 | 100,0 ± 0,00 |
| `har_t5` | 1,15 | 41,4 ± 0,70 | 36,1 ± 0,68 | 40,1 ± 0,69 | 37,9 ± 0,69 |
| `okno60_ep` | 1,02 | 44,4 ± 0,70 | 60,3 ± 0,69 | — | — |
| `ewma94_ep` | 1,01 | 4,1 ± 0,28 | 4,6 ± 0,30 | — | — |
| `garch_ep` | 1,05 | 8,3 ± 0,39 | 6,3 ± 0,34 | — | — |
| `okno60_ec` | 1,12 | 54,0 ± 0,70 | 60,3 ± 0,69 | 52,8 ± 0,71 | 61,3 ± 0,69 |
| `ewma94_ec` | 1,10 | 17,1 ± 0,53 | 5,4 ± 0,32 | 14,7 ± 0,50 | 4,9 ± 0,31 |
| `garch_ec` | 1,13 | 28,9 ± 0,64 | 8,3 ± 0,39 | 26,4 ± 0,62 | 7,8 ± 0,38 |

Wiersze `*_ep` (ogon z reszt wszystkich monet) liczono tylko w C1. „—” = nie liczono.

- **Prognoza poprawna.** Wyrocznia odrzuca 3,6–3,9 % paneli, mniej niż 5 %, bo test łączy trzy składniki
  poprawką Bonferroniego (to kontrola K1: dolna granica 2,5 %, zapas 1,1–1,4 pp). `garch_t5` odrzuca 4,9–5,0 %,
  a `garch_tnu` 8,2 / 5,5 / 8,0 / 5,0 % (C1 1 %, C1 5 %, C2 1 %, C2 5 %).
- **Zaniżenie σ.** O 5 % test widzi w 46–56 % paneli, o 10 % w 97,7–99,4 %, o 15 % i więcej we wszystkich.
  Najmniejsze zaniżenie wykrywane z mocą 80 % (MDE) to 0,082 / 0,079 / 0,083 / 0,078. Na modelu estymowanym moc
  przy zaniżeniu 10 % (kryterium K-b) wynosi 98,8 / 99,5 / 98,4 / 99,6 %, czyli o 0,2–0,9 pp więcej niż na
  wyroczni (97,9 / 99,2 / 97,7 / 99,4 %); estymacja nie osłabia tu testu.
- **Skąd nadwyżka fałszywych alarmów.** Model prawdziwy → ta sama prognoza z σ oszacowanym (`garch_t5`) → z
  σ i ν oszacowanymi (`garch_tnu`). W nawiasie przyrost w pp.

| komórka, p | wyrocznia | `garch_t5` (σ̂) | `garch_tnu` (σ̂ i ν̂) |
|---|---:|---:|---:|
| C1, 1 % | 3,9 | 5,0 (+1,1) | 8,2 (+3,2) |
| C1, 5 % | 3,6 | 5,0 (+1,4) | 5,5 (+0,5) |
| C2, 1 % | 3,8 | 4,9 (+1,1) | 8,0 (+3,1) |
| C2, 5 % | 3,6 | 5,0 (+1,4) | 5,0 (+0,0) |

  Przy VaR 1 % ponad dwie trzecie nadwyżki robi oszacowanie grubości ogona ν (średnie ν̂ = 5,236 przy prawdziwym
  5; poziom trwałości α̂ + β̂ = 0,9720 przy prawdziwym 0,98; bez zbieżności 0,00 %, czyli 90 z 5,7 mln dopasowań,
  nie więcej niż jedno na panel; przy granicy zakresu 2,23 %; to kontrola K7). Przy VaR 5 % ogon prawie nie ma
  znaczenia.
- **Prognozy rozsądne, ale nieidealne.** Okno 60 dni odrzucane jest w 97,1 / 93,4 % paneli, EWMA w 78,5 / 78,8 %
  (C2: 96,6 / 94,0 i 77,4 / 80,0 %), HAR w 41,4 / 36,1 %. Test zbiorczy nie nadaje się więc do oceny tych prognoz
  przy takim n; to przesądza o warunku 3 przeniesienia (sekcja „Werdykt”).

### Składniki testu zbiorczego (komórka C1)

Test zbiorczy odrzuca, gdy któryś z trzech składników ma p < α/3. **A** pyta o liczbę trafień (za dużo lub za
mało), **B** o ich skupianie w czasie (trafienia „idą kupą”), **C** o dotkliwość strat ponad VaR w porównaniu z
ES. Liczby to odsetek paneli, w których dany składnik sam odrzuca; kolumna „zbiorczy” to odsetek odrzuceń całego
testu.

| prognoza | p | A (pokrycie) | B (skupienie) | C (dotkliwość) | zbiorczy |
|---|---|---:|---:|---:|---:|
| `wyr_t5` | 1 % | 1,4 | 1,8 | 1,4 | 3,9 ± 0,27 |
| `wyr_t5` | 5 % | 1,3 | 1,6 | 1,5 | 3,6 ± 0,26 |
| `garch_t5` | 1 % | 1,9 | 1,8 | 2,8 | 5,0 ± 0,31 |
| `garch_t5` | 5 % | 1,9 | 1,8 | 2,7 | 5,0 ± 0,31 |
| `garch_tnu` | 1 % | 2,9 | 2,0 | 6,1 | 8,2 ± 0,39 |
| `garch_tnu` | 5 % | 1,8 | 2,0 | 3,0 | 5,5 ± 0,32 |
| `ewma94_t5` | 1 % | 66,2 | 2,7 | 77,9 | 78,5 ± 0,58 |
| `ewma94_t5` | 5 % | 60,6 | 3,0 | 78,2 | 78,8 ± 0,58 |
| `okno60_t5` | 1 % | 91,4 | 43,9 | 96,2 | 97,1 ± 0,24 |
| `okno60_t5` | 5 % | 69,2 | 54,7 | 89,2 | 93,4 ± 0,35 |
| `okno60_ep` | 1 % | 0,9 | 43,6 | 1,5 | 44,4 ± 0,70 |
| `okno60_ep` | 5 % | 0,6 | 59,8 | 1,0 | 60,3 ± 0,69 |
| `ewma94_ep` | 1 % | 0,6 | 2,9 | 1,0 | 4,1 ± 0,28 |
| `ewma94_ep` | 5 % | 0,4 | 3,8 | 0,7 | 4,6 ± 0,30 |
| `har_t5` | 1 % | 19,7 | 20,0 | 29,0 | 41,4 ± 0,70 |
| `har_t5` | 5 % | 11,5 | 21,3 | 20,8 | 36,1 ± 0,68 |

Odczyt opisowy (nie wynik rundy; nie badano tego osobnym eksperymentem):

- **`garch_tnu` przy 1 %:** nadwyżka siedzi w składniku C (6,1 %, wyrocznia 1,4 %), a A to tylko 2,9 %. Zgadza się
  to z rozbiciem wyżej: poziom zmienności jest prawie dobry, myli się kształt ogona.
- **EWMA:** odrzucana przez A (66,2 / 60,6 %) i C (77,9 / 78,2 %), a nie przez B (2,7 / 3,0 %): zmienność
  nadąża, ale ogon t5 jest dla reszt EWMA za lekki (prognoza zbyt rzadko przewiduje duże straty; trafień jest
  1,28 % zamiast 1 %). Z ogonem z danych (`ewma94_ep`) wszystkie trzy składniki są w normie (0,6 / 2,9 / 1,0 %
  przy 1 %). To najciekawszy trop opisowy z tej rundy; jego sprawdzenie wymaga osobnej karty i własnego
  licznika.
- **Okno 60 dni:** wysokie B (43,9 / 54,7 %) także z ogonem z danych (`okno60_ep`: 43,6 / 59,8 %). Trafienia
  skupiają się w czasie, bo okno zbyt wolno nadąża za zmiennością; ogon tego nie naprawia.
- **HAR** (istniejący moduł `modele.zmiennosc`, tylko opisowo): wszystkie trzy składniki podwyższone (A 19,7 /
  11,5 %, B 20,0 / 21,3 %, C 29,0 / 20,8 %).

### Zależność między monetami (R12): VR i ρ_h

VR to stosunek wariancji dziennej liczby trafień na wszystkich monetach do wariancji, jaka byłaby, gdyby monety
były niezależne (VR = Var(S_t)/(K p (1 − p)); 1 = brak zależności). Rośnie z liczbą monet, więc do porównań
służy ρ_h = (VR − 1)/(K − 1), czyli średnia korelacja trafień dwóch monet w tym samym dniu. „Monety
niezależne” to K/VR, wartość orientacyjna: tyle niezależnych monet dałoby taką samą zmienność dziennej liczby
trafień.

| komórka, p | VR `wyr_t5` | ρ_h `wyr_t5` | VR `garch_tnu` | ρ_h `garch_tnu` | monety niezależne (K/VR) |
|---|---:|---:|---:|---:|---:|
| C1, 1 % | 3,01 | 0,1058 | 3,17 | 0,1142 | 6,3 z 20 |
| C1, 5 % | 6,31 | 0,2795 | 6,36 | 0,2821 | 3,1 z 20 |
| C2, 1 % | 2,48 | 0,1057 | 2,60 | 0,1143 | 5,8 z 15 |
| C2, 5 % | 4,92 | 0,2800 | 4,95 | 0,2821 | 3,0 z 15 |

ρ_h jest w C1 i C2 prawie takie samo (0,114 i 0,282 dla `garch_tnu`), więc VR rośnie z K, a ρ_h nie. Przy
zależności ustawionej w laboratorium (ρ = 0,8: korelacja szoków monet przez wspólny czynnik rynkowy) 20 monet
niesie o trafieniach tyle informacji co 3–6 niezależnych: „20 monet ≠ 20 obserwacji” (R12). To wartość, z którą
warunek 2 przeniesienia każe porównać dane. Pilotaż 480 paneli dał dla `garch_tnu` VR 3,20 i 6,36 (C1), czyli
ρ_h 0,116 przy 1 % i 0,282 przy 5 %; od wartości rejestrowych różnią się o 0,002 i 0,000. Tekst pre-rejestracji
(warunek 2) podaje dla 5 % „≈ 0,284”; to się nie zgadza z wydrukiem pilotażu (VR 6,36 daje 0,282). Jest to
nieścisłość bez skutku, bo warunek 2 każe liczyć ρ_h z VR wydrukowanego w przebiegu rejestrowym (tabela wyżej), a
nie z pilotażu; tekstu pre-rejestracji nie poprawiam.

### Test porównawczy (Diebold–Mariano na stracie FZ0), komórka C1

Strata dnia to średnia po monetach (R12). Różnica Δ = strata A − strata B; t = średnia Δ / błąd HAC
(Newey–West, opóźnienie 7); **t > 0 znaczy, że B jest lepsza**. „B lepsza” to odsetek paneli z t > 1,96, „A
lepsza” z t < −1,96; d̄ to średnia Δ po panelach, t to średnie t. W pełnym wydruku jest też strata PINB (strata
kwantylowa samego VaR) i komórka C2; tu tylko FZ0 w C1.

| porównanie (strata FZ0) | p = 1 %: B lepsza / A lepsza [%] | d̄ | t | p = 5 %: B lepsza / A lepsza [%] | d̄ | t |
|---|---:|---:|---:|---:|---:|---:|
| **koszt estymacji** (prognoza estymowana A wobec wyroczni B) | | | | | | |
| `okno60_t5` wobec wyroczni | 100,0 / 0,0 | +0,09046 | +4,53 | 100,0 / 0,0 | +0,06262 | +5,68 |
| `ewma94_t5` wobec wyroczni | 84,8 / 0,0 | +0,03037 | +2,68 | 95,3 / 0,0 | +0,02090 | +3,25 |
| `garch_t5` wobec wyroczni | 45,2 / 0,0 | +0,00762 | +1,85 | 77,6 / 0,0 | +0,00553 | +2,68 |
| `garch_tnu` wobec wyroczni | 64,0 / 0,0 | +0,01157 | +2,28 | 74,9 / 0,0 | +0,00523 | +2,58 |
| `har_t5` wobec wyroczni | 90,8 / 0,0 | +0,03400 | +2,91 | 98,8 / 0,0 | +0,02308 | +3,64 |
| **pary realistyczne** (A → B) | | | | | | |
| okno60 → ewma94 | 99,1 / 0,0 | +0,06009 | +4,09 | 100,0 / 0,0 | +0,04172 | +5,23 |
| ewma94 → garch_tnu (para główna P-b) | 35,6 / 0,0 | +0,01880 | +1,63 | 73,3 / 0,0 | +0,01567 | +2,44 |
| okno60 → garch_tnu | 99,8 / 0,0 | +0,07889 | +4,12 | 100,0 / 0,0 | +0,05740 | +5,41 |
| garch_tnu → garch_t5 | 68,1 / 0,0 | +0,00395 | +2,34 | 0,3 / 19,0 | -0,00031 | -1,02 |
| ewma94 → har | 0,9 / 3,8 | -0,00363 | -0,25 | 1,0 / 3,7 | -0,00217 | -0,27 |
| ewma94 → ewma94_ep | 4,3 / 0,1 | +0,00753 | +0,89 | 4,8 / 0,0 | +0,00450 | +0,93 |

- **Koszt estymacji.** Każda prognoza estymowana ma w oczekiwaniu większą stratę niż wyrocznia, a kolejność jest
  taka, jak przewidziano (W2): okno 60 dni (+0,0905 przy 1 %) > EWMA (+0,0304) > `garch_tnu` (+0,0116); przy 5 %
  0,0626 > 0,0209 > 0,0052. Test widzi to różnie: okno 60 odróżnia od wyroczni w 100 % paneli, EWMA w 84,8 /
  95,3 %, `garch_tnu` tylko w 64,0 / 74,9 %.
- **Para główna P-b (EWMA → GARCH-t).** Strata EWMA jest większa o 0,0188 (1 %) i 0,0157 (5 %), ale test widzi
  to w 35,6 % i 73,3 % paneli (średnie t 1,63 i 2,44). Nigdy nie wskazuje EWMA jako lepszej (0,0 %): kierunek
  jest dobry, brakuje mocy.
- **Okno 60 → EWMA i okno 60 → GARCH-t** test rozdziela w 99,1–100,0 % paneli. Gdy różnica jest duża, test
  ją widzi; kłopot dotyczy różnic rzędu kosztu estymacji GARCH-t.
- **`garch_tnu` → `garch_t5`** (ν oszacowane wobec ν znanego). Przy 1 % znajomość prawdziwego ν pomaga: `garch_t5`
  jest lepsza w 68,1 % paneli (t +2,34). Przy 5 % wynik odwraca się nieznacznie: oszacowane ν̂ jest lepsze w
  19,0 % paneli (t −1,02, d̄ −0,0003).
- **EWMA → HAR** i **EWMA → EWMA z ogonem z danych**: bez różnic widocznych dla testu (0,9 / 3,8 % i 4,3 / 0,1 %
  paneli; t −0,25 i +0,89 przy 1 %), choć w drugim przypadku ogon z danych naprawia test zbiorczy (78,5 → 4,1 %).
  Różnicę, którą test zbiorczy widzi bardzo wyraźnie, test porównawczy ledwo zauważa.

**Pary „dokładnie zerowe”** (A = wyrocznia × c_A, B = wyrocznia × c_B, c_B > 1 dobrane tak, że oczekiwane straty
są równe, więc H0 jest prawdziwa; c_A = 0,9 lub 0,8). Odsetek paneli z t > 1,96 (B lepsza) / t < −1,96 (A lepsza):

| para zerowa | C1 p = 1 %: B / A [%] | C1 p = 5 %: B / A [%] | C2 p = 1 %: B / A [%] | C2 p = 5 %: B / A [%] |
|---|---:|---:|---:|---:|
| `zero_fz0_90` | 1,2 / 4,2 | 1,8 / 3,1 | 1,3 / 4,1 | 1,6 / 2,9 |
| `zero_pinb_90` | 1,4 / 3,9 | 1,9 / 2,8 | 1,4 / 3,8 | 1,6 / 2,6 |
| `zero_fz0_80` | 1,2 / 4,0 | 1,8 / 3,1 | 1,4 / 4,0 | 1,6 / 2,8 |
| `zero_pinb_80` | 1,5 / 3,7 | 1,9 / 3,0 | 1,4 / 3,8 | 1,8 / 2,6 |

Suma obu kierunków to rozmiar testu dwustronnego (K4: najgorsza para 5,3 / 4,7 / 5,4 / 4,2 %, wymagane
2,5–7,5 %). Rozkład jest jednak **skośny**: „A lepsza” zdarza się 1,4–3,5 raza częściej niż „B lepsza” (przy
1 % 2,5–3,5 raza, np. 4,2 % wobec 1,2 %; przy 5 % 1,4–1,8 raza). Test jest więc konserwatywny w kierunku „B
lepsza”, w którym liczymy moc, i jego moc w tym kierunku jest nieco zaniżona. Skali tego efektu nie zmierzono
osobno; kryterium P-a (niżej) zawodzi z zapasem, którego on nie tłumaczy.

### Kontrola błędu standardowego testu DM (K6)

Od różnicy strat odejmujemy jej średnią po panelach, więc prawdziwa średnia wynosi 0, a odsetek paneli z
|t| > 1,96 powinien wynosić ok. 5 %, jeśli błąd HAC jest wiarygodny. W komórkach: FZ0 / PINB [%];
**pogrubienie** = poza przedziałem 2,5–7,5 %. K6a bierze największą wartość FZ0 spośród par, K6b najmniejszą.

| para realistyczna (A → B) | C1, p = 1 % | C1, p = 5 % | C2, p = 1 % | C2, p = 5 % |
|---|---:|---:|---:|---:|
| okno60 → ewma94 | **9,1** / **8,8** | **10,1** / **10,6** | **8,1** / **8,0** | **10,1** / **10,4** |
| ewma94 → garch_tnu (para główna P-b) | 3,7 / 3,5 | 2,7 / **2,4** | 4,0 / 3,7 | 2,7 / **2,4** |
| okno60 → garch_tnu | **7,8** / 7,5 | **8,4** / **8,7** | 7,4 / 7,2 | **8,5** / **8,6** |
| garch_tnu → garch_t5 | 5,7 / 5,5 | **8,5** / **8,9** | 5,6 / 5,3 | **8,3** / **8,8** |
| ewma94 → har | 3,9 / 3,7 | 3,5 / 3,6 | 3,9 / 3,7 | 3,8 / 3,4 |
| ewma94 → ewma94_ep (tylko C1) | 6,1 / 6,1 | 4,2 / 5,1 | — | — |

Para okno 60 → EWMA wyznacza K6a w każdym bloku i zawsze jest powyżej 7,5 % (8,1–10,1 %). Dwie inne pary też
bywają powyżej, ale mniej: okno 60 → GARCH-t (7,8 % przy 1 % w C1; 8,4–8,7 % przy 5 %) i GARCH-t → GARCH-t5
(8,3–8,9 % przy 5 %); nie wyznaczają K6a, bo zawsze jest większa para okno 60 → EWMA. Rozrzut d̄ po panelach
(SD) podzielony przez średni błąd HAC (se) mówi, w którą stronę błąd jest mylny: SD/se > 1 = błąd za mały
(test liberalny), < 1 = za duży (test zachowawczy). Liczby wyliczone z wydruku (komórka × p):

| SD / se | C1, 1 % | C1, 5 % | C2, 1 % | C2, 5 % |
|---|---:|---:|---:|---:|
| okno 60 → EWMA | 1,134 | 1,196 | 1,114 | 1,186 |
| EWMA → GARCH-t (para główna P-b) | 0,916 | 0,862 | 0,931 | 0,865 |
| wyrocznia × 0,9 wobec wyroczni (wiersz kryterium P-a) | 0,993 | 0,987 | 0,993 | 0,987 |

- **Okno 60 → EWMA:** rzeczywisty rozrzut jest o 11–20 % większy niż błąd HAC, stąd K6a = NIE. Zgadza się to z
  hipotezą zapisaną w pre-rejestracji (efekt estymacji, West 1996), ale jej osobno nie badano.
- **Para główna:** rzeczywisty rozrzut jest o 7–14 % mniejszy niż błąd HAC, więc test jest zachowawczy, a
  zmierzona moc (35,6 / 73,3 / 33,8 / 73,1 %) jest niższa, niż byłaby przy dokładnym błędzie. Orientacyjnie, w
  przybliżeniu normalnym z se = SD, byłoby to 44 / 81 / 41 / 80 %. To **szacunek, nie wynik**; służy tylko do
  oceny, jak blisko progu 80 % jest P-b przy 5 % (orientacyjnie na samym progu, a nie 7 pp pod nim).
- **Wiersz kryterium P-a** (wyrocznia × 0,9 wobec wyroczni) ma błąd dokładny (SD/se 0,99), więc moc 49,1 /
  59,6 / 48,5 / 61,5 % jest wiarygodna. Odpowiada średniemu t 1,91 / 2,17 / 1,89 / 2,20, czyli ok. 2 błędom
  standardowym; do mocy 80 % przy progu 1,96 trzeba średniego t ok. 2,8. Nawet gdyby próg zluzować do 1,645
  (jednostronne 5 %), moc według przybliżenia normalnego wyniosłaby ok. 60 % przy 1 % i 70–71 % przy 5 %.
  **P-a zawodzi więc z braku sygnału przy n = 1 600 dniach, nie przez wadę kalibracji testu**, i dlatego wynik
  NIE reguły P nie zależy od K6 ani od HAC.

### Moc na siatce zaniżenia σ i MDE

Odsetek paneli, w których test odrzuca prognozę z σ zaniżonym o x (σ wyroczni × (1 − x)), czyli moc testu.
Kolumna x = 0 to rozmiar (dla DM: średni rozmiar na parach zerowych, jak w K4). MDE to najmniejsze x z mocą
≥ 80 % (interpolacja liniowa). Napis „siatka X_GRID” przy P-a w wydruku to nazwa stałej z kodu (patrz „Przebieg
rejestrowy”); siatka to x ∈ {0; 0,05; 0,10; 0,15; 0,20; 0,30}.

| komórka | test | x = 0 (rozmiar) | 0,05 | 0,10 | 0,15 | 0,20 | 0,30 | MDE |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| C1, p = 1 % | test zbiorczy | 3,9 | 46,8 | 97,9 | 100,0 | 100,0 | 100,0 | 0,082 |
| C1, p = 1 % | DM-FZ0 | 5,3 | 12,4 | 49,1 | 89,1 | 99,5 | 100,0 | 0,139 |
| C1, p = 1 % | DM-PINB | 5,2 | 12,8 | 49,2 | 88,3 | 99,2 | 100,0 | 0,139 |
| C1, p = 5 % | test zbiorczy | 3,6 | 54,4 | 99,2 | 100,0 | 100,0 | 100,0 | 0,079 |
| C1, p = 5 % | DM-FZ0 | 4,9 | 16,8 | 59,6 | 94,0 | 99,8 | 100,0 | 0,130 |
| C1, p = 5 % | DM-PINB | 4,8 | 16,6 | 57,0 | 91,9 | 99,5 | 100,0 | 0,133 |
| C2, p = 1 % | test zbiorczy | 3,8 | 45,8 | 97,7 | 100,0 | 100,0 | 100,0 | 0,083 |
| C2, p = 1 % | DM-FZ0 | 5,4 | 12,4 | 48,5 | 88,1 | 99,5 | 100,0 | 0,140 |
| C2, p = 1 % | DM-PINB | 5,2 | 12,6 | 48,2 | 87,6 | 99,3 | 100,0 | 0,140 |
| C2, p = 5 % | test zbiorczy | 3,6 | 55,6 | 99,4 | 100,0 | 100,0 | 100,0 | 0,078 |
| C2, p = 5 % | DM-FZ0 | 4,5 | 17,4 | 61,5 | 94,3 | 99,9 | 100,0 | 0,128 |
| C2, p = 5 % | DM-PINB | 4,3 | 17,1 | 58,3 | 92,1 | 99,7 | 100,0 | 0,132 |

- **Test zbiorczy** ma moc 80 % już przy zaniżeniu σ o ok. 8 % (MDE 0,078–0,083); przy 10 % odrzuca
  97,7–99,4 % paneli.
- **Test DM wobec wyroczni** potrzebuje zaniżenia o ok. 13–14 % (MDE 0,128–0,140): przy 10 % ma moc 48,5–61,5 %,
  przy 15 % 88,1–94,3 %. To wartość, którą P-a porównuje z progiem 0,10.
- **Strata PINB** (sam VaR, bez ES) daje prawie taką samą moc jak FZ0: różnice do 0,8 pp przy 1 % i do 3,2 pp przy
  5 % (przy 5 % zawsze na korzyść FZ0). Człon ES dokłada więc przy tych n niewiele.
- **C1 i C2** różnią się w tej tabeli o najwyżej 1,9 pp.

### Przewidywania W1–W4

Zapisane po obejrzeniu pilotażu (nie ślepe, patrz pre-rejestracja), nie wchodzą do reguł. Wynik: osiem na osiem
potwierdzonych (cztery przewidywania × dwa poziomy p), w komórce C1.

| przewidywanie | p = 1 % | p = 5 % |
|---|---|---|
| **W1** test zbiorczy odrzuca `okno60_t5` i `ewma94_t5` w ≥ 70 % paneli (minimum z dwóch) | 78,5 % — TAK | 78,8 % — TAK |
| **W2** strata FZ0 ponad wyrocznię maleje: `okno60_t5` > `ewma94_t5` > `garch_tnu` | 0,0905 > 0,0304 > 0,0116 — TAK | 0,0626 > 0,0209 > 0,0052 — TAK |
| **W3** P-a niespełnione (MDE > 0,10) | 0,139 — TAK | 0,130 — TAK |
| **W4** P-b niespełnione (moc < 80 %) | 35,6 % — TAK | 73,3 % — TAK |

Zapas W1 do progu wynosi 8,5 / 8,8 pp (SE ok. 0,6 pp). Spełnił się też łączny prognozowany obraz z
pre-rejestracji: K = TAK, P = NIE, a runda jest MIERZALNA wyłącznie przez pytanie K. Ryzyka, które zapisano jako
realne, się nie zrealizowały: K-a przy 1 % wyszło 8,2 ± 0,4 % (pre-rejestracja szacowała zbiorczo 8,9 ± 1,1 %,
więc K = NIE było możliwe), a P-b przy 5 % wyszło 73,3 % (szansę obalenia W4 oceniano na 6–7 %). Komplet
potwierdzeń czytam jako czerwoną flagę z listy kontrolnej („wynik idealnie potwierdzający oczekiwanie”); ma
swoje miejsce w uzasadnieniu werdyktu.

### Rejestr a pilotaż 480 paneli

Pilotaż (480 paneli, ziarno 777, widziany przed zapisem kryteriów) i rejestr (5 000 paneli, ziarno 20261016) to
niezależne zestawy paneli. Komórka C1, jeśli nie napisano inaczej; odsetki w %.

| wielkość | pilotaż 1 % | rejestr 1 % | pilotaż 5 % | rejestr 5 % |
|---|---:|---:|---:|---:|
| K1 rozmiar na wyroczni | 3,1 | 3,9 | 4,8 | 3,6 |
| K-a rozmiar `garch_tnu` | 7,9 | 8,2 | 5,0 | 5,5 |
| K-b moc `garch_tnu_zan10` | 99,4 | 98,8 | 99,6 | 99,5 |
| K4 najgorsza para zerowa | 6,0 | 5,3 | 5,6 | 4,7 |
| K6a największy z 6 par | 7,3 | 9,1 | 9,0 | 10,1 |
| K6b najmniejszy z 6 par | 2,5 | 3,7 | 2,9 | 2,7 |
| P-a moc DM-FZ0 przy x = 0,10 | 50,0 | 49,1 | 59,0 | 59,6 |
| P-a MDE | 0,140 | 0,139 | 0,131 | 0,130 |
| P-b moc `ewma94_t5 → garch_tnu` | 35,2 | 35,6 | 75,8 | 73,3 |
| C2: K-a | 9,4 | 8,0 | 4,4 | 5,0 |
| C2: P-b | 33,3 | 33,8 | 73,5 | 73,1 |
| VR dziennej sumy trafień, `garch_tnu` | 3,20 | 3,17 | 6,36 | 6,36 |
| W1 minimum (okno 60, EWMA) | 77,3 | 78,5 | 80,6 | 78,8 |
| W2 strata `okno60_t5` − `garch_tnu` (FZ0) | 0,080 | 0,079 | 0,058 | 0,057 |

K2 i K5 wynosiły 100 % w obu źródłach. K7 (oba p razem): pilotaż 5,232 / 0,9722 / 0,00 % / 2,10 %, rejestr
5,236 / 0,9720 / 0,00 % / 2,23 % (ν̂ / α̂ + β̂ / bez zbieżności / przy granicy).

Żadna z 22 różnic w odsetkach paneli (wszystkie wiersze tabeli poza MDE, VR i W2) nie przekracza 1,6 łącznego
błędu standardowego (SE liczone jak dla odsetka; dla największej i najmniejszej z 6 par to przybliżenie). Największe to K6b przy 1 % (2,5 → 3,7 %; 1,6 SE),
K-b przy 1 % (99,4 → 98,8 %; 1,6 SE) i K6a przy 1 % (7,3 → 9,1 %; 1,4 SE). Rejestr nie zmienia więc obrazu z
pilotażu, tylko zawęża niepewność (SE z ok. 1,2 pp do ok. 0,4 pp przy 8 %). Jedna z tych różnic przechodzi przez
próg kryterium: K6a przy 1 % leżało w pilotażu pod progiem 7,5 %, a w rejestrze leży nad nim. Pre-rejestracja
zapowiadała, że przy 1 % K6a może zawieść; po przeglądzie taka porażka nie zmienia wyniku NIE reguły P.

## Weryfikacja niezależna

Po przebiegu rejestrowym sprawdziłem wynik siedmioma sposobami, o różnym stopniu niezależności od kodu, który go
wyprodukował. Skrypty i ich wydruki leżą w `weryfikacja/` (każdy skrypt ma na początku opis, co robi). Skrypty
powstały i działały poza repo, a do repo trafiły dopiero po przebiegu (commit `6d71b5e`); o różnicach między
wersjami w dalszej części tej sekcji.

| # | co sprawdzono | jak | wynik |
|---|---|---|---|
| 1 | braki w wynikach | skan zapisanych wyników 5 000 paneli (`analiza_npz.py`) | brak NaN w statystykach; wszystkie p-wartości testu zbiorczego określone; 0 porównań DM z nieskończonością (36 w C1, 34 w C2) |
| 2 | czy wydruk zgadza się z danymi | 1 470 liczb z tabel wydruku przeliczono z zapisanych wyników; kryteria, reguły, flagi i W1–W4 zaprogramowano od nowa z tekstu pre-rejestracji (`reaggregate_npz.py`) | 0 rozbieżności (największa 0,50 jednostki ostatniej cyfry, czyli samo zaokrąglenie); 8 z 8 linii VR zgodnych; kryteria, reguły, trzy flagi i W1–W4 identyczne z wydrukiem |
| 3 | czy przebieg da się powtórzyć | panele 0–199 policzone ponownie z tym samym ziarnem, na 12 procesach (rejestr: 16) i bez ograniczania wątków BLAS (rejestr: po jednym) | wyniki identyczne co do bitu, więc wynik nie zależy od liczby procesów ani od liczby wątków (R19) |
| 4 | stałe matematyczne | wzory zamknięte na kwantyl i ES rozkładu t oraz mnożniki par „dokładnie zerowych” porównano z całkowaniem numerycznym: wzory skryptu niezależnego (`indep_lv2.py stale`) i wzory kodu rejestrowego (`stale_vs_rejestr.py`) | zgodne: kwantyl identyczny, ES do 1,3·10⁻¹⁵, mnożniki do 1,5·10⁻¹⁴ (np. ν = 5, p = 1 %: kwantyl −2,6064635694, ES −3,4488367600; mnożnik FZ0 przy c_A = 0,9: 1,126683) |
| 5 | prognozy i testy cudzym kodem | na 200 paneli: okno 60 i EWMA własnymi pętlami, GARCH-t przez pakiet `arch`, błąd HAC przez `statsmodels` | prognozy deterministyczne identyczne (różnica statystyki t w DM do 3·10⁻⁹); GARCH w granicach szumu estymacji: 3 z 1 600 decyzji testu zbiorczego inne, różnica t w DM najwyżej 0,62; średnie ν̂ 5,2450 wobec 5,2485, trwałość 0,97109 wobec 0,97108 |
| 6 | cały eksperyment od zera | 400 paneli z własnego generatora napisanego z opisu w kodzie (ziarno 424242), własny test A/B/C, `arch` dla GARCH (`cmp_zbiorczo.py`) | 24 porównania z rejestrem (12 prognoz × 2 poziomy p): 3 z \|z\| > 2, wszystkie przy mocy bliskiej 100 %, w obu kierunkach |
| 7 | skutek poprawek po przebiegu | cztery szybkie skrypty (`stale`, `reaggregate`, `analiza`, `cmp`) uruchomione ponownie w wersji z repo (po poprawkach stylu); `indep_lv2.py` w wersji z repo wobec wersji użytej w przebiegu na 4 panelach (`panele`) i 8 panelach (`zbiorczo`) | wydruki identyczne bajt w bajt; długich przebiegów (200 i 400 paneli) nie powtarzano |

- **Wiersz 3.** Polecenie: `indep_lv2.py panele --ziarno 20261016 --M 200 --workers 12 --npz data/lv2_wyniki_paneli.npz`
  (rejestr: `--workers 16` i po jednym wątku BLAS). Porównanie z zapisanym plikiem wyników: bez jednego bitu różnicy
  w obu tablicach (`abs` i `dm`). Ten sam skrypt na pierwszych 4 panelach dał ten sam wynik także dziś, w wersji z repo.
- **Wiersz 5.** Prognoz deterministycznych (`wyr_t5`, `zan05…zan30`, okno 60, EWMA) nie rozróżnia nic: 0
  niezgodnych decyzji. Niezgodne decyzje zdarzają się tylko przy czterech prognozach GARCH-t (`garch_t5`,
  `garch_tnu`, `garch_tnu_zan10`, `garch_tnu_zan20`), czyli tam, gdzie dwa optymalizatory kończą w nieco innych
  punktach. Tych prognoz jest 8 wierszy (4 prognozy × 2 poziomy p) po 200 paneli, czyli 1 600 decyzji zbiorczych i
  4 800 składowych (A, B, C). Niezgodne są 4 decyzje składowe: `garch_t5` przy 1 % (składnik C), `garch_tnu` przy
  1 % (B), `garch_tnu_zan10` przy 1 % (B) i `garch_tnu` przy 5 % (C). Decyzja zbiorcza różni się w trzech
  pierwszych (3 z 1 600); w czwartej obie wersje odrzucają model we wszystkich 200 panelach, więc wynik zbiorczy
  jest ten sam. Odsetek odrzuceń na tych 200 panelach: `garch_tnu` 7,5 % (rejestr) wobec 7,0 % (`arch`) przy 1 %
  i 5,0 % wobec 4,5 % przy 5 %.
- **Wiersz 6.** Trzy wartości o \|z\| > 2 to `zan10` przy 1 % (97,9 % wobec 96,25 %; z = −2,22), `zan10` przy 5 %
  (99,2 % wobec 98,0 %; z = −2,59) i `garch_tnu_zan10` przy 1 % (98,8 % wobec 100 %; z = +2,11). Przy mocy rzędu
  98–100 % liczy się każda przypadkowa różnica o 1–2 pp, a wiersze tej samej próby są skorelowane, więc 3 z 24
  to nie dowód wady. Wiersze prognoz poprawnych, które niosą wniosek rundy, zgadzają się z rejestrem w ramach
  szumu: `wyr_t5` 3,9 wobec 4,5 %, `garch_tnu` 8,2 wobec 7,25 %.
- **Wiersz 7 i wątki BLAS.** Strona niezależna (pakiet `arch`) zależy od liczby wątków BLAS. Ten sam przebieg `panele`
  na 4 panelach (`indep_lv2.py panele --ziarno 20261016 --M 4 --workers 4`), raz z `OMP_NUM_THREADS=1
  OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1` (`weryfikacja/panele_M4_1watek_output.txt`) i raz bez ograniczenia
  (`weryfikacja/panele_M4_output.txt`), daje wydruki różniące się w trzeciej cyfrze 8 z 60 wierszy tabeli różnic DM
  (np. największa różnica t pary `garch_tnu → garch_t5` przy 1 %: 5,66·10⁻² wobec 5,64·10⁻²), zawsze w wierszach
  z GARCH. Wydruk bez ograniczenia jest identyczny z zapisanym przed długimi przebiegami. Strona rejestrowa tego nie
  robi (wiersz 3). Przebiegi niezależne trzeba więc powtarzać w tych samych ustawieniach, czyli bez ograniczania
  wątków (tak działały długie przebiegi). Wniosków to nie dotyka: dotyczy liczb opisujących rozbieżność dwóch
  dopasowań GARCH, która i tak jest „w granicach szumu”.

### Czego tą weryfikacją nie objęto

- **Niezależność dotyczy kodu, nie wykonawcy.** Kod rejestrowy i kod niezależny napisał ten sam wykonawca (model);
  drugiego człowieka przy tym nie było. Przegląd przed przebiegiem też zrobiły modele, nie ludzie (sekcja „Zmiany
  po przeglądzie, przed pełnym przebiegiem”).
- **HAR i ogony empiryczne** (`har_t5`, `*_ep`, `*_ec`) liczy tylko kod rejestrowy; ich nie przeliczono innym kodem.
  Nie niosą wniosku rundy (to opis), ale stoją za tropem o ogonie EWMA (`ewma94_ep`), więc ten trop jest tym bardziej
  wstępny.
- **Warstwa reguł i wydruku** (kryteria, flagi, W1–W4) przeprogramowano od nowa z tekstu pre-rejestracji i dała
  to samo co wydruk (wiersz 2), ale po przebiegu nie czytałem jej kodu linia po linii. Kod przeglądano przed
  przebiegiem (commit `24c8863`).
- **Estymator GARCH** drugi optymalizator (`arch`) potwierdza w granicach szumu, ale nie co do cyfry (wiersz 5);
  to dwa różne programy, które kończą w nieco innych punktach.

### Wrażliwość wyniku na konwencję startu GARCH

Model GARCH liczy wariancję rekurencyjnie, więc trzeba mu podać wariancję początkową. Pre-rejestracja przyjęła
średnią z kwadratów zwrotów próby (tak robi `dopasuj_garch_t`). Pakiet `arch` domyślnie startuje inaczej (własny
„backcast” z pierwszych obserwacji). W niezależnej symulacji 400 paneli (wiersz 6) policzono oba warianty na tych
samych panelach; liczby to odsetek paneli odrzuconych przez test zbiorczy, „±” to SE:

| prognoza | VaR 1 %: start z próby (pre-rejestracja) | VaR 1 %: start domyślny `arch` | VaR 5 %: start z próby | VaR 5 %: start domyślny `arch` |
|---|---:|---:|---:|---:|
| `garch_tnu` | 7,25 ± 1,30 | 10,75 ± 1,55 | 6,00 ± 1,19 | 6,75 ± 1,26 |
| `garch_t5` | 5,25 ± 1,12 | 5,25 ± 1,12 | 6,50 ± 1,23 | 7,00 ± 1,28 |

Średnia trwałość α̂ + β̂ wynosi 0,97199 wobec 0,97258, a średnie ν̂ 5,2273 wobec 5,2968. Przy VaR 1 % różnica dla
`garch_tnu` to 3,5 pp, czyli 14 paneli z 400 (43 wobec 29 odrzuceń). Błędu różnicy liczonej parami nie
policzyłem; przy traktowaniu obu odsetków jak niezależnych różnica ma ok. 1,7 SE. To **wskazówka, nie dowód**, ale
wystarczająca, żeby nie przenosić liczby 8,2 % na inną konwencję: z domyślnym startem `arch` wynik przy VaR 1 %
mógłby leżeć na progu 10 % kryterium K-a albo nad nim. Dlatego warunek 3 werdyktu mówi „dokładnie
`dopasuj_garch_t`”, a rekomendacja wskazuje VaR 5 %, gdzie oba warianty mieszczą się poniżej 10 %.

### Co zmieniło się w skryptach weryfikacyjnych po przebiegu

- Skrypty weryfikacyjne działały poza repo. Do repo trafiły po przebiegu, po lintowaniu i formatowaniu. Różnice
  względem wersji użytych w przebiegu dotyczą wyłącznie zapisu, nie obliczeń:
  - nagłówki opisowe (docstringi) i formatowanie `black` (m.in. pętla `for (_i, …) in` zapisana jako
    `for _i, … in`);
  - nieużywane zmienne zastąpione przez `_`: `n, k = r.shape` → `_, k = r.shape` w `indep_lv2.py` oraz
    `v5, se5` → `v5, _` w `reaggregate_npz.py`;
  - usunięte trzy komentarze `# noqa` (jeden E731 w `indep_lv2.py`, po jednym E402 w `analiza_npz.py` i
    `reaggregate_npz.py`); przy konfiguracji lintera z repo sprawdzenie przechodzi bez nich;
  - ścieżki wyliczane z położenia pliku (`Path(__file__)`), a nie wpisane na sztywno (`analiza_npz.py`,
    `reaggregate_npz.py`, `cmp_zbiorczo.py`); w `reaggregate_npz.py` `open(...)` zastąpione przez
    `Path.read_text`; `cmp_zbiorczo.py` czyta teraz plik `zbiorczo_M400_output.txt` z tego katalogu.

  Obliczeń to nie dotyka: potwierdza to wiersz 7 (wydruki identyczne bajt w bajt) oraz jednorazowe porównanie
  drzew składni obu wersji czterech skryptów (komentarze i formatowanie drzewo pomija), które w kodzie pokazało
  tylko zmiany z tej listy; wyniku tego porównania nie zapisano w repo.
- `tabele_wynik.py` i `tabele_kryteria.py` (generatory tabel tego README) powstały po przebiegu i czytają tylko
  `raw_output.txt`; symulacji nie przeliczają. `tabele_wynik.py` wylicza z wydruku także liczby pochodne, których
  w wydruku nie ma: ρ_h z VR, zapasy do progów w jednostkach SE, stosunek rzeczywistego rozrzutu statystyki DM do
  jej błędu standardowego (SD/se), orientacyjną moc przy przybliżeniu normalnym i rozbicie nadwyżki fałszywych
  alarmów; zapisano je w `weryfikacja/pochodne_output.txt`. `stale_vs_rejestr.py` powstał po przebiegu i wywołuje
  funkcje kodu rejestrowego oraz skryptu niezależnego.
- Kod badany (`symulacje/`, `miara/`, `tests/`) nie zmienił się od commitu `24c8863` (`git diff 24c8863 HEAD --
  symulacje tests miara` jest puste).

## Kogo NIE ma w zbiorze

To laboratorium, więc „zbiorem” jest świat syntetyczny: 5 000 paneli z jednego ziarna (`20261016`) i jednego
zestawu parametrów prawdziwych (σ̄ = 4 % dziennie, α = 0,08, β = 0,90, ν = 5, ρ = 0,8). Wynik mówi o tym świecie.
Czego w nim brakuje, a na prawdziwych danych będzie:

- **Skoków i krachów.** Są tylko grube ogony t5 i wolne zmiany zmienności (GARCH). Nie ma wydarzeń typu upadek
  giełdy czy monety, po których wszystkie ceny spadają w jednym dniu.
- **Zależności ogonowej i osobnego wspólnego szoku zmienności.** Monety łączy wyłącznie wspólny czynnik gaussowski o
  stałym ρ = 0,8 (tak w pre-rejestracji). Prawdziwe krachy są bardziej synchroniczne, więc moc testu zbiorczego
  w tym laboratorium to raczej górne oszacowanie; stąd warunek 2 przeniesienia (ρ_h z prawdziwych danych).
- **Reżimów i zmiany parametrów.** Każda moneta ma te same parametry przez cały panel. Na prawdziwych danych
  parametry się przesuwają, a model dopasowywany co 30 dni może za nimi nie nadążać.
- **Monet, które znikają albo debiutują.** Wszystkie 15–20 monet żyje przez cały panel i ma co najmniej 400 dni
  historii przed pierwszą oceną. Monety z krótszą historią są poza zakresem laboratorium.
- **Błędu specyfikacji modelu.** GARCH-t jest prawdziwą klasą modelu generatora, więc to najlepszy przypadek:
  mierzymy rozmiar testu przy samym błędzie estymacji parametrów. Średnia (zero) też jest znana. Wynik „test się
  nie myli, gdy model jest dobry” to warunek konieczny, nie dowód, że test wykryje każdy błąd specyfikacji.
- **Innych prognoz, testów i ustawień.** Poza zestawem z karty (okno 60, EWMA 0,94, GARCH-t, HAR jako opis) nie
  badano np. asymetrycznego GARCH ani symulacji historycznej. Poza testem A/B/C i testem DM nie badano innych
  testów. Tylko poziomy 1 % i 5 %, tylko horyzont jednego dnia, tylko komórki C1 (20 monet × 1 600 dni) i C2
  (15 × 1 700).

Co zostało w zbiorze, choć mogło wypaść: **żaden panel nie został wyłączony.** Dopasowań GARCH, które nie zbiegły,
było 90 z 5,7 mln (0,00 %, najwyżej jedno na panel), a 2,23 % leżało przy granicy dozwolonego zakresu parametrów;
wszystkie zostały w wynikach, a kontrola K7 wyszła TAK.

Zbiór jest więc uczciwy wobec pytania, które zadano („czy test zbiorczy i DM zachowują się dobrze, gdy model jest
poprawny, ale estymowany”), a nie wobec pytania „czy prognoza VaR/ES jest dobra na prawdziwych danych”. Na to drugie
odpowie dopiero runda na danych, na warunkach przeniesienia z sekcji „Werdykt”.

## Co na plus (+) / Co na minus (−)

**Na plus (+)**

- **Zasady zapisane przed wynikiem.** Pre-rejestracja (commit `73fff28`), przegląd (`24c8863`) i hashe obu wersji
  w kolejnych commitach (`c9419a3`, `9acb8b9`) powstały przed startem przebiegu rejestrowego (10:21:45 UTC).
  Przegląd zmienił jedną regułę (`dotyczy` w regule P) i dodał reguły operacyjne, ale nie progi, prognozy,
  generator, komórki ani ziarno. Kod badany (`symulacje/`, `miara/`, `tests/`) nie zmienił się od `24c8863`.
- **Mała niepewność losowa.** 5 000 paneli daje błąd standardowy odsetka rzędu 0,3–0,4 pp przy 5–8 %. Pilotaż
  480 paneli (inne ziarno) zgadza się z rejestrem w granicach 1,6 błędu standardowego we wszystkich 22 porównaniach.
- **Kontrole dodatnie i ujemne (R8).** Prognoza idealna (wyrocznia) odrzucana jest w 3,6–3,9 % paneli, czyli poniżej
  nominalnych 5 %; zaniżenie σ o 10 % wykrywane jest w 97,7–99,4 % paneli; pary „dokładnie zerowe” w teście DM
  sprawdzają jego rozmiar.
- **Uczciwa liczba fałszywych alarmów.** Test zbiorczy na modelu poprawnym, ale estymowanym, odrzuca ok. 8 %
  paneli przy VaR 1 %, nie 5 %. Rozłożono to na część od oszacowania σ (+1,1 pp) i od oszacowania ν (+3,2 pp).
- **Sprawdzenie siedmioma sposobami** (sekcja „Weryfikacja niezależna”): 0 rozbieżności w 1 470 liczbach,
  wynik powtórzony co do bitu na 200 panelach, wzory zgodne z całkowaniem numerycznym, niezależna symulacja
  400 paneli zgodna na wierszach, które niosą wniosek.
- **Wynik negatywny też jest użyteczny.** Reguła P (pytanie porównawcze) jest NIEMIERZALNA z wyraźnym zapasem na
  kryterium P-a, które ma dokładny błąd (nie zależy od K6 ani od HAC): najmniejsze wykrywalne zaniżenie σ wynosi
  0,128–0,140 wobec 0,10 wymaganego, a moc 48,5–61,5 % wobec 80 %. Kryterium P-b przy VaR 5 % (73,1–73,3 %) leży
  bliżej progu, ale wynik reguły rozstrzyga P-a. Oszczędza to rundę na danych z pytaniem, na które przy n = 1 600
  nie da się odpowiedzieć.
- **Higiena.** Zero danych prawdziwych, liczniki bez zmian, LLM poza ścieżką decyzyjną (R15), wynik
  deterministyczny i niezależny od liczby procesów i wątków (R19).

**Na minus (−)**

- **Fałszywy alarm ok. 8 % przy VaR 1 %** (8,2 % w C1, 8,0 % w C2), czyli 1,8–2,0 pp od progu 10 %. Rundę
  na danych trzeba czytać względem 8 %, nie 5 %.
- **Próg K-a ≤ 10 % wybrano po pilotażu 64 paneli** (karta go nie podawała) i przy VaR 1 % rozstrzyga on o wyniku:
  przy progu 7,5 % reguła K przy 1 % byłaby NIE (8,2 i 8,0 % leżą 0,7 i 0,5 pp ponad). Przy VaR 5 % próg
  nie ma znaczenia (5,5 % i 5,0 %). To poprawia punkt 8 „Decyzji wykonawcy” (sekcja „Decyzje wykonawcy — ciąg dalszy”).
- **Wynik zależy od konwencji startu GARCH.** Niezależny przebieg 400 paneli dał dla `garch_tnu` przy 1 % 7,25 %
  z startem z próby (pre-rejestracja) i 10,75 % z domyślnym startem `arch`. Różnicy parami nie policzono (ok. 1,7 błędu
  standardowego, jeśli traktować próby jak niezależne), więc to wskazówka, nie dowód; przy 5 % obie konwencje
  dają 6,0 % i 6,75 %.
- **Przewidywania spełnione 8 z 8** (W1–W4 × dwa poziomy p), a „wynik idealnie potwierdzający hipotezę” to
  czerwona flaga z listy kontrolnej. Przewidywania zapisano po obejrzeniu pilotażu, na tym samym generatorze,
  więc zgodność jest w dużej mierze zbudowana; pilotaż miał inne ziarno, więc to powtórzenie, nie dowód niezależny.
- **Błąd HAC w teście DM jest mylny przy prognozach estymowanych.** Kontrola K6a wychodzi NIE we wszystkich
  4 blokach (para okno 60 → EWMA: 8,1–10,1 % wobec progu 7,5 %), a trzy wyniki są oznaczone flagą „blisko progu”
  (K6b w C1 przy 5 %, K6a w C2 przy 1 %, K6b w C2 przy 5 %), wszystkie na kontrolach reguły P. Moc pary głównej
  P-b przy 5 % (73,3 % w C1) mogłaby przy dokładnym błędzie HAC wynosić orientacyjnie ok. 80 %, czyli tyle co próg
  (szacunek, nie wynik). Wynik NIE reguły P trzyma jednak P-a, które od K6 nie zależy.
- **Pary „zerowe” w DM są asymetryczne:** „A lepsza” zdarza się 1,4–3,5 razy częściej niż „B lepsza”.
- **Nie przeliczono innym kodem:** HAR, ogonów empirycznych (`*_ep`, `*_ec`); warstwa wydruku i reguł jest
  przeprogramowana, ale po przebiegu nie czytałem jej kodu linia po linii.
- **Niezależne weryfikacje robi ten sam wykonawca,** a skille bramkowe (`data:validate-data`,
  `data:statistical-analysis`, `engineering:code-review`) wczytano po przebiegu (10:59 UTC, przebieg skończył się
  10:53), `clas5-quant` i `quant-strategy-catalog` nie wczytano wcale (sekcja „Użyte skille”).
- **Nieczystości przebiegu:** pierwszy start przerwano i uruchomiono od nowa (sekcja „Przebieg”); etykieta
  „siatka X_GRID” w wydruku to nazwa stałej, nie wartość (nie poprawiałem kodu po przebiegu); czas trwania jest
  tylko w `stderr_przebiegu.txt`; strona niezależna (`arch`) zależy od liczby wątków BLAS.
- **Jeden zestaw parametrów, jedno ziarno, słaby model zależności** (sekcja „Kogo NIE ma w zbiorze”): wynik to
  raczej górne oszacowanie mocy.

## Werdykt

**Caveats.** Podpisuje Claude (R14: skrypt tylko drukuje liczby i wynik reguł). To werdykt modelu po
siedmiu sprawdzeniach, nie przegląd człowieka; decyzje bramkowe są po stronie użytkownika.

Wynik mechaniczny reguł: runda pierwszej analizy VaR/ES na danych jest **MIERZALNA przy p = 1 % i p = 5 %, ale
wyłącznie przez regułę K** (pytanie bezwzględne). Reguła P (pytanie porównawcze) jest NIEMIERZALNA, więc pytań
porównawczych na tych n nie zadajemy. Poniżej warunki, bez których MIERZALNA nie obowiązuje. Warunki 1–5 to
warunki przeniesienia zapisane w pre-rejestracji (w jej numeracji), a 6–7 dopisuję po wyniku.

1. **Zakres.** Zakres (a), czyli ≥ 20 monet × ≥ 1 600 dni oceny po ≥ 400 dniach historii, jest dziś nieosiągalny.
   Zakres (b) to dokładnie komórka C2: 15 monet × 1 700 dni oceny po 400 dniach historii, z listą i kolejnością monet
   zapisanymi z góry. Otwiera się tylko, gdy ta sama reguła (K, to samo p) daje TAK w C2 i wynik C2 nie ma flagi
   „w granicach 2 SE od progu”. **Odczytanie (do przeglądu użytkownika):** „wynik C2” rozumiem jako wynik reguły,
   która ma otworzyć zakres, czyli K. Reguła K w C2 nie ma żadnej flagi (K-a 8,0 % i 5,0 %, K-b 98,4 % i 99,6 %),
   a dwie flagi bloku C2 (K6a przy 1 %, K6b przy 5 %) leżą na kontrolach reguły P. Zakres (b) jest więc otwarty
   **tylko dla pytania K**. Surowsze odczytanie (żadnej flagi w całym bloku C2) zamknęłoby Zakres (b); wtedy
   pierwsza runda wymagałaby ≥ 20 monet (np. top-50 z danymi od 2021).
2. **Zależność.** ρ_h (średnia korelacja trafień dwóch monet w tym samym dniu) zmierzone na prawdziwych danych dla
   prognozy typu `garch_tnu` musi spełniać ρ̂ + 2 SE ≤ 0,114 przy VaR 1 % i ≤ 0,282 przy VaR 5 % (to wartości z
   laboratorium: VR 3,17 i 6,36 w C1, 2,60 i 4,95 w C2). Inaczej trzeba policzyć nową komórkę z silniejszą zależnością.
3. **Klasa prognozy i konwencja.** Dokładnie `symulacje.garch_t.dopasuj_garch_t`: zerowa średnia, refit co 30 dni,
   okno rosnące od ≥ 400 dni, ogon t_ν̂, wariancja początkowa z próby. Inna konwencja startu (domyślna w pakiecie
   `arch`) zmieniła w niezależnym przebiegu 400 paneli fałszywy alarm przy VaR 1 % z 7,25 % na 10,75 % (sekcja
   „Weryfikacja niezależna”), więc wynik laboratorium jej nie pokrywa. Wynik K nie obejmuje innych prognoz: okno
   60 dni i EWMA z ogonem t5 test bezwzględny odrzuca w 77–97 % paneli (K-a i K-b policzono tylko dla `garch_tnu`).
4. **Pytanie.** Tylko pytania z wynikiem TAK, czyli bezwzględne (K). Odrzucenie znaczy „nie jest skalibrowana”, nie
   „jest bezużyteczna”. Żadnych porównań prognoz testem DM na n rzędu 1 600–1 700.
5. **Poziom p.** Jedno p wskazane z góry albo korekta α/2 dla dwóch. **Rekomenduję VaR 5 %:** fałszywy alarm
   5,5 % (nie 8,2 %), próg K-a nie ma tu znaczenia, a konwencja startu GARCH zmienia wynik słabo (6,0 % wobec 6,75 %).
6. **Czytanie wyniku.** Przy VaR 1 % odrzucenie czytamy względem ok. 8 % fałszywych alarmów (nie 5 %). W raporcie
   rundy na danych trzeba podać obok p także odsetek trafień i VR. Skrypt do pomiaru ρ_h z warunku 2 odsetka
   trafień nie drukuje (tak zapisała pre-rejestracja).
7. **Licznik i decyzja.** Licznik „ryzyko ogona (VaR/ES) 2021+” zostaje 0, dopóki użytkownik nie otworzy rundy
   (0 → 1); runda na danych dostaje własną pre-rejestrację (R1–R4). Ten werdykt mówi, że pytanie da się zmierzyć,
   a nie że prognoza jest dobra.

### Dlaczego nie Ready

- Reguła flagi z pre-rejestracji mówi, że wynik z flagą dostaje co najwyżej Caveats. Są trzy flagi (K6b w C1 przy
  5 %, K6a w C2 przy 1 %, K6b w C2 przy 5 %), wszystkie na kontrolach reguły P; nie wolno więc dosypywać paneli,
  zmieniać ziarna ani powtarzać przebiegu „bo blisko progu”, i tego nie zrobiłem.
- Próg K-a ≤ 10 % wybrano po pilotażu i przy VaR 1 % rozstrzyga on o wyniku.
- Wynik przy VaR 1 % zależy od konwencji startu GARCH (7,25 % wobec 10,75 %), choć jako wskazówka, nie dowód.
- Wszystkie 8 przewidywań W1–W4 wyszło zgodnie z oczekiwaniem, a zostały zapisane po obejrzeniu pilotażu.
- Nie wszystko policzono drugim kodem (HAR, ogony empiryczne) i skille bramkowe wczytano po przebiegu.

### Dlaczego nie Revision

- Nie znaleziono błędu w kodzie, w przebiegu ani w liczbach: 1 470 liczb przeliczono z zapisanych wyników bez
  rozbieżności, 200 paneli powtórzono co do bitu, a niezależny kod i niezależna symulacja zgadzają się w tym, co niesie wniosek.
- Pilotaż 480 paneli i przebieg rejestrowy zgadzają się w granicach 1,6 błędu standardowego we wszystkich 22 porównaniach.
- Rzeczy do decyzji (odczytanie Zakresu (b), próg K-a, wybór p) są decyzjami użytkownika, nie błędami rundy.

## Wniosek

Odpowiedzi na trzy pytania karty 016:

- **(a) Rozmiar testu zbiorczego dla modelu poprawnego, ale estymowanego.** Test odrzuca dobry model GARCH-t
  dopasowywany co 30 dni w **8,2 %** paneli przy VaR 1 % i **5,5 %** przy VaR 5 % (C1: 20 monet × 1 600 dni);
  w C2 (15 × 1 700) 8,0 % i 5,0 %. Nominalnie jest to 5 %. Nadwyżkę przy 1 % robi głównie oszacowanie grubości
  ogona (+3,2 pp), mniej oszacowanie zmienności (+1,1 pp). Próg kryterium (10 %) jest zachowany.
- **(b) Moc testu porównawczego (DM na stracie FZ0).** Za mała: zaniżenie zmienności o 10 % względem prognozy
  idealnej widzi w 49,1 % (VaR 1 %) i 59,6 % (VaR 5 %) paneli, a EWMA od GARCH-t odróżnia w 35,6 % i 73,3 %
  (wymagane 80 %). Najmniejsze wykrywalne zaniżenie to 0,139 i 0,130, wobec 0,10 wymaganego.
- **(c) Reguła mierzalności.** Pierwsza runda VaR/ES na danych jest **MIERZALNA tylko dla pytania bezwzględnego**
  (reguła K) i tylko na warunkach przeniesienia z sekcji „Werdykt”. Pytania porównawcze (reguła P) są NIEMIERZALNE
  przy tych n.

**Prostym językiem:** na pytanie „czy ta prognoza ryzyka jest dobra” da się na naszych danych uczciwie odpowiedzieć,
choć test jest trochę nerwowy (przy VaR 1 % odrzuca dobrą prognozę w ok. 8 przypadkach na 100, nie w 5). Na pytanie
„która z dwóch prognoz jest lepsza” nie da się odpowiedzieć, bo przy 1 600 dniach test porównawczy nie ma
wystarczającej mocy: brak wyniku nic by nie znaczył. Dlatego pierwsza runda na prawdziwych danych ma zadać tylko
pierwsze pytanie, jednej klasie prognoz i na jednym poziomie ryzyka.

## Rekomendacja

1. **Pierwsza runda VaR/ES na danych (decyzja użytkownika):** pytanie bezwzględne K; klasa `dopasuj_garch_t`
   w dokładnie tej konwencji; komórka C2 (15 monet × 1 700 dni, lista i kolejność monet zapisane z góry);
   **jeden poziom, VaR 5 %**; własna pre-rejestracja z mechanizmem jednym zdaniem (R1) i licznikiem „ryzyko ogona
   (VaR/ES) 2021+” 0 → 1.
2. **Najpierw osobna karta pomiarowa (licznik opisowy):** ρ_h na prawdziwych danych dla 15 monet i prognozy typu
   `garch_tnu`, bez drukowania odsetka trafień. Gdy ρ̂ + 2 SE > 0,282 (VaR 5 %), potrzebne jest LV2c z silniejszą
   zależnością. LV2b nie jest potrzebne: żadna reguła nie wyszła WSTRZYMANA.
3. **Opcjonalnie LV2c** (nie jest potrzebne do pierwszej rundy bezwzględnej): (i) wyjaśnić błąd HAC w teście DM
   przy prognozach estymowanych (K6a); (ii) policzyć wrażliwość na konwencję startu GARCH parami, na zapisanych
   panelach; (iii) przemyśleć regułę P′ dla pytania porównawczego, jeśli jest potrzebne (dłuższej historii niż 2021+
   dziś nie ma, więc zostaje np. więcej monet albo inna strata).
4. **Osobna karta opisowa:** czy EWMA zawodzi przez ogon (`ewma94_ep` odrzucana w 4,1 / 4,6 % paneli, wobec
   78,5 / 78,8 % z ogonem t5). To trop, nie wynik tej rundy.
5. **Czego nie robić:** nie dosypywać paneli, nie zmieniać ziarna, nie powtarzać przebiegu i nie zmieniać progów po
   fakcie (reguła flagi); nie czytać odrzucenia na danych jako „5 % istotności” przy VaR 1 %.

**Wniosek skumulowany (do `runs/INDEX.md`):**
`[2026-10-07, LV2] Model poprawny, ale estymowany (GARCH-t, refit co 30 dni, n = 1 600, 20 monet, ρ = 0,8): test
zbiorczy odrzuca 8,2 % (VaR 1 %) / 5,5 % (VaR 5 %) paneli [próg 10 %], moc wobec σ − 10 % 98,8 / 99,5 %; test
DM-FZ0 nie odróżnia EWMA od GARCH-t (moc 35,6 / 73,3 % < 80 %) i nie widzi σ − 10 % (49,1 / 59,6 %) → pierwsza runda
VaR/ES na danych MIERZALNA tylko dla pytania bezwzględnego o klasę GARCH-t(ν̂) (dokładnie dopasuj_garch_t) na
warunkach przeniesienia; pytań porównawczych na tych n nie zadawać; przy VaR 1 % wynik czytać względem ok. 8 %
fałszywych alarmów, nie 5 %.`

## Decyzje wykonawcy — ciąg dalszy

Punkty 10–19 dopisałem po przebiegu rejestrowym; to dalszy ciąg listy „Decyzje wykonawcy (poza zleceniem) — do
przeglądu” (punkty 1–9 zapisane przed przebiegiem). Wszystkie są do Twojego przeglądu; te, które czekają na Twoją
decyzję, mają znacznik **[decyzja]**.

10. **[decyzja] Odczytanie Zakresu (b).** Pre-rejestracja otwiera Zakres (b) tylko wtedy, gdy „ta sama reguła
    (to samo pytanie, to samo p) daje TAK także w C2 i wynik C2 nie ma flagi”. Zdanie mówi o wyniku tej samej
    reguły, więc „wynik C2” odczytałem jako wynik reguły, która ma otworzyć zakres, czyli K. Reguła K w C2 nie ma
    żadnej flagi, a trzy flagi całego przebiegu leżą na kontrolach reguły P (jedna w C1, dwie w C2). Stąd Zakres (b)
    jest otwarty dla pytania K. Surowsze odczytanie („żadnej flagi w całym bloku C2”) zamknęłoby go, a pierwsza
    runda wymagałaby ≥ 20 monet po ≥ 1 600 dniach oceny, czego dziś nie ma. Tekst da się odczytać na dwa sposoby;
    przyjąłem pierwszy, ale rozstrzygasz Ty.
11. **Werdykt Caveats.** Reguła flagi z pre-rejestracji wyklucza Ready, gdy wynik ma flagę; pozostałe powody
    są w sekcji „Werdykt” („Dlaczego nie Ready”). Revision nie dostał, bo nie znalazłem błędu.
12. **[decyzja] Sprostowanie punktu 8.** Punkt 8 (pisany po pilotażu 480) twierdzi, że żaden z punktów 2–4 nie
    zmienia werdyktu rundy. Dla punktu 2 (próg K-a ≤ 10 %) to się nie zgadza przy p = 1 %: przy ostrzejszym progu,
    np. 7,5 % (tyle wynosi górna granica kontroli K1), reguła K dałaby tam NIE (przebieg rejestrowy: K-a 8,2 % w C1
    i 8,0 % w C2, czyli o 0,7 i 0,5 pp za dużo), a skoro P też jest NIE, runda przy p = 1 % byłaby NIEMIERZALNA.
    Przy p = 5 % próg nie ma znaczenia (K-a 5,5 % i 5,0 %). Już pilotaż (7,9 % przy 1 %) leżał między 7,5 a 10 %,
    więc punkt 8 był w tej części nieścisły od początku. Punktu 8 nie usuwam (to część pre-rejestracji), tylko go
    prostuję tutaj. Dla punktów 3 i 4 pozostaje prawdziwy: K6 to dwie bramki jednostronne, tylko dla pytania
    porównawczego (K6a wstrzymuje wyłącznie wniosek TAK, K6b wyłącznie NIE, obie tylko dla P-b), więc nie dotyka
    reguły K; a C2 wpływa na Zakres, nie na werdykt rundy. Czy próg 10 % przyjmujesz, to Twoja decyzja.
13. **[decyzja] Poziom p.** Rekomenduję **VaR 5 % jako jedyny poziom** pierwszej rundy na danych. To moja
    rekomendacja, nie wynik reguł (reguły dają MIERZALNA przy obu p): przy 5 % fałszywy alarm to 5,5 %, nie 8,2 %,
    próg K-a o niczym nie rozstrzyga, a konwencja startu GARCH zmienia wynik słabo (6,0 % wobec 6,75 % w
    niezależnych 400 panelach). Dwa poziomy naraz wymagałyby korekty α/2.
14. **Zmiany w repozytorium po przebiegu.** README: zastąpiłem tylko blok STATUS na początku i dopisałem jedną
    uwagę pod nagłówkiem „W skrócie”; reszta dotychczasowego tekstu jest bez zmian, a nowe sekcje stoją przed nią
    („Wynik w skrócie”) i po niej. Porównałem plik z wersją z commitu `9acb8b9`: poza starym blokiem STATUS żaden
    dotychczasowy wiersz nie został zmieniony ani usunięty. Zmiany w `weryfikacja/` opisuje sekcja „Weryfikacja
    niezależna”; kod badany (`symulacje/`, `miara/`, `tests/`) jest bez zmian od `24c8863`.
15. **Etykieta „siatka X_GRID” w wydruku** zostaje niepoprawiona: zmiana kodu po przebiegu rejestrowym
    zmieniałaby kod, który dał wynik (patrz „Przebieg rejestrowy”). Poprawka przy następnej zmianie kodu.
16. **Pilotaż 480 poza repozytorium.** Surowy wydruk pilotażu (480 paneli, ziarno 777) leży w katalogu roboczym
    sesji, nie w repozytorium. Wszystkie liczby pilotażu użyte w tabeli „Rejestr a pilotaż 480 paneli” są już w
    tekście pre-rejestracji powyżej (sprawdziłem każdą wartość), więc porównanie da się odtworzyć z samego
    repozytorium; brak tylko surowego wydruku pilotażu.
17. **`stderr_przebiegu.txt`** dodałem do repozytorium bez zmian: to dziennik postępu przebiegu rejestrowego
    i jedyne miejsce, w którym zapisano czas przebiegu (1 894 s). Wydruk wyniku (`raw_output.txt`) czasu nie zawiera.
18. **Bez dodatkowych paneli i bez LV2b.** Zgodnie z regułą flagi nie dosypywałem paneli, nie zmieniałem ziarna i
    nie powtarzałem przebiegu, choć trzy kontrole reguły P leżą blisko progu. Żadna reguła nie wyszła WSTRZYMANA,
    więc LV2b (ziarno `20261017`) nie jest wywołane.
19. **Skille bramkowe po przebiegu.** `data:validate-data`, `data:statistical-analysis` i
    `engineering:code-review` wczytałem po zakończeniu przebiegu (10:59 UTC; przebieg skończył się o 10:53), więc
    ich listy kontrolne zastosowałem do weryfikacji i opisu wyniku, a nie do projektu rundy (sekcja „Użyte skille”).

Decyzje o otwarciu rundy na danych (licznik 0 → 1) i o zleceniu LV2c są w sekcji „Wynik w skrócie” (punkt 7) oraz
w „Rekomendacji”.

## Użyte skille

W repozytorium beta nie ma rejestru użyć skilli (jak `tools/skill_audit.py` w alpha), więc godziny pochodzą z zapisu
sesji (czas UTC). Skille wczytane w tej pracy:

| skill | kiedy | co wniósł |
|---|---|---|
| `clas5-runda` | 2026-10-06 16:52, przed pilotażami i pre-rejestracją | procedura rundy: pre-rejestracja przed wynikiem, katalog rundy, README z „Co na plus / Co na minus” i werdyktem, wiersz w `runs/INDEX.md`, wniosek skumulowany w formacie z jednym zdaniem i liczbą |
| `data:validate-data` | 2026-10-07 10:59, **po** przebiegu (koniec 10:53) | lista kontrolna walidacji wyniku: przeliczenie liczb drugą drogą, pytanie „kogo NIE ma w zbiorze”, czerwona flaga „wynik idealnie potwierdzający oczekiwanie” (sekcje „Weryfikacja niezależna”, „Kogo NIE ma w zbiorze” i „Werdykt”) |
| `data:statistical-analysis` | 2026-10-07 10:59, **po** przebiegu | efekt z błędem standardowym zamiast samego progu, przedziały zamiast fałszywej precyzji, ostrożność przy wielu porównaniach (sekcje „Wynik” i „Co na plus (+) / Co na minus (−)”) |
| `engineering:code-review` | 2026-10-07 10:59, **po** przebiegu | lista kontrolna przeglądu zmian po przebiegu: kod badany bez zmian od `24c8863`, a zmiany w skryptach weryfikacyjnych (lint, format) nie dotykają obliczeń (sekcja „Weryfikacja niezależna”, wiersz 7) |

Przegląd przed przebiegiem (07:04–07:05 UTC) zrobiły trzy agenty `general-purpose` (statystyczny, kodu, mutacyjny) i
`arxitect:architecture-review`; ich ustalenia są w sekcji „Zmiany po przeglądzie, przed pełnym przebiegiem”.

**Luki (uczciwie).**

- Trzy skille bramkowe (`data:validate-data`, `data:statistical-analysis`, `engineering:code-review`) wczytałem po
  przebiegu rejestrowym, nie przed nim. Przed przebiegiem bramkę stanowił przegląd modeli z poprzedniego akapitu,
  a nie te skille; po przebiegu skille objęły weryfikację i opis wyniku, nie projekt rundy.
- `clas5-quant` i `quant-strategy-catalog` (CLAUDE.md, sekcja „Skille”) nie były wczytane. To runda laboratoryjna na
  danych syntetycznych, więc metodologię brałem wprost z zasad `CLAUDE.md` i z `docs/PRD.md`, bez skilla. To formalna
  luka; nie sprawdzałem, co te skille by dodały.
- `dataviz`: bez wykresów (same tabele), więc niepotrzebny.
