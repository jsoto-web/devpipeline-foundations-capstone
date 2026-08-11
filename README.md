# Competency Tracking Tool

A console application for tracking employee skill/competency levels through
assessments. Built for the Coding Foundations Capstone Project.

## What it does

Managers can add users, competencies, and assessments, record assessment
results for employees, and pull competency reports across the team. Regular
users can log in, view their own profile, and see their own competency
summary. Passwords are hashed with bcrypt and never stored in plain text.

## Requirements

- Python 3.14.6
- [pipenv](https://pipenv.pypa.io/) for dependency management

## Setup

```bash
# from the project root
pipenv install
```

This installs `bcrypt`, the only third-party dependency.

## Building the database

The app expects a SQLite database file called `competency_tracker.db` in the
project root. Build (or rebuild) it with:

```bash
pipenv run python schema.py
```

This creates four tables -- `users`, `competencies`, `assessments`, and
`assessment_results` -- with foreign keys enforced. It's safe to run more
than once; it only creates tables that don't already exist, it doesn't wipe
existing data.

See `ERD_final_draft.drawio.pdf` for the full entity-relationship diagram.

## Running the app

```bash
pipenv run python main.py
```

You'll be prompted to log in with an email and password. There's no
self-signup -- a manager has to add new users from inside the app (see
below), so the very first account has to be inserted directly, e.g. with a
one-off script that calls `auth.create_user()`:

```python
from db import get_connection
from auth import create_user

conn = get_connection()
create_user(
    conn,
    first_name="Demo",
    last_name="Manager",
    phone="555-0100",
    email="demo.manager@example.com",
    plain_password="CorrectHorseBatteryStaple",
    hire_date="2026-01-15",
    user_type="manager",
)
conn.close()
```

Run that once, then log in with `demo.manager@example.com` /
`CorrectHorseBatteryStaple` and use "Add a user" from the manager menu for
everyone after that.

## Features

### Everyone (users and managers)

- Log in / log out
- View your own profile (name, email, phone, hire date, active status)
- Change your own password
- View your own competency summary -- your most recent score on every
  competency (0 if you've never been assessed on it), plus your average

### Managers only

- View all users, or search by first/last name
- Add a user
- View any individual user's competency report
- Manage competencies -- view / add / edit
- Manage assessments -- view / add / edit (each assessment belongs to one
  competency)
- Manage assessment results -- view / add / edit / delete
- View the competency results summary for any competency (every active
  user's most recent score on that competency, plus the team average)
- Export CSV: users list, competencies list, a user's competency summary,
  or a competency's results summary
- Import assessment results from CSV

Note on delete: only assessment results can be deleted through the app.
Competencies and assessments are view/add/edit only, per the project
requirements.

## Competency scale

Scores range from 0-4:

| Score | Meaning |
|-------|---------|
| 0 | No competency -- Needs Training and Direction |
| 1 | Basic Competency -- Needs Ongoing Support |
| 2 | Intermediate Competency -- Needs Occasional Support |
| 3 | Advanced Competency -- Completes Task Independently |
| 4 | Expert Competency -- Can effectively pass on knowledge and initiate optimizations |

## CSV import format

Import expects a CSV with a header row and these columns:

```
user_id,assessment_id,score,date_taken
1,3,4,2026-08-10
```

- `user_id` and `assessment_id` must reference existing rows
- `score` must be an integer from 0-4
- `date_taken` can't be blank

Rows that fail validation (bad foreign key, out-of-range score, missing
date, etc.) are skipped and reported individually; valid rows in the same
file still get imported. Imported results don't have a `manager_id`
recorded, since there's no way to know who administered an assessment
that happened outside the app.

## CSV export

Each export writes a file to the project's working directory with a header
row:

- `users_export.csv`
- `competencies_export.csv`
- `user_<id>_competency_summary.csv`
- `competency_<id>_results_summary.csv`

## Project files

| File | Purpose |
|------|---------|
| `main.py` | Console entry point -- login loop and all menus |
| `auth.py` | Password hashing (bcrypt) and login |
| `db.py` | Shared SQLite connection helper |
| `schema.py` | Creates the database and tables |
| `competency_tracker.db` | The SQLite database file |
| `ERD_final_draft.drawio` / `.pdf` | Entity-relationship diagram |

## Known limitations

- No self-registration; the first manager account has to be seeded manually
  (see "Running the app" above)
- CSV export/import paths aren't configurable -- files land in whatever
  directory you ran `main.py` from
- No PDF report export yet (extra credit, not yet implemented)