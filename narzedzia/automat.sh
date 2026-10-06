#!/usr/bin/env bash
# automat.sh — zadanie 012: powtarzalne zadania repo beta, uruchamiane z crona (PRD §6).
#
#   automat.sh codziennie   DVOL BTC/ETH (Deribit) + manifest
#   automat.sh miesiac      Binance top-20 za poprzedni pełny miesiąc + manifest (cron: 3. dnia)
#   automat.sh niedziela    raport tygodniowy raporty/tygodnie/<RRRR-Www>.md (komentarz zostaje)
#
# Po sukcesie commituje WYŁĄCZNIE pliki wyniku (zasada 28): `git add -- <ścieżki>`, `git commit --
# <ścieżki>`; danych (data/) nie commituje, cudzych zmian nie rusza. Potem wypycha bieżącą gałąź do
# origin, ale tylko wtedy, gdy KAŻDY niewypchnięty commit dotyka wyłącznie plików wyniku (inaczej
# odmowa — cudze lokalne commity nie wyjdą na GitHuba). Push nigdy nie jest wymuszany; po pushu
# skrypt sprawdza, że origin ma ten sam commit co HEAD. Brak zmian = brak commita (ale niewypchnięty
# commit z poprzedniego biegu zostaje ponowiony). Bez LLM (R15).
#
# Zmienne środowiskowe (wszystkie opcjonalne):
#   AUTOMAT_DRY_RUN=1    nic nie pobiera ani nie commituje; sprawdza środowisko (też odczyt
#                        origin) i wypisuje plan
#   AUTOMAT_BEZ_GITA=1   kroki Pythona tak, git (commit i push) nie
#   AUTOMAT_LOG_DIR      katalog logów (domyślnie ~/beta_logi)
#   AUTOMAT_REPO         katalog repo (domyślnie: katalog nad skryptem)
#   AUTOMAT_DATA         dzień uruchomienia RRRR-MM-DD (domyślnie dziś UTC; do testów)
#   AUTOMAT_CZEKAJ_S     ile sekund czekać na blokadę (domyślnie 1800)
#   AUTOMAT_LIMIT_KROKU_S  limit czasu kroku pobierania (domyślnie 1800; dla miesiac 21600)
#   AUTOMAT_LIMIT_PUSH_S   limit czasu pusha (domyślnie 600)
#   AUTOMAT_PONOW_S      przerwa między ponowieniami git add/commit (domyślnie 20; 3 próby)
#   AUTOMAT_PUSH_MAIN=1  zgoda na commit i push bezpośrednio na main/master (domyślnie odmowa:
#                        scalenie do main idzie przez PR)
#
# Kody wyjścia: 0 = OK; 1 lub kod kroku = błąd; 2 = zły argument; 75 = blokada zajęta za długo;
# 124 = krok lub push przekroczył limit; 129/130/143 = przerwany sygnałem (HUP/INT/TERM).
# Interpreter: <repo>/.venv/bin/python (nie zależy od PATH crona).
# Log: <katalog logów>/<RRRR-MM-DD>_<tryb>.log. Ostatni wynik trybu: <katalog logów>/
# ostatni_status_<tryb>.txt (jedna linia); przy błędzie dodatkowo linia na stderr (cron_stderr.log).

set -euo pipefail
set -o errtrace
set -m # każdy krok działa w tle we własnej grupie procesów: sygnał zabija go w całości

# Cron ma ubogie środowisko — to, od czego zależymy, ustawiamy jawnie.
export PATH=/usr/local/bin:/usr/bin:/bin
export LC_ALL=C.UTF-8 LANG=C.UTF-8 TZ=UTC
export PYTHONUNBUFFERED=1 GIT_TERMINAL_PROMPT=0

# Jedyne ścieżki, które automat wolno zatwierdzić i wypchnąć (suma wyników wszystkich trybów).
DOZWOLONE='^(dane/manifest_deribit_dvol\.json|dane/manifest_binance_um\.json'
DOZWOLONE+='|dane/sklad_top20\.json|raporty/tygodnie/[0-9]{4}-W[0-9]{2}\.md)$'

