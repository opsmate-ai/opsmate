from opsmate.dbq.dbq import SQLModel, Worker
from opsmate.libs.config import config
import asyncio
from sqlmodel import create_engine, Session, text
import structlog

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

    SQLModel.metadata.create_all(engine)

    session = Session(engine)
    worker = Worker(session, 10)
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
