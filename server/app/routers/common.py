from __future__ import annotations

import re
from datetime import date, time

from fastapi import HTTPException

from server.app.config import settings
from server.app.services.data_store import load_store


store = load_store()
CUTOFF_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def check_delivery_date(value: date) -> date:
    if not settings.first_delivery_date <= value <= settings.last_delivery_date:
        raise HTTPException(
            status_code=422,
            detail=(
                f"delivery_date must be between {settings.first_delivery_date.isoformat()} "
                f"and {settings.last_delivery_date.isoformat()}."
            ),
        )
    return value


def parse_cutoff(value: str | None) -> time:
    selected = settings.default_cutoff.strftime("%H:%M") if value is None else value
    if not CUTOFF_PATTERN.fullmatch(selected):
        raise HTTPException(status_code=422, detail="cutoff must use HH:MM (24-hour) format.")
    return time.fromisoformat(selected)
