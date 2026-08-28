import csv
import json
from datetime import datetime, timedelta, timezone

from aggregation.versioning import (
    compare_audit_metrics,
    compare_place_files,
    latest_successful_snapshot,
    publish_snapshot,
    snapshot_name,
    write_comparison_report,
)


FIELDS = [
    "source_id",
    "continent",
    "country",
    "city",
    "section",
    "category",
    "name",
    "address",
    "description",
    "url",
    "image_url",
]


def _write_places(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _place(name, description="Description", url="https://example.com/place"):
    return {
        "source_id": f"paragraph-{name}",
        "continent": "Europe",
        "country": "France",
        "city": "Paris",
        "section": "Attractions",
        "category": "Museums",
        "name": name,
        "address": "Paris",
        "description": description,
        "url": url,
        "image_url": "",
    }


def test_compare_place_files_reports_added_removed_and_changed(tmp_path):
    previous = tmp_path / "previous.csv"
    current = tmp_path / "current.csv"
    _write_places(
        previous,
        [
            _place("Louvre", description="Old description"),
            _place("Removed museum"),
        ],
    )
    _write_places(
        current,
        [
            _place("Louvre", description="New description"),
            _place("Added museum"),
        ],
    )

    comparison = compare_place_files(previous, current)

    assert comparison["places_delta"] == 0
    assert comparison["added_count"] == 1
    assert comparison["removed_count"] == 1
    assert comparison["changed_count"] == 1
    assert comparison["added"][0]["name"] == "Added museum"
    assert comparison["removed"][0]["name"] == "Removed museum"
    assert comparison["changed"][0]["fields"]["description"] == {
        "before": "Old description",
        "after": "New description",
    }


def test_comparison_report_is_human_and_machine_readable(tmp_path):
    current = tmp_path / "current.csv"
    _write_places(current, [_place("Added museum")])
    comparison = compare_place_files(None, current)
    report = tmp_path / "comparison.txt"
    machine_report = tmp_path / "comparison.json"

    write_comparison_report(
        comparison,
        report,
        machine_report,
        previous_name=None,
        current_name="2026-08-28_12-00-00",
    )

    text = report.read_text(encoding="utf-8")
    assert "места: 0 -> 1 (+1)" in text
    assert "+ France, Paris — Added museum" in text
    assert json.loads(machine_report.read_text(encoding="utf-8"))["added_count"] == 1


def test_latest_snapshot_uses_only_successful_complete_versions(tmp_path):
    for name, status in (
        ("2026-08-27_10-00-00", "success"),
        ("2026-08-28_10-00-00", "success"),
        ("2026-08-29_10-00-00", "pending_publish"),
    ):
        snapshot = tmp_path / name
        _write_places(snapshot / "csv" / "places.csv", [_place(name)])
        (snapshot / "manifest.json").write_text(
            json.dumps({"status": status}),
            encoding="utf-8",
        )

    latest = latest_successful_snapshot(tmp_path)

    assert latest is not None
    assert latest.name == "2026-08-28_10-00-00"


def test_audit_metric_comparison_reports_only_deltas(tmp_path):
    previous = tmp_path / "2026-08-27_10-00-00"
    previous.mkdir()
    (previous / "manifest.json").write_text(
        json.dumps({"metrics": {"places": 10, "countries": 2, "empty_url": 1}}),
        encoding="utf-8",
    )

    changes = compare_audit_metrics(
        previous,
        {"places": 11, "countries": 2, "empty_url": 0},
    )

    assert changes == {
        "empty_url": {"before": 1, "after": 0, "delta": -1},
        "places": {"before": 10, "after": 11, "delta": 1},
    }


def test_publish_snapshot_replaces_current_catalog(tmp_path):
    snapshot = tmp_path / "snapshots" / "2026-08-28_10-00-00"
    aggregation_dir = tmp_path / "aggregation"
    _write_places(snapshot / "csv" / "places.csv", [_place("New")])
    _write_places(snapshot / "merged_data" / "places.csv", [_place("New")])
    (snapshot / "export" / "media").mkdir(parents=True)
    (snapshot / "export" / "text.json").write_text("[]", encoding="utf-8")
    (snapshot / "reports").mkdir()
    (snapshot / "reports" / "audit_report.txt").write_text("ok", encoding="utf-8")
    _write_places(aggregation_dir / "csv" / "places.csv", [_place("Old")])

    publish_snapshot(snapshot, aggregation_dir)

    published = (aggregation_dir / "csv" / "places.csv").read_text(encoding="utf-8")
    assert "New" in published
    assert "Old" not in published
    assert (aggregation_dir / "export" / "text.json").is_file()
    assert (aggregation_dir / "audit_report.txt").read_text(encoding="utf-8") == "ok"


def test_snapshot_name_contains_local_date_and_time():
    created_at = datetime(
        2026,
        8,
        28,
        12,
        34,
        56,
        tzinfo=timezone(timedelta(hours=8)),
    )

    assert snapshot_name(created_at) == "2026-08-28_12-34-56"
