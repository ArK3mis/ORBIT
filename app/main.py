"""ORBIT API. Run from the project root:  uvicorn app.main:app --reload"""
import hashlib
import hmac
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from starlette.middleware.sessions import SessionMiddleware

from . import db
from .schemas import Credentials, Universe

SECRET = os.getenv("SECRET_KEY")
if not SECRET:
    SECRET = secrets.token_hex(32)
    print("WARNING: SECRET_KEY is not set. Using a random key, so logins reset on every restart.")

@asynccontextmanager
async def lifespan(_app):
    db.init_db()
    yield


app = FastAPI(title="ORBIT", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(
    SessionMiddleware, secret_key=SECRET, session_cookie="orbit_session",
    same_site="lax", https_only=os.getenv("COOKIE_SECURE") == "1", max_age=60 * 60 * 24 * 14,
)


# ---------- passwords ----------
def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${h.hex()}"


def check_password(pw: str, stored: str) -> bool:
    try:
        _, salt, h = stored.split("$")
        calc = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=2 ** 14, r=8, p=1, dklen=32)
        return hmac.compare_digest(calc.hex(), h)
    except Exception:
        return False


DUMMY_HASH = hash_password("not-a-real-password")  # keeps timing similar for unknown emails

# ---------- tiny login throttle (per process; use a shared store if you run several workers) ----------
_fails: dict = {}


def _throttle(key: str) -> None:
    n, t0 = _fails.get(key, (0, time.time()))
    if time.time() - t0 > 600:
        n, t0 = 0, time.time()
    if n >= 8:
        raise HTTPException(429, "Too many attempts. Try again in a few minutes.")
    _fails[key] = (n, t0)


def _fail(key: str) -> None:
    n, t0 = _fails.get(key, (0, time.time()))
    _fails[key] = (n + 1, t0)


def current_user(request: Request) -> int:
    uid = request.session.get("uid")
    if not uid:
        raise HTTPException(401, "Please log in.")
    return uid


# ---------- routes ----------
@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/register", status_code=201)
def register(c: Credentials, request: Request):
    email = c.email.lower()
    try:
        with db.engine.begin() as conn:
            r = conn.execute(db.users.insert().values(email=email, name=c.name, password_hash=hash_password(c.password)))
            uid = r.inserted_primary_key[0]
    except IntegrityError:
        raise HTTPException(409, "That email is already registered.")
    request.session.clear()
    request.session["uid"] = uid
    return {"email": email, "name": c.name}


@app.post("/api/login")
def login(c: Credentials, request: Request):
    email = c.email.lower()
    key = f"{request.client.host if request.client else '?'}|{email}"
    _throttle(key)
    with db.engine.connect() as conn:
        u = conn.execute(db.users.select().where(db.users.c.email == email)).mappings().first()
    ok = check_password(c.password, u["password_hash"] if u else DUMMY_HASH)
    if not (u and ok):
        _fail(key)
        raise HTTPException(401, "Wrong email or password.")
    _fails.pop(key, None)
    request.session.clear()
    request.session["uid"] = u["id"]
    return {"email": u["email"], "name": u["name"]}


@app.post("/api/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@app.get("/api/me")
def me(uid: int = Depends(current_user)):
    with db.engine.connect() as conn:
        u = conn.execute(db.users.select().where(db.users.c.id == uid)).mappings().first()
    if not u:
        raise HTTPException(401, "Please log in.")
    return {"email": u["email"], "name": u["name"]}


@app.get("/api/universe")
def get_universe(uid: int = Depends(current_user)):
    with db.engine.connect() as conn:
        return {"universe": db.load_universe(conn, uid)}


@app.put("/api/universe")
def put_universe(data: Universe, uid: int = Depends(current_user)):
    with db.engine.begin() as conn:
        db.save_universe(conn, uid, data)
    return {"ok": True, "people": len(data.people)}


FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="web")
