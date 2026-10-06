"""Exercise the entire workflow through an actual installed stdio MCP server."""

import argparse
import json
import sys
from contextlib import nullcontext
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import anyio
from mcp import Client, StdioServerParameters

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


class CheckError(ValueError):
    pass


async def check(cache_dir: Path | None = None, *, live: bool = False) -> dict[str, object]:
    directory = (
        nullcontext(str(cache_dir.absolute()))
        if cache_dir
        else TemporaryDirectory(prefix="cms-data-mcp-stdio-")
    )
    with directory as root, anyio.fail_after(90 if live else 20):
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-I", "-m", "cms_mcp.server", "--cache-dir", root]
            + (["--enable-live"] if live else []),
        )
        async with Client(parameters, read_timeout_seconds=40 if live else 5) as client:
            names = sorted(tool.name for tool in (await client.list_tools()).tools)
            if set(names) != TOOLS:
                raise CheckError("TOOL_DISCOVERY_FAILED")

            async def call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
                result = await client.call_tool(name, arguments)
                if result.is_error or not isinstance(result.structured_content, dict):
                    raise CheckError("TOOL_FAILED_" + name.upper())
                return result.structured_content

            dataset_id = "mj5m-pzi6" if live else "synthetic-count-v1"
            await call("search_datasets", {"query": "California cardiologist"})
            metadata = await call("get_dataset_metadata", {"dataset_id": dataset_id})
            source_ref = metadata["data"]["source_ref"]
            await call(
                "get_schema",
                {
                    "dataset_id": dataset_id,
                    "source_ref": source_ref,
                    "fields": ["state", "primary_specialty", "record_count"],
                },
            )
            count = await call(
                "retrieve_dataset", {"dataset_id": dataset_id, "source_ref": source_ref}
            )
            artifact_id = count["data"]["artifact_id"]
            validation = await call("validate_dataset", {"artifact_id": artifact_id})
            queried = await call(
                "query_dataset",
                {
                    "artifact_id": artifact_id,
                    "validation_id": validation["data"]["validation_id"],
                    "select": ["state", "record_count"],
                },
            )
            exported = await call("export_result", {"result_id": queried["data"]["result_id"]})
            fetched = await call("get_provenance", {"artifact_id": exported["provenance_id"]})
            provenance = fetched["data"]["provenance"]
            if (
                count["scope"]["synthetic"] is live
                or validation["data"]["report"]["overall"] != "pass"
                or provenance["cache_status"] != "hit"
                or (not live and count["data"]["record_count"] != 5)
            ):
                raise CheckError("UNEXPECTED_WORKFLOW_RESULT")
            return {
                "server": client.server_info.name if client.server_info else None,
                "sdk_version": version("mcp"),
                "protocol_version": client.protocol_version,
                "tools": names,
                "synthetic": not live,
                "record_count": count["data"]["record_count"],
                "counts_distinct_people": False,
                "cache_status": provenance["cache_status"],
                "retrieved_at": provenance["observation"]["retrieved_at"],
                "artifact_id": artifact_id,
                "source_ref": source_ref,
                "catalog_released": provenance["observation"]["source"]["catalog_released"],
                "publisher_immutable_release_id": None,
                "validation_status": validation["data"]["report"]["overall"],
                "query_rows": queried["data"]["result"]["rows"],
                "csv": exported["data"]["content"],
                "export_id": exported["data"]["export_id"],
                "lineage_steps": len(fetched["data"]["records"]),
                "storage": "persistent" if cache_dir else "temporary_removed_on_exit",
            }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-dir", type=Path, help="Retain artifacts in a trusted local directory."
    )
    parser.add_argument(
        "--live", action="store_true", help="Explicitly opt in to the fixed public CMS count."
    )
    args = parser.parse_args()
    try:

        async def run() -> dict[str, object]:
            return await check(args.cache_dir, live=args.live)

        result = anyio.run(run)
    except CheckError as exc:
        print(json.dumps({"error": "MCP_CHECK_FAILED", "stage": str(exc)}), file=sys.stderr)
        return 1
    except Exception:
        print('{"error":"MCP_CHECK_FAILED"}', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
