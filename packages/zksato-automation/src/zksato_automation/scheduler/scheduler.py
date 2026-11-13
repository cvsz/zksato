"""Trading scheduler for zksato."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from zksato_automation.service import TradingService


@dataclass
class ScheduledJob:
    """A scheduled trading job."""

    job_id: str
    name: str
    trigger: str  # "interval" or "cron"
    trigger_args: dict[str, Any]
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    enabled: bool = True


class TradingScheduler:
    """Manages scheduled trading jobs."""

    def __init__(self, trading_service: TradingService) -> None:
        self.trading_service = trading_service
        self.scheduler = AsyncIOScheduler()
        self._jobs: dict[str, ScheduledJob] = {}

    def add_interval_job(
        self,
        job_id: str,
        func: Callable,
        seconds: float = 60,
        *args,
        **kwargs,
    ) -> None:
        """Add an interval-based job."""
        job = ScheduledJob(
            job_id=job_id,
            name=func.__name__,
            trigger="interval",
            trigger_args={"seconds": seconds},
            func=func,
            args=args,
            kwargs=kwargs,
        )
        self._jobs[job_id] = job

        if self.scheduler.running:
            self.scheduler.add_job(
                func,
                IntervalTrigger(seconds=seconds),
                id=job_id,
                args=args,
                kwargs=kwargs,
            )

    def add_cron_job(
        self,
        job_id: str,
        func: Callable,
        cron_expr: str,
        *args,
        **kwargs,
    ) -> None:
        """Add a cron-based job."""
        job = ScheduledJob(
            job_id=job_id,
            name=func.__name__,
            trigger="cron",
            trigger_args={"cron_expr": cron_expr},
            func=func,
            args=args,
            kwargs=kwargs,
        )
        self._jobs[job_id] = job

        if self.scheduler.running:
            self.scheduler.add_job(
                func,
                CronTrigger.from_crontab(cron_expr),
                id=job_id,
                args=args,
                kwargs=kwargs,
            )

    def remove_job(self, job_id: str) -> bool:
        """Remove a job."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            if self.scheduler.running:
                self.scheduler.remove_job(job_id)
            return True
        return False

    def get_job(self, job_id: str) -> ScheduledJob | None:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[ScheduledJob]:
        """List all jobs."""
        return list(self._jobs.values())

    def start(self) -> None:
        """Start the scheduler."""
        # Add all registered jobs
        for job in self._jobs.values():
            if job.enabled:
                if job.trigger == "interval":
                    self.scheduler.add_job(
                        job.func,
                        IntervalTrigger(**job.trigger_args),
                        id=job.job_id,
                        args=job.args,
                        kwargs=job.kwargs,
                    )
                elif job.trigger == "cron":
                    self.scheduler.add_job(
                        job.func,
                        CronTrigger.from_crontab(job.trigger_args["cron_expr"]),
                        id=job.job_id,
                        args=job.args,
                        kwargs=job.kwargs,
                    )
        self.scheduler.start()

    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        self.scheduler.shutdown()

    async def run_once(self, job_id: str) -> Any:
        """Run a job once manually."""
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        return await job.func(*job.args, **job.kwargs)
