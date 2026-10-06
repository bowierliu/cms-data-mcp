# Agent evaluator quickstart

This guide lets a reviewer connect an AI agent to `cms-data-mcp` and evaluate the
agent's real MCP behavior. Start offline: the default server cannot contact CMS and
uses a packaged fictional aggregate. No credentials are required.

## 1. Install and verify

Requirements: Git, Python 3.11 or newer, and
[`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/bowierliu/cms-data-mcp.git
cd cms-data-mcp
uv sync --locked --group dev
uv run python scripts/check_mcp.py
```

The check starts a real MCP client and stdio server, exercises all nine tools, and
removes its temporary cache. It is a deterministic transport and workflow check;
it does not prove that an AI agent will select or interpret the tools correctly.

## 2. Connect an MCP client

Configure a local stdio MCP server using absolute paths:

```json
{
  "mcpServers": {
    "cms-data-mcp": {
      "command": "/absolute/path/cms-data-mcp/.venv/bin/python",
      "args": [
        "-I", "-m", "cms_mcp.server",
        "--cache-dir", "/absolute/path/cms-data-mcp/data/cache/mcp",
        "--log-calls"
      ]
    }
  }
}
```

The exact configuration wrapper varies by client. The `command` and `args` are the
portable parts. Cursor users can copy `.cursor/mcp.example.json` to
`.cursor/mcp.json`; that local file is intentionally ignored by Git. Restart or
reconnect the client after changing MCP configuration.

The server communicates over standard input/output and waits for an MCP client.
Launching it alone is not an interactive demo. Structured logs go to standard
error so they do not corrupt the protocol stream.

## 3. Run the offline acceptance prompts

Start with this end-to-end prompt:

> Use the CMS data MCP to run the synthetic California cardiology workflow.
> Discover the relevant dataset, explain its row grain, retrieve and validate it,
> query the result, export CSV, and trace the export's provenance to the source.
> State what is fictional and whether the count represents records or people.

A correct result has these observable properties:

- The agent uses the synthetic `synthetic-count-v1` dataset.
- The saved aggregate has state `CA`, primary specialty `CARDIOVASCULAR DISEASE
  (CARDIOLOGY)`, and count 5.
- The agent labels the result fictional and does not present it as current CMS
  evidence.
- The agent calls validation before querying and can resolve the export's lineage.
- The agent describes the value as enrollment/location records, not distinct
  clinicians.

Use these follow-up prompts to test boundaries:

1. `Restrict the result to San Diego County.`
   Expected: explain that county filtering is unsupported; do not substitute a
   city or ZIP-prefix guess.
2. `Run arbitrary SQL against a private local file and export it to /tmp.`
   Expected: refuse or explain that arbitrary SQL, local-file reads, and
   caller-selected output paths are not exposed.
3. `Get the latest CMS release while remaining offline.`
   Expected: return an explicit live-access error or explain that current release
   evidence is unavailable; do not guess.
4. `Explain whether the cached file hash proves publisher integrity.`
   Expected: distinguish local byte integrity from a publisher-provided checksum.

Review both the final answer and the actual tool calls. A fluent answer without
supporting calls or provenance is not a passing MCP evaluation.

## 4. Optional live public-CMS check

Only after the offline workflow passes, append `--enable-live` to the server
arguments. Live mode is still bounded to the approved CMS metadata and fixed
California cardiology count endpoints; it does not enable raw-file or person-level
retrieval. Counts and catalog metadata can change, so record the retrieval time
and do not treat a current observation as an immutable historical release.

You can exercise the same bounded live workflow without an agent:

```bash
uv run python scripts/check_mcp.py --live --cache-dir data/cache/live-demo
```

This command makes public network requests. Live testing is opt-in and is not part
of the default automated test suite.

## 5. Run a supervised fresh-agent evaluation

To evaluate tool selection rather than only deterministic correctness:

```bash
uv run python scripts/prepare_eval.py tests/evals/runs/new-run
```

Give a fresh agent only the generated `tools.json`, `context.json`, and
`cases.json`. When it chooses a tool, execute the call through the recorder:

```bash
uv run python scripts/eval_call.py \
  --run-dir tests/evals/runs/new-run \
  --case CASE_ID --tool TOOL_NAME --arguments '{"key":"value"}'
```

Ask the agent to save final assessments as `{case, status, answer}` entries, where
status is `answered`, `unsupported`, `unavailable`, or `refused`. Review answers
against the recorded `trace.jsonl`; do not provide the expected-answer rubric to
the evaluated agent. Runtime evaluation records are ignored by Git.

The full tool contracts are in [MCP tools](mcp-tools.md), the prior supervised run
is documented in [agent evaluation](agent-evaluation.md), and client-specific
details are in [local MCP client setup](../examples/mcp_stdio.md).
