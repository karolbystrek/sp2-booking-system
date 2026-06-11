# Prompty do korekty: architecture_output(gemini).md

---

## Prompt 1 – Po analizie domen i encji

Wyodrębniłeś siedem domen i od razu zaproponowałeś architekturę mikroserwisów. To jest prawdopodobnie zbyt dużo jak na system rezerwacji wizyt tej skali — 7 osobnych serwisów, każdy z własną bazą danych i brokerem wiadomości to ogromny overhead operacyjny. Zastanów się nad Modular Monolith: te same domeny mogą być modułami wewnątrz jednej aplikacji z jedną relacyjną bazą danych. Reporting & Analytics i System Configuration to nie muszą być osobne bounded contexts — reporting to widok na dane audytowe, a konfiguracja to tabela z parametrami. Uprość do 4-5 kluczowych domen: Identity & Access, Booking, Schedule/Availability, Audit.

---

## Prompt 2 – Po zaproponowaniu komponentów i ich komunikacji

Architektura mikroserwisów wymaga od ciebie rozwiązania distributed transactions — jak zapewnisz, że rezerwacja slotu w Scheduling Service i zapis Booking w Appointment Service są atomowe? W Gold Architecture to jest rozwiązane przez jedną bazę SQL z transakcją. Jeśli trzymasz się mikroserwisów, musisz wyjaśnić, jak unikasz double booking między serwisami. Alternatywnie przemyśl powrót do Modular Monolith — masz dużo lepszą kontrolę spójności, prostszy deployment i podobną modularność. Appointment Service i Scheduling Service mogą być modułami w jednej aplikacji komunikującymi się przez wywołania metod, nie przez HTTP.

---

## Prompt 3 – Po wygenerowaniu API i struktury danych

W projekcie API i baz danych dla Scheduling Service brakuje statusu `BLOCKED` dla slotu — jest AVAILABLE, BOOKED, CANCELLED ale nie BLOCKED. Specjalista musi mieć możliwość zablokowania slotu niezależnie od rezerwacji (np. urlop, przerwa). Dodaj ten status i endpoint `PATCH /slots/{id}/block`. W modelu danych Booking/Appointment brakuje pola `created_at` i nie ma jawnego ograniczenia uniemożliwiającego podwójną rezerwację (UNIQUE constraint na slot_id w tabeli rezerwacji). Dodaj też endpoint `GET /audit-logs` dla administratora, bo logi audytowe są kluczowym wymaganiem a brakuje do nich API.