uzycie() {
  cat <<'EOF'
Użycie: automat.sh <tryb>
  codziennie   DVOL BTC/ETH + manifest
  miesiac      Binance top-20 za poprzedni pełny miesiąc + manifest
  niedziela    raport tygodniowy raporty/tygodnie/<RRRR-Www>.md
Zmienne: AUTOMAT_DRY_RUN=1, AUTOMAT_BEZ_GITA=1, AUTOMAT_LOG_DIR, AUTOMAT_REPO, AUTOMAT_DATA,
         AUTOMAT_CZEKAJ_S, AUTOMAT_LIMIT_KROKU_S, AUTOMAT_LIMIT_PUSH_S, AUTOMAT_PONOW_S,
         AUTOMAT_PUSH_MAIN=1 (opis w nagłówku skryptu).
EOF
}

liczba() { # liczba <ZMIENNA> <domyślna> — wartość zmiennej środowiskowej jako liczba sekund
  local nazwa=$1 wartosc=${!1:-$2}
  if ! [[ $wartosc =~ ^[0-9]+$ ]]; then
    echo "Błąd: $nazwa='$wartosc' to nie liczba sekund." >&2
    exit 2
  fi
  printf '%s' "$wartosc"
}

# --- argumenty (przed logiem: zły tryb nie tworzy pliku logu) ---
if [[ $# -ne 1 ]]; then
  echo "Błąd: potrzebny dokładnie jeden argument (tryb)." >&2
  uzycie >&2
  exit 2
fi
TRYB=$1
case "$TRYB" in
  -h | --help)
    uzycie
    exit 0
    ;;
  codziennie | miesiac | niedziela) ;;
  *)
    echo "Błąd: nieznany tryb '$TRYB'." >&2
    uzycie >&2
    exit 2
    ;;
esac

