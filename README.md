<p align="center">
  <img src="static/logo.svg" alt="University Enrollment System" width="300" />
</p>

# University Enrollment System

[![CI](https://github.com/sidneyebuenaventura/university-enrollment-system/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/sidneyebuenaventura/university-enrollment-system/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/sidneyebuenaventura/university-enrollment-system/badges/coverage.json)](https://github.com/sidneyebuenaventura/university-enrollment-system/actions/workflows/ci.yml)

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
make seed        # demo data, see below
```

### Demo data

`make seed` (or `python manage.py seed_demo`) fills an empty database with a
small university to click through:

- Two schools with a 4-year curriculum each (Computer Science and
  Accountancy), faculty, rooms and class schedules
- Four school years, with the first semester of the current one in progress
  and enrollment for the second semester open
- 40 students with grades for past terms, statements of account, and bank and
  cashier payments. Some still owe money for this semester and some have
  already enrolled for the next one.

| Account | Username | Password |
|---|---|---|
| Admin (also Django admin) | `admin` | `demo1234` |
| Student, ready to enroll | `student` | `demo1234` |

Dates are based on the day you seed, so the demo always has an open
enrollment. Pass `--students` to change the number of students, or `--seed`
for different names and grades. The command refuses to run on a database that
already has data.

To start from an empty database instead, run `make init` for the default
modules, permissions and roles, then create an admin user with
`docker compose exec core python manage.py createsuperuser`.

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

Code is formatted and linted with [Ruff](https://docs.astral.sh/ruff/). Install
the git hooks so it runs on every commit:

```bash
uv run pre-commit install
```

### Production image

The default Docker build target is the production image. It has the code
and collected static files baked in, runs as a non-root user, and starts
gunicorn on `$PORT` (8000 if unset). Docker Compose uses the `dev` target
instead, which mounts the code and runs the dev server.

```bash
docker build -t university .
docker run university migrate                      # run before each release
docker run -p 8000:8000 university                 # core API
docker run university runworker                    # Celery worker
docker run university python manage.py run_core    # event consumers, same for the others
```

Settings are passed as environment variables. The image doesn't include
`.env`.

## Configuration

Settings come from environment variables (see [.env.example](.env.example)).
Set `UNIVERSITY_NAME` and `UNIVERSITY_STUDENT_PORTAL_URL` for your school, and
the `NOTIFICATION_MESSAGE_*` values for the contact details shown in emails.

Students pay by bank transfer or in cash at the cashier. The Dragonpay and
Bukas integrations are still in the code but turned off. To turn them back
on, add `DP` or `B` to `UNIVERSITY_PAYMENT_METHODS` and set the
`PAYMENT_DRAGONPAY_*` or `PAYMENT_BUKAS_*` values.
