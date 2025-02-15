from opsmate.dbq.dbq import SQLModel, Worker
from opsmate.libs.config import config
import asyncio
from sqlmodel import create_engine, Session, text
from opsmate.ingestions.jobs import init_engine
import structlog

logger = structlog.get_logger()


async def main():
    engine = create_engine(config.db_url, connect_args={"check_same_thread": False})
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.close()

    init_engine(engine)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        worker = Worker(session, 10)
        task = asyncio.create_task(worker.start())
        await task


if __name__ == "__main__":
    asyncio.run(main())
