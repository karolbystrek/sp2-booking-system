# Prompty do korekty: architecture_output_claude.md

---

## Prompt 1 – Po analizie domen i encji

Twój podział na Bounded Contexts jest generalnie sensowny, jednak Configuration Context wydaje się być zbyt osobnym bytem — w praktyce reguły anulowania i limity to nie oddzielna domena, lecz konfiguracja, którą Booking Service powinien konsumować bezpośrednio. Zastanów się, czy naprawdę potrzebujesz aż pięciu kontekstów czy może Configuration można uprościć i scalić z logiką Booking. Zwróć też uwagę, że encja Specialist powinna być raczej powiązana bezpośrednio z modelem User (jako user z rolą SPECIALIST), a nie jako zupełnie osobna encja — to upraszcza model danych i lepiej odzwierciedla wymagania.

---

## Prompt 2 – Po zaproponowaniu komponentów i ich komunikacji

W diagramie widzę, że Booking Module komunikuje się bezpośrednio ze Schedule Module po slot — i dobrze — ale nie opisałeś dokładnie, co dokładnie weryfikuje Booking Service przed zapisem rezerwacji: czy sprawdza limit 3 aktywnych rezerwacji? Czy sprawdza konflikty czasowe z innymi wizytami użytkownika (nie tylko czy slot jest dostępny)? Tego w Gold Architecture jest osobny krok. Warto też przemyśleć, czy separacja baz danych per moduł (BookingDB, ScheduleDB, etc.) jest rzeczywiście potrzebna w monolicie — wspólna relacyjna baza z logicznym podziałem na schematy jest prostsza i ułatwia transakcyjność między modułami.

---

## Prompt 3 – Po wygenerowaniu API i struktury danych

W strukturze bookings brakuje pola `created_at` oraz statusy rezerwacji powinny zawierać tylko `BOOKED` i `CANCELLED` — `COMPLETED` to status slotu, nie rezerwacji. Ważniejsza kwestia: w twoim API nie ma endpointu `PATCH /slots/{id}/block` dla specjalisty, który pozwala zablokować konkretny slot niezależnie od rezerwacji (status BLOCKED). Dodaj też do opisu przepływu rezerwacji jawny krok weryfikacji konfliktu czasowego (czy nowa wizyta nie nakłada się godzinowo na istniejące rezerwacje użytkownika) — tego kroku brakuje między sprawdzeniem dostępności slotu a zapisem rezerwacji.
