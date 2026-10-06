"""Prepare a fresh supervised agent evaluation without giving the agent a rubric."""

import argparse
import json
from pathlib import Path

from cms_mcp.api import CONTRACTS
from cms_mcp.workflow import Workflow


def prepare(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=False)
    app = Workflow(run_dir / "cache")
    metadata = app.metadata("synthetic-count-v1")
    artifact = app.retrieve("synthetic-count-v1", metadata.source_ref)
    validation_id, _ = app.validate(artifact.artifact_id)
    result_id, _ = app.query(artifact.artifact_id, validation_id, {})
    context = {
        "dataset_id": "synthetic-count-v1",
        "source_ref": metadata.source_ref,
        "artifact_id": artifact.artifact_id,
        "validation_id": validation_id,
        "result_id": result_id,
        "live_enabled": False,
        "fixture_id": "synthetic-count-v1",
    }
    scenarios = json.loads(
        (Path(__file__).resolve().parents[1] / "tests/evals/scenarios.json").read_text()
    )
    artifacts = {
        "context.json": context,
        "cases.json": [{"id": case["id"], "intent": case["intent"]} for case in scenarios["cases"]],
        "tools.json": [
            {
                "name": c.name,
                "description": c.description,
                "input_schema": c.input_model.model_json_schema(),
            }
            for c in CONTRACTS
        ],
    }
    for name, value in artifacts.items():
        (run_dir / name).write_text(json.dumps(value, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    prepare(parser.parse_args().run_dir)
