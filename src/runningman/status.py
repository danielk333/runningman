from enum import Enum


class ServiceStatus(Enum):
    NotStarted = 0
    Started = 1
    Stopped = 2


class TriggerStatus(Enum):
    NotStarted = 0
    Started = 1
    Stopped = 2


class ThreadStatus(Enum):
    NotStarted = 0
    Running = 1
    Completed = 2


class ProviderStatus(Enum):
    NotStarted = 0
    Started = 1
    Stopped = 2


class ProcessStatus(Enum):
    NotStarted = 0
    Running = 1
    Completed = 2
    Failed = 3


def thread_status(proc):
    if proc is None:
        return ThreadStatus.NotStarted
    elif proc.is_alive():
        return ThreadStatus.Running
    else:
        return ThreadStatus.Completed


def process_status(proc):
    if proc is None:
        return ProcessStatus.NotStarted
    elif proc.is_alive():
        return ProcessStatus.Running
    elif proc.exitcode != 0 and proc.exitcode is not None:
        return ProcessStatus.Failed
    else:
        return ProcessStatus.Completed
