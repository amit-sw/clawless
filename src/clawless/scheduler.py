from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


@dataclass
class ScheduledJob:
    id: int
    cron_spec: str
    payload: str
    enabled: bool


class SchedulerService:
    def __init__(self, conn, on_job: Callable[[dict], None]):
        self.conn = conn
        self.on_job = on_job
        self.scheduler = BackgroundScheduler()

    def start(self) -> None:
        self.scheduler.start()

    def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)

    def load_jobs(self) -> list[ScheduledJob]:
        rows = self.conn.execute(
            "SELECT id, cron_spec, payload, enabled FROM jobs"
        ).fetchall()
        return [
            ScheduledJob(
                id=row["id"],
                cron_spec=row["cron_spec"],
                payload=row["payload"],
                enabled=bool(row["enabled"]),
            )
            for row in rows
        ]

    def schedule_jobs(self) -> None:
        for job in self.load_jobs():
            if not job.enabled:
                continue
            trigger = CronTrigger.from_crontab(job.cron_spec)
            self.scheduler.add_job(
                self._run_job,
                trigger,
                args=[job.id],
                id=f"job:{job.id}",
                replace_existing=True,
            )

    def _run_job(self, job_id: int) -> None:
        row = self.conn.execute(
            "SELECT payload FROM jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        if not row:
            return
        payload = json.loads(row["payload"])
        self.on_job(payload)
