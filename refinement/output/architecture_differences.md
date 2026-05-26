# Comparison between Architecture Design (architecture_output.md) and Implementation in app/

This document provides a detailed comparison between the system architecture described in `architecture_output.md` and the actual implementation in the `app/` directory.

---

## 1. System Architecture (Monolith vs. Microservices)

*   **Design (architecture_output.md):**
    *   Proposes a **microservices architecture**. Each Bounded Context should function as a separate, independent microservice (`Identity & Access`, `Schedule Management`, `Reservations`, `Appointment Availability`, `Notifications`) with its own deployment lifecycle.
    *   Includes an **API Gateway** acting as a single entry point for clients, handling routing, authorization, and load balancing.
*   **Implementation (app/):**
    *   Implemented as a **modular monolith** within a single FastAPI application.
    *   All routers are imported and registered directly on a single `FastAPI` instance in `app/main.py`.
    *   There is no separate API Gateway component; routing is handled natively by FastAPI.

---

## 2. Communication Mechanism (Event-Driven Architecture)

*   **Design (architecture_output.md):**
    *   Inter-service communication is designed to be asynchronous, running through a full-fledged message bus (**Message Broker**, e.g., **Apache Kafka** or **RabbitMQ**).
    *   Services subscribe to events like `SpecialistScheduleUpdated`, `ReservationCreated`, and `ReservationCancelled` to synchronize data models and trigger notifications.
*   **Implementation (app/):**
    *   Uses an **In-Memory Event Bus** managed inside the application process, implemented in `app/events.py`.
    *   Events are handled asynchronously using `asyncio.create_task` within the same Python process. There are no external message broker dependencies.

---

## 3. Databases and the CQRS Pattern

*   **Design (architecture_output.md):**
    *   Recommends a **Database-per-Service** pattern (each microservice has its own isolated database, predominantly PostgreSQL).
    *   For the availability service (`Appointment Availability Service`), it proposes using the **CQRS (Command Query Responsibility Segregation)** pattern with a dedicated, query-optimized read store (such as **Elasticsearch** or **NoSQL/MongoDB**), updated asynchronously via events.
*   **Implementation (app/):**
    *   Uses a single, shared relational **SQLite** database (`booking.db` / `test_booking.db`) for all modules. All models inherit from a single SQLAlchemy Base defined in `app/database.py`.
    *   The CQRS pattern is **not implemented** in the availability module. The `get_available_appointments` method in `app/availability/service.py` queries the live tables of other modules (`users`, `specialist_details`, `specialist_schedule`, `reservations`) in real-time using SQL JOINs and calculates free slots in-memory.

---

## 4. Entity and Domain Model Differences by Context

### A. "Tożsamość i Dostęp" (Identity & Access) Context
*   **Design:** Outlines three key entities: `Użytkownik` (User), `Rola` (Role), and `Uprawnienie` (Permission).
*   **Implementation:**
    *   The **`Uprawnienie`** (Permission) entity is **entirely missing** from the code and database schema.
    *   Role management is simplified: permissions are checked using role names (Admin, Specialist, Patient) via FastAPI dependencies (the `RequireRole` class in `app/identity/auth.py`).
    *   A `specialist_details` table has been added to the database to hold specialist-specific information.

### B. "Zarządzanie Grafikiem" (Schedule Management) Context
*   **Design:** Identifies the `GrafikSpecjalisty` (Specialist Schedule) aggregate and the `BlokDostępności` (Availability Block) entity.
*   **Implementation:**
    *   The `GrafikSpecjalisty` aggregate is **not present** as a separate database model or table.
    *   All logic revolves around the `SpecialistSchedule` model (which matches `BlokDostępności`). A specialist's schedule is determined dynamically by querying blocks from this table using the `specialist_id`.

### C. "Dostępność Terminów" (Appointment Availability) Context
*   **Design:** Features the `Specjalista` (lightweight representation), `TerminDostępności` (calculated free slot), and optionally `Usługa` (Service) entities.
*   **Implementation:**
    *   The **`Usługa`** (Service) entity is **not implemented**.
    *   `TerminDostępności` is represented as a Pydantic schema `AvailableSlot` (not persisted to the database).
    *   The lightweight `Specjalista` representation is not stored separately and is instead queried from the common user tables.

### D. "Rezerwacje" (Reservations) Context
*   **Design:** Details the `Rezerwacja` (Reservation), `Pacjent` (Patient), `Specjalista` (Specialist), and `TerminWizyty` (Appointment Slot) entities.
*   **Implementation:**
    *   `Pacjent` and `Specjalista` models do not exist in this context—simple foreign keys (`patient_id`, `specialist_id`) point to the common `users` table.
    *   The `TerminWizyty` entity is not implemented separately; its attributes (`appointment_time` and `duration_minutes`) are embedded directly within the `Reservation` model.

### E. "Powiadomienia" (Notifications) Context
*   **Design:** Features `Powiadomienie` (Notification Message), `SzablonPowiadomienia` (Notification Template), and `AdresatPowiadomienia` (Recipient Contact Info).
*   **Implementation:**
    *   `Powiadomienie` is implemented as the `NotificationLog` model.
    *   `SzablonPowiadomienia` is implemented as the `NotificationTemplate` model.
    *   The `AdresatPowiadomienia` entity **does not exist** as an independent model. The recipient's email address or phone number is retrieved directly from the user's profile during event processing and written as a string under the `recipient` column in `NotificationLog`.

---

## 5. Technology Stack Differences

| Component | Technology Stack in Design | Technology Stack in Implementation |
| :--- | :--- | :--- |
| **Programming Language** | Java (Spring Boot) | Python (FastAPI) |
| **Database** | PostgreSQL, Elasticsearch, MongoDB | SQLite |
| **Message Bus** | Apache Kafka / RabbitMQ | In-Memory (FastAPI + Asyncio) |
| **Gateway** | Spring Cloud Gateway / Nginx | None (handled natively by FastAPI routing) |
| **ORM** | Spring Data JPA / Hibernate | SQLAlchemy |