DZIEN=${AUTOMAT_DATA:-$(date -u +%F)}
if ! [[ $DZIEN =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || ! date -u -d "$DZIEN" +%F >/dev/null 2>&1; then
  echo "Błąd: AUTOMAT_DATA='$DZIEN' to nie poprawna data RRRR-MM-DD." >&2
  exit 2
fi
LIMIT_KROKU_DOMYSLNY=1800
if [[ $TRYB == miesiac ]]; then LIMIT_KROKU_DOMYSLNY=21600; fi
CZEKAJ=$(liczba AUTOMAT_CZEKAJ_S 1800)
LIMIT_KROKU=$(liczba AUTOMAT_LIMIT_KROKU_S "$LIMIT_KROKU_DOMYSLNY")
LIMIT_PUSH=$(liczba AUTOMAT_LIMIT_PUSH_S 600)
PONOW_S=$(liczba AUTOMAT_PONOW_S 20)
MIESIAC=$(date -u -d "${DZIEN:0:7}-01 -1 month" +%Y-%m) # poprzedni pełny miesiąc
ETYKIETA=$(date -u -d "$DZIEN" +%G-W%V)                 # tydzień ISO, jak raporty.tydzien
DRY_RUN=0
BEZ_GITA=0
if [[ ${AUTOMAT_DRY_RUN:-0} == 1 ]]; then DRY_RUN=1; fi
if [[ ${AUTOMAT_BEZ_GITA:-0} == 1 ]]; then BEZ_GITA=1; fi

# --- ścieżki: wszystko względem położenia skryptu (a nie PATH ani katalogu bieżącego) ---
SKRYPT_DIR=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)
if ! REPO=$(cd "${AUTOMAT_REPO:-$SKRYPT_DIR/..}" 2>/dev/null && pwd -P); then
  echo "Błąd: katalog repo nie istnieje: ${AUTOMAT_REPO:-$SKRYPT_DIR/..}" >&2
  exit 1
fi
PY="$REPO/.venv/bin/python"
UNIWERSUM="$(dirname "$REPO")/alpha/data/raw/universe_full" # alpha: tylko odczyt (zasada 23)
DOM=${HOME:-$(getent passwd "$(id -u)" | cut -d: -f6)}
LOG_DIR=${AUTOMAT_LOG_DIR:-$DOM/beta_logi}
if ! mkdir -p "$LOG_DIR"; then
  echo "Błąd: nie mogę utworzyć katalogu logów: $LOG_DIR" >&2
  exit 1
fi
LOG_PLIK="$LOG_DIR/${DZIEN}_${TRYB}.log"
exec 3>>"$LOG_PLIK"

# --- log: każda linia ze znacznikiem czasu UTC, do pliku i na stdout (zerwany stdout: bez błędu)
log() {
  local linia
  printf -v linia '%(%Y-%m-%dT%H:%M:%SZ)T [%s] %s' -1 "$TRYB" "$*"
  printf '%s\n' "$linia" >&3
  printf '%s\n' "$linia" || true
}

blad() { # blad <komunikat> [kod]
  log "BŁĄD: $1"
  exit "${2:-1}"
}

TMP_DIR=""
PRACA_PGID="" # grupa procesów trwającego kroku (puste, gdy żaden nie trwa)
zakoncz() { # jedna linia statusu na końcu każdego uruchomienia
  local kod=$? wynik=OK znacznik
  trap - EXIT ERR
  if (( kod != 0 )); then wynik=BLAD; fi
  if (( kod == 0 )); then
    log "STATUS: OK"
  else
    log "STATUS: BLAD (kod wyjścia $kod)"
    echo "[beta automat] tryb $TRYB: BŁĄD (kod $kod) — log: $LOG_PLIK" >&2
  fi
  printf -v znacznik '%(%Y-%m-%dT%H:%M:%SZ)T' -1
  echo "$znacznik $TRYB $wynik kod=$kod log=$LOG_PLIK" \
    >"$LOG_DIR/ostatni_status_${TRYB}.txt" || true
  if [[ -n $TMP_DIR ]]; then rm -rf "$TMP_DIR"; fi
  exit "$kod"
}
zglos_blad() { # nieprzewidziana porażka polecenia (set -e) — ślad w logu
  local kod=$1
  log "BŁĄD: polecenie zawiodło (kod $kod, linia $2): $3"
}
przerwij() { # przerwij <kod> — sygnał dla skryptu: zabij trwający krok (całą grupę) i skończ
  local kod=$1
  trap - TERM INT HUP
  if [[ -n $PRACA_PGID ]]; then
    log "Sygnał — przerywam trwający krok (grupa procesów $PRACA_PGID)."
    kill -TERM -- "-$PRACA_PGID" 2>/dev/null || true
    for _ in 1 2 3 4 5 6 7 8 9 10; do # krok ignorujący TERM: bez `wait`, które by na niego czekało
      kill -0 -- "-$PRACA_PGID" 2>/dev/null || break
      sleep 0.5
    done
    kill -KILL -- "-$PRACA_PGID" 2>/dev/null || true
    wait 2>/dev/null || true
  fi
  exit "$kod"
}
trap zakoncz EXIT
trap 'zglos_blad "$?" "$LINENO" "$BASH_COMMAND"' ERR
trap 'przerwij 143' TERM
trap 'przerwij 130' INT
trap 'przerwij 129' HUP

# uruchom <opis> <polecenie...> — wyjście polecenia trafia do logu linia po linii; zwraca jego kod.
# Polecenie idzie w tle (`wait` pozwala przerwać je sygnałem od razu) i nie dziedziczy deskryptorów
# blokady (9) ani logu (3): osierocony potomek nie trzyma blokady po śmierci skryptu. Pętla logu
# blokadę dziedziczy i trzyma ją, dopóki krok żyje: po `kill -9` skryptu (np. OOM) krok nie biegnie
# dalej bez blokady, a następny bieg poczeka.
uruchom() {
  local opis=$1 kod=0 l
  shift
  log "KROK: $opis"
  # Pętla logu ignoruje TERM: `timeout` zabija całą grupę kroku, a loger ma przeżyć (status 124).
  "$@" 2>&1 9>&- 3>&- | {
    trap '' TERM
    while IFS= read -r l || [[ -n $l ]]; do log "| $l"; done
  } &
  PRACA_PGID=$(jobs -p)
  wait "$!" || kod=$?
  PRACA_PGID=""
  return "$kod"
}

# --- blokada: jeden bieg naraz (wszystkie tryby dzielą jeden plik) ---
exec 9>"$LOG_DIR/.automat.lock"
if ! flock -n 9; then
  log "Blokada zajęta — działa inny bieg automatu; czekam do ${CZEKAJ} s."
  if ! flock -w "$CZEKAJ" 9; then
    blad "blokada nadal zajęta po ${CZEKAJ} s — rezygnuję (inny bieg trwa; spróbuj później)" 75
  fi
fi

# --- opis trybu: polecenie, pliki wyniku, komunikat commita ---
przygotuj_tryb() {
  case "$TRYB" in
    codziennie)
      MODULY="dane.deribit_dvol"
      OPIS_KROKU="DVOL BTC/ETH do $DZIEN (pełne dni UTC)"
      KROK_CMD=("$PY" -m dane.deribit_dvol --koniec "$DZIEN")
      WYNIKI=(dane/manifest_deribit_dvol.json)
      OPIS_COMMITA="Dane: manifest DVOL BTC/ETH z $DZIEN (automat)"
      ;;
    miesiac)
      # Bieg przyrostowy (zadanie 015): tylko miesiące po ostatnim w manifeście (zwykle jeden nowy
      # miesiąc, kilka minut), doklejone do parquetów; zapis atomowy. Parquet niezgodny z SHA-256
      # w manifeście = błąd pary (bez cichej naprawy). Nic nowego = manifest bez zmian, brak commita.
      # Przerwany bieg (limit kroku, kill) albo świeca nachodząca na granicy miesięcy = błędy par
      # co miesiąc, aż ktoś uruchomi ręcznie pełny bieg (bez --przyrostowo, ~32 min).
      # Lista symboli = suma składów top-20 z alpha universe_full (kończy się na 2026-06: nowe
      # wejścia po tej dacie nie są pobierane, dopóki alpha go nie odświeży — decyzja użytkownika).
      MODULY="dane.binance_vision, yaml, narzedzia"
      OPIS_KROKU="Binance top-20 (5m, 1d) do $MIESIAC"
      KROK_CMD=("$PY" -m dane.binance_vision --tf 5m 1d --uniwersum "$UNIWERSUM" --top 20
        --watki 16 --przyrostowo --koniec "$MIESIAC")
      WYNIKI=(dane/manifest_binance_um.json dane/sklad_top20.json)
      OPIS_COMMITA="Dane: manifest Binance top-20 do $MIESIAC (automat)"
      ;;
    niedziela)
      MODULY="raporty.tydzien"
      RAPORT="raporty/tygodnie/${ETYKIETA}.md"
      OPIS_KROKU="raport tygodniowy $ETYKIETA"
      KROK_CMD=("$PY" -m raporty.tydzien --data "$DZIEN")
      WYNIKI=("$RAPORT")
      OPIS_COMMITA="Raport tygodniowy $ETYKIETA (automat)"
      ;;
  esac
}

