from __future__ import annotations

import sqlalchemy
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func, orm
from sqlalchemy.orm.decl_api import DeclarativeMeta


class RepresentableMixin:
    """A mixin that provides a simple `__repr__` for ORM models."""

    def __repr__(self) -> str:
        """Return an insightful representation of a model instance."""
        cls_name = type(self).__name__
        instance_state = sqlalchemy.inspect(self)
        formatted_fields = ", ".join(
            f"{attr.key}={attr.value!r}"
            if attr.key not in instance_state.unloaded
            else f"{attr.key}=<NOT_LOADED>"
            for attr in instance_state.attrs
        )
        return f"{cls_name}({formatted_fields})"


class Base(RepresentableMixin, metaclass=DeclarativeMeta):
    __abstract__ = True

    # these are supplied by the sqlalchemy2-stubs, so may be omitted
    # when they are installed
    registry = orm.registry()
    metadata = registry.metadata

    id = Column(Integer, primary_key=True)


class TravelerMixin:
    """A mixin class with common traveler columns."""

    created_at = Column(DateTime, server_default=func.now())
    name = Column(String(128))
    age = Column(Integer)


class LazyTraveler(TravelerMixin, Base):
    """A model representing a traveler."""

    __tablename__ = "lazy_traveler"
    __mapper_args__ = {"eager_defaults": False}


class EagerTraveler(TravelerMixin, Base):
    """A model representing a traveler."""

    __tablename__ = "eager_traveler"
    __mapper_args__ = {"eager_defaults": True}


class TravelerWithDestination(TravelerMixin, Base):

    __tablename__ = "traveler_with_destination"
    __mapper_args__ = {"eager_defaults": True}

    # Relational fields
    destination_id: int = Column(Integer, ForeignKey("country.id"))
    destination: Country = orm.relationship("Country")


class Country(Base):
    """A model representing a country."""

    __tablename__ = "country"

    name = Column(String(128))
