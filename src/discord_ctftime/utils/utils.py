from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Dict, List
from dateutil import parser  #  ← ajouté

def _to_datetime(obj: Any, tz: ZoneInfo) -> datetime | None:
    """Convertit str/int/datetime → datetime(tz) ou None si impossible."""
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.astimezone(tz) if obj.tzinfo else obj.replace(tzinfo=tz)
    if isinstance(obj, (int, float)):
        # timestamp (secondes)
        return datetime.fromtimestamp(obj, tz)
    if isinstance(obj, str):
        try:
            dt = parser.parse(obj, dayfirst=True, fuzzy=True)
            return dt.astimezone(tz) if dt.tzinfo else dt.replace(tzinfo=tz)
        except (ValueError, OverflowError):
            return None
    return None