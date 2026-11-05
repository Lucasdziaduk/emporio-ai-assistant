"""Run the dataset loader and print a compact ingestion report."""

from __future__ import annotations

import json
import sys

from app.config import settings
from app.data import DatasetRepository, create_connection, load_dataset


def main() -> int:
    source_dir = settings.private_data_dir / "source"
    connection = create_connection(settings.sqlite_database)
    try:
        report = load_dataset(source_dir, connection)
        metadata = DatasetRepository(connection).get_metadata()
        payload = {
            "status": "loaded",
            "table_counts": report.table_counts,
            "earliest_order_date": report.earliest_order_date,
            "latest_order_date": report.latest_order_date,
            "warning_count": report.warning_count,
            "issues": [
                {
                    "code": issue.code,
                    "severity": issue.severity,
                    "entity_type": issue.entity_type,
                    "entity_id": issue.entity_id,
                    "message": issue.message,
                }
                for issue in report.issues
            ],
            "metadata_recorded": metadata is not None,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"Dataset loading failed: {exc}", file=sys.stderr)
        return 1
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