# SHA gałęzi $GALAZ na origin (stdout); kod 2 = origin nie ma tej gałęzi. Stderr gita idzie do logu.
zdalny_sha() {
  timeout 60 git -C "$REPO" ls-remote --exit-code origin "refs/heads/$GALAZ" 2>&3 |
    cut -f1
}

# --- git: kontrole przed pracą (żeby nie pobierać godzinę i dopiero potem odkryć brak remote) ---
git_kontrola() {
  local korzen stan kod=0
  korzen=$(git -C "$REPO" rev-parse --show-toplevel 2>/dev/null) || korzen=""
  if [[ -z $korzen || $(readlink -f "$korzen") != "$REPO" ]]; then
    blad "$REPO nie jest korzeniem repo git (commit w cudzym repo odrzucony)"
  fi
  GALAZ=$(git -C "$REPO" symbolic-ref --short -q HEAD || true)
  if [[ -z $GALAZ ]]; then blad "HEAD odłączony — brak bieżącej gałęzi do wypchnięcia"; fi
  if [[ $GALAZ == main || $GALAZ == master ]] && [[ ${AUTOMAT_PUSH_MAIN:-0} != 1 ]]; then
    blad "gałąź $GALAZ: scalenie do main idzie przez PR; zmień gałąź lub ustaw AUTOMAT_PUSH_MAIN=1"
  fi
  for stan in MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD rebase-merge rebase-apply; do
    if [[ -e $(git -C "$REPO" rev-parse --git-path "$stan") ]]; then
      blad "trwa operacja git ($stan) — częściowy commit niemożliwy; dokończ albo przerwij ją"
    fi
  done
  if ! git -C "$REPO" remote get-url origin >/dev/null 2>&1; then
    blad "brak zdalnego repo 'origin' — nie mam gdzie wypchnąć"
  fi
  zdalny_sha >/dev/null || kod=$?
  case $kod in
    0) ;;
    2) blad "gałąź $GALAZ nie istnieje na origin — wypchnij ją raz ręcznie (git push -u origin \
$GALAZ); automat nie zakłada nowych gałęzi zdalnych" ;;
    *) blad "brak dostępu do origin (kod $kod; szczegóły w logu) — sprawdź SSH i sieć" "$kod" ;;
  esac
}

