"""Shared model helpers: UTC timestamps and a timestamp mixin."""

from datetime import datetime, timezone

from app.extensions import db


def utcnow() -> datetime:
    """Timezone-naive UTC now.

    SQLite has no native timezone support, so we store naive UTC values and
    convert only when displaying them. `datetime.utcnow()` is deprecated in
    Python 3.12+, which is why this helper exists.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    """Adds `created_at` / `updated_at` to any model.

    `default` runs on INSERT, `onupdate` runs on every UPDATE, so the audit
    columns maintain themselves without any code in the views.
    """

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
