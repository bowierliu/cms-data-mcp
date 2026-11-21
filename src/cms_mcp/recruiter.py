"""Loopback-only, model-assisted companion for the public synthetic replay."""

import argparse
import json
import os
import subprocess
import sys
import time
import webbrowser
from contextlib import closing
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import anyio
from mcp import Client

from cms_mcp.portfolio_guard import Guard, GuardError, Investigation
from cms_mcp.server import create_server

PORT = 8767
ROOT = Path(__file__).resolve().parents[2] / "docs"
SCENARIOS = {
    "validation": "Which properties of this fictional count have actually been checked?",
    "lineage": "What connects this fictional count to its source and transformation?",
}
TOOLS = {"validate_dataset", "get_provenance"}


class InvestigationError(ValueError):
    pass


async def collect(run: Investigation, chosen: str) -> dict[str, Any]:
    # Only the two tool calls touch this cache. No live source/stdio process inherits a key.
    with TemporaryDirectory(prefix="cms-demo-") as temp, anyio.fail_after(min(8, run.remaining())):
        async with Client(create_server(Path(temp))) as client:

            async def call(name: str, args: dict[str, Any]) -> dict[str, Any]:
                result = await run.tool(client.call_tool, name, args)
                run.check()
                if result.is_error or not isinstance(result.structured_content, dict):
                    raise InvestigationError("The MCP tool could not verify the fixture.")
                return result.structured_content

            count = await call("materialize_synthetic_count", {})
            result = await call(chosen, {"artifact_id": count["data"]["artifact_id"]})
            data = result["data"]
            if chosen == "validate_dataset":
                checks = data["report"]["checks"]
                detail = {
                    "overall": data["report"]["overall"],
                    "passed": [check["id"] for check in checks if check["status"] == "pass"],
                    "unchecked": [
                        check["id"] for check in checks if check["status"] == "not_checked"
                    ],
                }
            else:
                provenance = data["provenance"]
                detail = {
                    "source_ref": data["source_ref"],
                    "retrieved_at": provenance["observation"]["retrieved_at"],
                    "operations": [step["operation"] for step in provenance["lineage"]],
                    "hash_origin": provenance["hash_origin"],
                    "publisher_integrity": provenance["publisher_integrity"],
                }
            return {
                "fixture": count["scope"]["dataset_id"],
                "synthetic": count["scope"]["synthetic"],
                "state": count["scope"]["state"],
                "count_unit": count["scope"]["count_unit"],
                "record_count": count["data"]["record_count"],
                "counts_distinct_people": count["data"]["counts_distinct_people"],
                "artifact_id": count["data"]["artifact_id"],
                "tools": ["materialize_synthetic_count", chosen],
                "detail": detail,
            }


def investigate(scenario: str) -> dict[str, Any]:
    question = SCENARIOS[scenario]
    with Guard.from_env().investigation("local-owner") as run:
        decision = run.model(
            'Respond with a JSON object containing only "tool". Choose validate_dataset '
            "for contract checks or get_provenance for acquisition and transformations.",
            question,
        )
        try:
            parsed = json.loads(decision)
        except ValueError as exc:
            raise InvestigationError("The model did not return a valid tool selection.") from exc
        if (
            not isinstance(parsed, dict)
            or set(parsed) != {"tool"}
            or not isinstance(parsed["tool"], str)
            or parsed["tool"] not in TOOLS
        ):
            raise InvestigationError("The model selected an unsupported tool.")
        evidence = anyio.run(collect, run, parsed["tool"])
        explanation = run.model(
            "Explain only the provided synthetic MCP evidence in two short sentences. "
            "Label the fictional enrollment/location record count. Explain the limit relevant "
            "to the question. Do not infer a real CMS count, unique people or clinical guidance.",
            json.dumps({"question": question, "evidence": evidence}, separators=(",", ":")),
        )
        run.check()
    return {"mode": "live model", "evidence": evidence, "explanation": explanation}


