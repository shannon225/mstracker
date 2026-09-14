"""Explicit instrument-local wall time to UTC conversion, including DST folds."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def utcnow():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def zone(name):
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise ValueError("Choose a valid IANA time zone, for example America/Chicago.") from None


def local_instant(value, timezone_name, fold=""):
    try:
        wall = datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except (ValueError, TypeError):
        raise ValueError("Enter a valid date and time.") from None
    if not 1900 <= wall.year <= 2100:
        raise ValueError("Use a year between 1900 and 2100.")
    tz = zone(timezone_name)
    candidates = {}
    for choice in (0, 1):
        aware = wall.replace(tzinfo=tz, fold=choice)
        if aware.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) == wall:
            candidates[choice] = aware
    if not candidates:
        raise ValueError("This local time does not exist because of daylight saving time.")
    ambiguous = len({v.utcoffset() for v in candidates.values()}) > 1
    if ambiguous and fold not in ("0", "1"):
        raise ValueError("This time occurs twice. Choose the earlier or later DST occurrence.")
    result = candidates[int(fold)] if ambiguous else next(iter(candidates.values()))
    return iso(result), result.isoformat(), result.fold


def local_display(value, timezone_name):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(zone(timezone_name))
