import argparse
import json
import shutil
import traceback
from datetime import datetime
from pathlib import Path
from uuid import uuid4

try:
    from .audit import audit
    from .merge_places import merge
    from .normalize_csv import normalize
    from .parse_docx import DOCX_FILE, run as extract
    from .versioning import (
        compare_audit_metrics,
        compare_place_files,
        latest_successful_snapshot,
        publish_snapshot,
        snapshot_name,
        write_comparison_report,
        write_latest_pointer,
    )
except ImportError:
    from audit import audit
    from merge_places import merge
    from normalize_csv import normalize
    from parse_docx import DOCX_FILE, run as extract
    from versioning import (
        compare_audit_metrics,
        compare_place_files,
        latest_successful_snapshot,
        publish_snapshot,
        snapshot_name,
        write_comparison_report,
        write_latest_pointer,
    )


BASE_DIR = Path(__file__).parent
SNAPSHOTS_DIR = BASE_DIR / "snapshots"


def run_pipeline(
    docx_file: Path = DOCX_FILE,
    snapshots_dir: Path = SNAPSHOTS_DIR,
    created_at: datetime | None = None,
    aggregation_dir: Path = BASE_DIR,
) -> Path:
    created_at = created_at or datetime.now().astimezone()
    name = snapshot_name(created_at)
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    if (snapshots_dir / name).exists():
        name = f"{name}_{uuid4().hex[:8]}"

    staging = snapshots_dir / f".{name}.building-{uuid4().hex}"
    failed = snapshots_dir / f"{name}_FAILED"
    snapshot = snapshots_dir / name
    previous = latest_successful_snapshot(snapshots_dir)
    staging.mkdir(parents=True)

    try:
        print(f"SNAPSHOT: {name}")
        print("STEP 1: extract docx")
        extract(docx_file=docx_file, export_dir=staging / "export")
        media_dir = staging / "export" / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        (media_dir / ".gitkeep").write_text("\n", encoding="utf-8")

        print("STEP 2: merge places")
        merge(
            input_file=staging / "export" / "text.json",
            output_dir=staging / "merged_data",
        )

        print("STEP 3: normalize csv")
        normalize(
            input_file=staging / "merged_data" / "places.csv",
            output_dir=staging / "csv",
        )

        print("STEP 4: audit")
        metrics = audit(
            csv_dir=staging / "csv",
            report_file=staging / "reports" / "audit_report.txt",
        )

        print("STEP 5: compare with previous snapshot")
        previous_file = previous / "merged_data" / "places.csv" if previous else None
        comparison = compare_place_files(
            previous_file=previous_file,
            current_file=staging / "merged_data" / "places.csv",
        )
        comparison["metric_changes"] = compare_audit_metrics(previous, metrics)
        write_comparison_report(
            comparison=comparison,
            report_file=staging / "reports" / "comparison_report.txt",
            json_file=staging / "reports" / "comparison.json",
            previous_name=previous.name if previous else None,
            current_name=name,
        )

        shutil.rmtree(staging / "export" / "_unpacked", ignore_errors=True)
        manifest = {
            "status": "pending_publish",
            "snapshot": name,
            "created_at": created_at.isoformat(),
            "source_file": str(docx_file),
            "previous_snapshot": previous.name if previous else None,
            "metrics": metrics,
            "comparison": {
                key: comparison[key]
                for key in (
                    "previous_places",
                    "current_places",
                    "places_delta",
                    "added_count",
                    "removed_count",
                    "changed_count",
                )
            },
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        staging.rename(snapshot)
        publish_snapshot(snapshot, aggregation_dir)
        manifest["status"] = "success"
        manifest_file = snapshot / "manifest.json"
        manifest_temporary = snapshot / ".manifest.json.tmp"
        manifest_temporary.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        manifest_temporary.replace(manifest_file)
        write_latest_pointer(snapshots_dir, snapshot)
        print(f"DONE: {snapshot}")
        return snapshot
    except Exception:
        error = traceback.format_exc()
        failed.mkdir(parents=True, exist_ok=True)
        (failed / "error.txt").write_text(error, encoding="utf-8")
        shutil.rmtree(staging, ignore_errors=True)
        print(f"FAILED: details saved to {failed / 'error.txt'}")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a versioned travel catalog snapshot")
    parser.add_argument("--source", type=Path, default=DOCX_FILE, help="source DOCX file")
    parser.add_argument(
        "--snapshots-dir",
        type=Path,
        default=SNAPSHOTS_DIR,
        help="directory for timestamped snapshots",
    )
    args = parser.parse_args()
    run_pipeline(docx_file=args.source, snapshots_dir=args.snapshots_dir)


if __name__ == "__main__":
    main()
