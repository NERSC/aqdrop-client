import enum


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DECLINED = "declined"
    RESET = "reset"


class QueueState(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    RETIRED = "retired"


class QueueType(str, enum.Enum):
    QPU = "qpu"
    SIMU = "simu"
