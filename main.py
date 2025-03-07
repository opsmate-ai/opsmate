from opsmate.knowledgestore.models import aconn
from opsmate.tools.prom import PrometheusTool, PromQL, prometheus_query
from opsmate.libs.config import config
from sqlalchemy import text
from sqlmodel import create_engine, Session
import os
import asyncio


async def prom_graph(query: str, in_terminal: bool = False):
    query = await prometheus_query(
        query,
        context={
            "llm_summary": False,
            "top_n": 20,
        },
    )

    print(query)

    await query.run()

    query.time_series(in_terminal)


async def main():
    # await init_table()

    # dbconn = await aconn()

    # table = await dbconn.open_table("knowledge_store")

    # await prom_graph(
    #     "cpu usage broken down by node for the metal cluster over the past 2 hours",
    #     in_terminal=True,
    # )

    prom = PromQL(
        endpoint="https://prometheus-prod-01-eu-west-0.grafana.net/api/prom",
        user_id=os.getenv("GRAFANA_USER_ID"),
        api_key=os.getenv("GRAFANA_API_KEY"),
    )

    engine = create_engine(
        config.db_url,
        connect_args={"check_same_thread": False, "timeout": 20},
        # echo=True,
    )
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.close()
    with Session(engine) as session:
        await prom.ingest_metrics(session)


if __name__ == "__main__":
    asyncio.run(main())
