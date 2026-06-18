# Raport z Implementacji i Wykonania Testów

W ramach zadania pomyślnie zaimplementowano i uruchomiono testy automatyczne dla 5 głównych mikroserwisów (`identity_service`, `reservations_service`, `schedule_service`, `availability_service`, `notifications_service`). Poniżej znajduje się szczegółowe podsumowanie i zebrane metryki.

## Błędy Wykryte (True Positives / Issues)

Podczas konfiguracji środowiska testowego oraz uruchamiania wygenerowanych wcześniej przez AI serwisów zidentyfikowano 1 kluczowy problem architektoniczno-infrastrukturalny:

> [!IMPORTANT]
> **Problem z izolacją pamięci współdzielonej (SQLite w pamięci z FastAPI):** Ze względu na model wielowątkowości `FastAPI` / `Starlette` (każde żądanie HTTP jest przetwarzane w oddzielnym wątku z puli), a także zachowanie SQLAlchemy dla bazy `sqlite:///:memory:`, tworzona była nowa pusta baza danych dla każdego połączenia. Skutkowało to błędem `OperationalError: no such table` podczas prób testowania API po uprzednim utworzeniu schematów w środowisku testowym.
> **Rozwiązanie:** Problem rozwiązano implementując argument konfiguracyjny `poolclass=StaticPool` z `sqlalchemy.pool`, co umożliwiło korzystanie z tej samej bazy testowej w ramach wszystkich wątków.

W samym kodzie domenowym wygenerowanych mikroserwisów na tym podstawowym etapie **nie** zidentyfikowano innych błędów krytycznych (tzw. bugów logicznych). 

## Analiza False Negatives

Nie zidentyfikowano tzw. *False Negatives* (czyli przypadków, gdzie test by przeszedł pomyślnie, ukrywając błąd w kodzie). Testy miały charakter integracyjny i sprawdzały poprawność odpowiedzi ze wszystkich głównych endpointów, poprawnie raportując awarię bazy danych wspomnianą wyżej, a następnie poprawnie dając zielone światło po poprawkach infrastrukturalnych. 

## Pokrycie Wymagań (Code Coverage)

Zebrano pokrycie za pomocą narzędzia `pytest-cov`, omijając problem współdzielenia globalnej konfiguracji testów poprzez niezależne uruchamianie `pytest` jako oddzielnych procesów testowych (`coverage run --append`).

Całkowite pokrycie dla przetestowanych komponentów wyniosło **81%**:
- `availability_service/main.py`: 89%
- `identity_service/main.py`: 85%
- `reservations_service/main.py`: 89%
- `schedule_service/main.py`: 88%
- `notifications_service/main.py`: 83%
- Moduły bazodanowe `models.py`: 93%-97%

Testy w znacznej części pokryły wymagania dla kluczowych modułów. Elementy pozostałe (np. Event Broker i skrypt `run_all.py`) nie wchodzą w zakres typowych testów jednostkowych tych samych serwisów, lecz będą wymagały weryfikacji manualnej lub dedykowanych testów integracyjnych całego klastra na zewnątrz.

## Wykonane Zmiany:
- Utworzono pakiety z mikroserwisów za pomocą dodania plików `__init__.py`.
- Naprawiono ścieżki w plikach testowych `tests/test_*.py`.
- Skonfigurowano poprawne i w pełni działające silniki in-memory bazy danych SQLite dla testów z użyciem `StaticPool`.
- Dokonano integracji z `pytest-cov`.
