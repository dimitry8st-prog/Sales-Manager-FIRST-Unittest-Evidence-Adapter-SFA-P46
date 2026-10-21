"""Каркас SFA-P46-UNITTEST-ADAPTER R1. Реализовать по CONTRACT_RU.md."""
import unittest
class RecordingError(ValueError):
    def __init__(self,code):
        self.code=code
        super().__init__(code)
class RecordingResult(unittest.TestResult):
    def __init__(self,*,release_id,bindings,attempt=1):
        raise NotImplementedError("IMPLEMENTATION_REQUIRED")
    def records(self):
        raise NotImplementedError("IMPLEMENTATION_REQUIRED")
