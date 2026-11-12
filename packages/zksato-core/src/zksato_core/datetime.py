"""Bangkok timezone, market sessions, and datetime utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

import pendulum
from pendulum import DateTime

BANGKOK_TZ = pendulum.timezone("Asia/Bangkok")
UTC_TZ = pendulum.timezone("UTC")

# Weekday constants (Monday=0, Sunday=6)
WEEKDAY_SATURDAY = 5
WEEKDAY_SUNDAY = 6


def now_bangkok() -> DateTime:
    """Current time in Bangkok timezone."""
    return pendulum.now(BANGKOK_TZ)


def now_utc() -> DateTime:
    """Current time in UTC."""
    return pendulum.now(UTC_TZ)


def to_bangkok(dt: DateTime) -> DateTime:
    """Convert datetime to Bangkok timezone."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    return dt.astimezone(BANGKOK_TZ)


def to_utc(dt: DateTime) -> DateTime:
    """Convert datetime to UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BANGKOK_TZ)
    return dt.astimezone(UTC_TZ)


def bangkok_today() -> date:
    """Today's date in Bangkok timezone."""
    return now_bangkok().date()


def parse_iso_datetime(value: str) -> DateTime:
    """Parse ISO 8601 datetime string."""
    parsed = pendulum.parse(value)
    if not isinstance(parsed, DateTime):
        raise TypeError(f"Expected datetime, got {type(parsed)}")
    return parsed


def format_iso_datetime(dt: DateTime) -> str:
    """Format datetime as ISO 8601 string."""
    return dt.isoformat()


@dataclass(frozen=True, slots=True)
class MarketSession:
    """Market trading session."""

    name: str
    start: time
    end: time
    timezone: str = "Asia/Bangkok"

    def contains(self, dt: DateTime) -> bool:
        """Check if datetime falls within this session."""
        local = to_bangkok(dt).time()
        return self.start <= local < self.end


# Default SET equity sessions
DEFAULT_EQUITY_SESSIONS = [
    MarketSession("morning", time(9, 30), time(12, 30)),
    MarketSession("afternoon", time(14, 0), time(16, 30)),
]

# Default TFEX sessions
DEFAULT_TFEX_DAY_SESSION = MarketSession("tfex_day", time(9, 30), time(16, 30))
DEFAULT_TFEX_NIGHT_SESSION = MarketSession("tfex_night", time(19, 0), time(23, 59))


@dataclass(frozen=True, slots=True)
class MarketCalendar:
    """Market calendar with sessions and holidays."""

    equity_sessions: list[MarketSession]
    tfex_day_session: MarketSession
    tfex_night_session: MarketSession
    holidays: set[date]
    special_sessions: dict[date, list[MarketSession]]

    def is_holiday(self, dt: date) -> bool:
        return dt in self.holidays

    def is_trading_day(self, dt: date) -> bool:
        if self.is_holiday(dt):
            return False
        # Weekend check (Saturday=5, Sunday=6) - neither Saturday nor Sunday are trading days
        return dt.weekday() < WEEKDAY_SATURDAY

    def get_sessions(self, dt: date, market: str = "equity") -> list[MarketSession]:
        """Get trading sessions for a given date and market."""
        if self.is_holiday(dt) or not self.is_trading_day(dt):
            return []

        if dt in self.special_sessions:
            return self.special_sessions[dt]

        if market == "equity":
            return self.equity_sessions
        elif market == "tfex":
            return [self.tfex_day_session, self.tfex_night_session]
        return []

    def is_session_open(self, dt: DateTime, market: str = "equity") -> bool:
        """Check if market session is open at given datetime."""
        sessions = self.get_sessions(dt.date(), market)
        return any(s.contains(dt) for s in sessions)

    def next_session_open(self, dt: DateTime, market: str = "equity") -> DateTime | None:
        """Get next session open time."""
        current = pendulum.instance(dt)
        for _ in range(10):  # Look ahead up to 10 days
            sessions = self.get_sessions(current.date(), market)
            for session in sessions:
                open_dt = pendulum.datetime(
                    current.year,
                    current.month,
                    current.day,
                    session.start.hour,
                    session.start.minute,
                    tz=BANGKOK_TZ,
                )
                if open_dt > current:
                    return open_dt
            current = current.add(days=1).start_of("day")
        return None


def create_default_calendar(
    equity_sessions: list[MarketSession] | None = None,
    holidays: list[date] | None = None,
    special_sessions: dict[date, list[MarketSession]] | None = None,
) -> MarketCalendar:
    """Create a default market calendar."""
    return MarketCalendar(
        equity_sessions=equity_sessions or DEFAULT_EQUITY_SESSIONS,
        tfex_day_session=DEFAULT_TFEX_DAY_SESSION,
        tfex_night_session=DEFAULT_TFEX_NIGHT_SESSION,
        holidays=set(holidays or []),
        special_sessions=special_sessions or {},
    )
