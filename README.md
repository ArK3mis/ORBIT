# ORBIT

A personal universe made of people. Click a person to enter their orbit, keep memories that
connect people, group them into constellations, and travel back in time.

- **Frontend:** one file, `frontend/index.html` (HTML, CSS, JavaScript, canvas). No build step.
- **Backend:** Python FastAPI in `app/`, served together with the frontend.
- **Database:** SQLite by default, MySQL 8+ for real use.
- **Accounts:** email and password, session cookie. Each account sees only its own universe.

## Run it (SQLite, 2 minutes)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")   # Windows: set SECRET_KEY=any-long-random-text
uvicorn app.main:app --reload
```

Open http://localhost:8000, press **Enter My Universe**, then **Create an account**.
A new account starts with an example family. Press **Start fresh** in the top-left card to clear it.
Interactive API docs are at http://localhost:8000/api/docs.

## Use MySQL

```sql
CREATE DATABASE orbit CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'orbit'@'localhost' IDENTIFIED BY 'choose-a-password';
GRANT ALL ON orbit.* TO 'orbit'@'localhost';
```

```bash
export DATABASE_URL="mysql+pymysql://orbit:choose-a-password@localhost:3306/orbit?charset=utf8mb4"
uvicorn app.main:app --reload
```

The app creates its tables on first start. `schema.sql` holds the same tables if you would rather create them by hand.

## How the data is stored

| Table | Purpose |
|---|---|
| `users` | Accounts (password stored as a salted scrypt hash) |
| `people` | Every person, **one row per person**, with orbit distance, color, note, birthday |
| `relationships` | Connections between two person ids, with a label ("Cousins") |
| `constellations` | Groups |
| `memories` + `memory_participants` | A memory and who was in it |
| `timelines` | Milestones |

Connections are rows pointing at person ids, never text inside a profile, so your mother is the same
person whether you meet her from your universe or your grandmother's. Everything is scoped by `user_id`
and removed with the account.

The browser works with one JSON universe: `GET /api/universe` reads it, `PUT /api/universe` saves it
(the page saves about a second after you stop editing). That keeps the first version simple. When
universes get large or shared, split this into per-record endpoints; the tables already support it.

## Tests

```bash
python -m pytest -q tests
```

Covers login, isolation between users, round trips, removal, validation and the login throttle.

## Before you put it on the internet

- Set a real `SECRET_KEY`, and `COOKIE_SECURE=1` when serving over HTTPS (see `.env.example`).
- Put it behind HTTPS (nginx or Caddy). The cookie is `SameSite=Lax`.
- The login throttle is per process. With several workers, use a shared store such as Redis.
- Profiles hold information about other people. Keep universes private, and add sharing controls before inviting others in.
- Photos and videos are not built yet. Start with local file storage as in your plan.
- The page loads two Google fonts. Without internet it falls back to Georgia and system sans-serif.

## Roadmap

Done: login, people, 2D universe, enter-orbit navigation, connections, constellations, memories, timeline,
time travel, connection finder, Star Finder search. Next: family tree view, photo and video uploads,
per-record API, 3D universe, shared universes.