sprawdz_srodowisko() {
  local narz kod=0
  for narz in git flock timeout date readlink; do
    if ! command -v "$narz" >/dev/null 2>&1; then blad "brak narzędzia: $narz"; fi
  done
  if [[ ! -x $PY ]]; then blad "brak interpretera Pythona: $PY"; fi
  uruchom "import: $MODULY" "$PY" -c "import $MODULY" || kod=$?
  if (( kod != 0 )); then blad "środowisko Pythona nie przechodzi importu ($MODULY)" "$kod"; fi
  if [[ $TRYB == miesiac && ! -d $UNIWERSUM ]]; then
    blad "brak katalogu uniwersum alpha: $UNIWERSUM"
  fi
  if (( BEZ_GITA == 0 )); then git_kontrola; fi
}

pokaz_plan() {
  local pelne
  printf -v pelne '%q ' "${KROK_CMD[@]}"
  pelne=${pelne% }
  log "[DRY-RUN] tryb=$TRYB dzień=$DZIEN repo=$REPO"
  log "[DRY-RUN] krok: $OPIS_KROKU"
  log "[DRY-RUN] polecenie: $pelne"
  log "[DRY-RUN] limity: krok ${LIMIT_KROKU} s, push ${LIMIT_PUSH} s, blokada ${CZEKAJ} s"
  log "[DRY-RUN] pliki wyniku: ${WYNIKI[*]}"
  if (( BEZ_GITA )); then
    log "[DRY-RUN] git pominięty (AUTOMAT_BEZ_GITA=1)"
  else
    log "[DRY-RUN] commit: \"$OPIS_COMMITA\" tylko dla plików wyniku"
    log "[DRY-RUN] push: origin refs/heads/$GALAZ (bez wymuszania); odczyt origin działa"
  fi
  log "[DRY-RUN] nic nie pobrano, nic nie zatwierdzono."
}

# --- raport tygodniowy: komentarz Claude musi przeżyć ponowne generowanie ---
komentarz() { sed -n '/<!-- komentarz -->/,/<!-- \/komentarz -->/p' "$1"; }

niedziela_przed() {
  TMP_DIR=$(mktemp -d)
  # Niezatwierdzone zmiany w raporcie to np. komentarz w trakcie pisania — nie publikujemy go.
  if (( BEZ_GITA == 0 )) && [[ -n $(git -C "$REPO" status --porcelain -- "$RAPORT") ]]; then
    blad "$RAPORT ma niezatwierdzone zmiany (np. komentarz w trakcie pisania) — nie nadpisuję i \
nie publikuję; zatwierdź plik (git add + commit) albo cofnij zmiany i uruchom ponownie"
  fi
  if [[ -f $RAPORT ]]; then
    cp -p "$RAPORT" "$TMP_DIR/stary.md"
    komentarz "$RAPORT" >"$TMP_DIR/komentarz_przed.txt"
  fi
}

