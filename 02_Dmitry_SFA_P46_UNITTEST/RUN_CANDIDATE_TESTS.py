"""Обязательный полный gate собственных регрессий без ложного успеха."""
import pathlib,sys,unittest
sys.dont_write_bytecode=True
root=pathlib.Path(__file__).resolve().parent
folder=root/'tests'
if not folder.is_dir():
    print('Собственные тесты отсутствуют: tests/test_candidate_*.py');raise SystemExit(1)
suite=unittest.defaultTestLoader.discover(str(folder),pattern='test_candidate_*.py')
r=unittest.TextTestRunner(verbosity=2).run(suite)
valid=r.testsRun>=1 and r.wasSuccessful() and not r.skipped and not r.expectedFailures
print('Собственные проверки: '+str(r.testsRun)+'; пропуски: '+str(len(r.skipped))+'; ожидаемые ошибки: '+str(len(r.expectedFailures)))
raise SystemExit(0 if valid else 1)
