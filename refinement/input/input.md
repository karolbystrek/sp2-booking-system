You are a senior backend engineer and software architect.

Generate a production-ready backend application strictly based on the architecture and requirements described in the following markdown document:

File: `agents/architecture_output.md`

IMPORTANT:

* Do NOT redesign or reinterpret the architecture.
* Use the markdown document as the single source of truth for business logic, domains, APIs, entities, workflows, and constraints.
* Preserve all bounded contexts, services, entities, flows, and API contracts described in the document unless implementation adaptation is technically required.

Mandatory technology stack:

* Python
* FastAPI
* SQLite
* SQLAlchemy
* JWT authentication
* uv

Technical requirements:

* Use clean architecture principles.
* Use modular project structure.
* Use Pydantic models for validation.
* Use Alembic migrations.
* Use environment-based configuration.
* Implement JWT access and refresh tokens.
* Add role-based authorization.
* Include OpenAPI/Swagger documentation.
* Implement proper exception handling and validation.
* Add logging.
* Add Docker support.
* Add unit tests for core business logic.
* Use async endpoints where appropriate.
* Follow RESTful API conventions.

Implementation requirements:

* Generate complete backend code, not pseudo-code.
* Create all required database models.
* Create all required API endpoints.
* Create authentication and authorization flows.
* Implement repositories/services/controllers separation.
* Implement DTO/schema layer.
* Implement database initialization and migrations.
* Add example `.env` file.
* Add README with setup instructions.

Database requirements:

* Use SQLite for persistence.
* Use SQLAlchemy ORM.
* Design schemas according to the architecture document.

Authentication requirements:

* JWT authentication must be implemented manually or with FastAPI-compatible libraries.
* Support roles:

  * Patient
  * Specialist
  * Administrator

Output requirements:

* Generate the complete project structure.
* Include all source files.
* Include installation instructions.
* Include commands to run the project locally.

Do not replace the specified technologies with alternatives mentioned in the architecture document.
The required stack is:
Python + FastAPI + SQLite + JWT + uv.
