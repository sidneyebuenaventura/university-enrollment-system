<p align="center">
  <img src="static/logo.svg" alt="University Enrollment System" width="300" />
</p>

# University Enrollment System

Backend for a university's admin portal and student portal. Handles curriculum
and class setup, enrollment, fees and payments, grades, and student requests.
It runs as a few Django services that talk to each other through RabbitMQ.

## Features

- Users, roles and module permissions for admin staff
- Schools, departments, personnel, academic years and semesters
- Courses, curricula, subjects and prerequisites, classes, schedules and rooms
- Enrollment with schedules, discounts and status tracking
- Grade sheets and GWA computation
- Student requests (change schedule, add subject, open class, withdrawal) with
  a review flow
- Statements of account and online payments through Dragonpay and Bukas, plus
  over-the-counter and cashier payments
- Email notifications for enrollment, payment and request updates
- Audit trail of create/update/delete events

## Architecture

One codebase, deployed as several services:

| Service | Port | What it does |
|---|---|---|
| `core` | 8000 | Main REST API and Django admin |
| `payment` | 8001 | Payment API and provider callbacks |
| `core_consumer` | | Handles events for the core service |
| `notification` | | Sends emails from events |
| `audit_trail` | | Writes audit logs from events |
| `worker`, `beat` | | Celery workers and scheduled tasks |

Postgres is the database, RabbitMQ carries both the events and the Celery
queue, and MailHog catches emails locally.

The code follows the [HackSoft Django Style Guide](https://github.com/HackSoftware/Django-Styleguide).
Business logic goes in `services.py`, queries in `selectors.py`, and views
stay thin.

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

Python 3.12, Django 5.2, Django REST Framework, PostgreSQL, RabbitMQ, Celery,
drf-spectacular (OpenAPI), Docker Compose, uv, pytest

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

### Without Docker

Dependencies are managed with [uv](https://docs.astral.sh/uv/). You still need
a Postgres database, and RabbitMQ for the event consumers.

```bash
uv sync
uv run python manage.py migrate
uv run pytest
```

## Configuration

Settings come from environment variables (see [.env.example](.env.example)).
Set `UNIVERSITY_NAME` and `UNIVERSITY_STUDENT_PORTAL_URL` for your school, and
the `NOTIFICATION_MESSAGE_*` values for the contact details shown in emails.
