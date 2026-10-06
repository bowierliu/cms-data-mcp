"""Run the packaged synthetic count workflow: python -m cms_mcp.demo."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from cms_mcp.service import CountService, CountServiceError
from cms_mcp.storage import LocalArtifactStore
from cms_mcp.synthetic import FIXTURE_ID, load_synthetic_fixture


def _run(root: Path, *, persistent: bool) -> dict[str, object]:
    fixture = load_synthetic_fixture()
    created = CountService(LocalArtifactStore(root)).materialize_count(
        fixture.body,
        source=fixture.source,
        retrieved_at=fixture.retrieved_at,
        normalized_at=fixture.normalized_at,
    )
    served = CountService(LocalArtifactStore(root)).get_provenance(
        created.artifact_id,
        expected_source_ref=fixture.source.source_ref,
        served_at=datetime.now(UTC),
    )
    observation = served.observation
    return {
        "synthetic": True,
        "fixture_id": FIXTURE_ID,
        "storage": "persistent" if persistent else "temporary_removed_on_exit",
        "artifact_id": created.artifact_id,
        "source_ref": fixture.source.source_ref,
        "snapshot_id": observation.snapshot_id,
        "stored_provenance_id": created.provenance.provenance_id,
        "served_provenance_id": served.provenance_id,
        "record_count": observation.record_count,
        "counts_distinct_people": observation.counts_distinct_people,
        "provenance": served.model_dump(mode="json"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a synthetic cms-data-mcp count workflow offline."
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Retain artifacts in this trusted local directory; default: temporary storage.",
    )
    args = parser.parse_args(argv)
    error = "invalid_fixture"
    try:
        if args.cache_dir is None:
            with TemporaryDirectory(prefix="cms-data-mcp-demo-") as directory:
                output = _run(Path(directory), persistent=False)
        else:
            output = _run(args.cache_dir, persistent=True)
        print(json.dumps(output, sort_keys=True, indent=2))
        return 0
    except CountServiceError as exc:
        error = str(exc)
    except OSError:
        error = "demo_io_error"
    except (KeyError, ValueError, TypeError):
        pass
    print(json.dumps({"error": error, "synthetic": True}), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
