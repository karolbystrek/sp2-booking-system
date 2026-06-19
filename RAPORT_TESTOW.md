# Raport testów E2 - GPT

## Zakres

Zestaw testuje implementację z gałęzi `code/e2/gpt` w trybie PIPELINE. Testy uruchamiają rzeczywiste endpointy FastAPI przez `TestClient`, korzystając z osobnej, świeżo seedowanej bazy SQLite dla każdego przypadku.

Obszary objęte testami:

- Identity & Access: logowanie, tokeny, role, autoryzacja i katalog specjalistów,
- Scheduling: grafik, walidacja przedziałów, wyjątki i dostępność,
- Booking: limity, konflikty, anulowanie, izolacja danych i współbieżność,
- Policy Configuration: wersjonowanie polityki rezerwacji,
- Conflict Management: tworzenie, listowanie i usuwanie wyjątków,
- Audit: zapis zdarzeń oraz filtrowanie logów.

## Wynik wykonania

Komenda:

```bash
python -m pytest --cov=src --cov-report=term-missing --cov-report=xml
```

Wynik z 19.06.2026:

- 49 przypadków testowych,
- 47 `PASSED`,
- 2 `XFAIL` - potwierdzone, znane defekty produktu,
- 0 błędów konfiguracji i kolekcji,
- 98% łącznego code coverage dla `src/`.

Pokrycie modułów:

| Moduł | Coverage |
|---|---:|
| `src/audit/api/routes.py` | 88% |
| `src/booking/api/routes.py` | 95% |
| `src/conflict_management/api/routes.py` | 100% |
| `src/identity_access/api/routes.py` | 97% |
| `src/main.py` | 100% |
| `src/policy_configuration/api/routes.py` | 100% |
| `src/scheduling/api/routes.py` | 100% |
| `src/shared/api.py` | 100% |
| `src/shared/database.py` | 100% |
| `src/shared/security.py` | 100% |

## Wykryte defekty produktu

### D1 - brak synchronizacji terminów po usunięciu grafiku

Test: `test_removing_schedule_removes_future_available_slots`

Po ustawieniu pustego grafiku specjalisty w bazie pozostaje 40 terminów ze statusem `AVAILABLE`. Jest to niespójne z inwariantem Gold Architecture: wolne terminy powinny wynikać z aktualnego grafiku pomniejszonego o aktywne rezerwacje.

### D2 - brak wykrywania nakładających się rezerwacji użytkownika

Test: `test_overlapping_reservation_for_same_user_is_rejected`

System pozwala temu samemu użytkownikowi utworzyć dwie aktywne rezerwacje o nachodzących na siebie przedziałach czasu. Jest to niespójne z odpowiedzialnością Conflict Management Context, według której rezerwacja konfliktowa powinna zostać odrzucona.

Oba przypadki oznaczono `xfail(strict=True)`. Dzięki temu znane defekty są jawne, CI pozostaje użyteczne, a naprawa kodu spowoduje `XPASS` i wymusi usunięcie nieaktualnego oznaczenia.

## Weryfikacja współbieżności

Test `test_concurrent_booking_allows_exactly_one_active_reservation` równolegle wysyła dwa żądania rezerwacji tego samego terminu przez różnych użytkowników. Oczekiwany rezultat to dokładnie jedno `201 Created`, jedno `409 Conflict` oraz jedna aktywna rezerwacja w bazie.

Test został dodatkowo wykonany pięć razy niezależnie i za każdym razem zakończył się powodzeniem.

## False positives i false negatives

- Nie sklasyfikowano żadnego nieuzasadnionego failure jako błędu produktu.
- Wcześniejsze oczekiwania dotyczące duplikatu roli i zachowania statusu `BLOCKED` po anulowaniu usunięto, ponieważ nie miały jednoznacznego oparcia w Gold Architecture.
- Liczby false negatives nie można wiarygodnie wyznaczyć bez referencyjnego katalogu zasianych defektów lub mutation testingu. Zielony test nie stanowi dowodu braku niewykrytych błędów.

## Ograniczenia

- Testy wydajnościowe i długotrwałe obciążenie pozostają poza zakresem tego zestawu.
- Współbieżność sprawdzono dla krytycznego przypadku double booking, nie dla pełnego profilu obciążenia.
- Ostrzeżenia deprecacyjne FastAPI/Starlette dotyczą zależności i nie wpływają na wynik testów.

## Powtarzalność

Gałąź zawiera:

- kod odpowiadający `code/e2/gpt`,
- komplet testów,
- przypięte wersje zależności,
- konfigurację `pytest`,
- workflow GitHub Actions,
- macierz pokrycia wymagań w `TEST_MATRIX.md`.

Nie są wersjonowane pliki baz danych, `.coverage`, cache ani środowiska wirtualne.

