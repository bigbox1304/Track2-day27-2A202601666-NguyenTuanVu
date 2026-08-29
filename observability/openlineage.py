"""Small dependency-free OpenLineage event emitter for the local lab."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def emit_dataset_event(
    *,
    job_name: str,
    inputs: Iterable[str],
    outputs: Iterable[str],
    output_path: str | Path,
    run_id: str | None = None,
) -> dict:
    """Append a valid OpenLineage COMPLETE event to a local JSONL sink."""
    event = {
        "eventType": "COMPLETE",
        "eventTime": datetime.now(timezone.utc).isoformat(),
        "run": {"runId": run_id or str(uuid.uuid4())},
        "job": {"namespace": "data-reliability-lab", "name": job_name},
        "inputs": [{"namespace": "local", "name": name} for name in inputs],
        "outputs": [{"namespace": "local", "name": name} for name in outputs],
        "producer": "https://openlineage.io",
        "schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json#/$defs/RunEvent",
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event
