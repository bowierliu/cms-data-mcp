# Agent evaluation

`scenarios.json` defines eight intent-based checks for the implemented fixed
aggregate workflow. A supervised fresh-agent run was executed on 2026-10-04;
[the report](../../docs/agent-evaluation.md) documents all final outcomes and the
NPI field-name recovery. This is separate from deterministic tool correctness.

Prepare a fresh run with `scripts/prepare_eval.py`. Give the evaluated agent only
the generated context, input tool schemas, and intents, not expected answers.
`scripts/eval_call.py` records its actual SDK calls, results, protocol and latency
with live access disabled. Review answers against both trace evidence and the
case's critical-failure criteria. Runtime records remain ignored in `runs/`.

The host did not expose the exact evaluated model ID or token count for the first
run. No universal agent reliability, cross-model comparison, or native editor
acceptance score is claimed. Legacy city-level fixtures are not the current
single-row synthetic MCP view.
