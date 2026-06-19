# Macierz testów E2 - GPT

| Obszar / wymaganie | Główne scenariusze | Lokalizacja |
|---|---|---|
| Uwierzytelnianie | poprawne i błędne logowanie, nieprawidłowy token, brak użytkownika | `tests/test_identity_access.py` |
| Role i autoryzacja | blokada dostępu pacjenta, operacje administratora, nieznana rola | `tests/test_identity_access.py` |
| Specjaliści | lista, szczegóły i brak zasobu | `tests/test_identity_access.py` |
| Grafik specjalisty | odczyt, aktualizacja, walidacja zakresów i nakładania | `tests/test_scheduling.py` |
| Spójność grafik -> terminy | usunięcie grafiku powinno usunąć przyszłe wolne terminy | `tests/test_scheduling.py` |
| Wyjątki grafiku | poprawne utworzenie i błędny przedział czasu | `tests/test_scheduling.py` |
| Dostępność | specjalista, data, status `AVAILABLE` | `tests/test_scheduling.py` |
| Rezerwacja | happy path, brak slotu, limit trzech aktywnych rezerwacji | `tests/test_booking_rules.py` |
| Konflikty | double booking, rezerwacja nakładająca się, zablokowany slot | `tests/test_booking_rules.py` |
| Współbieżność | dwa równoległe żądania rezerwacji jednego slotu | `tests/test_booking_rules.py` |
| Anulowanie | happy path, okno 24h, uprawnienia i override administratora | `tests/test_booking_rules.py` |
| Izolacja danych | użytkownik widzi i modyfikuje wyłącznie swoje rezerwacje | `tests/test_booking_rules.py` |
| Polityki | odczyt, walidacja i wersjonowanie aktywnej polityki | `tests/test_policy_conflict_audit.py` |
| Wyjątki konfliktów | zakres, przedział czasu, pełny CRUD | `tests/test_policy_conflict_audit.py` |
| Audyt | zdarzenia rezerwacji, anulowania, polityk oraz filtrowanie | `tests/test_booking_rules.py`, `tests/test_policy_conflict_audit.py` |

## Interpretacja statusów

- `PASSED` - zachowanie kodu jest zgodne z asercją i wymaganiem.
- `XFAIL(strict=True)` - test wykrywa udokumentowany defekt produktu.
- `FAILED` - nowa regresja, błąd testu albo nieudokumentowana rozbieżność wymagająca analizy.

