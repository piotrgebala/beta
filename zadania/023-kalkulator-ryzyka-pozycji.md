---
id: 023
tytul: kalkulator ryzyka pozycji — wielkość z celu zmienności, dystans do likwidacji, limit ES
typ: badawcze
status: do_przegladu
zlecil: uzytkownik
decyzja_uzytkownika: "2026-10-09: „to kontynuuj ten wątek” (po pytaniu, do czego prace mogą się przydać: wielkość pozycji, odległość od likwidacji przy 3×, limit ryzyka portfela)"
utworzono: 2026-10-09
zalezy_od: []
budzet: "Opus, 1 sesja"
---

# 023 — kalkulator ryzyka pozycji

## Po co

Prace nad zmiennością i ryzykiem nie dają sygnału handlowego; jedyne praktyczne zastosowanie to ryzyko
pozycji (PRD F2 „Zastosowanie”, F4). Karta zamienia prognozę σ na trzy liczby: dźwignię z celu zmienności,
odległość do likwidacji i skalę wag pod limit ES. To kalkulator stanu bieżącego, nie ocena prognozy.

## Zakres (zrobione)

- `modele/ryzyko_pozycji.py` — czyste funkcje: `dzwignia_celu`, `dzwignia_konc` (jawne `min()` z sufitem i limitem ES,
  zasada 5 z alpha), `ruch_do_likwidacji`, `dystans_w_sigmach`, `p_likwidacji`, `es_straty` (przez `miara.var_es.var_es_t`),
  `skala_limitu_es` (zero dywersyfikacji, R12).
- `modele/rozmiar_dzis.py` — tabela dla BTC, ETH, SOL, BNB: GARCH-t na całej historii do 2026-09-30, σ na następny dzień,
  dźwignia dla celów zmienności, dystans i P likwidacji dla 2× i 3×, wrażliwość na zapas σ ×1,0 / 1,25 / 1,5.
- `tests/test_ryzyko_pozycji.py` (24 testy: wartości ręczne, symulacja t i zwrotów, `hypothesis` na własnościach) i
  `tests/test_rozmiar_dzis.py`. Hypothesis znalazł skraj: long 1× bez mmr likwiduje się dopiero przy cenie 0 → zwracamy −∞ (dystans ∞, P = 0).

## Czego NIE robić

- Nie oceniać prognozy σ na historii ani nie liczyć, ile likwidacji by było (to licznik „ryzyko 2021+”, osobna pre-rejestracja).
- Nie używać wyniku do ZWIĘKSZANIA dźwigni ponad obecne reguły dziennika; kalkulator służy tylko do zmniejszania ekspozycji.
- Nie dotykać dziennika alpha ani kapitału.

## Kryteria odbioru (dowody)

- `python -m pytest -q`, `ruff`, `black` zielone; `PYTHONPATH=. python -m modele.rozmiar_dzis` drukuje tabelę.
- Licznik „ryzyko 2021+” nadal 0; rejestr alpha (N = 40) nietknięty (nic nie liczy zwrotu strategii).

## Wynik

Tabela na 2026-09-30 (2 091 wspólnych dni; skrót, zapas σ ×1,0 i ×1,5; pełny wydruk: `python -m modele.rozmiar_dzis`):

```
 moneta  zapas  sigma_dzien_%  sigma_rok_%    nu  trwalosc  dopasowanie_ok  ES5_dzien_%  dzwignia_cel_18%  dzwignia_cel_35%  dystans_2x_sigm  P_likw_2x_7d_%  dystans_3x_sigm  P_likw_3x_7d_%
BTCUSDT   1.00          2.412       46.083 3.310     1.000           False        5.458             0.391             0.760           28.324           0.025           16.500           0.142
BTCUSDT   1.50          3.618       69.124 3.310     1.000           False        8.188             0.260             0.506           18.883           0.092           11.000           0.516
ETHUSDT   1.00          2.704       51.664 3.515     1.000           False        6.134             0.348             0.677           25.264           0.029           14.717           0.185
ETHUSDT   1.50          4.056       77.496 3.515     1.000           False        9.201             0.232             0.452           16.843           0.117            9.812           0.707
SOLUSDT   1.00          3.628       69.304 4.889     0.965            True        8.132             0.260             0.505           18.834           0.028           10.971           0.316
SOLUSDT   1.50          5.441      103.957 4.889     0.965            True       12.198             0.173             0.337           12.556           0.176            7.314           1.622
BNBUSDT   1.00          2.176       41.563 3.490     0.999            True        4.934             0.433             0.842           31.404           0.014           18.294           0.090
BNBUSDT   1.50          3.263       62.345 3.490     0.999            True        7.401             0.289             0.561           20.936           0.057           12.196           0.350
```

Jak to czytać: BTC przy σ ≈ 2,4 %/dzień (46 % rocznie) daje dźwignię ≈ 0,39× dla celu 18 % rocznie i ≈ 0,76× dla 35 %, czyli
**poniżej 1×** — cele zmienności nóg dziennika (TS1 18 %, CP1 35 % rocznie) przy dzisiejszej zmienności rynku nie dają dźwigni 2–3×.
Dystans do likwidacji 3× to ok. 16 σ dziennych, a modelowe P(likwidacja w 7 dni) ≈ 0,14 % (BTC) i 0,3 % (SOL).

**Zastrzeżenia (obowiązkowe):**

1. Prognoza σ nie przeszła testu kalibracji na danych (018 wstrzymana, 022 czeka). Dla BTC i ETH dopasowanie GARCH-t kończy się na granicy
   (α + β = 1,000; `dopasowanie_ok = False`), czyli σ to w praktyce silnie wygładzony poziom ostatnich dni.
2. `P_likw` to przybliżenie modelowe: stała σ, bez cen śróddziennych, skoków σ, kaskad likwidacji, opłat, funduszu i stopni mmr giełdy.
   Należy je traktować jako **dolne oszacowanie** ryzyka; alpha zmierzyła na historii, że 3× na altach kosztuje ok. 3,6 pkt rocznie w likwidacjach (PRD §2.1), czego
   ten model by nie przewidział. Porównanie z historią zrobiła karta 024 (Caveats): P 3× bywa zaniżone ok. 1,6× (wynik brzegowy) — tabela ma kolumnę `P_likw_3x_7d_kor_%`.
3. Limit ES portfela (`skala_limitu_es`) liczy sumę ES nóg (bez dywersyfikacji); ERC/HRP i CVaR z PRD F4 nie są zbudowane (przy 2 nogach ERC = 1/σ).

**Dalej:** (a) wykonane jako karta 024; (b) wpiąć kalkulator w raport tygodniowy (karta 007) jako tabelę „na dziś”.
