"""Database layer for ORBIT.

Every person has ONE identity per user (people.id), and relationships are rows that
point at two person ids. Nothing about a connection is stored as text inside a profile.

DATABASE_URL examples:
  sqlite:///./orbit.db                                   (default, zero setup)
  mysql+pymysql://orbit:secret@localhost:3306/orbit      (MySQL)
"""
import os

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, ForeignKeyConstraint, Integer,
                        MetaData, SmallInteger, String, Table, Text, create_engine, event, func)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./orbit.db")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
)

if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

md = MetaData()
CASCADE = {"ondelete": "CASCADE"}

users = Table(
    "users", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String(255), nullable=False, unique=True),
    Column("name", String(120), nullable=False, server_default=""),
    Column("password_hash", String(255), nullable=False),
    Column("me_id", String(40)),                       # which person is "you" in this universe
    Column("is_sample", Boolean, nullable=False, server_default="0"),
    Column("created_at", DateTime, server_default=func.now()),
    mysql_engine="InnoDB", mysql_charset="utf8mb4",
)

constellations = Table(
    "constellations", md,
    Column("user_id", Integer, ForeignKey("users.id", **CASCADE), primary_key=True),
    Column("id", String(40), primary_key=True),
    Column("name", String(120), nullable=False),
    Column("hue", SmallInteger, nullable=False, server_default="260"),
    Column("position", Integer, nullable=False, server_default="0"),     # keeps the user's own ordering
    mysql_engine="InnoDB", mysql_charset="utf8mb4",
)

people = Table(
    "people", md,
    Column("user_id", Integer, ForeignKey("users.id", **CASCADE), primary_key=True),
    Column("id", String(40), primary_key=True),
    Column("name", String(120), nullable=False),
    Column("relation", String(120), nullable=False, server_default=""),   # label, e.g. "Mother"
    Column("birthday", String(5), nullable=False, server_default=""),     # MM-DD
    Column("since_year", SmallInteger, nullable=False, server_default="2026"),
    Column("constellation_id", String(40)),
    Column("hue", SmallInteger, nullable=False, server_default="260"),
    Column("orbit_ring", SmallInteger, nullable=False, server_default="2"),  # manual: 1 inner .. 3 outer
    Column("note", Text),                                                  # private note about the person
    Column("position", Integer, nullable=False, server_default="0"),
    mysql_engine="InnoDB", mysql_charset="utf8mb4",
)

relationships = Table(
    "relationships", md,
    Column("user_id", Integer, primary_key=True),
    Column("person_a", String(40), primary_key=True),
    Column("person_b", String(40), primary_key=True),
    Column("label", String(120), nullable=False, server_default="Connected"),
    ForeignKeyConstraint(["user_id", "person_a"], ["people.user_id", "people.id"], ondelete="CASCADE"),
    ForeignKeyConstraint(["user_id", "person_b"], ["people.user_id", "people.id"], ondelete="CASCADE"),
    mysql_engine="InnoDB", mysql_charset="utf8mb4",
)

memories = Table(
    "memories", md,
    Column("user_id", Integer, ForeignKey("users.id", **CASCADE), primary_key=True),
    Column("id", String(40), primary_key=True),
    Column("title", String(200), nullable=False),
    Column("memory_date", String(10), nullable=False, server_default=""),  # YYYY-MM-DD
    Column("location", String(200), nullable=False, server_default=""),
    Column("body", Text),
    mysql_engine="InnoDB", mysql_charset="utf8mb4",
)

memory_participants = Table(
    "memory_participants", md,
    Column("user_id", Integer, primary_key=True),
    Column("memory_id", String(40), primary_key=True),
    Column("person_id", String(40), primary_key=True),
    ForeignKeyConstraint(["user_id", "memory_id"], ["memories.user_id", "memories.id"], ondelete="CASCADE"),
    ForeignKeyConstraint(["user_id", "person_id"], ["people.user_id", "people.id"], ondelete="CASCADE"),
    mysql_engine="InnoDB", mysql_charset="utf8mb4",
)

timelines = Table(
    "timelines", md,
    Column("user_id", Integer, ForeignKey("users.id", **CASCADE), primary_key=True),
    Column("id", String(40), primary_key=True),
    Column("year", SmallInteger, nullable=False),
    Column("text", String(300), nullable=False),
    Column("person_id", String(40)),
    mysql_engine="InnoDB", mysql_charset="utf8mb4",
)
# Note: people.constellation_id and timelines.person_id are optional pointers checked in save_universe()
# instead of by composite foreign keys, so deleting a user can cascade cleanly in any order.


