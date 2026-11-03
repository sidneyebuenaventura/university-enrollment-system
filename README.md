<p align="center">
  <img src="static/logo.svg" alt="University Enrollment System" width="300" />
</p>

# University Enrollment System

A backend for a university's admin and student portals. It covers the full
student lifecycle: curriculum management, enrollment, fees and billing, online
payments, grading, and student requests. It's built as a set of Django services
that communicate through RabbitMQ events.

## Features

- **Accounts & access control:** users, roles, and module-level permissions
  for admin staff; schools, departments, personnel, academic years, and semesters.
- **Academic catalog:** courses, curricula, subjects with prerequisites,
  classes and schedules, buildings and rooms.
- **Enrollment:** enrollment windows, a step-by-step enrollment flow, discounts,
  and enrollment status tracking.
- **Grades:** per-class grade sheets, grade states, and general weighted average (GWA).
- **Student requests:** change schedule, add subject, open class, and withdrawal,
  each with a review and approval history.
- **Billing & payments:** fee specifications, statements of account, and
  pluggable payment providers (Dragonpay, Bukas, over-the-counter, cashier).
- **Notifications:** templated emails triggered by enrollment, payment, and
  request events.
- **Audit trail:** an event-sourced activity log for every create, update, and
  delete.

## Architecture

The system is one codebase that runs as several services:

| Service | Port | Role |
|---|---|---|
| `core` | 8000 | Main REST API and Django Admin |
| `payment` | 8001 | Payment API and provider callbacks/webhooks |
| `core_consumer` | — | Consumes domain events for the core service |
| `notification` | — | Consumes events and sends emails |
| `audit_trail` | — | Consumes events and writes audit logs |
| `worker` / `beat` | — | Celery async and scheduled tasks |

Supporting infrastructure: PostgreSQL, RabbitMQ (events and the Celery broker),
and MailHog (local email capture).

The code follows the [HackSoft Django Style Guide](https://github.com/HackSoftware/Django-Styleguide):
business logic lives in `services.py`, read queries live in `selectors.py`,
and views stay thin.

```
university/
├── core/
│   ├── accounts/      # users, roles, permissions, org structure
│   ├── cms/           # courses, curricula, subjects, classes, fees
│   ├── students/      # students, enrollment, grades, requests
│   └── maintenance/   # module config, enrollment schedules
├── payment/           # statements of account, transactions, providers
├── notification/      # email channels and templates
├── audit_trail/       # activity logging
└── framework/         # shared base models, events, permissions, OpenAPI
```

## Tech stack

Python · Django · Django REST Framework · PostgreSQL · RabbitMQ · Celery ·
drf-spectacular (OpenAPI) · Docker Compose · pytest

## Getting started

Requirements: Docker and Docker Compose.

```bash
cp .env.example .env
docker compose build
docker compose up -d
make migrate
make init        # default modules, permissions, and roles
```

Create an admin user:

```bash
docker compose exec core python manage.py createsuperuser
```

### Services

- Core API: http://localhost:8000 ([API docs](http://localhost:8000/docs))
- Payment API: http://localhost:8001 ([API docs](http://localhost:8001/docs))
- Django Admin: http://localhost:8000/admin
- RabbitMQ management: http://localhost:8080
- MailHog: http://localhost:8025

### Common commands

```bash
make migrations                 # makemigrations
make migrate                    # migrate
make test                       # run the test suite
make shell                      # Django shell
docker compose exec <service> python manage.py <command>
```

See the [Makefile](Makefile) for more.

## Configuration

The institution's name and portal URLs are configured through environment
variables in `.env`, including `UNIVERSITY_NAME`, `UNIVERSITY_STUDENT_PORTAL_URL`,
and the `NOTIFICATION_MESSAGE_*` contact details. See [.env.example](.env.example).
