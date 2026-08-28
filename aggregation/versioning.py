from __future__ import annotations

import csv
import json
import os
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


SNAPSHOT_FORMAT = "%Y-%m-%d_%H-%M-%S"
COMPARE_FIELDS = ("section", "address", "description", "url", "image_url")
IDENTITY_FIELDS = ("continent", "country", "city", "category", "name")


def snapshot_name(created_at: datetime) -> str:
    return created_at.astimezone().strftime(SNAPSHOT_FORMAT)


def successful_snapshots(snapshots_dir: Path) -> list[Path]:
    if not snapshots_dir.exists():
        return []

    result = []
    for path in snapshots_dir.iterdir():
        manifest_file = path / "manifest.json"
        if not path.is_dir() or not manifest_file.is_file():
            continue
        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if manifest.get("status") == "success" and (path / "csv" / "places.csv").is_file():
            result.append(path)
    return sorted(result, key=lambda path: path.name)


def latest_successful_snapshot(snapshots_dir: Path) -> Path | None:
    snapshots = successful_snapshots(snapshots_dir)
    return snapshots[-1] if snapshots else None


def _clean(value: str | None) -> str:
    return " ".join((value or "").split()).casefold()


def _read_places(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as source:
        return [dict(row) for row in csv.DictReader(source)]


def _indexed_places(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = tuple(_clean(row.get(field)) for field in IDENTITY_FIELDS)
        groups[key].append(row)

    indexed: dict[str, dict[str, str]] = {}
    for key, group in groups.items():
        ordered = sorted(
            group,
            key=lambda row: (
                _clean(row.get("address")),
                _clean(row.get("url")),
                _clean(row.get("source_id")),
            ),
        )
        base = " | ".join(key)
        for index, row in enumerate(ordered, start=1):
            unique_key = base if len(ordered) == 1 else f"{base} | occurrence={index}"
            indexed[unique_key] = row
    return indexed


def compare_place_files(
    previous_file: Path | None,
    current_file: Path,
) -> dict[str, Any]:
    previous = _indexed_places(_read_places(previous_file))
    current = _indexed_places(_read_places(current_file))
    previous_keys = set(previous)
    current_keys = set(current)

    added = [current[key] for key in sorted(current_keys - previous_keys)]
    removed = [previous[key] for key in sorted(previous_keys - current_keys)]
    changed = []
    for key in sorted(previous_keys & current_keys):
        fields = {
            field: {
                "before": previous[key].get(field, ""),
                "after": current[key].get(field, ""),
            }
            for field in COMPARE_FIELDS
            if previous[key].get(field, "") != current[key].get(field, "")
        }
        if fields:
            changed.append(
                {
                    "identity": {
                        field: current[key].get(field, "") for field in IDENTITY_FIELDS
                    },
                    "fields": fields,
                }
            )

    return {
        "previous_places": len(previous),
        "current_places": len(current),
        "places_delta": len(current) - len(previous),
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_count": len(changed),
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def compare_audit_metrics(
    previous_snapshot: Path | None,
    current_metrics: dict[str, int],
) -> dict[str, dict[str, int]]:
    previous_metrics: dict[str, int] = {}
    if previous_snapshot:
        try:
            manifest = json.loads(
                (previous_snapshot / "manifest.json").read_text(encoding="utf-8")
            )
            previous_metrics = manifest.get("metrics", {})
        except (OSError, json.JSONDecodeError):
            previous_metrics = {}

    changes = {}
    for key in sorted(set(previous_metrics) | set(current_metrics)):
        before = int(previous_metrics.get(key, 0))
        after = int(current_metrics.get(key, 0))
        if before != after:
            changes[key] = {
                "before": before,
                "after": after,
                "delta": after - before,
            }
    return changes


def _place_label(row: dict[str, str]) -> str:
    location = ", ".join(
        value for value in (row.get("country", ""), row.get("city", "")) if value
    )
    category = f" [{row['category']}]" if row.get("category") else ""
    url = f" — {row['url']}" if row.get("url") else ""
    return f"{location} — {row.get('name', '<unnamed>')}{category}{url}"


def _short(value: str, limit: int = 240) -> str:
    clean = " ".join(value.split())
    return clean if len(clean) <= limit else f"{clean[:limit].rstrip()}..."


def write_comparison_report(
    comparison: dict[str, Any],
    report_file: Path,
    json_file: Path,
    previous_name: str | None,
    current_name: str,
) -> None:
    delta = comparison["places_delta"]
    lines = [
        "Сравнение версий каталога",
        "",
        f"Предыдущая версия: {previous_name or '<нет: первая версия>'}",
        f"Текущая версия:     {current_name}",
        "",
        "Итог:",
        f"места: {comparison['previous_places']} -> {comparison['current_places']} ({delta:+d})",
        f"добавлено: {comparison['added_count']}",
        f"удалено: {comparison['removed_count']}",
        f"изменено: {comparison['changed_count']}",
        "",
        "Изменения метрик аудита:",
    ]
    metric_changes = comparison.get("metric_changes", {})
    lines.extend(
        f"{key}: {values['before']} -> {values['after']} ({values['delta']:+d})"
        for key, values in metric_changes.items()
    )
    if not metric_changes:
        lines.append("(нет)")

    lines.extend([
        "",
        "Добавленные места:",
    ])
    lines.extend(f"+ {_place_label(row)}" for row in comparison["added"])
    if not comparison["added"]:
        lines.append("(нет)")

    lines.extend(["", "Удалённые места:"])
    lines.extend(f"- {_place_label(row)}" for row in comparison["removed"])
    if not comparison["removed"]:
        lines.append("(нет)")

    lines.extend(["", "Изменённые места:"])
    for item in comparison["changed"]:
        lines.append(f"* {_place_label(item['identity'])}")
        for field, values in item["fields"].items():
            lines.append(
                f"  {field}: {_short(values['before'])!r} -> {_short(values['after'])!r}"
            )
    if not comparison["changed"]:
        lines.append("(нет)")

    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_file.write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def replace_directory(source: Path, target: Path) -> None:
    suffix = uuid4().hex
    temporary = target.parent / f".{target.name}.new-{suffix}"
    backup = target.parent / f".{target.name}.old-{suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, temporary)
    try:
        if target.exists():
            os.replace(target, backup)
        os.replace(temporary, target)
    except Exception:
        if backup.exists() and not target.exists():
            os.replace(backup, target)
        raise
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
        if backup.exists():
            shutil.rmtree(backup)


def publish_snapshot(snapshot: Path, aggregation_dir: Path) -> None:
    replace_directory(snapshot / "csv", aggregation_dir / "csv")
    replace_directory(snapshot / "merged_data", aggregation_dir / "merged_data")
    replace_directory(snapshot / "export", aggregation_dir / "export")
    shutil.copy2(
        snapshot / "reports" / "audit_report.txt",
        aggregation_dir / "audit_report.txt",
    )


def write_latest_pointer(snapshots_dir: Path, snapshot: Path) -> None:
    pointer = snapshots_dir / "latest.json"
    temporary = snapshots_dir / f".latest-{uuid4().hex}.json"
    temporary.write_text(
        json.dumps({"snapshot": snapshot.name}, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, pointer)
