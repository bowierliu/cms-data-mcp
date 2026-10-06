"""Full workflow through advertised MCP tools, not direct Python handlers."""

import json
from datetime import UTC, datetime

import pytest
from jsonschema import validate
from mcp import Client

from cms_mcp.server import create_server

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_limited_catalog_response_reports_truncation(tmp_path):
    async with Client(create_server(tmp_path)) as client:
        result = await client.call_tool("search_datasets", {"query": "cms", "limit": 1})
        assert not result.is_error
        assert result.structured_content["scope"]["truncated"] is True
        assert result.structured_content["data"]["total_matches"] == 2


async def test_complete_offline_pipeline_uses_advertised_schemas(tmp_path):
    async with Client(
        create_server(tmp_path, clock=lambda: datetime(2026, 10, 4, 20, tzinfo=UTC))
    ) as c:
        tools = {t.name: t for t in (await c.list_tools()).tools}
        assert len(tools) == 9

        async def call(name, arguments):
            result = await c.call_tool(name, arguments)
            assert not result.is_error, result
            output = result.structured_content
            validate(output, tools[name].output_schema)
            assert json.loads(result.content[0].text) == output
            return output

        search = await call("search_datasets", {"query": "cardiologist"})
        assert len(search["data"]["datasets"]) == 2
        meta = await call("get_dataset_metadata", {"dataset_id": "synthetic-count-v1"})
        source = meta["data"]["source_ref"]
        await call(
            "get_schema",
            {
                "dataset_id": "synthetic-count-v1",
                "source_ref": source,
                "fields": ["npi", "record_count"],
            },
        )
        created = await call(
            "retrieve_dataset", {"dataset_id": "synthetic-count-v1", "source_ref": source}
        )
        artifact = created["data"]["artifact_id"]
        report = await call("validate_dataset", {"artifact_id": artifact})
        assert report["data"]["report"]["overall"] == "pass"
        query = await call(
            "query_dataset",
            {
                "artifact_id": artifact,
                "validation_id": report["data"]["validation_id"],
                "select": ["state", "record_count"],
            },
        )
        export = await call(
            "export_result", {"result_id": query["data"]["result_id"], "format": "csv"}
        )
        assert export["data"]["content"] == "state,record_count\r\nCA,5\r\n"
        full = await call("get_provenance", {"artifact_id": export["provenance_id"]})
        assert len(full["data"]["records"]) == 3
        assert full["scope"]["synthetic"] is True
        assert full["scope"]["truncated"] is False


@pytest.mark.parametrize(
    "tool,args,code",
    [
        ("get_dataset_metadata", {"dataset_id": "mj5m-pzi6"}, "LIVE_ACCESS_DISABLED"),
        ("get_dataset_metadata", {"dataset_id": "unknown"}, "DATASET_NOT_FOUND"),
        (
            "get_dataset_metadata",
            {"dataset_id": "synthetic-count-v1", "release": "1900"},
            "RELEASE_UNRESOLVED",
        ),
        ("query_dataset", {"sql": "SELECT DO_NOT_ECHO"}, "INVALID_ARGUMENTS"),
        ("export_result", {"result_id": "../../DO_NOT_ECHO"}, "INVALID_ARGUMENTS"),
        ("search_datasets", {"query": "cms", "limit": 0}, "INVALID_ARGUMENTS"),
    ],
)
async def test_workflow_tool_errors_are_safe_and_leave_no_files(tmp_path, tool, args, code):
    async with Client(create_server(tmp_path)) as c:
        result = await c.call_tool(tool, args)
        assert result.is_error
        assert result.structured_content["error"]["code"] == code
        assert "DO_NOT_ECHO" not in result.model_dump_json()
    assert not list(tmp_path.iterdir())
