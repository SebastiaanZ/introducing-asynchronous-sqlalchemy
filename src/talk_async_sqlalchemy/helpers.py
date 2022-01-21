from collections import abc
from typing import Any, Optional, Type, TypeVar, cast

import sqlalchemy
from sqlalchemy import exc, orm, sql
from sqlalchemy.ext import asyncio as asyncio_ext
from sqlalchemy.ext.asyncio import engine

from . import models

DIVIDER_WIDTH = 80
ReturnValue = TypeVar("ReturnValue")


def format_divider(label: str = "", width: int = DIVIDER_WIDTH) -> str:
    """Format a divider to a specific width with a label.

    :param label: The label for the divider (default: "")
    :param width: The width of the divider
    :return: The formatted divider, optionally with label
    """
    if label:
        label = f"| {label} |"
    return f"{label:=^{width}}"


def get_engine_async(database_url: str, *, echo: bool = True) -> engine.AsyncEngine:
    """Create an asynchronous SQLAlchemy engine.

    The engine will run in future mode and have echo enabled.

    :param database_url: The database connection url
    :param echo: If ``True``, turn on the engine's echo mode
    :return: The engine instance
    """
    return asyncio_ext.create_async_engine(
        database_url,
        echo=echo,
        future=True,
    )


def get_async_sessions_maker(async_engine: engine.AsyncEngine) -> orm.sessionmaker:
    """Create an asynchronous session maker.

    :param async_engine: The async engine to use for the session maker
    :return: The session maker
    """
    return orm.sessionmaker(
        async_engine,
        expire_on_commit=False,
        class_=asyncio_ext.AsyncSession,
    )


async def flush_database_async(*, async_engine: engine.AsyncEngine) -> None:
    """Recreate the database schema using an async engine.

    :param async_engine: The async engine to use to flush
    :return: None
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.drop_all)
        await conn.run_sync(models.Base.metadata.create_all)


async def execute_verbosely_async(
    coroutine: abc.Coroutine[Any, Any, ReturnValue], *, label: str
) -> ReturnValue:
    """Execute the coroutine verbosely.

    :param coroutine: The coroutine to execute
    :param label: The label to give to the output
    :return: The result of the coroutine
    """
    print(format_divider(f"Start Execution of {label!r}"))
    result = await coroutine
    print(format_divider("Result"))
    print(result if result is not None else "(no result)")
    print(format_divider("End"), end="\n\n\n")
    return result


async def create_orm_instance_async(
    orm_model: Type[models.Base],
    creation_kwargs: dict[str, Any],
    *,
    session_maker: orm.sessionmaker,
) -> sql.Select:
    """Create an ORM instance and return a select that fetches it.

    :param orm_model: The ORM model to use
    :param creation_kwargs: The kwargs to create the model with
    :param session_maker: The session maker to use
    :return: The select that would fetch the instance
    """
    instance = orm_model(**creation_kwargs)
    async with session_maker() as session:
        async with session.begin():
            session.add(instance)

    return sqlalchemy.select(orm_model).where(getattr(orm_model, "id") == instance.id)


async def access_attribute_with_server_default(
    orm_model: Type[models.LazyTraveler] | Type[models.EagerTraveler],
    *,
    session_maker: orm.sessionmaker,
) -> Optional[str]:
    traveler = orm_model(name="Sebastiaan", age=35)
    async with session_maker() as session:
        async with session.begin():
            session.add(traveler)

        print(format_divider("Engine activity after committing ORM-instance"))
        try:
            result = f"Traveler Sebastiaan created at: {traveler.created_at}"
        except exc.MissingGreenlet as exception:
            print(f"Cannot access lazy attribute: {exception!r}")
            result = None

    return result
