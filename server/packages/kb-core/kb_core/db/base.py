"""Shared SQLAlchemy declarative base — single source of truth."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
