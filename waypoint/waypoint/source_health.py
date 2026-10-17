"""Freshness-aware source metadata; never turns an old report into a live signal.

The persisted health receipt stays unchanged. These functions derive an effective
state at read time so activity counts and the catalogue share the same boundary.
"""
from __future__ import annotations

from datetime import datetime, timezone

HEALTH_FRESHNESS_SECONDS = 25


def source_health(source: dict, now: datetime | None = None) -> dict:
    """Return the report plus an effective state and its conservative freshness.

    Unknown/missing/naive timestamps and timestamps in the future cannot attest
    current connectivity. Exactly 25 seconds old is stale, as for actor activity.
    Raw state/time remain available even when their effective state has expired.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Source health evaluation requires an aware time")
    reported_state = source.get('reported_state', source.get('state'))
    reported_at = source.get('reported_at', source.get('at'))
    age = None
    try:
        if not isinstance(reported_at, str):
            raise ValueError('Missing timestamp')
        timestamp = datetime.fromisoformat(reported_at.replace('Z', '+00:00'))
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError('Timestamp has no timezone')
        elapsed = (now - timestamp).total_seconds()
        if elapsed >= 0:
            age = elapsed
    except (ValueError, TypeError, OverflowError):
        pass
    known_state = reported_state in ('connected', 'disconnected')
    if reported_state == 'demo':
        effective, freshness = 'demo', 'not_applicable'
    elif age is None or not known_state:
        effective, freshness = 'unknown', 'unknown'
    elif age >= HEALTH_FRESHNESS_SECONDS:
        effective, freshness = 'stale', 'stale'
    else:
        effective, freshness = reported_state, 'fresh'
    return {**source, 'reported_state': reported_state, 'reported_at': reported_at,
            'state': effective, 'age_seconds': age, 'freshness': freshness}


def source_is_connected(source: dict, now: datetime | None = None) -> bool:
    return source_health(source, now)['state'] == 'connected'


def aggregate_source_health(sources: list[dict], now: datetime | None = None) -> dict:
    """A fresh connected source proves connectivity; uncertain peers do not.

    Disconnected is definitive only when every registered source freshly reports
    it. With no fresh connected source, stale/unknown peers remain explicit.
    """
    now = now or datetime.now(timezone.utc)
    normalized = [source_health(source, now) for source in sources]
    states = {source['state'] for source in normalized}
    state = next((candidate for candidate in ('connected', 'stale', 'unknown', 'disconnected', 'demo')
                  if candidate in states), 'unknown')
    return {'state': state, 'sources': normalized}