class CompanionHandler(BaseHTTPRequestHandler):
    server_version = "CMSCompanion"

    # Do not retain HTTP requests, model content, keys, user identities, or paths in logs.
    def log_message(self, format: str, *args: Any) -> None:
        pass

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(8)

    @property
    def address(self) -> str:
        assert isinstance(self.server, ThreadingHTTPServer)
        return f"127.0.0.1:{self.server.server_port}"

    def send_data(self, status: int, content_type: str, content: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        )
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, status: int, value: dict[str, Any]) -> None:
        self.send_data(status, "application/json", json.dumps(value).encode())

    def do_GET(self) -> None:
        if self.headers.get_all("Host") != [self.address]:
            self.send_json(403, {"error": "This companion accepts local requests only."})
            return
        if self.path == "/api/status":
            self.send_json(200, {"service": "cms-data-mcp-companion"})
            return
        assets = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/demo.css": ("demo.css", "text/css"),
            "/demo.js": ("demo.js", "text/javascript"),
            "/replay.json": ("replay.json", "application/json"),
        }
        if self.path not in assets:
            self.send_json(404, {"error": "Unknown route."})
            return
        filename, media = assets[self.path]
        self.send_data(200, media, (ROOT / filename).read_bytes())

    def do_POST(self) -> None:
        if self.headers.get_all("Host") != [self.address] or self.headers.get_all("Origin") != [
            f"http://{self.address}"
        ]:
            self.send_json(403, {"error": "Open the companion directly on this computer."})
            return
        if self.headers.get_all("Content-Type") != ["application/json"] or self.headers.get_all(
            "Transfer-Encoding"
        ):
            self.send_json(415, {"error": "Use a JSON request."})
            return
        sizes = self.headers.get_all("Content-Length") or []
        if len(sizes) != 1 or not sizes[0].isascii() or not sizes[0].isdigit() or len(sizes[0]) > 3:
            self.send_json(400, {"error": "Invalid request size."})
            return
        size = int(sizes[0])
        if not 0 < size <= 128:
            self.send_json(413, {"error": "Invalid request size."})
            return
        try:
            body = json.loads(self.rfile.read(size))
        except ValueError:
            self.send_json(400, {"error": "Invalid JSON."})
            return
        if self.path == "/api/stop" and body == {}:
            self.send_json(200, {"stopped": True})
            self.server.shutdown()
            return
        if self.path != "/api/investigate":
            self.send_json(404, {"error": "Unknown route."})
            return
        if (
            not isinstance(body, dict)
            or set(body) != {"scenario"}
            or not isinstance(body["scenario"], str)
            or body["scenario"] not in SCENARIOS
        ):
            self.send_json(400, {"error": "Choose one of the two fixture questions."})
            return
        try:
            result = investigate(body["scenario"])
        except GuardError as exc:
            self.send_json(503, {"error": str(exc)})
        except InvestigationError as exc:
            self.send_json(422, {"error": str(exc)})
        except Exception:
            self.send_json(
                503, {"error": "The investigation stopped. No automatic retry was made."}
            )
        else:
            self.send_json(200, result)


def running() -> bool:
    try:
        with closing(HTTPConnection("127.0.0.1", PORT, timeout=1)) as connection:
            connection.request("GET", "/api/status")
            response = connection.getresponse()
            return response.status == 200 and json.loads(response.read(256)) == {
                "service": "cms-data-mcp-companion"
            }
    except (OSError, ValueError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--launch", action="store_true", help="Start in background and open browser."
    )
    args = parser.parse_args()
    if not (ROOT / "index.html").is_file():
        sys.exit(
            "Use the launcher from a checked-out copy of cms-data-mcp with its docs directory."
        )
    if args.launch:
        if not running():
            with open(os.devnull, "r+b") as silence:
                process = subprocess.Popen(
                    [sys.executable, "-I", "-m", "cms_mcp.recruiter"],
                    stdin=silence,
                    stdout=silence,
                    stderr=silence,
                    start_new_session=True,
                    close_fds=True,
                )
            for _ in range(80):
                if running():
                    break
                if process.poll() is not None:
                    sys.exit(
                        "Could not start the companion. Check whether its port is already in use."
                    )
                time.sleep(0.1)
            else:
                process.terminate()
                sys.exit("The companion did not start.")
        webbrowser.open(f"http://127.0.0.1:{PORT}/#live")
        return 0
    with ThreadingHTTPServer(("127.0.0.1", PORT), CompanionHandler) as server:
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
