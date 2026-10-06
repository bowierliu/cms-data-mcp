"""Record one real MCP call for a supervised, offline agent-usability evaluation."""

import argparse
import json
import sys
from pathlib import Path
from time import monotonic

import anyio
from mcp import Client, StdioServerParameters


async def record_call(run_dir: Path, case: str, tool: str, arguments: str) -> None:
    root = run_dir / "cache"
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-I", "-m", "cms_mcp.server", "--cache-dir", str(root.absolute())],
    )
    args = json.loads(arguments)
    if not isinstance(args, dict):
        raise ValueError("object_arguments_required")
    started = monotonic()
    with anyio.fail_after(20):
        async with Client(parameters, read_timeout_seconds=5) as client:
            result = await client.call_tool(tool, args)
            event = {
                "case": case,
                "tool": tool,
                "arguments": args,
                "result": result.structured_content,
                "is_error": result.is_error,
                "protocol": client.protocol_version,
                "latency_ms": round((monotonic() - started) * 1000),
            }
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "trace.jsonl").open("a") as handle:
        handle.write(json.dumps(event) + "\n")
    print(json.dumps(event))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--tool", required=True)
    parser.add_argument("--arguments", required=True)
    args = parser.parse_args()
    anyio.run(record_call, args.run_dir, args.case, args.tool, args.arguments)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
