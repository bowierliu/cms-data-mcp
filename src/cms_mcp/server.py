"""Local stdio MCP transport for the bounded CMS aggregate workflow."""

import argparse
import json
import logging
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from time import monotonic
from typing import Any

import anyio
from mcp import MCPError
from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.types import (
    INVALID_PARAMS,
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
    ToolAnnotations,
)
from pydantic import BaseModel, ValidationError

from cms_mcp.analytics import AnalyticsError
from cms_mcp.api import CONTRACTS, ErrorEnvelope, ToolError, invoke
from cms_mcp.sources import SourceError
from cms_mcp.storage import ArtifactStoreError
from cms_mcp.synthetic import load_synthetic_fixture
from cms_mcp.workflow import Workflow, WorkflowError

MAX_STRUCTURED_BYTES = 16_384
LOGGER = logging.getLogger("cms-data-mcp")
_ERRORS = {
    "INVALID_ARGUMENTS": (
        "Arguments do not match this tool's schema.",
        "Use tools/list and only declared fields.",
    ),
    "ARTIFACT_NOT_FOUND": (
        "The requested record is unavailable.",
        "Use an ID returned by an earlier successful tool call.",
    ),
    "SOURCE_SCOPE_MISMATCH": (
        "Source, fixture, or parent evidence does not match.",
        "Use matching source/artifact/validation IDs from this workflow.",
    ),
    "ARTIFACT_CORRUPT": (
        "Stored integrity or validation failed.",
        "Ask the operator to inspect the cache; it was not repaired.",
    ),
    "STORAGE_UNAVAILABLE": (
        "Local storage could not complete the operation.",
        "Ask the operator to check the cache directory.",
    ),
    "RESOURCE_LIMIT": (
        "The artifact or result exceeds the size limit.",
        "Request only the supported bounded aggregate view.",
    ),
    "INTERNAL_ERROR": (
        "The operation could not complete safely.",
        "Ask the operator to check the installation and system clock.",
    ),
    "DATASET_NOT_FOUND": (
        "This dataset is not in the curated catalog.",
        "Use search_datasets for supported IDs.",
    ),
    "RELEASE_UNRESOLVED": (
        "This release selector is unsupported.",
        "Use latest, or fixture-v1 for the synthetic example.",
    ),
    "LIVE_ACCESS_DISABLED": (
        "Live CMS requests are disabled by the operator.",
        "Use synthetic-count-v1 or start the server with --enable-live.",
    ),
    "UNSUPPORTED_GEOGRAPHY": (
        "The saved aggregate has no city, ZIP, or county detail.",
        "Use only the fixed California view; do not substitute city for county.",
    ),
    "UNSUPPORTED_FIELD": (
        "The field is not supported by this contract.",
        "Use case-sensitive names: state, primary_specialty, record_count, "
        "npi, pri_spec, citytown, zip_code.",
    ),
    "VALIDATION_FAILED": (
        "Required validation checks did not pass.",
        "Inspect the validation report before querying.",
    ),
    "SOURCE_CHANGED": (
        "CMS source metadata changed since selection.",
        "Resolve fresh metadata and retry with its source_ref.",
    ),
    "SOURCE_UNAVAILABLE": (
        "The approved CMS source could not be read safely.",
        "Retry later; no alternate data or raw-file fallback was used.",
    ),
    "SOURCE_CONTRACT_FAILED": (
        "The CMS response does not match the approved contract.",
        "Review the source contract; no result was published.",
    ),
}
_CODE_MAP = {
    "artifact_not_found": "ARTIFACT_NOT_FOUND",
    "source_scope_mismatch": "SOURCE_SCOPE_MISMATCH",
    "validation_scope_mismatch": "SOURCE_SCOPE_MISMATCH",
    "lineage_mismatch": "SOURCE_SCOPE_MISMATCH",
    "artifact_hash_mismatch": "ARTIFACT_CORRUPT",
    "invalid_artifact": "ARTIFACT_CORRUPT",
    "invalid_artifact_file": "ARTIFACT_CORRUPT",
    "storage_io_error": "STORAGE_UNAVAILABLE",
    "artifact_too_large": "RESOURCE_LIMIT",
    "invalid_query": "INVALID_ARGUMENTS",
    "invalid_arguments": "INVALID_ARGUMENTS",
    "invalid_artifact_id": "INVALID_ARGUMENTS",
    "invalid_validation_id": "INVALID_ARGUMENTS",
    "dataset_not_found": "DATASET_NOT_FOUND",
    "release_unresolved": "RELEASE_UNRESOLVED",
    "live_access_disabled": "LIVE_ACCESS_DISABLED",
    "unsupported_geography": "UNSUPPORTED_GEOGRAPHY",
    "unsupported_field": "UNSUPPORTED_FIELD",
    "validation_failed": "VALIDATION_FAILED",
    "source_changed": "SOURCE_CHANGED",
    "source_metadata_invalid": "SOURCE_CONTRACT_FAILED",
    "count_response_invalid": "SOURCE_CONTRACT_FAILED",
    "source_scope_invalid": "SOURCE_CONTRACT_FAILED",
    "live_source_required": "SOURCE_SCOPE_MISMATCH",
    "source_response_invalid": "SOURCE_CONTRACT_FAILED",
    "source_address_rejected": "SOURCE_UNAVAILABLE",
    "source_http_error": "SOURCE_UNAVAILABLE",
    "source_timeout": "SOURCE_UNAVAILABLE",
    "source_unavailable": "SOURCE_UNAVAILABLE",
}


