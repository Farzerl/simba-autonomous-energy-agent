from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

TARIFF_CODE = "E4.3.11"
TARIFF_NAME = "ZETDC Time-of-Use tariff — 11 kV supply"
TARIFF_TIMEZONE = "Africa/Harare"

ENERGY_RATES_USD_PER_KWH: dict[str, float] = {
    "peak": 0.23,
    "standard": 0.13,
    "offpeak": 0.06,
}
DEMAND_CHARGE_USD_PER_KVA_MONTH = 9.43
REACTIVE_ENERGY_USD_PER_KVARH = 0.052
POWER_FACTOR_THRESHOLD = 0.95

# Public-holiday dates supplied with the verified 2026 tariff workbook/deck.
# The setting remains overridable in Admin for future years.
DEFAULT_PUBLIC_HOLIDAYS_2026: frozenset[date] = frozenset(
    {
        date(2026, 1, 1),
        date(2026, 2, 21),
        date(2026, 4, 3),
        date(2026, 4, 4),
        date(2026, 4, 6),
        date(2026, 4, 18),
        date(2026, 5, 1),
        date(2026, 5, 25),
    }
)

# One code per clock hour, 00:00 through 23:59.
# P = peak, S = standard, O = off-peak.
_SCHEDULE_CODES: dict[str, tuple[str, ...]] = {
    "weekday": (
        "O", "O", "O", "O", "O", "O", "O",
        "P", "P", "P", "P", "P",
        "S", "S", "S", "S", "S",
        "P", "P", "P", "P",
        "S", "O", "O",
    ),
    "saturday": (
        "O", "O", "O", "O", "O", "O", "O",
        "P", "P", "P", "P",
        "S", "S", "S", "S", "S", "S",
        "P", "P", "P",
        "S", "S", "O", "O",
    ),
    "sunday_or_holiday": (
        "O", "O", "O", "O", "O", "O", "O",
        "S", "S", "S", "S", "S", "S", "S", "S", "S", "S",
        "P", "P", "P",
        "S", "S", "O", "O",
    ),
}

_PERIOD_BY_CODE = {"P": "peak", "S": "standard", "O": "offpeak"}


@dataclass(frozen=True)
class TariffInterval:
    timestamp: datetime
    day_type: str
    period: str
    rate_usd_per_kwh: float


def _as_datetime(timestamp: datetime | object) -> datetime:
    """Return a Python datetime without changing the represented local clock time."""
    if isinstance(timestamp, datetime):
        return timestamp
    converter = getattr(timestamp, "to_pydatetime", None)
    if callable(converter):
        value = converter()
        if isinstance(value, datetime):
            return value
    raise TypeError("timestamp must be a datetime or pandas Timestamp")


def parse_holiday_dates(values: Iterable[str | date] | None) -> frozenset[date]:
    if values is None:
        return DEFAULT_PUBLIC_HOLIDAYS_2026
    parsed: set[date] = set()
    for item in values:
        if isinstance(item, date) and not isinstance(item, datetime):
            parsed.add(item)
            continue
        text = str(item).strip()
        if not text:
            continue
        try:
            parsed.add(date.fromisoformat(text))
        except ValueError as exc:
            raise ValueError(f"Invalid public-holiday date '{text}'. Use YYYY-MM-DD.") from exc
    return frozenset(parsed)


def classify_day_type(
    timestamp: datetime | object,
    public_holidays: Iterable[str | date] | None = None,
) -> str:
    value = _as_datetime(timestamp)
    holidays = parse_holiday_dates(public_holidays)
    if value.date() in holidays or value.weekday() == 6:
        return "sunday_or_holiday"
    if value.weekday() == 5:
        return "saturday"
    return "weekday"


def classify_tariff_period(
    timestamp: datetime | object,
    public_holidays: Iterable[str | date] | None = None,
) -> str:
    """Classify Zimbabwe-local time using the verified 11 kV ToU schedule."""
    value = _as_datetime(timestamp)
    day_type = classify_day_type(value, public_holidays)
    return _PERIOD_BY_CODE[_SCHEDULE_CODES[day_type][value.hour]]


def tariff_rate_usd_per_kwh(
    timestamp: datetime | object,
    public_holidays: Iterable[str | date] | None = None,
    rates: dict[str, float] | None = None,
) -> float:
    selected_rates = rates or ENERGY_RATES_USD_PER_KWH
    return float(selected_rates[classify_tariff_period(timestamp, public_holidays)])


def interval_details(
    timestamp: datetime | object,
    public_holidays: Iterable[str | date] | None = None,
    rates: dict[str, float] | None = None,
) -> TariffInterval:
    value = _as_datetime(timestamp)
    period = classify_tariff_period(value, public_holidays)
    selected_rates = rates or ENERGY_RATES_USD_PER_KWH
    return TariffInterval(
        timestamp=value,
        day_type=classify_day_type(value, public_holidays),
        period=period,
        rate_usd_per_kwh=float(selected_rates[period]),
    )


def next_lower_cost_interval(
    timestamp: datetime | object,
    public_holidays: Iterable[str | date] | None = None,
    rates: dict[str, float] | None = None,
    *,
    step_minutes: int = 30,
    max_hours: int = 72,
) -> TariffInterval | None:
    """Find the next half-hour interval whose energy rate is lower than the source."""
    value = _as_datetime(timestamp)
    selected_rates = rates or ENERGY_RATES_USD_PER_KWH
    source_period = classify_tariff_period(value, public_holidays)
    source_rate = float(selected_rates[source_period])
    steps = max(1, int(max_hours * 60 / step_minutes))
    candidate = value
    for _ in range(steps):
        candidate += timedelta(minutes=step_minutes)
        details = interval_details(candidate, public_holidays, selected_rates)
        if details.rate_usd_per_kwh < source_rate:
            return details
    return None


def public_tariff_summary() -> dict[str, object]:
    return {
        "tariff_code": TARIFF_CODE,
        "tariff_name": TARIFF_NAME,
        "timezone": TARIFF_TIMEZONE,
        "energy_rates_usd_per_kwh": dict(ENERGY_RATES_USD_PER_KWH),
        "demand_charge_usd_per_kva_month": DEMAND_CHARGE_USD_PER_KVA_MONTH,
        "reactive_energy_usd_per_kvarh": REACTIVE_ENERGY_USD_PER_KVARH,
        "power_factor_threshold": POWER_FACTOR_THRESHOLD,
        "schedule": {
            day_type: [
                {"hour": hour, "period": _PERIOD_BY_CODE[code]}
                for hour, code in enumerate(codes)
            ]
            for day_type, codes in _SCHEDULE_CODES.items()
        },
        "public_holidays_2026": sorted(item.isoformat() for item in DEFAULT_PUBLIC_HOLIDAYS_2026),
        "claim_boundary": (
            "Operational tariff logic uses the supplied ZETDC 11 kV schedule. "
            "Invoice reproduction still requires the institution's billing registers, taxes, adjustments and billing-cycle reconciliation."
        ),
    }


def add_tariff_features(data):  # type: ignore[no-untyped-def]
    """Backwards-compatible pandas helper used by the original ingestion pipeline."""
    result = data.copy()
    result["tariff_period"] = result["timestamp"].apply(classify_tariff_period)
    result["is_peak"] = (result["tariff_period"] == "peak").astype(int)
    result["is_offpeak"] = (result["tariff_period"] == "offpeak").astype(int)
    return result
