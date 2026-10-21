"""Executable P46 contract regressions using real nested unittest suites.

Intentional failures/errors/skips belong to synthetic INNER TestCases. Every
outer regression must pass without skips or expected failures. This suite does
not claim a trusted runner, accepted F1-27 implementation or runtime wiring.
"""

import ast
import copy
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from contextlib import ExitStack
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
import audit_release.unittest_evidence as sut


def binding(test_id="synthetic.a", suite="unit", case="a"):
    return {"test_id": test_id, "suite_id": suite, "case_id": case}


def synthetic(test_id="synthetic.a", outcome="PASS", cleanup=None):
    class Synthetic(unittest.TestCase):
        def id(self):
            return test_id

        def runTest(self):
            if cleanup is not None:
                self.addCleanup(cleanup)
            if outcome == "FAIL":
                self.fail("SYNTHETIC_ASSERTION")
            if outcome == "ERROR":
                raise RuntimeError("SYNTHETIC_ERROR")
            if outcome == "SKIP":
                self.skipTest("SYNTHETIC_SKIP")
            if outcome == "SUB_PASS":
                with self.subTest(value=1):
                    self.assertTrue(True)
            if outcome == "SUB_FAIL":
                with self.subTest(value=1):
                    self.fail("SYNTHETIC_SUB_FAILURE")
            if outcome == "SUB_ERROR":
                with self.subTest(value=1):
                    raise RuntimeError("SYNTHETIC_SUB_ERROR")

    if outcome == "EXPECTED_FAILURE":
        Synthetic.runTest = unittest.expectedFailure(
            lambda self: self.fail("SYNTHETIC_EXPECTED_FAILURE")
        )
    if outcome == "UNEXPECTED_SUCCESS":
        Synthetic.runTest = unittest.expectedFailure(lambda self: None)
    return Synthetic()


def error_info(kind=AssertionError):
    try:
        raise kind("SYNTHETIC_EXCEPTION_PAYLOAD")
    except kind:
        return sys.exc_info()


def run_inner(result, *cases):
    unittest.TestSuite(cases).run(result)
    return result


