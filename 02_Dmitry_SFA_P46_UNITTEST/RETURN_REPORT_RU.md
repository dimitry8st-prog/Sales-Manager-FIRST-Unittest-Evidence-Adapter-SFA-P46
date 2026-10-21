# Возврат SFA-P46-UNITTEST-ADAPTER R1

COMPONENT_IMPLEMENTED; компонентные проверки PASS; integration_status NOT_CONNECTED; внешняя приёмка PENDING.

Изменён только `source/audit_release/unittest_evidence.py`. Добавлены собственные tests, IMPLEMENTATION_RU.md, RETURN_REPORT_RU.md, raw_logs, OUTPUT_SHA256.json и PATCH.diff. Все 14 protected hashes и остальные оригинальные файлы кроме разрешённого модуля сохранены. Исходные/возвращённые хеши — raw_logs/SOURCE_INTEGRITY.json; полный состав возвращённых байтов — OUTPUT_SHA256.json.

Фактически: **16 публичных + 49 собственных = 65 внешних тестовых методов**, 0 пропусков/expectedFailure внешних suites; все три обязательные команды exit 0. Внутренние намеренные ошибки/провалы/пропуски являются проверяемыми данными, не выдаются за дефекты или пропуски внешнего набора. Подсчёт не включает subTest как отдельные методы.

```bash
python -B CHECK_PACKAGE.py
python -B RUN_PUBLIC_TESTS.py
python -B RUN_CANDIDATE_TESTS.py
```

Реальные interpreter/cwd/argv/exit/stdout/stderr, хеши логов, версия Python/платформа и import origins — raw_logs/COMMANDS.json и соответствующие сырые .log. Карта требований и фактических cases — raw_logs/TRACEABILITY.json, полный inventory — raw_logs/TEST_INVENTORY.json. CHECK_PACKAGE проверяет входы, а не принимает реализацию; PASS реализации подтверждён public и собственным gates.

PATCH.diff содержит только изменённый модуль и собственные tests, применяется из корня исходного пакета. Реальные git apply --check / git apply и побайтная сверка восстановленных файлов — raw_logs/PATCH_VERIFICATION.json. Документы/логи/manifest передаются полными файлами и не включены в patch scope.

OUTPUT_SHA256.json охватывает все файлы возврата **кроме самого OUTPUT_SHA256.json**; это явное исключение устраняет самоссылку. SHA-256 самого ZIP находится в соседнем внешнем протоколе, не внутри ZIP. Окончательный ZIP после заморозки проверяется повторно в чистой папке с отдельными логами, привязанными к его SHA-256.

Не выполнены: установка, PostgreSQL, production/connected runtime, принятая F1-27 интеграция, P23 runner, полномочия исполнения и решение о выпуске — NOT_RUN. Адаптер не авторизует внешние действия. План неактивной установки/отката и условия источников изложены в IMPLEMENTATION_RU.md. Ошибки произвольного некорректного err остаются ответственностью стандартного unittest; неподдержанные subtests/expected outcomes/class fixture errors дают INVALID_EXECUTION. Другие платформы/версии вне фактических команд не заявляются проверенными.
