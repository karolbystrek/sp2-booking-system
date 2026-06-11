# Prompty do korekty: architecture_output_gpt.md

---

## Prompt 1 – Po analizie domen i encji

Wyodrębniłeś aż sześć domen, w tym osobny Appointment Management. Zastanów się, czy naprawdę potrzebujesz oddzielnego kontekstu dla samej wizyty — w systemie rezerwacji wizyta (Appointment/Slot) jest bezpośrednio zarządzana przez Schedule Management, a jej rezerwacja przez Booking Management. Osobny kontekst Appointment Management tylko komplikuje model i duplikuje odpowiedzialności. Uprość do czterech lub pięciu kontekstów: Booking, Schedule, Identity & Access, Configuration/Rules i Audit — i jasno przypisz statusy AVAILABLE/BOOKED/BLOCKED/COMPLETED do slotu (Schedule), a nie do osobnej encji Appointment.

---

## Prompt 2 – Po zaproponowaniu komponentów i ich komunikacji

Diagram komunikacji w twoim projekcie jest bardzo uproszczony i schodzi do sekwencji liniowej (Authentication → Booking → Schedule → Configuration → Audit), co nie do końca oddaje rzeczywiste zależności. Booking Module powinien aktywnie odpytywać Schedule Module o dostępność slotu, a także sprawdzać w Configuration, czy użytkownik nie przekroczył limitu 3 aktywnych rezerwacji — te dwa kroki powinny być widoczne w diagramie jako synchroniczne wywołania przed zapisem rezerwacji. Dodaj też wyraźny opis, jak Audit Module odbiera zdarzenia: czy jest to wywołanie synchroniczne po każdej operacji, czy publikacja eventu?

---

## Prompt 3 – Po wygenerowaniu API i struktury danych

W tabeli APPOINTMENTS brakuje statusu `BLOCKED` — to kluczowy stan, który pozwala specjaliście zablokować slot niezależnie od rezerwacji. Dodaj go do enuma statusów. W API brakuje również endpointu dla specjalisty do blokowania slotu (`PATCH /api/schedules/{id}/block`) oraz endpointu dla admina do przeglądania logów audytowych. Struktura tabeli AUDIT_LOG używa `BIGINT` jako klucza, co jest w porządku, ale brakuje kolumny `details` jako JSON (lub TEXT z opisem stanu przed/po zmianie), co jest ważne dla pełnej rozliczalności operacji.
