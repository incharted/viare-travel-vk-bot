from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from services.requests import list_requests_for_export, request_status_label


def _exports_dir() -> Path:
    path = Path("./data/exports")
    path.mkdir(parents=True, exist_ok=True)
    return path


async def export_requests_csv() -> Path:
    rows = await list_requests_for_export()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _exports_dir() / f"requests_{timestamp}.csv"

    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(
            [
                "request_id",
                "created_at",
                "updated_at",
                "user_vk_id",
                "travel_scope",
                "country",
                "destination",
                "budget",
                "travelers",
                "start_date",
                "end_date",
                "rest_type",
                "status_code",
                "status_label",
                "manager_required",
                "assigned_manager_vk_id",
                "sla_15_sent",
                "sla_30_sent",
                "sla_60_sent",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row["id"],
                    row["created_at"],
                    row.get("updated_at") or "",
                    row["vk_id"],
                    row.get("travel_scope") or "",
                    row["country"] or "",
                    row.get("destination") or "",
                    row["budget"] or "",
                    row["travelers"] or "",
                    row["start_date"] or "",
                    row["end_date"] or "",
                    row["rest_type"] or "",
                    row["status"],
                    request_status_label(row["status"]),
                    row["manager_required"],
                    row.get("assigned_manager_vk_id") or "",
                    row.get("sla_15_sent") or 0,
                    row.get("sla_30_sent") or 0,
                    row.get("sla_60_sent") or 0,
                ]
            )
    return path


async def export_requests_xlsx() -> Path | None:
    try:
        from openpyxl import Workbook
    except ImportError:
        return None

    rows = await list_requests_for_export()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _exports_dir() / f"requests_{timestamp}.xlsx"

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Requests"
    worksheet.append(
        [
            "request_id",
            "created_at",
            "updated_at",
            "user_vk_id",
            "travel_scope",
            "country",
            "destination",
            "budget",
            "travelers",
            "start_date",
            "end_date",
            "rest_type",
            "status_code",
            "status_label",
            "manager_required",
            "assigned_manager_vk_id",
            "sla_15_sent",
            "sla_30_sent",
            "sla_60_sent",
        ]
    )
    for row in rows:
        worksheet.append(
            [
                row["id"],
                row["created_at"],
                row.get("updated_at") or "",
                row["vk_id"],
                row.get("travel_scope") or "",
                row["country"] or "",
                row.get("destination") or "",
                row["budget"] or "",
                row["travelers"] or "",
                row["start_date"] or "",
                row["end_date"] or "",
                row["rest_type"] or "",
                row["status"],
                request_status_label(row["status"]),
                row["manager_required"],
                row.get("assigned_manager_vk_id") or "",
                row.get("sla_15_sent") or 0,
                row.get("sla_30_sent") or 0,
                row.get("sla_60_sent") or 0,
            ]
        )

    workbook.save(path)
    return path
