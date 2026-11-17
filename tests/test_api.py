import json
import os
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["SECRET_KEY"] = "test-secret"

import pytest
from fastapi.testclient import TestClient

from app.main import app

SAMPLE = json.loads((Path(__file__).parent / "sample_universe.json").read_text())


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def reg(c, email, pw="correct horse"):
    r = c.post("/api/register", json={"email": email, "password": pw, "name": "T"})
    assert r.status_code == 201, r.text


def test_requires_login(client):
    assert client.get("/api/universe").status_code == 401
    assert client.put("/api/universe", json=SAMPLE).status_code == 401
    assert client.get("/api/me").status_code == 401


def test_register_login_logout(client):
    reg(client, "a@example.com")
    assert client.get("/api/me").json()["email"] == "a@example.com"
    assert client.post("/api/register", json={"email": "A@example.com", "password": "another one"}).status_code == 409
    client.post("/api/logout")
    assert client.get("/api/me").status_code == 401
    assert client.post("/api/login", json={"email": "a@example.com", "password": "wrong password"}).status_code == 401
    assert client.post("/api/login", json={"email": "a@example.com", "password": "correct horse"}).status_code == 200
    assert client.get("/api/me").status_code == 200


def test_short_password_rejected(client):
    assert client.post("/api/register", json={"email": "s@example.com", "password": "short"}).status_code == 422


def test_universe_round_trip(client):
    reg(client, "rt@example.com")
    assert client.get("/api/universe").json() == {"universe": None}
    assert client.put("/api/universe", json=SAMPLE).status_code == 200
    got = client.get("/api/universe").json()["universe"]
    assert got["me"] == SAMPLE["me"] and got["sample"] is True
    assert [p["id"] for p in got["people"]] == [p["id"] for p in SAMPLE["people"]]
    assert [c["id"] for c in got["cons"]] == [c["id"] for c in SAMPLE["cons"]]
    assert {p["id"] for p in got["people"]} == {p["id"] for p in SAMPLE["people"]}
    assert len(got["links"]) == len(SAMPLE["links"])
    assert {m["id"]: sorted(m["people"]) for m in got["mems"]} == {m["id"]: sorted(m["people"]) for m in SAMPLE["mems"]}
    mara = next(p for p in got["people"] if p["id"] == "mara")
    assert mara["rel"] == "Mother" and mara["bday"] == "12-12" and mara["ring"] == 1 and mara["con"] == "family"
    assert len(got["events"]) == len(SAMPLE["events"])


def test_edit_and_remove_person(client):
    reg(client, "ed@example.com")
    u = json.loads(json.dumps(SAMPLE))
    client.put("/api/universe", json=u)
    u["people"] = [p for p in u["people"] if p["id"] != "mara"]
    u["links"] = [l for l in u["links"] if "mara" not in (l["a"], l["b"])]
    u["mems"][0]["people"].remove("mara")
    next(p for p in u["people"] if p["id"] == "jules")["name"] = "Julian"
    assert client.put("/api/universe", json=u).status_code == 200
    got = client.get("/api/universe").json()["universe"]
    assert "mara" not in {p["id"] for p in got["people"]}
    assert next(p for p in got["people"] if p["id"] == "jules")["name"] == "Julian"
    assert all("mara" not in (l["a"], l["b"]) for l in got["links"])


def test_dangling_references_are_dropped(client):
    reg(client, "dg@example.com")
    u = json.loads(json.dumps(SAMPLE))
    u["links"].append({"a": "me", "b": "ghost", "label": "x"})
    u["links"].append({"a": "me", "b": "mara", "label": "duplicate pair"})
    u["mems"][0]["people"].append("ghost")
    u["people"][1]["con"] = "no-such-constellation"
    u["events"].append({"id": "ev9", "year": 2020, "text": "x", "pid": "ghost"})
    assert client.put("/api/universe", json=u).status_code == 200
    got = client.get("/api/universe").json()["universe"]
    assert len(got["links"]) == len(SAMPLE["links"])
    assert "ghost" not in next(m for m in got["mems"] if m["id"] == SAMPLE["mems"][0]["id"])["people"]
    assert next(p for p in got["people"] if p["id"] == SAMPLE["people"][1]["id"])["con"] is None
    assert next(e for e in got["events"] if e["id"] == "ev9")["pid"] is None


def test_users_are_isolated(client):
    reg(client, "u1@example.com")
    client.put("/api/universe", json=SAMPLE)
    client.post("/api/logout")
    reg(client, "u2@example.com")
    assert client.get("/api/universe").json() == {"universe": None}
    other = json.loads(json.dumps(SAMPLE)); other["people"][1]["name"] = "Other"
    assert client.put("/api/universe", json=other).status_code == 200
    client.post("/api/logout")
    client.post("/api/login", json={"email": "u1@example.com", "password": "correct horse"})
    assert client.get("/api/universe").json()["universe"]["people"][1]["name"] == SAMPLE["people"][1]["name"]


def test_validation(client):
    reg(client, "v@example.com")
    bad = json.loads(json.dumps(SAMPLE)); bad["people"][0]["id"] = "has space"
    assert client.put("/api/universe", json=bad).status_code == 422
    bad = json.loads(json.dumps(SAMPLE)); bad["people"][0]["bday"] = "13/45"
    assert client.put("/api/universe", json=bad).status_code == 422


def test_login_throttle(client):
    reg(client, "th@example.com"); client.post("/api/logout")
    codes = [client.post("/api/login", json={"email": "th@example.com", "password": "bad password"}).status_code for _ in range(10)]
    assert codes[0] == 401 and codes[-1] == 429


def test_serves_frontend(client):
    r = client.get("/")
    assert r.status_code == 200 and "ORBIT" in r.text
