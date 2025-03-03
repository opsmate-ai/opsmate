from opsmate.tools.prom import prometheus_query, prometheus_metrics, PromQL
import asyncio
import os


async def main():
    prom = PromQL(
        endpoint="https://prometheus-prod-01-eu-west-0.grafana.net/api/prom",
        user_id=os.getenv("GRAFANA_USER_ID"),
        api_key=os.getenv("GRAFANA_API_KEY"),
    )
    metrics = await prom.metrics()
    print(metrics)


asyncio.run(main())
