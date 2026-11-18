"""Uncompleted human review template, separate from immutable observations."""
import csv
from pathlib import Path

FIELDS = ("snapshot_sha256", "indicator_id", "name", "unit", "reference_periods", "source",
          "available_at_build", "evidence_at_build", "review_scope", "technical_review_status",
          "reviewer", "reviewed_on", "limitations_and_decision", "stakeholder_validation_status",
          "questions_for_fieldwork")


def write_template(path: Path, payload: dict, *, snapshot_sha256: str) -> None:
    """Write a fresh blank review; this never changes scientific approval flags."""
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for metric in payload["indicators"]:
            writer.writerow({
                "snapshot_sha256": snapshot_sha256, "indicator_id": metric["id"],
                "name": metric["name"], "unit": metric["unit"],
                "reference_periods": ";".join(metric.get("years", [])), "source": metric["source"],
                "available_at_build": str(metric["available"]).lower(),
                "evidence_at_build": metric.get("evidence", ""),
                "review_scope": "this_technical_snapshot_only",
                "technical_review_status": "pending", "stakeholder_validation_status": "not_performed",
            })
