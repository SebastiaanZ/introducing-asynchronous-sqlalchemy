import asyncio
import os
import warnings
from typing import Optional, cast

import sqlalchemy
from sqlalchemy import exc, orm, sql
from sqlalchemy.ext.asyncio import engine

from . import helpers, models


async def simple_statement(message: str, *, async_engine: engine.AsyncEngine) -> str:
    """Execute a simple statement.

    :param message: The message to SELECT from the database
    :param async_engine: The async engine to execute the statement with
    :return: The result of the simple statement.
    """
    statement = sqlalchemy.text("SELECT :message")
    async with async_engine.connect() as conn:
        result = await conn.execute(statement, parameters={"message": message})

    return cast(str, result.scalar())


async def lazy_loading(*, session_maker: orm.sessionmaker) -> Optional[str]:
    """Demonstrate the problem with lazily loading database defaults.

    :param session_maker: The async session maker to use
    :return: The result of the simple statement
    """
    return await helpers.access_attribute_with_server_default(
        models.LazyTraveler, session_maker=session_maker
    )


async def eager_loading(*, session_maker: orm.sessionmaker) -> Optional[str]:
    """Demonstrate the eager solution to database defaults.

    :param session_maker: The async session maker to use
    :return: The result of the simple statement.
    """
    return await helpers.access_attribute_with_server_default(
        models.EagerTraveler, session_maker=session_maker
    )


async def unloaded_relationship(*, session_maker: orm.sessionmaker) -> str:
    """Show that relationships are not preloaded.

    :param session_maker: The async session maker
    :return: The ``repr`` of the ORM instance
    """
    select_traveler = await helpers.create_orm_instance_async(
        orm_model=models.TravelerWithDestination,
        creation_kwargs={
            "name": "Sebastiaan",
            "age": 35,
            "destination": models.Country(name="Norway"),
        },
        session_maker=session_maker,
    )

    async with session_maker() as session:
        result = await session.execute(select_traveler)
        traveler = cast(models.TravelerWithDestination, result.scalar())
    return f"{traveler!r}"


async def access_unloaded_relationship(
    *, session_maker: orm.sessionmaker
) -> str | None:
    """Demonstrate that accessing an unloaded relationship fails.

    :param session_maker: The async session
    :return: The optional string showing the value of the relationship
    """
    select_traveler = await helpers.create_orm_instance_async(
        orm_model=models.TravelerWithDestination,
        creation_kwargs={
            "name": "Sebastiaan",
            "age": 35,
            "destination": models.Country(name="Norway"),
        },
        session_maker=session_maker,
    )
    return await _get_destination(select_traveler, session_maker=session_maker)


async def access_loaded_relationship(*, session_maker: orm.sessionmaker) -> str | None:
    """Demonstrate that accessing an unloaded relationship fails.

    :param session_maker: The async session
    :return: The optional string showing the value of the relationship
    """
    select_traveler = await helpers.create_orm_instance_async(
        orm_model=models.TravelerWithDestination,
        creation_kwargs={
            "name": "Sebastiaan",
            "age": 35,
            "destination": models.Country(name="Norway"),
        },
        session_maker=session_maker,
    )
    joinedload_select = select_traveler.options(
        orm.joinedload(models.TravelerWithDestination.destination)
    )
    return await _get_destination(joinedload_select, session_maker=session_maker)


async def _get_destination(
    traveler_select: sql.Select, *, session_maker: orm.sessionmaker
) -> str | None:
    """Try to get the destination of the selected traveler.

    :param traveler_select: The select to fetch the traveler
    :param session_maker: The session maker to use
    :return: A string containing the destination or None
    """
    async with session_maker() as session:
        result = await session.execute(traveler_select)
        traveler = cast(models.TravelerWithDestination, result.scalar())
        print(helpers.format_divider("Engine activity after fetching ORM-instance"))
        try:
            result = f"The traveler is traveling to {traveler.destination.name!r}"
        except exc.MissingGreenlet as exception:
            print(f"Cannot access lazy attribute: {exception!r}")
            result = None
    return result


async def main():
    async_engine = helpers.get_engine_async(os.environ["DATABASE_URL"])
    session_maker = helpers.get_async_sessions_maker(async_engine)
    await helpers.execute_verbosely_async(
        helpers.flush_database_async(async_engine=async_engine), label="flush_db"
    )

    targets = {
        "simple": simple_statement("Hello, world!", async_engine=async_engine),
        "lazy_loading": lazy_loading(session_maker=session_maker),
        "eager_loading": eager_loading(session_maker=session_maker),
        "unloaded_relationship": unloaded_relationship(session_maker=session_maker),
        "access_unloaded_relationship": access_unloaded_relationship(
            session_maker=session_maker
        ),
        "access_loaded_relationship": access_loaded_relationship(
            session_maker=session_maker
        ),
    }

    for label, coroutine in targets.items():
        await helpers.execute_verbosely_async(coroutine, label=label)

    await async_engine.dispose()


if __name__ == "__main__":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        asyncio.run(main())
