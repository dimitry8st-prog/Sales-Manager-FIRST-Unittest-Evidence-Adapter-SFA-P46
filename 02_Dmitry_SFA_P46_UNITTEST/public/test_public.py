"""Внешние проверки адаптера. Вложенные искусственные ошибки тестируются намеренно."""
import copy,importlib.util,json,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('p46_sut',ROOT/'source/audit_release/unittest_evidence.py')
sut=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(sut)
def binding(name): return {'test_id':'fake.'+name,'suite_id':'unit','case_id':name}
def case(name,kind='success'):
    class Artificial(unittest.TestCase):
        def id(self): return 'fake.'+name
        def runTest(self):
            if kind=='fail': self.fail('искусственный провал')
            if kind=='error': raise RuntimeError('искусственная ошибка')
            if kind=='skip': self.skipTest('искусственный пропуск')
            if kind=='sub':
                with self.subTest(value=1): self.assertTrue(True)
    if kind=='expected':
        Artificial.runTest=unittest.expectedFailure(lambda self:self.fail('ожидаемая ошибка'))
    if kind=='unexpected':
        Artificial.runTest=unittest.expectedFailure(lambda self:None)
    return Artificial()
def result(names,attempt=1):
    return sut.RecordingResult(release_id='release-1',bindings=[binding(n) for n in names],attempt=attempt)
def run_cases(r,*cs): unittest.TestSuite(cs).run(r);return r
class PublicTests(unittest.TestCase):
    def invalid_execution(self,r):
        with self.assertRaises(sut.RecordingError) as c:r.records()
        self.assertEqual(c.exception.code,'INVALID_EXECUTION');self.assertEqual(str(c.exception),'INVALID_EXECUTION')
    def test_empty(self):
        r=result([]);self.assertIsInstance(r,unittest.TestResult);self.assertEqual(r.records(),[])
    def test_actual_success(self):
        r=run_cases(result(['a']),case('a'))
        self.assertEqual(r.records(),[{'release_id':'release-1','suite_id':'unit','case_id':'a','attempt':1,'status':'PASS','exit_code':0,'skip_count':0}]);self.assertEqual(r.testsRun,1)
    def test_all_actual_outcomes(self):
        r=result(['success','failure','error','skip'],2)
        run_cases(r,case('success'),case('failure','fail'),case('error','error'),case('skip','skip'))
        expected=json.loads((ROOT/'fixtures/outcomes.json').read_text(encoding='utf-8'))
        self.assertEqual(r.records(),expected);self.assertEqual((r.testsRun,len(r.failures),len(r.errors),len(r.skipped)),(4,1,1,1))
    def test_configuration_invalid(self):
        samples=[dict(release_id=True,bindings=[]),dict(release_id='bad id',bindings=[]),dict(release_id='ok',bindings=()),dict(release_id='ok',bindings=[],attempt=True),dict(release_id='ok',bindings=[],attempt=0),dict(release_id='ok',bindings=[binding('a'),binding('a')]),dict(release_id='ok',bindings=[dict(binding('a'),extra=1)]),dict(release_id='ok',bindings=[{'test_id':'x y','suite_id':'a','case_id':'b'}])]
        for kw in samples:
            with self.subTest(kw=kw):
                with self.assertRaises(sut.RecordingError) as c:sut.RecordingResult(**kw)
                self.assertEqual(c.exception.code,'INVALID_CONFIGURATION');self.assertEqual(str(c.exception),'INVALID_CONFIGURATION')
    def test_exact_types(self):
        class L(list):pass
        with self.assertRaises(sut.RecordingError):sut.RecordingResult(release_id='r',bindings=L())
        b=binding('b');b['case_id']=True
        with self.assertRaises(sut.RecordingError):sut.RecordingResult(release_id='r',bindings=[b])
    def test_unknown(self):
        self.invalid_execution(run_cases(result(['a']),case('unknown')))
    def test_repeated_execution(self):
        r=result(['a']);run_cases(r,case('a'),case('a'));self.invalid_execution(r)
    def test_missing_start_or_terminal(self):
        r=result(['a']);r.addSuccess(case('a'));self.invalid_execution(r)
        r=result(['a']);c=case('a');r.startTest(c);r.stopTest(c);self.invalid_execution(r)
    def test_active_snapshot_latches(self):
        r=result(['a']);c=case('a');r.startTest(c);self.invalid_execution(r);r.addSuccess(c);r.stopTest(c);self.invalid_execution(r)
    def test_subtest_success_is_unsupported(self):
        self.invalid_execution(run_cases(result(['a']),case('a','sub')))
    def test_expected_and_unexpected_are_unsupported(self):
        for outcome in ['expected','unexpected']:
            self.invalid_execution(run_cases(result(['a']),case('a',outcome)))
    def test_failfast_omits_notrun(self):
        r=result(['a','b']);r.failfast=True;run_cases(r,case('a','fail'),case('b'))
        self.assertTrue(r.shouldStop);self.assertEqual(r.testsRun,1);self.assertEqual([(x['case_id'],x['status']) for x in r.records()],[('a','FAIL')])
    def test_mutation_and_snapshot_independence(self):
        b=[binding('b'),binding('a')];before=copy.deepcopy(b);r=sut.RecordingResult(release_id='r',bindings=b)
        b[0]['case_id']='changed';run_cases(r,case('b'),case('a'));a=r.records();c=r.records();a[0]['status']='changed';a.append({})
        self.assertEqual([x['case_id'] for x in c],['a','b']);self.assertEqual(r.records(),c);self.assertEqual(before,[binding('b'),binding('a')])
    def test_sequential_snapshots_and_attempts(self):
        r=result(['a','b'],7);run_cases(r,case('a'));first=r.records();run_cases(r,case('b'));self.assertEqual(len(first),1);self.assertEqual(len(r.records()),2);self.assertTrue(all(x['attempt']==7 for x in r.records()))
    def test_setup_class_error_is_not_case_pass(self):
        class Broken(unittest.TestCase):
            @classmethod
            def setUpClass(cls):raise RuntimeError('искусственная ошибка setup')
            def test_a(self):pass
        c=Broken('test_a');r=sut.RecordingResult(release_id='r',bindings=[{'test_id':c.id(),'suite_id':'s','case_id':'c'}]);run_cases(r,c);self.invalid_execution(r)
    def test_duplicate_terminal_and_bad_order(self):
        r=result(['a']);c=case('a');r.startTest(c);r.addSuccess(c);r.addSuccess(c);r.stopTest(c);self.invalid_execution(r)
        r=result(['a','b']);r.startTest(case('a'));r.startTest(case('b'));self.invalid_execution(r)
if __name__=='__main__':unittest.main(verbosity=2)
