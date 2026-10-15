"""Runs the missed check-in sweep on a timer; safe with several workers, since alerts are deduplicated."""

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler = None


async def _sweep_missed_checkins() -> None:
    """Scheduled job: raise alerts for patients who have gone quiet."""
    from app.common import alerts as alert_engine

    try:
        created = await alert_engine.scan_missed_checkins()
        if created:
            logger.info("Missed check-in sweep raised %d alert(s)", created)
    except Exception as exc:
        # Log and carry on, so one failed sweep doesn't stop the next.
        logger.exception("Missed check-in sweep failed: %s", exc)


def start_scheduler() -> None:
    """Start background jobs. Safe to call when APScheduler is not installed."""
    global _scheduler

    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler disabled by configuration")
        return

    if _scheduler is not None:
        return

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        logger.warning(
            "apscheduler is not installed — the missed check-in sweep falls back "
            "to running opportunistically when alerts are loaded"
        )
        return

    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        _sweep_missed_checkins,
        trigger=IntervalTrigger(minutes=settings.MISSED_CHECKIN_SCAN_MINUTES),
        id="missed_checkin_sweep",
        name="Missed check-in sweep",
        replace_existing=True,
        # After downtime, run once instead of replaying every missed interval.
        coalesce=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info(
        "Scheduler started — missed check-in sweep every %d minute(s)",
        settings.MISSED_CHECKIN_SCAN_MINUTES,
    )


def shutdown_scheduler() -> None:
    """Stop background jobs on application shutdown."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")


def is_running() -> bool:
    """Whether a scheduler is currently driving the sweep."""
    return _scheduler is not None
