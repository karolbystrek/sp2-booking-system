# Protokół przygotowania zestawu tests/gpt

## Kontekst

- Data: 19.06.2026
- Tryb: Hybrid - model przygotował i rozszerzył testy, człowiek określił zakres oraz zaakceptował publikację.
- Narzędzie: Codex, model z rodziny GPT; dokładny identyfikator wdrożenia nie jest udostępniany w interfejsie.
- Kod wejściowy: `code/e2/gpt` @ `1ef4f8c531847a40861f7dac631d1fcb61a8b8b5`.
- Specyfikacja: `refinement/input/gold_architecture.md`.
- Materiał porównawczy: struktura `tests/gemini`; testy i wyniki nie były kopiowane mechanicznie.

## Ograniczenia zadania

- zmiany wyłącznie na gałęzi `tests/gpt`,
- bez zmian i bez merge do `main`,
- maksymalnie trzy iteracje przygotowania,
- zapis artefaktów, wyników i metryk,
- odróżnienie błędu produktu, testu i środowiska.

## Iteracje

1. Audyt istniejących sześciu testów i weryfikacja ich uruchamialności z kodem `code/e2/gpt`.
2. Rozszerzenie zestawu o API, autoryzację, grafik, rezerwacje, polityki, konflikty, audyt i współbieżność; usunięcie założeń bez pokrycia w specyfikacji.
3. Walidacja pełnego zestawu, coverage, pięciokrotne powtórzenie testu współbieżności oraz przygotowanie raportu.

## Kryteria akceptacji

- brak `importorskip` ukrywającego brak implementacji,
- izolowana baza dla każdego testu,
- uruchomienie przez publiczne endpointy FastAPI tam, gdzie jest to możliwe,
- jawne traceability defektów do Gold Architecture,
- powtarzalne środowisko i CI,
- brak wersjonowania baz danych, cache i plików coverage.

