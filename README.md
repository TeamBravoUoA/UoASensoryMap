# UoA Sensory Map

**UoA Sensory Map** is an interactive web platform for the University of Aberdeen that
helps neurodivergent students and visitors navigate campus using sensory-aware mapping.
It visualises noise, lighting, temperature, scents, crowd levels and quiet zones, and
supports user feedback and accessible wayfinding.

Inspired by the [TCD Sense Map](https://tcdsensemap.ie/).

---

## Features

- Interactive **map** and **list** of campus locations.
- **Sensory profiles** for each location across five axes: Auditory, Visual,
  Olfactory, Thermal and Vestibular (rated 1–5).
- **Filtering** by category and by sensory level (e.g. low noise).
- **Quiet zones** highlighted for low-stimulation spaces.
- **Search and sort** locations.
- **User reports** of current conditions, with **admin moderation**.
- **Facilities** info (wheelchair access, WiFi, power, etc.).
- **Sensory radar chart** and **mobile-friendly**, accessible UI.

## Tech Stack

- **Backend:** Django (Python) + Django REST Framework
- **Frontend:** HTML / CSS / vanilla JavaScript (no build step); map & charts via CDN
- **Database:** SQLite (development)
- **Testing:** Django test framework

## Requirements

- Python 3.12
- pip and venv

## Getting Started

1. **Clone the repository**

   ```bash
   git clone https://github.com/FaizanKhan-AutoDev/UoASensoryMap.git
   cd UoASensoryMap
   ```
2. **Create and activate a virtual environment**

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1     # Windows PowerShell
   # source .venv/bin/activate      # macOS / Linux
   ```
3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```
4. **Apply database migrations**

   ```bash
   python manage.py migrate
   ```
5. **Run the development server**

   ```bash
   python manage.py runserver
   ```

   Open http://127.0.0.1:8000/ in your browser.
6. **(Optional) Create an admin user**

   ```bash
   python manage.py createsuperuser
   ```

   Then visit http://127.0.0.1:8000/admin/.

## Running Tests

```bash
python manage.py test
```

## API

Locations are available at:

```text
GET /api/locations/
POST /api/locations/
GET /api/locations/<id>/
PUT /api/locations/<id>/
DELETE /api/locations/<id>/
```

The location list supports simple filters:

```text
/api/locations/?category=quiet
/api/locations/?axis=auditory&max_level=2
/api/locations/?axis=visual&min_level=3
```

Valid sensory axes are `auditory`, `visual`, `olfactory`, `thermal`, and
`vestibular`.

## Project Structure

```
UoASensoryMap/
├─ manage.py
├─ requirements.txt
├─ UoASensoryMap/        # project configuration (settings, urls, wsgi)
└─ sensemap/             # main app (models, views, serializers, templates, static)
```

## Contributing

This is a university group project. Before writing code, read the team coding
guidelines and follow the branch-and-pull-request workflow:

- Create a feature branch: `git checkout -b feature/<task>`
- Commit in small, logical chunks with clear messages.
- Open a Pull Request for review before merging to `main`.
- Never commit `.venv/`, `db.sqlite3`, or secrets.

## Maintenance Manual

### Installation Instructions

1. Install **Python 3.12+** from <https://www.python.org/downloads/>.
2. Clone the repository and open the project folder.
3. Create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1          # Windows
   # source .venv/bin/activate             # macOS / Linux
   ```
4. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Create a `.env` file (see `.env.example` if available) and set `SECRET_KEY`,
   `DEBUG=True`, `ALLOWED_HOSTS` and optionally `DATABASE_URL`.
6. Apply migrations:
   ```bash
   python manage.py migrate
   ```
7. Seed the database from CSV files:
   ```bash
   python manage.py seed
   ```
   Use `--skip-errors` to continue past minor validation issues.
8. Start the development server:
   ```bash
   python manage.py runserver
   ```

### Third-Party Software

| Software | Purpose | Where to get it |
|----------|---------|-----------------|
| Python 3.12+ | Runtime and package manager | <https://www.python.org/downloads/> |
| Django 5.1.3 | Web framework and ORM | PyPI (`pip install Django`) |
| Django REST Framework 3.15.2 | REST API layer | PyPI (`pip install djangorestframework`) |
| PostgreSQL | Production database (optional) | <https://www.postgresql.org/download/> or a cloud host such as Render |
| SQLite | Default local database | Bundled with Python |
| Leaflet 1.9.4 | Interactive map control | CDN (<https://unpkg.com/leaflet/>) |

### Packages and Key Files

**Python packages (from `requirements.txt`)**

- `Django` — core web framework and ORM.
- `djangorestframework` — API serialisers and viewsets.
- `dj-database-url` — parses `DATABASE_URL` from the environment.
- `psycopg` — PostgreSQL adapter for production.
- `python-dotenv` — loads environment variables from `.env`.
- `whitenoise` — serves static files in production.
- `gunicorn` — WSGI server for deployment.
- `pillow` — image processing for uploaded photos.
- `django-cors-headers` — CORS handling for API consumers.
- `requests` — used by the seed command to fetch external data if needed.
- `tqdm` — progress bars for long-running management commands.

**Key project files**

- `manage.py` — Django management entry point.
- `UoASensoryMap/settings.py` — project settings, database, static files.
- `UoASensoryMap/urls.py` — top-level URL routing.
- `sensemap/models.py` — `Location`, `Space`, `Facility`, `SensoryAttribute`, etc.
- `sensemap/views.py` — page views and DRF API endpoints.
- `sensemap/serializers.py` — JSON serialisers for the API.
- `sensemap/management/commands/seed.py` — ETL command that loads CSV data.
- `sensemap/templates/sensemap/*.html` — page templates.
- `sensemap/static/sensemap/` — CSS, JavaScript, icons and images.
- `data/` — source CSV files for the seed command.

### Future Adaptations and Extensions

- **New space types**: add a choice to `Space.SpaceType` in `sensemap/models.py`,
  add matching metadata to `SPACE_TYPE_META` in `app.js` and `places.js`,
  and update the space-type filter options.
- **New facilities**: add a row to `data/Facility.csv` and run `python manage.py seed`;
  the CSV icon path will be exposed automatically by the `FacilitySerializer`.
- **New API endpoints**: add a view in `sensemap/views.py`, wire it in
  `sensemap/urls.py`, and write a corresponding test in `sensemap/tests/`.
- **Template / static changes**: bump the `?v=<n>` query string in the
  `{% static %}` tag of any edited JS/CSS file so returning browsers load the
  new version.
- **Custom styling**: edit `sensemap/static/sensemap/css/styles.css`; mobile
  styles are grouped at the bottom under `/* ---------- Responsive ---------- */`.

### Updating Static Assets
The project uses cache-busted static files. After changing any file in
`sensemap/static/sensemap/js/` or `sensemap/static/sensemap/css/`, bump the
`?v=<number>` query string in the corresponding `{% static %}` include in the
templates (e.g. `index.html` and `places.html`).

### Running the Test Suite
The project uses Django's test runner. To run all tests:

```bash
python manage.py test
```

To run only the app-specific tests:

```bash
python manage.py test sensemap
```

### Deployment Checklist
- Ensure `DEBUG=False` and `ALLOWED_HOSTS` is set in `.env` before deploying.
- Set `DATABASE_URL` to a valid PostgreSQL connection string for production.
- Collect static files: `python manage.py collectstatic`.
- Run migrations: `python manage.py migrate`.

## Team Bravo

University of Aberdeen — group project (2026).
