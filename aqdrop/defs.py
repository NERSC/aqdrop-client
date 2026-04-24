import enum


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DECLINED = "declined"


class QueueState(str, enum.Enum):
    OPEN = "open"
    DOWN = "down"


class QueueType(str, enum.Enum):
    QPU = "qpu"
    SIMU = "simu"
