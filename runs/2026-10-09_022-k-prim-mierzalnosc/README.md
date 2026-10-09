# 022 — czy reguła K′ (bootstrap blokowy) w ogóle może być mierzalna: górna granica mocy

**Status: PRE-REJESTRACJA rachunku mierzalności (R3), zapisana przed liczeniem.** Typ: laboratorium (panele syntetyczne z 021, zero nowych
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
