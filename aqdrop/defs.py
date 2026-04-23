import enum


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    #RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    KILLED = "killed"


class QueueState(str, enum.Enum):
    OPEN = "open"
    DOWN = "down"


class QueueType(str, enum.Enum):
    QPU = "qpu"
    SIMU = "simu"
