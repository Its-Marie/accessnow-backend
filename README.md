💙 About AccessNow

This backend supports the AccessNow Mobility App, a project focused on accessibility, inclusion, and equitable navigation for
anyone needing safer and more comfortable routes.

You are helping build a more inclusive world. 🌍💙

Features

  - REST API
  - SQLite database
  - User model
  - CRUD operations
  - Flask-Migrate
  - Marshmallow serialization

Tech Stack

  - Python 3
  - Flask
  - SQLAlchemy
  - Marshmallow
  - Flask-Migrate
  - SQLite

Installation
  git clone https://github.com/YOUR-USERNAME/accessnow-backend.git
  cd accessnow-backend

  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt

  flask db upgrade
  flask run


Server:

  http://127.0.0.1:5000

API Overview (minimal)

  Health Check
    GET /health

Users

  Basic user CRUD operations under:
    /api/users

Project Structure

├── app.py
├── config.py
├── models.py
├── routes.py
├── schemas.py
├── migrations/
├── instance/app.db
└── .env

