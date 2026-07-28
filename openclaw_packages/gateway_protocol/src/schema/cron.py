from typing import Literal, Final, Optional, List, Any

CRON_SCHEDULE_KIND = Literal["every", "cron", "at"]

CRON_SCHEDULE_KIND_EVERY: Literal["every"] = "every"
CRON_SCHEDULE_KIND_CRON: Literal["cron"] = "cron"
CRON_SCHEDULE_KIND_AT: Literal["at"] = "at"

CRON_SCHEDULE_KINDS: Final[tuple] = (
    CRON_SCHEDULE_KIND_EVERY,
    CRON_SCHEDULE_KIND_CRON,
    CRON_SCHEDULE_KIND_AT,
)

CRON_JOB_STATUS = Literal["active", "paused", "deleted"]

CRON_JOB_STATUS_ACTIVE: Literal["active"] = "active"
CRON_JOB_STATUS_PAUSED: Literal["paused"] = "paused"
CRON_JOB_STATUS_DELETED: Literal["deleted"] = "deleted"

CRON_JOB_STATUSES: Final[tuple] = (
    CRON_JOB_STATUS_ACTIVE,
    CRON_JOB_STATUS_PAUSED,
    CRON_JOB_STATUS_DELETED,
)

class CronSchedule:
    kind: CRON_SCHEDULE_KIND
    every_ms: Optional[int]
    cron_expr: Optional[str]
    at_time: Optional[str]

class CronJob:
    job_id: str
    name: str
    schedule: CronSchedule
    enabled: bool
    payload: Optional[dict]
    status: CRON_JOB_STATUS
    metadata: Optional[dict]

class CronCreateParams:
    name: str
    schedule_kind: CRON_SCHEDULE_KIND
    schedule: CronSchedule
    enabled: Optional[bool]
    payload: Optional[dict]
    metadata: Optional[dict]

class CronCreateResult:
    job_id: str
    name: str
    metadata: Optional[dict]

class CronUpdateParams:
    job_id: str
    name: Optional[str]
    schedule_kind: Optional[CRON_SCHEDULE_KIND]
    schedule: Optional[CronSchedule]
    enabled: Optional[bool]
    payload: Optional[dict]
    metadata: Optional[dict]

class CronUpdateResult:
    job_id: str
    metadata: Optional[dict]

class CronDeleteParams:
    job_id: str
    metadata: Optional[dict]

class CronDeleteResult:
    job_id: str
    metadata: Optional[dict]

class CronGetParams:
    job_id: str
    metadata: Optional[dict]

class CronGetResult:
    job: Optional[CronJob]
    metadata: Optional[dict]

class CronListParams:
    metadata: Optional[dict]

class CronListResult:
    jobs: List[CronJob]
    metadata: Optional[dict]
