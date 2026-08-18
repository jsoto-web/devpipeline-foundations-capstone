# Competency Tracking Tool

A console application for tracking employee skill/competency levels through
assessments. Built for the Coding Foundations Capstone Project.

## What it does

Managers can add and edit users, competencies, and assessments, record
assessment results for employees, and pull competency reports across the
team. Regular users can log in, view and edit their own profile, and see
their own competency summary. Passwords are hashed with bcrypt and never
stored in plain text.

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
- Edit your own name
- Change your own password
- View your own competency summary -- your most recent score on every
  competency (0 if you've never been assessed on it), plus your average

### Managers only

- View all users, or search by first/last name
- Add a user
- Edit a user (name, phone, email, hire date, user type, active status --
  this is also how you deactivate/reactivate an account)
- View any individual user's competency report
- View any individual user's raw assessment history (every assessment
  they've taken, in order, distinct from the aggregated competency report)
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
requirements. To remove a user's access without deleting their history,
use "Edit a user" and set them to inactive instead.

### Manager menu

```
1)  View my profile
2)  Edit my name
3)  Change my password
4)  View all users
5)  Search users
6)  Add a user
7)  Edit a user
8)  View a user's competency report
9)  View a user's assessment history
10) Manage competencies
11) Manage assessments
12) Manage assessment results
13) View competency results summary (all users)
14) Export CSV
15) Import CSV
16) Log out
```

### User menu

```
1) View my profile
2) Edit my name
3) Change my password
4) View my competency summary
5) Log out
```

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
- `date_taken` must be a valid date in `YYYY-MM-DD` format

Rows that fail validation (bad foreign key, out-of-range score, malformed
or missing date, etc.) are skipped and reported individually, with the row
number and the reason; valid rows in the same file still get imported.
Imported results don't have a `manager_id` recorded, since there's no way
to know who administered an assessment that happened outside the app.

A ready-to-use example is included: `sample_assessment_results.csv`.

## CSV export

Each export writes a file to the project's working directory with a header
row:

- `users_export.csv`
- `competencies_export.csv`
- `user_<id>_competency_summary.csv`
- `competency_<id>_results_summary.csv`

## Error handling

This is meant to run as production-quality Beta software, so it's built to
degrade gracefully instead of crashing:

- **Input validation at entry.** Required fields loop until you enter
  something; dates loop until they're valid `YYYY-MM-DD`; scores are
  restricted to menu choices or validated on free-text entry. Bad data
  never reaches the database in the first place.
- **Database errors are caught, not fatal.** A duplicate email (`UNIQUE`
  constraint) or an out-of-range score (`CHECK` constraint) is reported in
  plain language and returns you to the menu -- it doesn't crash the app or
  print a raw SQLite traceback.
- **Every menu action runs inside a safety net.** If something
  unanticipated still goes wrong in a single action, the app reports it and
  returns to the menu rather than ending your session.
- **File I/O failures are handled.** A missing CSV file, a bad path, or a
  permissions problem on export/import prints a clear message instead of
  crashing.
- **Nothing ends in a raw traceback.** Ctrl+C, Ctrl+D, or any other
  unexpected error at the top level prints a friendly "Goodbye" and exits
  cleanly.

## Type hints

Every function has type hints on its parameters and its return type, using
Python 3.10+ union syntax (e.g. `str | None`) rather than `typing.Optional`.
`sqlite3.Connection` and `sqlite3.Row` are aliased to `Connection` and `Row`
at the top of `main.py` to keep signatures readable.

## Project files

| File | Purpose |
|------|---------|
| `main.py` | Console entry point -- login loop and all menus |
| `auth.py` | Password hashing (bcrypt) and login |
| `db.py` | Shared SQLite connection helper |
| `schema.py` | Creates the database and tables |
| `competency_tracker.db` | The SQLite database file |
| `sample_assessment_results.csv` | Example file for testing CSV import |
| `ERD_final_draft.drawio` / `.pdf` | Entity-relationship diagram |

## Known limitations

- No self-registration; the first manager account has to be seeded manually
  (see "Running the app" above)
- CSV export/import paths aren't configurable -- files land in whatever
  directory you ran `main.py` from
- No PDF report export yet (extra credit, not yet implemented)