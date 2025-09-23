# Copilot Instructions for Cafe Finder

## Project Overview
This is a Flask-based web application for discovering cafes in Surabaya. It supports user registration, login, favorites, and an admin panel for managing cafes. Data is stored in JSON files, not a database.

## Architecture & Data Flow
- **Main app:** `app.py` contains all routes, helpers, and logic. No blueprints or modularization.
- **Templates:** HTML files in `templates/` use Jinja2 for rendering. Key files: `index.html`, `detail.html`, `admin.html`, `login.html`, `register.html`, `update_cafe.html`.
- **Static files:** CSS in `static/style.css`, images uploaded to `static/uploads/`.
- **Data:**
  - `cafes.json`: List of cafes, each with id, name, location, categories, menu, photo.
  - `users.json`: Registered users (username, password hash, role).
  - `admin.json`: Admin users (username, password hash).
- **Authentication:** Session-based, with roles ('user', 'admin').
- **Admin features:** Add, update, delete cafes; only accessible to admins.
- **Favorites:** Stored in session per user.

## Developer Workflows
- **Run locally:**
  ```powershell
  python app.py
  ```
  (Debug mode enabled by default)
- **Production deploy:**
  Uses Gunicorn via Procfile:
  ```plaintext
  web: gunicorn app:app
  ```
- **Dependencies:**
  - Flask
  - Gunicorn
  - Requests
  (See `requirements.txt`)

## Project-Specific Patterns
- **Data persistence:** All data is read/written via helper functions (`read_json`, `write_json`). No ORM.
- **ID assignment:** Cafe IDs are stringified integers, reassigned on delete to keep sequential order.
- **Menu items:** Each cafe has a list of menu dicts (`nama`, `harga`).
- **File uploads:** Only image files (png, jpg, jpeg, gif) allowed for cafe photos.
- **Role checks:** Use `admin_required()` for admin-only routes.
- **Flash messages:** Used for user feedback on actions.

## Integration Points
- No external APIs or services.
- All authentication and data management is local.

## Examples
- To add a new cafe, POST to `/admin` with name, location, categories (comma-separated), menu items, and optional photo.
- To update a cafe, POST to `/update/<cafe_id>` with similar fields.
- To favorite/unfavorite a cafe, POST to `/favorite/toggle/<cafe_id>`.

## Conventions
- All JSON files must be UTF-8 encoded and pretty-printed.
- Cafe categories and menu items are lists, not strings.
- Uploaded images are stored in `static/uploads/`.
- No migrations; manual edits to JSON files are possible but discouraged.

---
For questions or unclear patterns, review `app.py` for canonical logic. Suggest improvements only if they match existing conventions.
