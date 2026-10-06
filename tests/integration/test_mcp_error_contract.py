"""Validate error payloads as a strict client does, even when isError is true."""

import json

import pytest
from jsonschema import Draft202012Validator
from mcp import Client

from cms_mcp.server import create_server

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.parametrize(
    "tool,arguments,code",
    [
        ("search_datasets", {"query": ""}, "INVALID_ARGUMENTS"),
        ("get_dataset_metadata", {"dataset_id": "unknown"}, "DATASET_NOT_FOUND"),
        (
            "get_schema",
            {"dataset_id": "synthetic-count-v1", "fields": ["county"]},
            "UNSUPPORTED_GEOGRAPHY",
        ),
        ("retrieve_dataset", {"dataset_id": "unknown"}, "DATASET_NOT_FOUND"),
        ("materialize_synthetic_count", {"unexpected": True}, "INVALID_ARGUMENTS"),
        ("validate_dataset", {"artifact_id": "artifact:" + "0" * 64}, "ARTIFACT_NOT_FOUND"),
        (
            "query_dataset",
            {
                "artifact_id": "artifact:" + "0" * 64,
                "validation_id": "validation:" + "0" * 64,
                "limit": 0,
            },
            "INVALID_ARGUMENTS",
        ),
        ("get_provenance", {"artifact_id": "artifact:" + "0" * 64}, "ARTIFACT_NOT_FOUND"),
        ("export_result", {"result_id": "result:" + "0" * 64}, "ARTIFACT_NOT_FOUND"),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
async def test_error_response_matches_advertised_output_schema(tmp_path, tool, arguments, code):
    async with Client(create_server(tmp_path)) as client:
        tools = {item.name: item for item in (await client.list_tools()).tools}
        if tool in {"get_schema", "retrieve_dataset"}:
            metadata = await client.call_tool(
                "get_dataset_metadata", {"dataset_id": "synthetic-count-v1"}
            )
            assert not metadata.is_error
            arguments = arguments | {
                "source_ref": metadata.structured_content["data"]["source_ref"]
            }

        result = await client.call_tool(tool, arguments)
        assert result.is_error
        payload = result.structured_content
        assert payload["error"]["code"] == code
        assert payload["error"]["message"]
        assert payload["error"]["recovery"]
        assert json.loads(result.content[0].text) == payload

        # The SDK skips this check for isError results; strict clients need it too.
        schema = tools[tool].output_schema
        Draft202012Validator.check_schema(schema)
        errors = list(Draft202012Validator(schema).iter_errors(payload))
        assert not errors, "\n".join(error.message for error in errors)


async def test_output_schemas_keep_success_and_error_envelopes_strict(tmp_path):
    async with Client(create_server(tmp_path)) as client:
        tools = {item.name: item for item in (await client.list_tools()).tools}
        created = await client.call_tool("materialize_synthetic_count", {})
        assert not created.is_error
        success = created.structured_content
        error = {"code": "INVALID_ARGUMENTS", "message": "Invalid input.", "recovery": "Retry."}

        for tool in tools.values():
            validator = Draft202012Validator(tool.output_schema)
            for malformed in (
                {},
                {"error": {"code": "INVALID_ARGUMENTS", "message": "Invalid input."}},
                {"error": error | {"code": 123}},
                {"error": error | {"unexpected": True}},
                {"error": error, "unexpected": True},
                success | {"error": error},
            ):
                assert not validator.is_valid(malformed), (tool.name, malformed)

        validator = Draft202012Validator(tools["materialize_synthetic_count"].output_schema)
        for required in ("summary", "data", "scope", "warnings", "provenance_id"):
            incomplete = {key: value for key, value in success.items() if key != required}
            assert not validator.is_valid(incomplete), required
        assert not validator.is_valid(success | {"data": success["data"] | {"record_count": "5"}})
