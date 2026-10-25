"""Local PostgreSQL settings. No remote connection is selected implicitly."""
import json
import os
import re
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SETTINGS_FILE = ROOT / 'settings.json'


def read_settings():
    if not SETTINGS_FILE.is_file():
        raise RuntimeError('Нет settings.json. Сначала запустите python run.py.')
    try:
        settings = json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
    except (ValueError, OSError) as error:
        raise RuntimeError('Не удалось прочитать settings.json.') from error
    if not isinstance(settings, dict):
        raise RuntimeError('settings.json должен содержать объект настроек.')
    host = settings.get('db_host', '127.0.0.1')
    if host not in ('127.0.0.1', 'localhost', '::1'):
        raise RuntimeError('Эта сборка подключается только к PostgreSQL на этом компьютере.')
    port = settings.get('db_port', 5432)
    if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        raise RuntimeError('db_port должен быть целым числом от 1 до 65535.')
    schema = settings.get('db_schema', 'wildmarket')
    if not isinstance(schema, str) or not re.fullmatch(r'[a-z_][a-z0-9_]*', schema):
        raise RuntimeError('Некорректное имя схемы db_schema.')
    if not isinstance(settings.get('db_name'), str) or not settings['db_name'].strip():
        raise RuntimeError('Укажите имя базы db_name.')
    if settings['db_name'].lower() in ('postgres', 'template0', 'template1'):
        raise RuntimeError('Укажите отдельную базу приложения, не служебную базу PostgreSQL.')
    if not isinstance(settings.get('db_user'), str) or not settings['db_user'].strip():
        raise RuntimeError('Укажите пользователя db_user.')
    if not isinstance(settings.get('db_password', ''), str):
        raise RuntimeError('db_password должен быть строкой.')
    return settings


def connection_parameters(settings, *, maintenance=False):
    return {
        'host': settings.get('db_host', '127.0.0.1'),
        'port': settings.get('db_port', 5432),
        'dbname': 'postgres' if maintenance else settings['db_name'],
        'user': settings['db_user'],
        'password': settings.get('db_password', ''),
        'connect_timeout': 5,
    }


def database_url(settings):
    from sqlalchemy.engine import URL
    return URL.create(
        'postgresql+psycopg2',
        username=settings['db_user'],
        password=settings.get('db_password', ''),
        host=settings.get('db_host', '127.0.0.1'),
        port=settings.get('db_port', 5432),
        database=settings['db_name'],
    )


def session_secret():
    path = ROOT / '.session-key'
    if not path.exists():
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, 'w', encoding='ascii') as stream:
                stream.write(secrets.token_hex(32))
    value = path.read_text(encoding='ascii').strip()
    if len(value) < 32:
        raise RuntimeError('Файл .session-key повреждён. Удалите его при остановленном приложении.')
    return value
