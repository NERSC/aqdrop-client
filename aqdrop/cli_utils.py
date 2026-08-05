import httpx
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

PT_TIMEZONE = ZoneInfo("America/Los_Angeles")
DB_TIME_FORMAT = "%Y-%m-%d %H:%M:%S %Z"

def connect_verbose():
    """Connects to the AQDROP service and prints connection status.

    Returns:
        AqdropClient: An authenticated AqdropClient instance.
    """
    try:
        print("Connecting...")
        from .main import AqdropClient
        c = AqdropClient()
        print("AQDrop client configured.\n")
    except httpx.ConnectError as e:
        print("Could not connect to AQDROP service. Is environment variable AQDROP_HOSTNAME properly set?")
        print(f"Error: {e}")
        exit()
    except httpx.HTTPStatusError as e:
        resp = e.response
        detail = resp.json().get('detail') if 'application/json' in resp.headers.get('content-type', '') else resp.text
        print(f"Could not connect to AQDROP service. Error {resp.status_code}: {detail}")
        exit()
    return c

def format_db_time_pt(db_time):
    """Formats a database timestamp to Pacific Time (PT) string.

    Args:
        db_time: The timestamp to format. Can be a datetime object or a string.

    Returns:
        str: The formatted timestamp string in DB_TIME_FORMAT.
    """
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

def trim(s: str, w: int = 80):
    """Trims a string by inserting newlines every w characters.

    Args:
        s: The string to trim.
        w: The width at which to insert newlines. Defaults to 80.

    Returns:
        str: The trimmed string.
    """
    r = ""
    i = 0
    for ch in s:
        if i > 0 and i % w == 0:
            r += "\n"
        r += ch
        i += 1
        if ch == "\n":
            i = 0
    return r

def _format_table_row(values, widths, alignments):
    """Formats a single row of a table with specified widths and alignments.

    Args:
        values: The values to be formatted in the row.
        widths: The target width for each column.
        alignments: The alignment ('right' or 'left') for each column.

    Returns:
        str: The formatted row as a string.
    """
    fields = []
    for value, width, alignment in zip(values, widths, alignments):
        if alignment == "right":
            fields.append(str(value).rjust(width))
        else:
            fields.append(str(value).ljust(width))
    return "   ".join(fields).rstrip()

def print_job_table(jobs):
    """Prints a formatted table of jobs to the console.

    Args:
        jobs: A list of job dictionaries to print.
    """
    headers = list(jobs[0].keys())
    alignments = ["right" if header == "id" else "left" for header in headers]
    rows = []
    for job in jobs:
        row = []
        for header in headers:
            value = job.get(header, "")
            if header == "last_action":
                value = format_db_time_pt(value)
            row.append(value)
        rows.append(row)

    widths = [
        max(len(str(header)), *(len(str(row[col_id])) for row in rows))
        for col_id, header in enumerate(headers)
    ]
    print(_format_table_row(headers, widths, alignments))
    print(_format_table_row(["-" * len(header) for header in headers], widths, alignments))
    for row in rows:
        print(_format_table_row(row, widths, alignments))