niedziela_po() {
  if [[ ! -f $RAPORT ]]; then blad "generator nie utworzył pliku $RAPORT"; fi
  # Poprzedni plik bez bloku komentarza (pusty `komentarz_przed`) nie ma czego chronić.
  if [[ -s $TMP_DIR/komentarz_przed.txt ]]; then
    komentarz "$RAPORT" >"$TMP_DIR/komentarz_po.txt"
    if ! cmp -s "$TMP_DIR/komentarz_przed.txt" "$TMP_DIR/komentarz_po.txt"; then
      cp -p "$TMP_DIR/stary.md" "$RAPORT"
      blad "generator zmienił blok komentarza Claude — przywróciłem poprzednią wersję pliku"
    fi
  fi
}

# --- miesiąc: czy pobranie jest kompletne (downloader traktuje brak miesiąca jak 404, bez błędu)
kontrola_miesiaca() {
  local kod=0
  uruchom "kontrola kompletności pobrania do $MIESIAC" "$PY" -c \
    'from narzedzia import kontrola_miesiaca as k; import sys; sys.exit(k(*sys.argv[1:]))' \
    dane/manifest_binance_um.json dane/sklad_top20.json "$MIESIAC" || kod=$?
  if (( kod != 0 )); then
    blad "pobranie niekompletne (patrz wyżej) — nie zatwierdzam manifestu; w drzewie zostaje jego \
niezatwierdzona wersja" "$kod"
  fi
}

# --- git: commit i push tylko plików wyniku ---
git_z_ponowieniem() { # git_z_ponowieniem <opis> <argumenty git...> — 3 próby (np. index.lock)
  local opis=$1 proba kod=0
  shift
  for proba in 1 2 3; do
    kod=0
    uruchom "$opis" git -C "$REPO" "$@" || kod=$?
    if (( kod == 0 )); then return 0; fi
    if (( proba < 3 )); then
      log "Próba $proba z 3 nieudana (kod $kod) — ponowię za ${PONOW_S} s."
      sleep "$PONOW_S"
    fi
  done
  return "$kod"
}

odepnij_wyniki() { # po nieudanym commicie pliki wyniku nie zostają w indeksie (w drzewie tak)
  git -C "$REPO" reset -q -- "${WYNIKI[@]}" >/dev/null 2>&1 || true
  log "Cofnięto dodanie plików wyniku do indeksu; pliki w drzewie roboczym są niezatwierdzone."
}

git_wypchnij() {
  local zdalny glowa zakres plik kod=0
  zdalny=$(zdalny_sha) || blad "nie mogę odczytać gałęzi $GALAZ z origin (kod $?)"
  glowa=$(git -C "$REPO" rev-parse HEAD)
  if [[ $zdalny == "$glowa" ]]; then
    log "origin/$GALAZ ma już ten sam commit co HEAD ($glowa) — nic do wypchnięcia."
    return 0
  fi
  uruchom "git fetch origin $GALAZ" timeout 120 \
    git -C "$REPO" fetch -q origin "refs/heads/$GALAZ" || kod=$?
  if (( kod != 0 )); then blad "git fetch nie powiódł się" "$kod"; fi
  if git -C "$REPO" merge-base --is-ancestor "$glowa" "$zdalny" 2>/dev/null; then
    log "origin/$GALAZ jest przed lokalną gałęzią — nie ma lokalnych commitów do wypchnięcia."
    return 0
  fi
  if ! git -C "$REPO" merge-base --is-ancestor "$zdalny" "$glowa" 2>/dev/null; then
    blad "origin/$GALAZ i lokalna gałąź się rozeszły (są commity po obu stronach) — nie wypycham; \
zrób ręcznie git pull --rebase i uruchom automat ponownie"
  fi
  zakres="$zdalny..$glowa"
  if [[ -n $(git -C "$REPO" rev-list --merges "$zakres") ]]; then
    blad "wśród niewypchniętych commitów jest scalenie (merge) — nie wypycham; sprawdź ręcznie"
  fi
  while IFS= read -r plik; do
    if [[ -n $plik && ! $plik =~ $DOZWOLONE ]]; then
      blad "niewypchnięty commit dotyka pliku spoza wyniku automatu ($plik) — nie wypycham; \
wypchnij ręcznie albo usuń commit"
    fi
  done < <(git -C "$REPO" log --no-merges --no-renames --name-only --format= "$zakres")
  uruchom "git push origin $GALAZ" timeout --kill-after=30 "$LIMIT_PUSH" \
    git -C "$REPO" push origin "$glowa:refs/heads/$GALAZ" || kod=$?
  if (( kod != 0 )); then
    blad "push nie powiódł się (kod $kod) — commit zostaje lokalnie; następny bieg ponowi push, \
a jeśli zdalna gałąź się rozeszła, trzeba ręcznie git pull --rebase" "$kod"
  fi
  zdalny=$(zdalny_sha) || blad "nie mogę zweryfikować origin po pushu (kod $?)"
  if [[ $zdalny != "$glowa" ]]; then
    blad "po pushu origin/$GALAZ ($zdalny) różni się od HEAD ($glowa)"
  fi
  log "Wypchnięto: origin/$GALAZ = $glowa."
}

