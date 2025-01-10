from opsmate.tests.base import BaseTestCase
from opsmate.tools.loki import LokiMetrics, LokiLogs, loki_logs
import pytest
import os


class TestLoki(BaseTestCase):

    @staticmethod
    def skip_if_no_loki_credentials():
        return os.getenv("LOKI_USER_ID") is None or os.getenv("LOKI_AUTH_TOKEN") is None

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        skip_if_no_loki_credentials(),
        reason="LOKI_USER_ID and LOKI_AUTH_TOKEN must be set",
    )
    async def test_loki_metrics(self):
        LokiMetrics.endpoint = "https://logs-prod-eu-west-0.grafana.net/loki"

        loki = LokiMetrics(query="1+1", limit=100, direction="forward")
        assert loki._client is not None

        response = await loki.run()

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        skip_if_no_loki_credentials(),
        reason="LOKI_USER_ID and LOKI_AUTH_TOKEN must be set",
    )
    async def test_loki_logs(self):
        LokiLogs.endpoint = "https://logs-prod-eu-west-0.grafana.net/loki"
        loki = LokiLogs(
            query='{namespace="external-dns"}', limit=100, direction="forward"
        )
        assert loki._client is not None

        response = await loki.run()
        print(response)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        skip_if_no_loki_credentials(),
        reason="LOKI_USER_ID and LOKI_AUTH_TOKEN must be set",
    )
    async def test_loki_logs_dino(self):
        LokiLogs.endpoint = "https://logs-prod-eu-west-0.grafana.net/loki"
        query = await loki_logs(
            "show me the external-dns logs for the last 10 minutes",
            "Use cluster=hjktech-metal-001 as the cluster label filter",
        )
        result = await query.run()
        print(result)
