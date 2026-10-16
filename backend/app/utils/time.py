from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(moment: datetime) -> datetime:
    # SQLite round-trips datetimes without tzinfo, so naive values are assumed UTC.
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def start_of_day(moment: datetime) -> datetime:
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)