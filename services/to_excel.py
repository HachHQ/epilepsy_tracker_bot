import logging
import uuid
from datetime import datetime
from datetime import time as time_class
from pathlib import Path

import pandas as pd

from i18n import get_excel_export_headers

Path("temp_tables").mkdir(exist_ok=True)
logger = logging.getLogger(__name__)

EXCEL_TEMPLATE_PATH = "template_seizures.xlsx"

EXPECTED_COLUMNS = [
    "date",
    "time",
    "severity",
    "duration",
    "comment",
    "type_of_seizure",
    "location",
    "triggers",
    "symptoms",
]


def write_seizures_excel(rows: list[dict]) -> str:
    headers = get_excel_export_headers()
    data = [{headers[key]: row[key] for key in headers} for row in rows]
    df = pd.DataFrame(data)
    path = f"temp_tables/{uuid.uuid4().hex}_seizure_report.xlsx"
    df.to_excel(path, index=False)
    return path


def get_excel_template_path() -> str:
    return EXCEL_TEMPLATE_PATH


def validate_row(row: pd.Series) -> bool:
    try:
        if pd.isna(row["date"]):
            return False
        pd.to_datetime(row["date"], dayfirst=True, errors="raise")
        time_value = row.get("time")
        if pd.notna(time_value):
            if isinstance(time_value, time_class):
                pass
            elif isinstance(time_value, datetime):
                time_value = time_value.time()
            elif isinstance(time_value, float):
                total_seconds = int(time_value * 86400)
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                time_value = time_class(hour=hours, minute=minutes)
            elif isinstance(time_value, str):
                time_value = datetime.strptime(time_value.strip(), "%H:%M").time()
            else:
                return False
        duration_value = row.get("duration")
        if pd.notna(duration_value) and not isinstance(duration_value, (int, float)):
            return False
        return True
    except Exception:
        logger.exception("Invalid Excel row")
        return False


def parse_excel_time(time_value) -> time_class | None:
    if pd.isna(time_value):
        return None
    if isinstance(time_value, time_class):
        return time_value
    if isinstance(time_value, datetime):
        return time_value.time()
    if isinstance(time_value, float):
        total_seconds = int(time_value * 86400)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return time_class(hour=hours, minute=minutes)
    if isinstance(time_value, str):
        try:
            return datetime.strptime(time_value.strip(), "%H:%M").time()
        except ValueError:
            pass
    return None
