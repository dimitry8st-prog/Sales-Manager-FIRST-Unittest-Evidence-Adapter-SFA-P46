"""Проверить защищённые входы. Не является приёмкой реализации."""
import hashlib,json,pathlib,sys
sys.dont_write_bytecode=True
root=pathlib.Path(__file__).resolve().parent
try:
    m=json.loads((root/'PROTECTED_SHA256.json').read_text(encoding='utf-8'))
    bad=[n for n,h in m.items() if not (root/n).is_file() or (root/n).is_symlink() or hashlib.sha256((root/n).read_bytes()).hexdigest()!=h]
    if bad:raise ValueError('защищённые файлы изменены: '+','.join(bad))
    print('Проверка входов успешна: '+str(len(m))+'; реализация не принималась.')
except (OSError,ValueError,TypeError) as e:
    print('Ошибка комплекта: '+str(e));raise SystemExit(1)
