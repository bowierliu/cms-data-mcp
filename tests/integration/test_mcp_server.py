"""Real SDK sessions, plus stdio subprocesses, with synthetic artifacts only."""

import json
import socket
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import anyio
import pytest
from jsonschema import validate
from mcp import Client, MCPError, StdioServerParameters
from mcp.types import INVALID_PARAMS

from cms_mcp.server import create_server
from cms_mcp.service import CountService
from cms_mcp.storage import LocalArtifactStore

pytestmark = [pytest.mark.integration, pytest.mark.anyio]
NOW = datetime(2026, 10, 4, 18, tzinfo=UTC)
TOOLS = {
    "search_datasets",
    "get_dataset_metadata",
    "get_schema",
    "retrieve_dataset",
    "materialize_synthetic_count",
    "validate_dataset",
    "query_dataset",
    "export_result",
    "get_provenance",
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Network access is forbidden in MCP tests")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


@pytest.fixture
def server(tmp_path):
    return create_server(tmp_path / "cache", clock=lambda: NOW)


def error_code(result):
    assert result.is_error is True
    assert json.loads(result.content[0].text) == result.structured_content
    return result.structured_content["error"]["code"]


async def test_discovery_advertises_strict_schemas_and_side_effects(server, tmp_path):
    async with Client(server, raise_exceptions=True) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
        assert set(tools) == TOOLS
        create = tools["materialize_synthetic_count"]
        lookup = tools["get_provenance"]
        assert create.input_schema["properties"] == {}
        assert create.input_schema["additionalProperties"] is False
        assert lookup.input_schema["required"] == ["artifact_id"]
        assert lookup.input_schema["additionalProperties"] is False
        assert lookup.input_schema["properties"]["artifact_id"]["maxLength"] == 75
        assert create.annotations.read_only_hint is False
        assert create.annotations.destructive_hint is False
        assert create.annotations.idempotent_hint is True
        assert lookup.annotations.read_only_hint is True
        assert all(t.annotations.open_world_hint is False for t in tools.values())
        assert client.server_info.name == "cms-data-mcp"
        assert client.protocol_version
        assert not (tmp_path / "cache").exists()


async def test_sdk_calls_validate_outputs_and_preserve_provenance(server, tmp_path):
    async with Client(server, raise_exceptions=True) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
        first = await client.call_tool("materialize_synthetic_count", {})
        assert first.is_error is False
        created = first.structured_content
        validate(created, tools["materialize_synthetic_count"].output_schema)
        assert json.loads(first.content[0].text) == created
        assert created["scope"]["synthetic"] is True
        assert created["scope"]["truncated"] is False
        assert created["scope"]["state"] == "CA"
        assert created["data"]["record_count"] == 5
        assert created["data"]["counts_distinct_people"] is False
        assert created["warnings"]
        path = next((tmp_path / "cache").glob("*.json"))
        original = path.read_bytes()
        second = await client.call_tool("materialize_synthetic_count", {})
        assert second.structured_content == created
        fetched = await client.call_tool(
            "get_provenance", {"artifact_id": created["data"]["artifact_id"]}
        )
        assert fetched.is_error is False
        data = fetched.structured_content
        validate(data, tools["get_provenance"].output_schema)
        provenance = data["data"]["provenance"]
        assert provenance["cache_status"] == "hit"
        assert provenance["served_at"] == "2026-10-04T18:00:00Z"
        assert provenance["observation"]["retrieved_at"] == "2026-01-01T00:00:01Z"
        assert data["data"]["snapshot_id"] == created["data"]["snapshot_id"]
        assert path.read_bytes() == original
        assert len(fetched.model_dump_json().encode()) < 32768


@pytest.mark.parametrize(
    "tool,args",
    [
        ("materialize_synthetic_count", {"url": "DO_NOT_ECHO"}),
        ("materialize_synthetic_count", {"filters": {"city": "DO_NOT_ECHO"}}),
        ("get_provenance", {}),
        ("get_provenance", {"artifact_id": "../../DO_NOT_ECHO"}),
        ("get_provenance", {"artifact_id": 1}),
        ("get_provenance", {"artifact_id": None}),
        ("get_provenance", {"artifact_id": "artifact:" + "a" * 64, "path": "DO_NOT_ECHO"}),
        ("get_provenance", {"artifact_id": "artifact:" + "a" * 64 + "\n"}),
        ("get_provenance", {"artifact_id": "a" * 10000}),
    ],
)
async def test_invalid_inputs_are_safe_tool_errors(server, tmp_path, caplog, tool, args):
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool(tool, args)
        assert error_code(result) == "INVALID_ARGUMENTS"
        assert "DO_NOT_ECHO" not in result.model_dump_json()
        assert "DO_NOT_ECHO" not in caplog.text
    assert not (tmp_path / "cache").exists()


async def test_unknown_tool_is_safe_protocol_error(server, caplog):
    async with Client(server, raise_exceptions=True) as client:
        with pytest.raises(MCPError) as caught:
            await client.call_tool("DO_NOT_ECHO", {})
        assert caught.value.code == INVALID_PARAMS
        assert "DO_NOT_ECHO" not in str(caught.value)
    assert "DO_NOT_ECHO" not in caplog.text


async def test_missing_artifact_returns_recovery_then_client_can_retry(server):
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("get_provenance", {"artifact_id": "artifact:" + "0" * 64})
        assert error_code(result) == "ARTIFACT_NOT_FOUND"
        assert result.structured_content["error"]["recovery"]
        assert (await client.call_tool("materialize_synthetic_count", {})).is_error is False


async def test_corrupt_artifact_is_not_repaired(server, tmp_path):
    async with Client(server, raise_exceptions=True) as client:
        created = (await client.call_tool("materialize_synthetic_count", {})).structured_content
        path = next((tmp_path / "cache").glob("*.json"))
        path.write_bytes(b"DO_NOT_ECHO")
        for tool, args in (
            ("get_provenance", {"artifact_id": created["data"]["artifact_id"]}),
            ("materialize_synthetic_count", {}),
        ):
            result = await client.call_tool(tool, args)
            assert error_code(result) == "ARTIFACT_CORRUPT"
            assert "DO_NOT_ECHO" not in result.model_dump_json()
        assert path.read_bytes() == b"DO_NOT_ECHO"


async def test_cache_source_is_fixed_by_server(server, tmp_path):
    from cms_mcp.models import SourceReference
    from cms_mcp.synthetic import load_synthetic_fixture

    fixture = load_synthetic_fixture()
    changed = SourceReference.model_validate(
        fixture.source.model_dump() | {"metadata_hash": "b" * 64}
    )
    seeded = CountService(LocalArtifactStore(tmp_path / "cache")).materialize_count(
        fixture.body,
        source=changed,
        retrieved_at=fixture.retrieved_at,
        normalized_at=fixture.normalized_at,
    )
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("get_provenance", {"artifact_id": seeded.artifact_id})
        assert error_code(result) == "SOURCE_SCOPE_MISMATCH"


@pytest.mark.parametrize("change", ["count", "retrieval_time", "normalization_time"])
async def test_same_source_different_fixture_evidence_is_rejected(server, tmp_path, change):
    from cms_mcp.synthetic import load_synthetic_fixture

    fixture = load_synthetic_fixture()
    body = fixture.body
    retrieved_at = fixture.retrieved_at
    normalized_at = fixture.normalized_at
    if change == "count":
        body = json.dumps(json.loads(body) | {"count": 123}).encode()
    elif change == "retrieval_time":
        retrieved_at += timedelta(microseconds=1)
    else:
        normalized_at += timedelta(seconds=1)
    seeded = CountService(LocalArtifactStore(tmp_path / "cache")).materialize_count(
        body,
        source=fixture.source,
        retrieved_at=retrieved_at,
        normalized_at=normalized_at,
    )
    path = next((tmp_path / "cache").glob("*.json"))
    original = path.read_bytes()
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("get_provenance", {"artifact_id": seeded.artifact_id})
        assert error_code(result) == "SOURCE_SCOPE_MISMATCH"
        assert "fixture_id" not in result.structured_content
    assert path.read_bytes() == original


async def test_storage_failure_does_not_leak_local_path(tmp_path):
    root = tmp_path / "DO_NOT_ECHO"
    root.write_text("existing")
    async with Client(create_server(root, clock=lambda: NOW), raise_exceptions=True) as client:
        result = await client.call_tool("materialize_synthetic_count", {})
        assert error_code(result) == "STORAGE_UNAVAILABLE"
        assert "DO_NOT_ECHO" not in result.model_dump_json()
    assert root.read_text() == "existing"


async def test_large_provenance_returns_limit_error_without_truncating(tmp_path, monkeypatch):
    from cms_mcp import server as adapter
    from cms_mcp.models import SourceReference
    from cms_mcp.synthetic import load_synthetic_fixture

    fixture = load_synthetic_fixture()
    source = SourceReference.model_validate(
        fixture.source.model_dump()
        | {
            "download_url": "https://data.cms.gov/provider-data/sites/default/files/resources/"
            + "x" * 18000
            + "/DAC_NationalDownloadableFile.csv",
            "metadata_hash": "b" * 64,
        }
    )
    monkeypatch.setattr(adapter, "load_synthetic_fixture", lambda: replace(fixture, source=source))
    async with Client(create_server(tmp_path, clock=lambda: NOW), raise_exceptions=True) as client:
        created = await client.call_tool("materialize_synthetic_count", {})
        assert created.is_error is False
        result = await client.call_tool(
            "get_provenance", {"artifact_id": created.structured_content["data"]["artifact_id"]}
        )
        assert error_code(result) == "RESOURCE_LIMIT"
        assert "x" * 100 not in result.model_dump_json()


# Install a test-only network audit hook before importing/running the actual
# module entry point. Stdio and asyncio's local socketpair remain available.
OFFLINE_BOOT = """
import runpy, sys
def deny_network(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo', 'socket.bind'}:
        raise RuntimeError('network disabled in stdio test')
sys.addaudithook(deny_network)
sys.argv = ['cms_mcp.server', *sys.argv[1:]]
runpy.run_module('cms_mcp.server', run_name='__main__')
"""


async def test_stdio_process_discovers_calls_and_restarts_without_state_loss(tmp_path, capfd):
    root = tmp_path / "cache"
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-I", "-c", OFFLINE_BOOT, "--cache-dir", str(root)],
        cwd=tmp_path,
    )
    with anyio.fail_after(20):
        async with Client(parameters, read_timeout_seconds=5) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
            assert set(tools) == TOOLS
            created = await client.call_tool("materialize_synthetic_count", {})
            assert created.is_error is False
            artifact_id = created.structured_content["data"]["artifact_id"]
            invalid = await client.call_tool("get_provenance", {"artifact_id": "DO_NOT_ECHO"})
            assert error_code(invalid) == "INVALID_ARGUMENTS"
            validate(invalid.structured_content, tools["get_provenance"].output_schema)
            protocol = client.protocol_version
        before = next(root.glob("*.json")).read_bytes()
        async with Client(parameters, read_timeout_seconds=5) as client:
            assert client.protocol_version == protocol
            result = await client.call_tool("get_provenance", {"artifact_id": artifact_id})
            assert result.is_error is False
            assert result.structured_content["data"]["record_count"] == 5
            assert result.structured_content["data"]["provenance"]["cache_status"] == "hit"
        assert next(root.glob("*.json")).read_bytes() == before
    captured = capfd.readouterr()
    assert "DO_NOT_ECHO" not in captured.err
    assert "Traceback" not in captured.err


def test_terminal_smoke_script_runs_real_client_without_leaving_artifacts(tmp_path):
    script = Path(__file__).resolve().parents[2] / "scripts/check_mcp.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["tools"] == sorted(TOOLS)
    assert output["synthetic"] is True
    assert output["record_count"] == 5
    assert output["cache_status"] == "hit"
    assert output["validation_status"] == "pass"
    assert output["query_rows"] == [["CA", 5]]
    assert output["csv"] == "state,record_count\r\nCA,5\r\n"
    assert output["lineage_steps"] == 3
    assert output["protocol_version"]
    assert not list(tmp_path.iterdir())
