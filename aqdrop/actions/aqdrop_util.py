from datetime import datetime, timezone
from zoneinfo import ZoneInfo


PT_TIMEZONE = ZoneInfo("America/Los_Angeles")
DB_TIME_FORMAT = "%Y-%m-%d %H:%M:%S %Z"


def format_db_time_pt(db_time):
    if db_time is None:
        return ""

    if isinstance(db_time, datetime):
        action_time = db_time
    elif isinstance(db_time, str):
        normalized_time = db_time
        if normalized_time.endswith("Z"):
            normalized_time = normalized_time[:-1] + "+00:00"
        try:
            action_time = datetime.fromisoformat(normalized_time)
        except ValueError:
            return db_time
    else:
        return str(db_time)

    if action_time.tzinfo is None or action_time.tzinfo.utcoffset(action_time) is None:
        action_time = action_time.replace(tzinfo=timezone.utc)
    action_time = action_time.astimezone(PT_TIMEZONE)

    return action_time.strftime(DB_TIME_FORMAT)