def init_db() -> None:
    md.create_all(engine)


# ---------- universe <-> rows ----------
# The front-end works with one JSON "universe"; it is stored relationally and rebuilt on read.

def load_universe(conn, uid: int):
    u = conn.execute(users.select().where(users.c.id == uid)).mappings().first()
    ppl = conn.execute(people.select().where(people.c.user_id == uid).order_by(people.c.position)).mappings().all()
    if not u or not ppl:
        return None
    cons = conn.execute(constellations.select().where(constellations.c.user_id == uid).order_by(constellations.c.position)).mappings().all()
    rels = conn.execute(relationships.select().where(relationships.c.user_id == uid)).mappings().all()
    mems = conn.execute(memories.select().where(memories.c.user_id == uid)).mappings().all()
    parts = conn.execute(memory_participants.select().where(memory_participants.c.user_id == uid)).mappings().all()
    evs = conn.execute(timelines.select().where(timelines.c.user_id == uid)).mappings().all()
    by_mem: dict = {}
    for p in parts:
        by_mem.setdefault(p["memory_id"], []).append(p["person_id"])
    return {
        "sample": bool(u["is_sample"]),
        "me": u["me_id"] or ppl[0]["id"],
        "cons": [{"id": c["id"], "name": c["name"], "hue": c["hue"]} for c in cons],
        "people": [{"id": p["id"], "name": p["name"], "rel": p["relation"], "bday": p["birthday"], "since": p["since_year"],
                    "con": p["constellation_id"], "hue": p["hue"], "ring": p["orbit_ring"], "note": p["note"] or ""} for p in ppl],
        "links": [{"a": r["person_a"], "b": r["person_b"], "label": r["label"]} for r in rels],
        "mems": [{"id": m["id"], "title": m["title"], "date": m["memory_date"], "loc": m["location"], "text": m["body"] or "",
                  "people": by_mem.get(m["id"], [])} for m in mems],
        "events": [{"id": e["id"], "year": e["year"], "text": e["text"], "pid": e["person_id"]} for e in evs],
    }


def save_universe(conn, uid: int, data) -> None:
    """Replace the user's universe inside the caller's transaction. Dangling references are dropped."""
    for t in (memory_participants, timelines, relationships, memories, people, constellations):
        conn.execute(t.delete().where(t.c.user_id == uid))

    con_ids = {c.id for c in data.cons}
    person_ids = {p.id for p in data.people}
    me = data.me if data.me in person_ids else (data.people[0].id if data.people else None)

    conn.execute(users.update().where(users.c.id == uid).values(me_id=me, is_sample=data.sample))
    if data.cons:
        conn.execute(constellations.insert(), [{"user_id": uid, "id": c.id, "name": c.name, "hue": c.hue, "position": i} for i, c in enumerate(data.cons)])
    if data.people:
        conn.execute(people.insert(), [{
            "user_id": uid, "id": p.id, "name": p.name, "relation": p.rel, "birthday": p.bday, "since_year": p.since,
            "constellation_id": p.con if p.con in con_ids else None, "hue": p.hue, "orbit_ring": p.ring, "note": p.note, "position": i,
        } for i, p in enumerate(data.people)])
    seen, rels = set(), []
    for l in data.links:
        key = frozenset((l.a, l.b))
        if l.a == l.b or l.a not in person_ids or l.b not in person_ids or key in seen:
            continue
        seen.add(key)
        rels.append({"user_id": uid, "person_a": l.a, "person_b": l.b, "label": l.label or "Connected"})
    if rels:
        conn.execute(relationships.insert(), rels)
    if data.mems:
        conn.execute(memories.insert(), [{"user_id": uid, "id": m.id, "title": m.title, "memory_date": m.date, "location": m.loc, "body": m.text} for m in data.mems])
        parts = [{"user_id": uid, "memory_id": m.id, "person_id": pid} for m in data.mems for pid in dict.fromkeys(m.people) if pid in person_ids]
        if parts:
            conn.execute(memory_participants.insert(), parts)
    if data.events:
        conn.execute(timelines.insert(), [{"user_id": uid, "id": e.id, "year": e.year, "text": e.text,
                                           "person_id": e.pid if e.pid in person_ids else None} for e in data.events])
