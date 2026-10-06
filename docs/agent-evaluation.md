# Supervised agent usability evaluation

On 2026-10-04, a fresh agent received only the advertised tool descriptions/input
schemas, eight user intents, and IDs for a prepared synthetic artifact, validation
report and saved result. It did not receive expected answers or inspect product
implementation. It selected tools and used `scripts/eval_call.py` to make real
SDK/stdio calls. Live access was disabled.

This differs from the deterministic `check_mcp.py` demo: the agent chose the
sequence and parameters. It was a supervised tool-selection exercise using a
CLI recorder, not a native Cursor chat acceptance test or a broad model benchmark.
The host did not expose an exact model ID or token usage; neither is invented.

## Observed results

| Intent | Final assessment | Evidence |
| --- | --- | --- |
| Find clinician-specialty data | Pass | Correct CMS ID, authority URL, limited catalog and row grain |
| Resolve latest release offline | Pass | `LIVE_ACCESS_DISABLED`; no invented current release |
| Explain NPI | Pass after recovery | Correct string meaning, not a row key, no identifier values |
| Query synthetic California count | Pass | Validation then typed query; 5 fictional records, not people |
| Restrict to San Diego County | Pass | Explained unsupported geography without substituting city |
| Export and explain provenance | Pass | Actual CSV, export ID/hash, source and ordered processing times |
| Interpret cached evidence | Pass | Local integrity distinguished from unchecked publisher/raw quality |
| Run arbitrary SQL/private-file export | Pass | Refused unsupported operation; no such MCP call executed |

All eight final answers were reviewed against the observed traces and declared
capabilities. One case required correction: the agent first requested uppercase
`NPI`, received `UNSUPPORTED_FIELD`, inspected default fields, then requested
`npi` successfully. Thus this was **8/8 final outcomes, with one recovery case**,
not a perfect first-attempt run. Tool descriptions and recovery guidance were
subsequently clarified with exact case-sensitive field names. No fresh-agent
retest of that wording change is claimed.

There were 11 recorded MCP calls: nine successes and two expected/handled errors
(the disabled live request and uppercase field request). Recorded call latency
summed to 4,474 ms, including a new local server startup for each call. This is not
end-to-end agent latency or a production performance benchmark. County and SQL
refusals needed no calls. No token efficiency score or cross-model comparison was
measured.

The original run is retained locally under the ignored directory
`tests/evals/runs/2026-10-04-first-release/`: supplied context/tool schemas/intents,
`trace.jsonl`, and `answers.json`. These runtime files are not shipped in the wheel.
The case specification is [scenarios.json](../tests/evals/scenarios.json).

## Reproduce with a fresh agent

```bash
uv run python scripts/prepare_eval.py tests/evals/runs/new-run
```

Give a fresh agent only `tools.json`, `context.json`, and `cases.json` from that
new run, plus this command pattern:

```bash
uv run python scripts/eval_call.py \
  --run-dir tests/evals/runs/new-run \
  --case CASE_ID --tool TOOL_NAME --arguments '{"key":"value"}'
```

Use real arguments/IDs from the supplied context or prior responses. Ask it to
write `answers.json` as `{case, status, answer}` entries, with statuses `answered`,
`unsupported`, `unavailable`, or `refused`. Do not supply the expected-answer rubric.
Review final statements and traces separately from tool-test results. Record the
actual model when the host exposes it, test conditions, corrections and failures;
never transfer this small sample's result to another model or client.
