from multiprocessing import Value
import time
from ctypes import Structure, c_double, c_int


class Porfile(Structure):
    _fields_ = [('total_walltime', c_double), ('executions', c_int)]


def make_profile():
    return Value(Porfile, 0.0, 0)


class Porfiler:
    def __init__(self):
        self.executions = 0
        self.total_walltime = 0.0
        self.t0 = None

    def start(self):
        self.t0 = time.time()

    def stop(self):
        if self.t0 is None:
            return
        self.executions += 1
        self.total_walltime += time.time() - self.t0
        self.t0 = None


class MPPorfiler:
    def __init__(self, profile):
        self.profile = profile
        self.t0 = None

    def start(self):
        self.t0 = time.time()

    def stop(self):
        if self.t0 is None:
            return
        with self.profile.get_lock():
            self.profile.executions += 1
            self.profile.total_walltime += time.time() - self.t0
        self.t0 = None