def _error(code: str) -> CallToolResult:
    message, recovery = _ERRORS[code]
    payload = ErrorEnvelope(
        error=ToolError(code=code, message=message, recovery=recovery)
    ).model_dump(mode="json")
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload))],
        structured_content=payload,
        is_error=True,
    )


def _success(result: BaseModel) -> CallToolResult:
    payload = result.model_dump(mode="json")
    body = json.dumps(payload, separators=(",", ":"))
    if len(body.encode()) > MAX_STRUCTURED_BYTES:
        return _error("RESOURCE_LIMIT")
    return CallToolResult(content=[TextContent(type="text", text=body)], structured_content=payload)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def create_server(
    root: Path,
    *,
    clock: Callable[[], datetime] = _utc_now,
    enable_live: bool = False,
    workflow: Workflow | None = None,
) -> Server[None]:
    """Build without network or filesystem writes; root/clock are operator configuration."""
    app = workflow or Workflow(
        root, clock=clock, enable_live=enable_live, fixture=load_synthetic_fixture()
    )
    contracts = {contract.name: contract for contract in CONTRACTS}
    tools = [
        Tool(
            name=contract.name,
            description=contract.description,
            input_schema=contract.input_model.model_json_schema(),
            output_schema=contract.output_schema(),
            annotations=ToolAnnotations(
                read_only_hint=not contract.writes,
                destructive_hint=False,
                idempotent_hint=contract.idempotent,
                open_world_hint=contract.network and enable_live,
            ),
        )
        for contract in CONTRACTS
    ]

    async def list_tools(
        ctx: ServerRequestContext[None], params: PaginatedRequestParams | None
    ) -> ListToolsResult:
        return ListToolsResult(tools=tools)

    def dispatch(name: str, arguments: dict[str, Any]) -> CallToolResult:
        if name not in contracts:
            raise MCPError(code=INVALID_PARAMS, message="Unknown tool. Use tools/list.")
        contract = contracts[name]
        try:
            parsed = contract.input_model.model_validate_json(json.dumps(arguments))
        except (ValidationError, ValueError):
            return _error("INVALID_ARGUMENTS")
        try:
            return _success(invoke(app, name, parsed))
        except (AnalyticsError, ArtifactStoreError, WorkflowError, SourceError) as exc:
            code = _CODE_MAP.get(str(exc), "INTERNAL_ERROR")
        except Exception:
            code = "INTERNAL_ERROR"
        return _error(code)

    async def call_tool(
        ctx: ServerRequestContext[None], params: CallToolRequestParams
    ) -> CallToolResult:
        started = monotonic()
        # Cancellation can finish atomic publication; it never exposes a partial file.
        result = await anyio.to_thread.run_sync(
            partial(dispatch, params.name, params.arguments or {})
        )
        LOGGER.info(
            json.dumps(
                {
                    "event": "tool_call",
                    "tool": params.name,
                    "duration_ms": round((monotonic() - started) * 1000),
                    "is_error": result.is_error,
                }
            )
        )
        return result

    return Server(
        "cms-data-mcp",
        version="0.0.1",
        instructions="Use the curated catalog, resolve metadata, "
        "retrieve only the fixed aggregate, "
        "validate, query, export, and inspect lineage. Synthetic data is fictional. "
        "Counts are records, not people. County analysis is unsupported.",
        on_list_tools=list_tools,
        on_call_tool=call_tool,
        get_tool_input_schema=lambda name: next(
            (t.input_schema for t in tools if t.name == name), None
        ),
    )


async def _run_stdio(root: Path, enable_live: bool) -> None:
    server = create_server(root, enable_live=enable_live)
    async with stdio_server() as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="cms-data-mcp aggregate workflow (local stdio).")
    parser.add_argument(
        "--cache-dir", type=Path, required=True, help="Trusted local artifact directory."
    )
    parser.add_argument(
        "--enable-live",
        action="store_true",
        help="Permit only approved CMS metadata/count requests.",
    )
    parser.add_argument(
        "--log-calls",
        action="store_true",
        help="Write call names/timing/outcomes as JSON to stderr.",
    )
    args = parser.parse_args(argv)
    if args.log_calls:
        LOGGER.addHandler(logging.StreamHandler(sys.stderr))
        LOGGER.setLevel(logging.INFO)
        LOGGER.propagate = False
    try:
        anyio.run(_run_stdio, args.cache_dir, args.enable_live)
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception:
        print('{"error":"SERVER_FAILED"}', file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
