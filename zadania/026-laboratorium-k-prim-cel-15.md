---
id: 026
tytul: laboratorium K′ (bootstrap blokowy) przy celu mocy σ −15 % — czy test z błędem szacowanym z danych jest mierzalny
typ: badawcze
status: do_przegladu
zlecil: uzytkownik
decyzja_uzytkownika: "2026-10-17: „tak Tor VaR/ES na danych: potrzebuje Twojej decyzji o celu σ −15 %.” — zgoda na cel mocy σ −15 % zamiast −10 % (zmiana zamrożonego progu mocy zatwierdzona przez użytkownika); kod K′ jest nowy, pliki zamrożone nietknięte"
utworzono: 2026-10-17
zalezy_od: [018, 022, 021]
budzet: "Opus, 1–2 sesje (pre-rejestracja, dwa przebiegi laboratoryjne ok. 10–20 min, wynik)"
---

# 026 — K′ przy celu σ −15 %

## Po co

Karta 022 pokazała, że przy celu σ −10 % reguła K′ jest niemierzalna (idealny test: 65 %), a przy σ −15 % idealny test ma 92 % mocy. Idealny test zna prawdziwy błąd;
prawdziwy test musi go oszacować z danych (bootstrap blokowy). Ta karta sprawdza na laboratorium LV2d, czy po tej wymianie rozmiar testu nadal mieści się w 10 % i moc wobec σ −15 % w 80 %.
Jeśli tak — karta 027 (runda 018′ na prawdziwych danych, osobna pre-rejestracja). Jeśli nie — tor VaR/ES na danych zamknięty do ok. 2028.

## Zakres

1. Pre-rejestracja w `runs/2026-10-17_026-k-prim-lab/README.md` w gicie PRZED przebiegiem.
2. Kod: `symulacje/k_prim_blokowy.py`, `symulacje/run_kprim.py`, `tests/test_k_prim_blokowy.py` (nowe pliki).
3. Przebieg „wybór” (2 000 paneli na komórkę, 4 długości bloku), potem „potwierdzenie” (4 000 świeżych paneli, jedna długość).
4. Wynik, werdykt, wiersz w `runs/INDEX.md`, wniosek skumulowany, `STATUS.md`.

## Czego NIE robić

- Nie zmieniać plików zamrożonych (`run_lv2c.py`, `run_lv2.py`, `run_lv2d.py`, `garch_t.py`, `miara/var_es.py`), progów 10 % i 80 %, p, estymatora.
- Nie dodawać długości bloku ani nie powtarzać wyboru po obejrzeniu wyniku.
- Nie liczyć nic na prawdziwych danych; nie używać zajętych ziaren; nie dotykać alpha; `data/` nie do gita.

## Kryteria odbioru (dowody)

- Pre-rejestracja w gicie przed przebiegiem; testy, ruff, black zielone; `raw_output_*.txt` w katalogu rundy; wiersz w INDEX.

## Wynik

Wydana [runda 026](../runs/2026-10-17_026-k-prim-lab/README.md), werdykt **Ready — K′ NIEMIERZALNA**: krok 1 (2 000 paneli/komórkę) — w B2 K-a 20,4–21,8 % przy L = 20/60/150 (próg 10 %), K-b σ −15 % ≥ 99 %;
reguła STOP, kroku 2 nie uruchomiono. Bootstrap blokowy odtwarza tylko ok. 10 % brakującego błędu (stosunek 1,05 wobec prawdziwego 1,48). Karta 027 nie powstaje, 018 zostaje `odrzucone`.
