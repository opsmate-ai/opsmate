from opsmate.dbq.dbq import Worker
from opsmate.config import config
import asyncio
import structlog
import signal

logger = structlog.get_logger()


async def main(worker_count: int = 10, worker_queue: str = "default"):
    engine = config.db_engine()

    worker = Worker(engine, worker_count, queue_name=worker_queue)

    def handle_signal(signal_number, frame):
        logger.info("Received signal", signal_number=signal_number)
        asyncio.create_task(worker.stop())

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
