"""Declarative base shared by all models (M1 adds the actual models)."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
