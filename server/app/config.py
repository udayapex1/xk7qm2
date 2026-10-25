from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, time
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Settings:
    decision_start: date
    decision_end: date
    default_cutoff: time
    timezone_name: str
    allowed_origins: tuple[str, ...]
    minimum_buffer_samples: int

    @property
    def timezone(self) -> ZoneInfo:
        """Return the configured IANA timezone."""
        return ZoneInfo(self.timezone_name)

    @property
    def first_delivery_date(self) -> date:
        """Return the first delivery day after the decision window starts."""
        return date.fromordinal(self.decision_start.toordinal() + 1)

    @property
    def last_delivery_date(self) -> date:
        """Return the last delivery day after the decision window ends."""
        return date.fromordinal(self.decision_end.toordinal() + 1)


def get_settings() -> Settings:
    """Build application settings from environment variables and defaults."""
    origins = os.getenv("ALLOWED_ORIGINS", "*")
    return Settings(
        decision_start=date.fromisoformat(os.getenv("DECISION_START", "2026-01-01")),
        decision_end=date.fromisoformat(os.getenv("DECISION_END", "2026-01-31")),
        default_cutoff=time.fromisoformat(os.getenv("DEFAULT_CUTOFF", "09:00")),
        timezone_name=os.getenv("TIMEZONE", "Europe/London"),
        allowed_origins=tuple(origin.strip() for origin in origins.split(",") if origin.strip()),
        minimum_buffer_samples=int(os.getenv("MINIMUM_BUFFER_SAMPLES", "30")),
    )


settings = get_settings()