git_zatwierdz_i_wypchnij() {
  local sciezka zmiany biezaca kod=0
  # Gałąź mogła się zmienić podczas kroku (godziny pobierania) — nie commitujemy na cudzej.
  biezaca=$(git -C "$REPO" symbolic-ref --short -q HEAD || true)
  if [[ $biezaca != "$GALAZ" ]]; then
    blad "gałąź zmieniła się w trakcie biegu ($GALAZ -> ${biezaca:-HEAD odłączony}); nie commituję"
  fi
  for sciezka in "${WYNIKI[@]}"; do
    if [[ ! $sciezka =~ $DOZWOLONE ]]; then blad "niedozwolona ścieżka wyniku: $sciezka"; fi
    if [[ ! -f $REPO/$sciezka ]]; then blad "krok się powiódł, ale brak pliku wyniku: $sciezka"; fi
  done
  git_z_ponowieniem "git add (tylko pliki wyniku)" add -- "${WYNIKI[@]}" || kod=$?
  if (( kod != 0 )); then
    odepnij_wyniki
    blad "git add nie powiódł się" "$kod"
  fi
  zmiany=$(git -C "$REPO" status --porcelain --untracked-files=all -- "${WYNIKI[@]}")
  if [[ -z $zmiany ]]; then
    log "Brak zmian w plikach wyniku — nie ma czego zatwierdzać."
  else
    git_z_ponowieniem "git commit: $OPIS_COMMITA" \
      commit -q -m "$OPIS_COMMITA" -- "${WYNIKI[@]}" || kod=$?
    if (( kod != 0 )); then
      odepnij_wyniki
      blad "git commit nie powiódł się" "$kod"
    fi
    uruchom "zatwierdzono" git -C "$REPO" show --stat --format='%h %s' --no-patch HEAD || true
  fi
  git_wypchnij
}

main() {
  local kod=0
  cd "$REPO"
  przygotuj_tryb
  log "START tryb=$TRYB dzień=$DZIEN dry_run=$DRY_RUN bez_gita=$BEZ_GITA log=$LOG_PLIK"
  sprawdz_srodowisko
  if (( DRY_RUN )); then
    pokaz_plan
    return 0
  fi
  if [[ $TRYB == niedziela ]]; then niedziela_przed; fi
  uruchom "$OPIS_KROKU" timeout --kill-after=60 "$LIMIT_KROKU" "${KROK_CMD[@]}" ||
    kod=$?
  if (( kod == 124 )); then
    blad "krok '$OPIS_KROKU' przekroczył limit czasu (${LIMIT_KROKU} s) i został przerwany" "$kod"
  fi
  if (( kod != 0 )); then blad "krok '$OPIS_KROKU' zakończył się kodem $kod" "$kod"; fi
  if [[ $TRYB == niedziela ]]; then niedziela_po; fi
  if [[ $TRYB == miesiac ]]; then kontrola_miesiaca; fi
  if (( BEZ_GITA )); then
    log "AUTOMAT_BEZ_GITA=1 — pomijam commit i push."
  else
    git_zatwierdz_i_wypchnij
  fi
}

main
