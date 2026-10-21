"""Запустить все внешние проверки без пропусков."""
import pathlib,sys,unittest
sys.dont_write_bytecode=True
root=pathlib.Path(__file__).resolve().parent
suite=unittest.defaultTestLoader.discover(str(root/'public'),pattern='test_public.py')
r=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if r.testsRun==16 and r.wasSuccessful() and not r.skipped and not r.expectedFailures else 1)
