# Developer guide

## Project overview

The application is a Flask web app. Its Python package contains the routes,
services, and templates. MongoDB stores application data.

## Technology Stack

### Backend

- Flask
- PyMongo
- OpenCV
- NumPy

### Frontend

- Jinja2
- JavaScript
- Bootstrap
- Leaflet

### Database

- MongoDB

### Infrastructure

- Azure VM

## Architecture

The application follows a server-rendered architecture using Flask and Jinja2.

1. Flask handles routing, authentication, business logic, and database access.
2. Jinja2 templates render dynamic HTML pages on the server.
3. JavaScript provides client-side interactivity where required.
4. MongoDB stores application data.

```text
Browser
  |
  v
Flask Routes
  |
  +--> Business Logic
  |
  +--> MongoDB
  |
  +--> Jinja2 Templates
          |
          v
      HTML Response
```

## Prerequisites

- Python 3.12+
- MongoDB
- Git

## Run the application locally

The app connects to `mongodb://localhost:27017/colorimetry_db` by default. To
use a different MongoDB URI, set the `MONGO_URI` environment variable (in .env) before
starting the app.

From the project root, create and activate a virtual environment, then install
the application requirements:

```powershell
python -m venv .venv
source .venv/bin/activate# 	   #Linux/macOS
.venv\Scripts\activate         # Windows
python -m pip install -r requirements.txt
```

Create a `.env` file in the project root (next to `run.py`). Copy the template and fill in your own values:

    | Variable | How to get it |
    |---|---|
    | `SECRET_KEY` | Generate one: `python -c "import secrets; print(secrets.token_hex(32))"` |
    | `RECAPTCHA_SITE_KEY`, `RECAPTCHA_SECRET_KEY` | Register a site at [google.com/recaptcha/admin](https://www.google.com/recaptcha/admin) (add `localhost` as a domain for local use) |
    | `RESEND_API_KEY` | Create a key in the [Resend](https://resend.com) dashboard under API Keys |

Never commit `.env`. It is listed in `.gitignore`.

Start the Flask development server with:

```powershell
python run.py
```

The app will be available at `http://127.0.0.1:5000`.

## Preview the documentation

Activate the project virtual environment where MkDocs is installed:

```powershell
.\.venv\Scripts\Activate.ps1
mkdocs serve
```

MkDocs serves a live preview locally and rebuilds it when documentation files
change.

## Build the documentation

```powershell
mkdocs build
```

MkDocs writes the generated site to `site/`. Do not edit generated files
directly; make changes in `docs/` or `mkdocs.yml`.

## Run the application tests

```console
uv run pytest
```
