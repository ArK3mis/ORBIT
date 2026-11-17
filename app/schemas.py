"""Request models. Limits keep one account from filling the database."""
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

ID = Field(pattern=r"^[A-Za-z0-9_-]{1,40}$")


class _M(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class Con(_M):
    id: str = ID
    name: str = Field(max_length=120)
    hue: int = Field(260, ge=0, le=360)


class Person(_M):
    id: str = ID
    name: str = Field(min_length=1, max_length=120)
    rel: str = Field("", max_length=120)
    bday: str = Field("", pattern=r"^(\d\d-\d\d)?$")
    since: int = Field(2026, ge=1800, le=2200)
    con: Optional[str] = None
    hue: int = Field(260, ge=0, le=360)
    ring: int = Field(2, ge=1, le=3)
    note: str = Field("", max_length=5000)


class Link(_M):
    a: str = ID
    b: str = ID
    label: str = Field("Connected", max_length=120)


class Mem(_M):
    id: str = ID
    title: str = Field(min_length=1, max_length=200)
    date: str = Field("", max_length=10)
    loc: str = Field("", max_length=200)
    text: str = Field("", max_length=10000)
    people: List[str] = Field(default_factory=list, max_length=500)


class Event(_M):
    id: str = ID
    year: int = Field(ge=1800, le=2200)
    text: str = Field(min_length=1, max_length=300)
    pid: Optional[str] = None


class Universe(_M):
    sample: bool = False
    me: str
    cons: List[Con] = Field(default_factory=list, max_length=200)
    people: List[Person] = Field(default_factory=list, max_length=2000)
    links: List[Link] = Field(default_factory=list, max_length=10000)
    mems: List[Mem] = Field(default_factory=list, max_length=5000)
    events: List[Event] = Field(default_factory=list, max_length=5000)


class Credentials(_M):
    email: str = Field(max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=200)
    name: str = Field("", max_length=120)
