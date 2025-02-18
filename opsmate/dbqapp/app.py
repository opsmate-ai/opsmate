from opsmate.dbq.dbq import Worker
from opsmate.libs.config import config
import asyncio
from sqlmodel import create_engine, Session, text
import structlog
from opsmate.app.base import on_startup as base_app_on_startup

logger = structlog.get_logger()


async def main():
    engine = create_engine(
        config.db_url,
        connect_args={"check_same_thread": False},
        # echo=True,
    )
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.close()

    await base_app_on_startup(engine)

    session = Session(engine)
    worker = Worker(session, 10)
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
