# Промпт для Cursor — SFA-P46-UNITTEST-ADAPTER R1

Работай в https://github.com/dimitry8st-prog/Sales-Manager-FIRST-Unittest-Evidence-Adapter-SFA-P46 . Пакет задания — `02_Dmitry_SFA_P46_UNITTEST/`. Сначала прочитай CONTRACT_RU.md, TESTING_RU.md, RETURN_RU.md, INTEGRATION_RU.md, README_RU.md и reference/F127_CONTRACT_RU.md. Проверь актуальный код и ветку: не перезаписывай уже выполненную реализацию или чужие изменения. Нормативный источник — выданный контракт.

Реализуй законченный компонент `audit_release.unittest_evidence`: RecordingError(ValueError), RecordingResult(unittest.TestResult), keyword-only конструктор release_id/bindings/attempt=1 и records(). Менять внутри задания можно только source/audit_release/unittest_evidence.py; добавлять tests/**, IMPLEMENTATION_RU.md, RETURN_REPORT_RU.md, raw_logs/**, OUTPUT_SHA256.json и PATCH.diff. Остальные исходники и manifests сохраняются побайтно. Python 3.12, стандартная библиотека.

Конструктор строго проверяет exact builtin типы, ASCII release/suite/case ID, test_id с отдельными Unicode-правилами/длиной 1..512, attempt exact int>=1, bindings exact list 0..10000, exactdict с тремя plainstr ключами, уникальность test_id и пары suite/case. Не исполняй пользовательские hooks при проверке типов. Копируй конфигурацию без удержания изменяемых caller-контейнеров. Ошибка — INVALID_CONFIGURATION.

Реальные стандартные callbacks формируют один последовательный цикл startTest → ровно один поддержанный исход → stopTest по идентификатору test.id(), а не object identity. Одновременно один активный ID; повтор/неизвестный ID/неверный порядок/несколько исходов/активный records() навсегда делают объект недействительным. Не поднимай RecordingError из ошибочных callbacks: стандартное завершение и cleanup должны закончиться. После нарушения records всегда INVALID_EXECUTION без частичных результатов.

addSuccess→PASS/0/0; addFailure→FAIL/1/0; addError→ERROR/1/0; addSkip→SKIP/0/1. Это нормализованный код случая, не реальный процессный exit code. Сохрани стандартные fields/TestResult behaviors/failfast/stop обязательными super-вызовами, включая неподдержанные callbacks. Любые addSubTest, даже успешные, addExpectedFailure и addUnexpectedSuccess ставят invalid latch. Ошибки setUpClass/tearDownClass не превращаются в случайный PASS. Неполученные события и неисполненные после failfast привязки не дают записей.

Перехватывай обычный Exception только от test.id(), фиксируя недействительность. MemoryError (он подкласс Exception!), KeyboardInterrupt, SystemExit и неожиданные собственные/родительские ошибки не подавляй. Не форматируй test/исключение ради records. Стандартное форматирование диагностики unittest через super и linecache разрешено контрактом; не вводи ложный запрет этого поведения.

records выдаёт fresh list/freshdict, ровно семь полей release_id/suite_id/case_id/attempt/status/exit_code/skip_count, сортировку по suite/case, только полностью завершённые случаи. Пустой прогон [], snapshot не sealing, следующие ещё не начатые ID допустимы; новая попытка — новый экземпляр с явным attempt. Нет собственного IO/env/часов/сети/процессов/БД/случайности или глобального хранения входов. Сам адаптер тесты не запускает и stdout не парсит; не создаёт доверенность или релизную сводку.

Собственные meaningful tests должны использовать настоящий unittest и вложенные искусственные TestCase, покрыть все обязательные условия контракта. Намеренные FAIL/ERROR/SKIP внутри искусственных наборов — входные данные внешнего теста: внешний тест обязан проверить точные записи/коды и пройти. Во внешнем public/candidate suite пропуски, expectedFailure и нулевой прогон не PASS.

Обязательные команды из корня пакета:

```bash
python -B CHECK_PACKAGE.py
python -B RUN_PUBLIC_TESTS.py
python -B RUN_CANDIDATE_TESTS.py
```

CHECK_PACKAGE подтверждает исходные входы, а не реализацию. До реализации public ожидаемо падает с IMPLEMENTATION_REQUIRED; не выдавай этот запуск за PASS. После реализации все16public и все собственные тесты должны реально пройти. Сохрани реальную версию/interpreter/cwd/argv/stdout/stderr/exit codes/importorigins; не создавай фиктивные логи.

Документы должны объяснить цикл, необратимый отказ, mapping, сохранённое поведение super, per-case/process exit distinction, исходные/выходные хеши, ограничения и предложение неактивной установки/отката. Сохрани PATCH.diff, проверь применение к оригиналу и совпадение продукта/тестов; OUTPUT_SHA256 охватывает возвращённые файлы кроме самого себя с явным описанием исключения. Machine-readable evidence можно добавлять только под raw_logs/.

Верни один `02_Dmitry_SFA_P46_UNITTEST_RETURN.zip` с единственным корнем `02_Dmitry_SFA_P46_UNITTEST_RETURN/`, полным исходным пакетом и разрешёнными добавлениями. Корневые служебные документы репозитория/исходный ZIP/кэши/окружения/реальные данные в сдачу не входят.

Проверь дважды: первый раз контракт/diff/всеgates/патч/хеши; второй раз окончательный ZIP в новой чистой папке с повторением всехgates и importorigins. Внешний протокол второго контроля привяжи к SHA-256 неизменного ZIP. Не объявляй INTEGRATED/ENABLED/productionaccepted: принятие F1-27 не требуется для разработки, но рабочее подключение принятой точной версии/плана/bindings/provenance и installation/rollback остаётся интегратору. Не реализуй отсутствующий F1-27 или P23.

После двух успешных проверок сохрани код, тесты, README, evidence и один актуальный ZIP на GitHub с сохранением истории и чужих изменений, без force push. Укажи commit, SHA-256, фактические количества тестов и ограничения. При блокере дай точную причину; protectedфайлы не исправляй самостоятельно.
