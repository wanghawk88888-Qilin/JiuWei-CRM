"""Consistent handling of stored datetime strings and business-time boundaries.

Two concerns live here:

1. **String normalisation.** ``FollowUp.next_followup_at`` is a plain ``String``
   column, and two formats coexist in the database:

     * ISO-8601 local, from ``<input type="datetime-local">``: ``2026-08-24T00:05``
     * legacy space-separated:                              ``2026-08-24 00:05:00``

   The dashboard/pending filters compare against a space-separated day boundary
   (e.g. ``2026-08-24 23:59:59``). Naive lexicographic comparison breaks for the
   ISO variant because ``'T'`` (0x54) sorts *after* ``' '`` (0x20), so a
   ``<= 23:59:59`` string comparison silently drops same-day ISO records.

   The normalise helpers convert both formats to the space-separated form before
   any comparison, without touching the stored value or the schema.

2. **Business date boundaries.** "today / today new leads / pending followups /
   next 3 days" must be computed in the Chinese business timezone
   (``Asia/Shanghai``), never from the server-local clock. The production Docker
   image runs on UTC, so during Beijing 00:00–07:59 the server-local
   ``datetime.datetime.now()`` still reports the *previous* calendar day and
   would misclassify the whole business day.

   ``business_now()`` and the boundary helpers below are the single source of
   truth for those "today" calculations.
"""

import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func

# The CRM's business timezone. All "today / tomorrow / next N days / due today"
# boundaries are computed against this wall clock, regardless of where the
# server happens to be deployed.
BUSINESS_TZ = ZoneInfo("Asia/Shanghai")


def business_now() -> datetime.datetime:
    """Current wall-clock time in the business timezone (Asia/Shanghai).

    Use this for every CRM *business date boundary*. Keep using
    ``datetime.datetime.now(datetime.timezone.utc)`` for system timestamps
    (created_at / updated_at), which remain UTC.
    """
    return datetime.datetime.now(BUSINESS_TZ)


def business_today() -> str:
    """Today's date in the business timezone, ``YYYY-MM-DD``."""
    return business_now().strftime("%Y-%m-%d")


def business_day_utc_range(day: str | None = None) -> tuple[str, str]:
    """UTC ``[start, end)`` string bounds covering one full Beijing business day.

    ``created_at`` / ``updated_at`` are stored in UTC, so "today new leads"
    filters must compare against the UTC window that maps to the Beijing
    business day — never against the Beijing date string itself.

    ``day`` is a ``YYYY-MM-DD`` business date (Asia/Shanghai); defaults to
    today's Beijing date.

    Beijing 2026-08-25 00:00 -> UTC 2026-08-24 16:00:00
    Beijing 2026-08-26 00:00 -> UTC 2026-08-25 16:00:00
    """
    if day is None:
        day = business_today()
    year, month, day_num = (int(part) for part in day.split("-"))
    start_bj = datetime.datetime(year, month, day_num, 0, 0, 0, tzinfo=BUSINESS_TZ)
    end_bj = start_bj + datetime.timedelta(days=1)
    utc_start = start_bj.astimezone(datetime.timezone.utc)
    utc_end = end_bj.astimezone(datetime.timezone.utc)
    return (
        utc_start.strftime("%Y-%m-%d %H:%M:%S"),
        utc_end.strftime("%Y-%m-%d %H:%M:%S"),
    )


def normalize_datetime(value: str | None) -> str | None:
    """Normalise a stored datetime string to ``YYYY-MM-DD HH:MM:SS``.

    Accepts both ``T`` and space separators, and pads missing seconds so the
    result compares correctly against day boundaries (``00:00:00`` /
    ``23:59:59``). Returns ``None`` (or empty string) unchanged.
    """
    if not value:
        return value
    value = value.replace("T", " ")
    if len(value) == 16:  # "YYYY-MM-DD HH:MM" — append missing seconds
        value += ":00"
    return value


def normalize_column(column):
    """SQLAlchemy expression normalising a datetime-string column.

    Replaces the ISO ``T`` separator with a space. The query filters only ever
    compare against whole-day ``23:59:59`` boundaries, where the date prefix
    decides the outcome, so a plain ``replace`` is sufficient on the SQL side.
    """
    return func.replace(column, "T", " ")
