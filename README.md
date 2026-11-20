# Taskboard Django Overdue Service

This Django project is the overdue-task rules service used by the Taskboard Laravel API. It determines whether tasks are overdue, synchronizes overdue status into the shared task table, and validates status changes. It is a backend service, not a standalone task-management UI.

## What it does

- Marks tasks with past due dates as `OVERDUE`, unless they are already `DONE` or `OVERDUE`.
- Calculates effective overdue status from the current date even before a database sync has run.
- Validates requested task status changes and returns a decision and reason to Laravel.
- Protects service-to-service POST endpoints with a shared `X-Service-Key`.
- Exposes a simple health endpoint for local checks and deployment monitoring.

Laravel owns the task schema and user-facing API. Django connects to the same MySQL database and maps only the task columns it needs. It does not create or migrate the database schema.

## Request flow

The Laravel backend calls Django when it needs to synchronize overdue tasks or validate a transition. Django checks the shared service key, reads the task, applies the rules below, and returns a JSON response. Laravel remains responsible for user authentication, role/assignee authorization, and normal task operations; Django validates the overdue-specific transition rules.

The service uses UTC (`TIME_ZONE = "UTC"`) so its date comparison matches Laravel's default timezone.

## Overdue and status rules

1. A task whose `due_date` is before today is effectively `OVERDUE` if its stored status is not `DONE`. A task due today is not overdue.
2. The sync endpoint stores `OVERDUE` for past-due tasks except those already `DONE` or `OVERDUE`, and updates their `updated_at` timestamp.
3. An overdue task cannot move back to `IN_PROGRESS`.
4. Only an administrator can change an overdue task to `DONE`.
5. Non-overdue tasks may transition to `TODO`, `IN_PROGRESS`, or `DONE`. `OVERDUE` is not a user-selected target; the sync operation sets it.

## HTTP endpoints

| Method | Path | Authentication | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | None | Return a healthy status and service name |
| `POST` | `/api/overdue/sync` | `X-Service-Key` header | Synchronize past-due task statuses |
| `POST` | `/api/tasks/validate-transition` | `X-Service-Key` header | Validate one task status transition |

The POST routes expect JSON and return a consistent envelope with `success`, `message`, and `data` fields. The transition request body contains `task_id`, `new_status`, and `role` (`admin` or `user`). The response data includes `allowed`, `reason`, `stored_status`, and `current_status`.

Example health check:

```bash
curl http://127.0.0.1:8001/health
```

Example transition validation (use the same service key configured in both backends):

```bash
curl -X POST http://127.0.0.1:8001/api/tasks/validate-transition \
  -H 'Content-Type: application/json' \
  -H 'X-Service-Key: your-local-service-key' \
  -d '{"task_id":1,"new_status":"DONE","role":"admin"}'
```

## Database relationship

The service requires the Laravel database and its `tasks` table. Django's unmanaged `Task` model (`managed = False`) maps these columns:

| Column | Usage |
| --- | --- |
| `id` | Task identifier used by Laravel |
| `title` | Task title; mapped but not changed by this service |
| `status` | Current task status |
| `due_date` | Date used to calculate overdue state |
| `updated_at` | Updated by overdue synchronization |

There are no Django migrations for the shared task table. Apply schema migrations from the Laravel backend. Configure Django's `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` to connect to the same MySQL database Laravel uses; do not point this service at an unrelated database.

## Configuration and secrets

Copy `.env.example` to `.env` and set values appropriate for the environment. Important settings:

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django secret key; use a private random value |
| `DEBUG` | Django debug mode; disable in production |
| `ALLOWED_HOSTS` | Comma-separated hostnames accepted by Django |
| `SERVICE_KEY` | Private shared key expected in `X-Service-Key` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Credentials for the Laravel MySQL database |
| `DB_HOST`, `DB_PORT` | MySQL server address and port |

Set Django's `SERVICE_KEY` to the same secret as Laravel's `DJANGO_SERVICE_KEY`. Keep both values private. Never commit `.env`, service keys, database passwords, database dumps, or other real credentials. The example environment file contains placeholders only.

## Run locally

### Requirements

- Python 3
- MySQL compatible with the Laravel backend, plus the system libraries needed to build `mysqlclient`
- The Laravel backend's database schema already migrated

### Install dependencies

From this directory:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Set the database and service-key values in `.env`, then start Django on the default port used by Laravel:

```bash
python manage.py runserver 127.0.0.1:8001
```

For production, run the WSGI application with a production server such as Gunicorn and configure the host, TLS, database, and secrets in the deployment environment. Do not use Django's development server in production.

### Checks and tests

```bash
python manage.py check
python manage.py test
```

The tests cover overdue-date calculation and transition rules without requiring a live database.

## Repository contents

The repository should contain the Django source, dependency list, documentation, and safe environment template. `.gitignore` excludes local `.env` secrets, virtual environments, Python bytecode/cache directories, local databases/dumps, and unrelated zero-byte workspace artifacts. No database contents or credentials are needed in Git: the Laravel project supplies the shared schema.

## Project structure

```text
config/
  settings.py       Django settings and MySQL/service-key configuration
  urls.py           Health and service API routes
  wsgi.py           WSGI entry point
overdue/
  models.py         Unmanaged mapping to Laravel's tasks table
  services.py       Overdue synchronization and transition rules
  views.py          Health, sync, and validation endpoints
  tests.py          Overdue rule tests
manage.py           Django management entry point
requirements.txt    Python dependencies
```

## Dependencies

- Django
- mysqlclient
- python-dotenv
- Gunicorn for WSGI deployment
