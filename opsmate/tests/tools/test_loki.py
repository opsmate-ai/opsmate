from opsmate.tools.loki import log_format, LogParser, LokiQuery
import pytest
from unittest.mock import patch, AsyncMock
from httpx import Response
import json


async def test_log_format():
    assert (
        await log_format(
            '2025-04-23T10:10:24.377036381Z level=info msg="rejoining peers"',
            model="gpt-4o-mini",
        )
        == LogParser.LOGFMT
    )

    assert (
        await log_format(
            """{"level":"info","msg":"rejoining peers","time":"2025-04-23T10:10:24.377036381Z"}""",
            model="gpt-4o-mini",
        )
        == LogParser.JSON
    )

    assert (
        await log_format("this is a log line", model="gpt-4o-mini") == LogParser.UNKNOWN
    )


async def test_loki_query():
    # Create a mock response for the HTTP client
    mock_response = Response(
        status_code=200,
        content=json.dumps(
            {
                "data": {
                    "result": [
                        {
                            "stream": {"container": "app", "namespace": "test"},
                            "values": [
                                [
                                    "1682412624000000000",
                                    '{"level":"info","msg":"test log","time":"2025-04-23T10:10:24Z"}',
                                ]
                            ],
                        }
                    ]
                }
            }
        ).encode(),
    )

    # Create a mock HTTP client
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # Configure the mock to return our predefined response
        mock_post.return_value = mock_response

        # Create and call a LokiQuery instance
        query = LokiQuery(
            query='{namespace="test"} | json',
            start="2025-04-23T10:00:00Z",
            end="2025-04-23T11:00:00Z",
            log_parser=LogParser.JSON,
        )

        result = await query(context={})

        # Assert that the mock was called with the expected parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        assert "data" in call_args
        assert call_args["data"]["query"] == '{namespace="test"} | json'

        # Assert that the result is as expected
        assert len(result) == 1
        assert result[0]["container"] == "app"
        assert result[0]["namespace"] == "test"


async def test_loki_query_auto_detect_parser():
    # Create a mock response for the log sample
    sample_response = Response(
        status_code=200,
        content=json.dumps(
            {
                "data": {
                    "result": [
                        {
                            "stream": {"container": "app", "namespace": "test"},
                            "values": [
                                [
                                    "1682412624000000000",
                                    '{"level":"info","msg":"test log","time":"2025-04-23T10:10:24Z"}',
                                ]
                            ],
                        }
                    ]
                }
            }
        ).encode(),
    )

    # Create a mock response for the actual query
    query_response = Response(
        status_code=200,
        content=json.dumps(
            {
                "data": {
                    "result": [
                        {
                            "stream": {
                                "container": "app",
                                "namespace": "test",
                                "pod": "test-pod",
                                "level": "info",
                                "msg": "test log",
                                "time": "2025-04-23T10:10:24Z",
                            },
                            "values": [
                                [
                                    "1682412624000000000",
                                    '{"level":"info","msg":"test log","time":"2025-04-23T10:10:24Z"}',
                                ]
                            ],
                        }
                    ]
                }
            }
        ).encode(),
    )

    # Create a mock HTTP client that returns different responses for each call
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [sample_response, query_response]

        # Mock the log_format function to return JSON format
        with patch(
            "opsmate.tools.loki.log_format", new_callable=AsyncMock
        ) as mock_log_format:
            mock_log_format.return_value = LogParser.JSON

            # Create and call a LokiQuery instance with UNKNOWN parser
            query = LokiQuery(
                query='{namespace="test"}',
                start="2025-04-23T10:00:00Z",
                end="2025-04-23T11:00:00Z",
                log_parser=LogParser.UNKNOWN,
            )

            result = await query.run(context={})

            # Assert log_format was called
            mock_log_format.assert_called_once()

            # Assert that the mock was called twice (once for detection, once for query)
            assert mock_post.call_count == 2

            # Second call should include the detected parser
            second_call_args = mock_post.call_args_list[1][1]
            assert second_call_args["data"]["query"] == '{namespace="test"} | json'

            # Assert that the result is as expected
            assert len(result) == 1
            assert result[0]["container"] == "app"
            assert result[0]["namespace"] == "test"
            assert result[0]["pod"] == "test-pod"

            assert query.log_parser == LogParser.JSON
            assert query.output == [
                {
                    "container": "app",
                    "namespace": "test",
                    "pod": "test-pod",
                    "level": "info",
                    "msg": "test log",
                    "time": "2025-04-23T10:10:24Z",
                }
            ]
            assert query.dataframe.shape == (1, 6)


async def test_loki_query_error_handling():
    # Create a mock error response
    error_response = Response(
        status_code=400,
        content=json.dumps({"error": "Bad request"}).encode(),
    )

    # Create a mock HTTP client
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # Configure the mock to return our error response
        mock_post.return_value = error_response

        # Create and call a LokiQuery instance
        query = LokiQuery(
            query='{namespace="test"}',
            start="2025-04-23T10:00:00Z",
            end="2025-04-23T11:00:00Z",
            log_parser=LogParser.JSON,
        )

        result = await query(context={})

        # Assert that the mock was called
        mock_post.assert_called_once()

        # Assert that the result contains the error information
        assert len(result) == 1
        assert "error" in result[0]
        assert result[0]["error"] == "Failed to fetch logs from loki"
        assert "data" in result[0]
