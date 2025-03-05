from opsmate.tools.knowledge_retrieval import KnowledgeRetrieval
from opsmate.knowledgestore.models import aconn, Category, init_table
from opsmate.tools.prom import PromQL, prometheus_query
from sqlmodel import create_engine, Session, text
from opsmate.libs.config import config
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

    await query.run(
        context={
            "prometheus_endpoint": "https://prometheus-prod-01-eu-west-0.grafana.net/api/prom",
            "prometheus_user_id": os.getenv("GRAFANA_USER_ID"),
            "prometheus_api_key": os.getenv("GRAFANA_API_KEY"),
        }
    )

    query.time_series(in_terminal)


async def main():
    await init_table()

    # dbconn = await aconn()

    # table = await dbconn.open_table("knowledge_store")

    # await prom_graph(
    #     "cpu usage broken down by node for the metal cluster over the past hour",
    #     in_terminal=True,
    # )

    prom = PromQL(
        endpoint="https://prometheus-prod-01-eu-west-0.grafana.net/api/prom",
        user_id=os.getenv("GRAFANA_USER_ID"),
        api_key=os.getenv("GRAFANA_API_KEY"),
    )

    engine = create_engine(
        config.db_url,
        connect_args={"check_same_thread": False},
        # echo=True,
    )
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.close()
    with Session(engine) as session:
        await prom.ingest_metrics(session)


if __name__ == "__main__":
    asyncio.run(main())
