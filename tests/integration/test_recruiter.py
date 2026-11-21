"""Browser-facing HTTP contract, real MCP tools and real ledger with a mock provider."""

import json
import socket
import sqlite3
from contextlib import closing
from http.client import HTTPResponse
from http.server import ThreadingHTTPServer
from threading import Thread

import pytest

from cms_mcp import recruiter
from cms_mcp.portfolio_guard import MODEL, Guard, initialize


@pytest.fixture
def companion(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.sqlite3"
    initialize(ledger)
    with sqlite3.connect(ledger) as db:
        db.execute("UPDATE settings SET value=1 WHERE name='enabled'")
    calls = []
    answers = []

    def provider(action, key, body, timeout):
        calls.append((action, body))
        if action == "count":
            return {"input_tokens": 10}
        return {
            "status": "completed",
            "model": MODEL,
            "service_tier": "default",
            "usage": {"input_tokens": 10, "output_tokens": 5},
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": answers.pop(0)}]}
            ],
        }

    monkeypatch.setattr(
        Guard, "from_env", classmethod(lambda cls: Guard(ledger, lambda: "test", provider))
    )

    def request(method, path, value=None, **headers):
        # socketpair exercises the complete BaseHTTPRequestHandler parser and response writer
        # while retaining the repository-wide outside-network denial fixture.
        with ThreadingHTTPServer(
            ("127.0.0.1", recruiter.PORT), recruiter.CompanionHandler, bind_and_activate=False
        ) as server:
            server.server_port = recruiter.PORT
            local, client = socket.socketpair()
            with local, client:
                task = Thread(target=server.finish_request, args=(local, ("127.0.0.1", 1)))
                task.start()
                body = json.dumps(value).encode() if value is not None else b""
                fields = {
                    "Host": f"127.0.0.1:{recruiter.PORT}",
                    "Origin": f"http://127.0.0.1:{recruiter.PORT}",
                    "Content-Type": "application/json",
                    "Content-Length": str(len(body)),
                    **headers,
                }
                lines = [f"{method} {path} HTTP/1.0", *(f"{k}: {v}" for k, v in fields.items())]
                client.sendall(("\r\n".join(lines) + "\r\n\r\n").encode() + body)
                client.shutdown(socket.SHUT_WR)
                with closing(HTTPResponse(client)) as response:
                    response.begin()
                    content = response.read()
                    status = response.status
                    if response.headers["Content-Type"] == "application/json":
                        content = json.loads(content)
                task.join(timeout=4)
                assert not task.is_alive()
                return status, content

    return request, calls, answers, ledger


def test_offline_replay_starts_without_key_or_provider(companion):
    request, calls, _, _ = companion
    status, page = request("GET", "/")
    assert status == 200 and b"Offline replay" in page and b"fictional enrollment" in page
    assert request("GET", "/demo.css")[0] == request("GET", "/demo.js")[0] == 200
    status, replay = request("GET", "/replay.json")
    assert status == 200 and replay["synthetic"] is True and replay["record_count"] == 5
    assert replay["csv"] == "state,record_count\r\nCA,5\r\n"
    assert replay["validation_status"] == "pass" and replay["lineage_steps"] == 3
    assert len(replay["tools"]) == 9 and calls == []


@pytest.mark.parametrize(
    "scenario,tool", [("validation", "validate_dataset"), ("lineage", "get_provenance")]
)
def test_model_selects_mcp_tool_and_receives_its_actual_evidence(companion, scenario, tool):
    request, calls, answers, ledger = companion
    answers.extend([json.dumps({"tool": tool}), "Mock review of fictional records."])
    status, result = request("POST", "/api/investigate", {"scenario": scenario})
    assert status == 200
    evidence = result["evidence"]
    assert evidence["tools"] == ["materialize_synthetic_count", tool]
    assert evidence["record_count"] == 5 and evidence["counts_distinct_people"] is False
    assert result["explanation"] == "Mock review of fictional records."
    assert json.loads(calls[-1][1]["input"])["evidence"] == evidence
    assert [action for action, _ in calls] == ["count", "generate", "count", "generate"]
    if tool == "validate_dataset":
        assert len(evidence["detail"]["passed"]) == len(evidence["detail"]["unchecked"]) == 6
    else:
        assert evidence["detail"]["operations"] == ["normalize_fixed_count"]
        assert evidence["detail"]["hash_origin"] == "local"
    with sqlite3.connect(ledger) as db:
        assert db.execute("SELECT tools,active FROM runs").fetchone() == (2, 0)
        assert db.execute("SELECT count(*) FROM calls").fetchone() == (2,)


def test_invalid_model_selection_cannot_invoke_unapproved_tool(companion):
    request, calls, answers, ledger = companion
    answers.append('{"tool":"retrieve_dataset"}')
    assert request("POST", "/api/investigate", {"scenario": "validation"})[0] == 422
    assert [action for action, _ in calls] == ["count", "generate"]
    with sqlite3.connect(ledger) as db:
        assert db.execute("SELECT tools FROM runs").fetchone() == (0,)


def test_browser_cannot_submit_keys_budget_fields_external_origins_or_private_paths(companion):
    request, calls, _, _ = companion
    body = {"scenario": "validation"}
    for headers in [
        {"Origin": "https://example.invalid"},
        {"Origin": "null"},
        {"Host": "elsewhere.invalid"},
    ]:
        assert request("POST", "/api/investigate", body, **headers)[0] == 403
    for extra in ["key", "model", "identity", "global_cents", "instructions"]:
        assert request("POST", "/api/investigate", {**body, extra: "untrusted"})[0] == 400
    assert request("GET", "/../.env")[0] == 404
    assert request("POST", "/api/investigate", body, **{"Content-Type": "text/plain"})[0] == 415
    assert calls == []


def test_disabled_ledger_and_tool_limit_stop_provider_calls(companion):
    request, calls, answers, ledger = companion
    with sqlite3.connect(ledger) as db:
        db.execute("UPDATE settings SET value=0 WHERE name='enabled'")
    assert request("POST", "/api/investigate", {"scenario": "validation"})[0] == 503
    assert calls == []
    with sqlite3.connect(ledger) as db:
        db.execute("UPDATE settings SET value=1 WHERE name IN ('enabled','tool_calls')")
    answers.append('{"tool":"validate_dataset"}')
    assert request("POST", "/api/investigate", {"scenario": "validation"})[0] == 503
    assert [action for action, _ in calls] == ["count", "generate"]
    with sqlite3.connect(ledger) as db:
        assert db.execute("SELECT tools,active FROM runs").fetchone() == (1, 0)