class RecordingContractTests(unittest.TestCase):
    def make(self, names=("a",), attempt=1, release="release-1"):
        return sut.RecordingResult(
            release_id=release,
            bindings=[binding("synthetic." + name, case=name) for name in names],
            attempt=attempt,
        )

    def row(self, case="a", status="PASS", attempt=1, suite="unit", release="release-1"):
        return {
            "release_id": release, "suite_id": suite, "case_id": case,
            "attempt": attempt, "status": status,
            "exit_code": 1 if status in ("FAIL", "ERROR") else 0,
            "skip_count": 1 if status == "SKIP" else 0,
        }

    def invalid_configuration(self, **configuration):
        with self.assertRaises(sut.RecordingError) as caught:
            sut.RecordingResult(**configuration)
        self.assertIsInstance(caught.exception, ValueError)
        self.assertEqual(caught.exception.code, "INVALID_CONFIGURATION")
        self.assertEqual(str(caught.exception), "INVALID_CONFIGURATION")
        self.assertEqual(caught.exception.args, ("INVALID_CONFIGURATION",))

    def invalid_execution(self, result):
        with self.assertRaises(sut.RecordingError) as caught:
            result.records()
        self.assertEqual(caught.exception.code, "INVALID_EXECUTION")
        self.assertEqual(str(caught.exception), "INVALID_EXECUTION")
        self.assertEqual(caught.exception.args, ("INVALID_EXECUTION",))

    def finish(self, result, test=None):
        case = synthetic() if test is None else test
        result.startTest(case)
        result.addSuccess(case)
        result.stopTest(case)

    def test_public_abi_and_inheritance(self):
        self.assertTrue(issubclass(sut.RecordingError, ValueError))
        self.assertTrue(issubclass(sut.RecordingResult, unittest.TestResult))
        parameters = inspect.signature(sut.RecordingResult).parameters
        self.assertEqual(tuple(parameters), ("release_id", "bindings", "attempt"))
        for parameter in parameters.values():
            self.assertIs(parameter.kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertIs(parameters["release_id"].default, inspect.Parameter.empty)
        self.assertIs(parameters["bindings"].default, inspect.Parameter.empty)
        self.assertEqual(parameters["attempt"].default, 1)

    def test_release_suite_case_identifier_boundaries(self):
        for value in ("A", "AZaz09_.-", "a" * 128):
            result = sut.RecordingResult(
                release_id=value,
                bindings=[binding(suite=value, case=value)],
            )
            self.finish(result)
            self.assertEqual(result.records(), [self.row(case=value, suite=value, release=value)])
        bad = ("", "a" * 129, "a b", "a\n", "a/b", "ю", "Ａ", "é", "a\x00", True, 1, None)
        for field in ("release_id", "suite_id", "case_id"):
            for value in bad:
                with self.subTest(field=field, type=type(value).__name__):
                    cfg = {"release_id": "r", "bindings": [binding()]}
                    if field == "release_id":
                        cfg[field] = value
                    else:
                        cfg["bindings"][0][field] = value
                    self.invalid_configuration(**cfg)

    def test_attempt_is_exact_positive_int_without_invented_cap(self):
        for value in (True, False, 0, -1, 1.5, "1", None, [], {}):
            self.invalid_configuration(release_id="r", bindings=[], attempt=value)
        huge = 1 << 200
        result = self.make(attempt=huge)
        run_inner(result, synthetic())
        self.assertEqual(result.records()[0]["attempt"], huge)
        self.assertIs(type(result.records()[0]["attempt"]), int)

    def test_bindings_container_element_and_key_shapes(self):
        for value in (None, True, (), {}, "x", 1):
            self.invalid_configuration(release_id="r", bindings=value)
        for value in (None, [], True, "x", 1, {}, {"test_id": "a"}, {**binding(), "extra": 1}):
            self.invalid_configuration(release_id="r", bindings=[value])
        for bad_key in (1, None, ("test_id",)):
            bad = binding()
            del bad["test_id"]
            bad[bad_key] = "synthetic.a"
            self.invalid_configuration(release_id="r", bindings=[bad])

    def test_exact_builtin_subclasses_rejected_for_every_config_position(self):
        class StrSubclass(str):
            pass

        class IntSubclass(int):
            pass

        class ListSubclass(list):
            pass

        class DictSubclass(dict):
            pass

        self.invalid_configuration(release_id=StrSubclass("r"), bindings=[])
        self.invalid_configuration(release_id="r", bindings=[], attempt=IntSubclass(1))
        self.invalid_configuration(release_id="r", bindings=ListSubclass())
        self.invalid_configuration(release_id="r", bindings=[DictSubclass(binding())])
        for field in ("test_id", "suite_id", "case_id"):
            value = binding()
            value[field] = StrSubclass(value[field])
            self.invalid_configuration(release_id="r", bindings=[value])
        value = {StrSubclass(key): item for key, item in binding().items()}
        self.invalid_configuration(release_id="r", bindings=[value])

    def test_invalid_objects_do_not_escape_configuration_error(self):
        class HostileMeta(type):
            def __eq__(cls, other):
                raise AssertionError("metaclass comparison hook")

        class Hostile(metaclass=HostileMeta):
            def __str__(self):
                raise AssertionError("string hook")

        for position in ("release_id", "bindings", "attempt"):
            cfg = {"release_id": "r", "bindings": [], "attempt": 1}
            cfg[position] = Hostile()
            self.invalid_configuration(**cfg)

    def test_test_id_length_unicode_and_exact_comparison(self):
        for test_id in ("x", "я" * 512, "case:[]/{};!?", "😀"):
            result = sut.RecordingResult(release_id="r", bindings=[binding(test_id)])
            run_inner(result, synthetic(test_id))
            self.assertEqual(result.records(), [self.row(release="r")])
        for value in ("", "x" * 513, 1, True, None):
            self.invalid_configuration(release_id="r", bindings=[binding(value)])
        result = sut.RecordingResult(release_id="r", bindings=[
            binding("é", case="precomposed"), binding("e\u0301", case="decomposed"),
        ])
        run_inner(result, synthetic("é"), synthetic("e\u0301"))
        self.assertEqual([row["case_id"] for row in result.records()], ["decomposed", "precomposed"])

    def test_test_id_rejects_all_c0_del_whitespace_and_surrogates(self):
        forbidden = [chr(value) for value in range(32)] + ["\x7f", " ", "\u0085", "\u00a0", "\u2003", "\u2028", "\ud800", "\udfff"]
        for character in forbidden:
            with self.subTest(codepoint=ord(character)):
                self.invalid_configuration(release_id="r", bindings=[binding("x" + character + "y")])

    def test_bindings_zero_and_ten_thousand_boundary(self):
        self.assertEqual(self.make(names=()).records(), [])
        values = [binding("synthetic." + str(i), case="case-" + str(i)) for i in range(10000)]
        result = sut.RecordingResult(release_id="r", bindings=values)
        self.assertEqual(result.records(), [])
        self.invalid_configuration(release_id="r", bindings=values + [binding("extra", case="extra")])

    def test_duplicate_test_ids_and_suite_case_pairs_rejected(self):
        self.invalid_configuration(release_id="r", bindings=[binding(), binding()])
        self.invalid_configuration(release_id="r", bindings=[binding(), binding("other")])
        self.invalid_configuration(release_id="r", bindings=[binding(), binding(case="other")])
        result = sut.RecordingResult(release_id="r", bindings=[
            binding("one", suite="one", case="shared"),
            binding("two", suite="two", case="shared"),
        ])
        run_inner(result, synthetic("one"), synthetic("two"))
        self.assertEqual([row["suite_id"] for row in result.records()], ["one", "two"])

    def test_configuration_is_snapshotted_without_mutable_aliases(self):
        values = [binding()]
        before = copy.deepcopy(values)
        result = sut.RecordingResult(release_id="r", bindings=values)
        values[0].update(test_id="foreign", suite_id="foreign", case_id="foreign")
        values.append(binding("new", case="new"))
        run_inner(result, synthetic())
        self.assertEqual(result.records(), [self.row(release="r")])
        self.assertEqual(before, [binding()])

    def test_constructor_and_records_never_run_or_load_tests(self):
        def forbidden(*args, **kwargs):
            raise AssertionError("adapter attempted to execute/load tests")

        with (
            patch.object(unittest.TestCase, "run", side_effect=forbidden),
            patch.object(unittest.TestSuite, "run", side_effect=forbidden),
            patch.object(unittest.TestLoader, "loadTestsFromName", side_effect=forbidden),
        ):
            result = self.make()
            self.assertEqual(result.records(), [])

    def test_actual_mixed_outcomes_exact_rows_and_standard_fields(self):
        result = self.make(names=("pass", "fail", "error", "skip"), attempt=7)
        cases = [synthetic("synthetic." + name, status) for name, status in (
            ("pass", "PASS"), ("fail", "FAIL"), ("error", "ERROR"), ("skip", "SKIP"),
        )]
        run_inner(result, *cases)
        self.assertEqual(result.records(), [self.row(case=name, status=status, attempt=7) for name, status in (
            ("error", "ERROR"), ("fail", "FAIL"), ("pass", "PASS"), ("skip", "SKIP"),
        )])
        self.assertEqual((result.testsRun, len(result.failures), len(result.errors), len(result.skipped)), (4, 1, 1, 1))
        self.assertFalse(result.wasSuccessful())
        self.assertFalse(result.shouldStop)
        self.assertIs(result.failures[0][0], cases[1])
        self.assertIs(result.errors[0][0], cases[2])
        self.assertIs(result.skipped[0][0], cases[3])
        self.assertIn("SYNTHETIC_ASSERTION", result.failures[0][1])
        self.assertIn("SYNTHETIC_ERROR", result.errors[0][1])

    def test_success_and_skip_keep_standard_was_successful_semantics(self):
        result = self.make(names=("a", "b"))
        run_inner(result, synthetic(), synthetic("synthetic.b", "SKIP"))
        self.assertTrue(result.wasSuccessful())
        self.assertEqual([r["status"] for r in result.records()], ["PASS", "SKIP"])

    def test_parent_methods_are_called_for_supported_callbacks(self):
        names = ("startTest", "addSuccess", "addFailure", "addError", "addSkip", "stopTest")
        originals = {name: getattr(unittest.TestResult, name) for name in names}
        calls = []

        def wrapper(name):
            def invoke(result, *args):
                calls.append(name)
                return originals[name](result, *args)
            return invoke

        with ExitStack() as stack:
            for name in names:
                stack.enter_context(patch.object(unittest.TestResult, name, wrapper(name)))
            result = self.make(names=("a", "b", "c", "d"))
            run_inner(result, synthetic(), synthetic("synthetic.b", "FAIL"), synthetic("synthetic.c", "ERROR"), synthetic("synthetic.d", "SKIP"))
        self.assertEqual(calls.count("startTest"), 4)
        self.assertEqual(calls.count("stopTest"), 4)
        for name in names[1:-1]:
            self.assertEqual(calls.count(name), 1)

    def test_failfast_failure_and_error_leave_remaining_bindings_absent(self):
        for status in ("FAIL", "ERROR"):
            with self.subTest(status=status):
                result = self.make(names=("a", "b"))
                result.failfast = True
                run_inner(result, synthetic(outcome=status), synthetic("synthetic.b"))
                self.assertTrue(result.shouldStop)
                self.assertEqual(result.testsRun, 1)
                self.assertEqual(result.records(), [self.row(status=status)])

    def test_explicit_stop_before_run_produces_no_records(self):
        result = self.make()
        result.stop()
        run_inner(result, synthetic())
        self.assertTrue(result.shouldStop)
        self.assertEqual(result.testsRun, 0)
        self.assertEqual(result.records(), [])

    def test_explicit_stop_during_test_keeps_only_completed_case(self):
        result = self.make(names=("a", "b"))

        class Stopper(unittest.TestCase):
            def id(self):
                return "synthetic.a"

            def runTest(self):
                result.stop()

        run_inner(result, Stopper(), synthetic("synthetic.b"))
        self.assertEqual(result.records(), [self.row()])
        self.assertEqual(result.testsRun, 1)

    def test_start_and_stop_test_run_are_optional_and_do_not_reset(self):
        result = self.make(names=("a", "b"))
        result.startTestRun()
        run_inner(result, synthetic())
        result.stopTestRun()
        first = result.records()
        result.startTestRun()
        run_inner(result, synthetic("synthetic.b"))
        result.stopTestRun()
        self.assertEqual(first, [self.row()])
        self.assertEqual(result.records(), [self.row(), self.row(case="b")])

    def test_same_identifier_can_use_different_test_instances_across_cycle(self):
        result = self.make()
        result.startTest(synthetic())
        result.addSuccess(synthetic())
        result.stopTest(synthetic())
        self.assertEqual(result.records(), [self.row()])

    def test_no_events_and_unexecuted_bindings_do_not_become_pass(self):
        result = self.make(names=("a", "b", "c"))
        self.assertEqual(result.records(), [])
        run_inner(result, synthetic("synthetic.b"))
        self.assertEqual(result.records(), [self.row(case="b")])

    def test_records_are_plain_exact_seven_field_containers(self):
        result = run_inner(self.make(), synthetic())
        rows = result.records()
        self.assertIs(type(rows), list)
        self.assertIs(type(rows[0]), dict)
        self.assertEqual(set(rows[0]), {"release_id", "suite_id", "case_id", "attempt", "status", "exit_code", "skip_count"})
        for key in ("release_id", "suite_id", "case_id", "status"):
            self.assertIs(type(rows[0][key]), str)
        for key in ("attempt", "exit_code", "skip_count"):
            self.assertIs(type(rows[0][key]), int)

    def test_snapshot_sorting_is_python_suite_then_case_order(self):
        bindings = [binding("z", suite="z", case="a"), binding("A", suite="A", case="z"), binding("a", suite="A", case="A")]
        result = sut.RecordingResult(release_id="r", bindings=bindings)
        run_inner(result, synthetic("z"), synthetic("A"), synthetic("a"))
        self.assertEqual([(r["suite_id"], r["case_id"]) for r in result.records()], [("A", "A"), ("A", "z"), ("z", "a")])

    def test_snapshots_are_nonsealing_and_independent(self):
        result = self.make(names=("a", "b"))
        run_inner(result, synthetic())
        first = result.records()
        second = result.records()
        first[0]["status"] = "altered"
        first.append({})
        self.assertEqual(second, [self.row()])
        run_inner(result, synthetic("synthetic.b"))
        self.assertEqual(second, [self.row()])
        self.assertEqual(result.records(), [self.row(), self.row(case="b")])

    def test_attempts_and_instances_are_independent(self):
        one, two = self.make(attempt=1), self.make(attempt=2)
        run_inner(one, synthetic(outcome="FAIL"))
        run_inner(two, synthetic())
        self.assertEqual(one.records(), [self.row(status="FAIL")])
        self.assertEqual(two.records(), [self.row(attempt=2)])
        self.assertIsNot(one.records()[0], two.records()[0])

    def test_unknown_identifier_cannot_return_partial_prior_success(self):
        result = run_inner(self.make(), synthetic())
        run_inner(result, synthetic("unknown"))
        self.invalid_execution(result)
        self.invalid_execution(result)

    def test_unknown_identifier_in_each_callback_latches(self):
        for callback in ("startTest", "addSuccess", "addSkip", "addFailure", "addError", "stopTest"):
            result = self.make()
            args = (synthetic("unknown"),)
            if callback == "addSkip":
                args += ("reason",)
            if callback in ("addFailure", "addError"):
                args += (error_info(),)
            getattr(result, callback)(*args)
            self.invalid_execution(result)

    def test_repeated_started_identifier_is_invalid_even_after_complete(self):
        result = self.make()
        run_inner(result, synthetic())
        run_inner(result, synthetic())
        self.invalid_execution(result)

    def test_terminal_without_start_never_raises_recordingerror_in_callback(self):
        for callback in ("addSuccess", "addSkip", "addFailure", "addError"):
            result = self.make()
            args = (synthetic(),)
            if callback == "addSkip":
                args += ("reason",)
            if callback in ("addFailure", "addError"):
                args += (error_info(),)
            getattr(result, callback)(*args)
            self.invalid_execution(result)

    def test_stop_without_start_and_stop_without_outcome_are_invalid(self):
        result = self.make()
        result.stopTest(synthetic())
        self.invalid_execution(result)
        result = self.make()
        result.startTest(synthetic())
        result.stopTest(synthetic())
        self.invalid_execution(result)

    def test_duplicate_terminal_callbacks_latch_permanently(self):
        for second in ("addSuccess", "addSkip", "addFailure", "addError"):
            result = self.make()
            case = synthetic()
            result.startTest(case)
            result.addSuccess(case)
            args = (case,)
            if second == "addSkip":
                args += ("reason",)
            if second in ("addFailure", "addError"):
                args += (error_info(),)
            getattr(result, second)(*args)
            result.stopTest(case)
            self.invalid_execution(result)

    def test_next_start_before_prior_stop_is_invalid(self):
        result = self.make(names=("a", "b"))
        result.startTest(synthetic())
        result.addSuccess(synthetic())
        result.startTest(synthetic("synthetic.b"))
        result.addSuccess(synthetic("synthetic.b"))
        result.stopTest(synthetic("synthetic.b"))
        result.stopTest(synthetic())
        self.invalid_execution(result)

    def test_terminal_or_stop_for_different_active_identifier_is_invalid(self):
        for callback in ("addSuccess", "stopTest"):
            result = self.make(names=("a", "b"))
            result.startTest(synthetic())
            getattr(result, callback)(synthetic("synthetic.b"))
            self.invalid_execution(result)

    def test_terminal_after_stop_and_second_stop_are_invalid(self):
        for callback in ("addSuccess", "stopTest"):
            result = run_inner(self.make(), synthetic())
            getattr(result, callback)(synthetic())
            self.invalid_execution(result)

    def test_snapshot_of_active_test_invalidates_even_after_valid_completion(self):
        for with_terminal in (False, True):
            result = self.make()
            case = synthetic()
            result.startTest(case)
            if with_terminal:
                result.addSuccess(case)
            self.invalid_execution(result)
            if not with_terminal:
                result.addSuccess(case)
            result.stopTest(case)
            self.invalid_execution(result)

    def test_invalid_execution_stays_invalid_after_other_valid_test(self):
        result = self.make(names=("a", "b"))
        result.addSuccess(synthetic())
        run_inner(result, synthetic("synthetic.b"))
        self.invalid_execution(result)

    def test_nonstring_and_unbound_id_return_values_invalidate(self):
        class StrSubclass(str):
            pass

        for value in (None, True, 7, [], {}, "unknown", StrSubclass("synthetic.a")):
            class BadId(unittest.TestCase):
                def id(self):
                    return value

                def runTest(self):
                    pass

            result = self.make()
            run_inner(result, BadId())
            self.invalid_execution(result)

    def test_ordinary_id_exceptions_latch_without_interrupting_cleanup(self):
        cleaned = []

        class BrokenId(unittest.TestCase):
            def id(self):
                raise RuntimeError("SYNTHETIC_PRIVATE_ID_ERROR")

            def runTest(self):
                self.addCleanup(lambda: cleaned.append(True))

        result = self.make()
        run_inner(result, BrokenId())
        self.assertEqual(cleaned, [True])
        self.assertEqual(result.testsRun, 1)
        self.invalid_execution(result)

    def test_fatal_id_exceptions_propagate_from_each_identity_callback(self):
        for kind in (MemoryError, KeyboardInterrupt, SystemExit):
            for callback in ("startTest", "addSuccess", "stopTest"):
                marker = kind("SYNTHETIC_FATAL")

                class FatalId(unittest.TestCase):
                    def id(self):
                        raise marker

                    def runTest(self):
                        pass

                result = self.make()
                with self.assertRaises(kind) as caught:
                    getattr(result, callback)(FatalId())
                self.assertIs(caught.exception, marker)

    def test_subtest_success_failure_and_error_are_all_unsupported(self):
        for outcome in ("SUB_PASS", "SUB_FAIL", "SUB_ERROR"):
            with self.subTest(outcome=outcome):
                result = run_inner(self.make(), synthetic(outcome=outcome))
                self.invalid_execution(result)
                if outcome == "SUB_FAIL":
                    self.assertEqual(len(result.failures), 1)
                if outcome == "SUB_ERROR":
                    self.assertEqual(len(result.errors), 1)

    def test_expected_failure_and_unexpected_success_preserve_parent_diagnostics(self):
        for outcome in ("EXPECTED_FAILURE", "UNEXPECTED_SUCCESS"):
            result = run_inner(self.make(), synthetic(outcome=outcome))
            self.invalid_execution(result)
            if outcome == "EXPECTED_FAILURE":
                self.assertEqual(len(result.expectedFailures), 1)
            else:
                self.assertEqual(len(result.unexpectedSuccesses), 1)
                self.assertFalse(result.wasSuccessful())

    def test_direct_unsupported_callbacks_always_latch(self):
        for callback in ("addSubTest", "addExpectedFailure", "addUnexpectedSuccess"):
            result = self.make()
            case = synthetic()
            if callback == "addSubTest":
                result.addSubTest(case, case, None)
            elif callback == "addExpectedFailure":
                result.addExpectedFailure(case, error_info())
            else:
                result.addUnexpectedSuccess(case)
            self.invalid_execution(result)

    def test_class_setup_error_is_not_a_case_record(self):
        class Broken(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                raise RuntimeError("SYNTHETIC_SETUP_CLASS")

            def test_one(self):
                pass

        case = Broken("test_one")
        result = sut.RecordingResult(release_id="r", bindings=[binding(case.id())])
        run_inner(result, case)
        self.assertEqual(result.testsRun, 0)
        self.assertEqual(len(result.errors), 1)
        self.invalid_execution(result)

    def test_class_teardown_error_invalidates_already_completed_case(self):
        class Broken(unittest.TestCase):
            @classmethod
            def tearDownClass(cls):
                raise RuntimeError("SYNTHETIC_TEARDOWN_CLASS")

            def test_one(self):
                pass

        case = Broken("test_one")
        result = sut.RecordingResult(release_id="r", bindings=[binding(case.id())])
        run_inner(result, case)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(len(result.errors), 1)
        self.invalid_execution(result)

    def test_cleanup_runs_after_unsupported_result(self):
        cleanup = []
        result = run_inner(self.make(), synthetic(outcome="SUB_FAIL", cleanup=lambda: cleanup.append(True)))
        self.assertEqual(cleanup, [True])
        self.invalid_execution(result)

    def test_records_does_not_format_test_or_exception(self):
        calls = []

        class TrackedError(RuntimeError):
            def __str__(self):
                calls.append("exception")
                return "SYNTHETIC_ERROR_ALLOWED_IN_PARENT_DIAGNOSTIC"

        class TrackedCase(unittest.TestCase):
            def id(self):
                return "synthetic.a"

            def __str__(self):
                # Python 3.12's standard addDuration may format the testcase.
                # Only formatting by records() is forbidden by this contract.
                calls.append("test str")
                return "SYNTHETIC_TEST"

            def __repr__(self):
                calls.append("test repr")
                return "SYNTHETIC_TEST"

            def runTest(self):
                raise TrackedError()

        result = run_inner(self.make(), TrackedCase())
        calls.clear()
        records = result.records()
        self.assertEqual(calls, [])
        self.assertEqual(records, [self.row(status="ERROR")])
        self.assertNotIn("SYNTHETIC_ERROR", json.dumps(records))

    def test_parent_implementation_errors_are_not_suppressed(self):
        marker = RuntimeError("SYNTHETIC_PARENT_FAILURE")
        result = self.make()
        case = synthetic()
        result.startTest(case)
        with patch.object(unittest.TestResult, "addSuccess", side_effect=marker):
            with self.assertRaises(RuntimeError) as caught:
                result.addSuccess(case)
        self.assertIs(caught.exception, marker)

    def test_invalid_err_is_left_to_standard_unittest(self):
        result = self.make()
        case = synthetic()
        result.startTest(case)
        with self.assertRaises((TypeError, ValueError, IndexError)):
            result.addFailure(case, None)

    def test_import_and_success_callbacks_without_adapter_side_effects(self):
        source = Path(sut.__file__).read_text(encoding="utf-8")
        compiled = compile(source, "p46_no_effects.py", "exec")
        case = synthetic()

        def forbidden(*args, **kwargs):
            raise AssertionError("adapter I/O/environment/clock/network/process effect")

        with ExitStack() as stack:
            for module, methods in (
                (io, ("open",)),
                (os, ("open", "getenv", "stat", "listdir", "scandir")),
                (socket, ("socket", "create_connection")),
                (subprocess, ("Popen", "run")),
                (time, ("time", "monotonic", "sleep")),
            ):
                for method in methods:
                    stack.enter_context(patch.object(module, method, side_effect=forbidden))
            stack.enter_context(patch("builtins.open", side_effect=forbidden))
            for method in ("open", "read_bytes", "read_text", "write_bytes", "write_text", "stat", "exists", "glob", "rglob", "iterdir"):
                stack.enter_context(patch.object(Path, method, side_effect=forbidden))
            namespace = {"__name__": "p46_effect_check"}
            exec(compiled, namespace)
            result = namespace["RecordingResult"](release_id="r", bindings=[binding()])
            result.startTest(case)
            result.addSuccess(case)
            result.stopTest(case)
            self.assertEqual(result.records(), [self.row(release="r")])
        tree = ast.parse(source)
        forbidden_clock_calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"now", "utcnow", "today"}]
        self.assertEqual(forbidden_clock_calls, [])


if __name__ == "__main__":
    unittest.main()
