import httpx
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pprint import pprint
from . import creds

PT_TIMEZONE = ZoneInfo("America/Los_Angeles")
DB_TIME_FORMAT = "%Y-%m-%d %H:%M:%S %Z"

def connect_verbose():
    try:
        print("Connecting...")
        from .main import AqdropClient
        c = AqdropClient()
        print(f"Connected to AQDROP service as user {creds.get_username()}.\n")
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

def get_submit_error_message(exc: BaseException) -> str:
    """Best-effort API error text (works with httpx.HTTPStatusError or aqdrop.AqdropHttpError)."""
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            data = exc.response.json()
        except Exception:
            text = (exc.response.text or "").strip()
            return text[:2000] if text else str(exc)
        if isinstance(data, dict) and "detail" in data:
            d = data["detail"]
            if isinstance(d, str):
                return d
            if isinstance(d, list):
                return "; ".join(str(x.get("msg", x)) if isinstance(x, dict) else str(x) for x in d)
            return str(d)
        return str(data) if data is not None else str(exc)
    return str(exc)

def print_circuit_table(circuits, meta: dict):
    """Pretty-print circuit list with their requested shots."""
    shots = meta.get("shots", [])
    if isinstance(shots, int):
        shots = [shots] * len(circuits)
    print("idx  num_qubits  num_shots")
    for idx, qc in enumerate(circuits):
        num_shots = shots[idx] if idx < len(shots) else "n/a"
        print(f"{idx:>3}  {qc.num_qubits:>10}  {num_shots}")

def print_shot_summary(input_md: dict, output: dict):
    """Compare asked vs received shots."""
    asked = input_md["shots"]
    received = output["shots"]
    print(f"shots asked={asked}")
    print(f"received={received}")
    if asked != received:
        missing = [a - r for a, r in zip(asked, received)]
        print(f"missing={missing}")

def print_output_counts(input_md: dict, output: dict):
    """Pretty-print counts for each circuit."""
    counts_list = output["counts"]
    asked_list = input_md["shots"]
    received_list = output["shots"]
    print(f"Output counts for {len(counts_list)} circuit(s)")
    for idx, counts in enumerate(counts_list):
        a = asked_list[idx]
        r = received_list[idx]
        print(f"circuit[{idx}] shots asked={a} received={r}")
        pprint(counts)

def _format_table_row(values, widths, alignments):

def _format_table_row(values, widths, alignments):
    fields = []
    for value, width, alignment in zip(values, widths, alignments):
        if alignment == "right":
            fields.append(str(value).rjust(width))
        else:
            fields.append(str(value).ljust(width))
    return "   ".join(fields).rstrip()

def print_job_table(jobs):
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
