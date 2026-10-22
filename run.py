"""Start the independent local storefront: python run.py."""
import argparse
import getpass
import json
import os
import sys

from local_settings import (
    ROOT, SETTINGS_FILE, read_settings, connection_parameters,
)


def configure():
    print('Настройка отдельной PostgreSQL на этом компьютере.')
    print('Установите и запустите PostgreSQL до продолжения.')
    settings = {
        'db_host': input('Адрес [127.0.0.1]: ').strip() or '127.0.0.1',
        'db_port': int(input('Порт [5432]: ').strip() or '5432'),
        'db_name': input('Имя отдельной базы [wildmarket_local]: ').strip() or 'wildmarket_local',
        'db_user': input('Пользователь PostgreSQL [postgres]: ').strip() or 'postgres',
        'db_password': getpass.getpass('Пароль пользователя PostgreSQL: '),
        'db_schema': 'wildmarket',
        'google_oauth_enabled': False,
        'google_client_id': '',
        'google_client_secret': '',
        'google_redirect_uri': 'http://127.0.0.1:8000/auth/google/callback',
        'yandex_maps_api_key': '',
    }
    temporary = SETTINGS_FILE.with_suffix('.json.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(settings, stream, ensure_ascii=False, indent=2)
    os.replace(temporary, SETTINGS_FILE)
    try:
        read_settings()
    except Exception:
        SETTINGS_FILE.unlink()
        raise
    print('Настройки сохранены в settings.json. Не передавайте этот файл другим.')


def initialize_database(settings):
    import psycopg2
    from psycopg2 import sql
    try:
        connection = psycopg2.connect(**connection_parameters(settings))
    except psycopg2.OperationalError as error:
        # Only an absent database permits the creation path; other failures must stop.
        if error.pgcode != '3D000' and 'does not exist' not in str(error):
            raise
        maintenance = psycopg2.connect(**connection_parameters(settings, maintenance=True))
        try:
            maintenance.autocommit = True
            with maintenance.cursor() as cursor:
                cursor.execute(
                    sql.SQL('CREATE DATABASE {}').format(sql.Identifier(settings['db_name']))
                )
        finally:
            maintenance.close()
        connection = psycopg2.connect(**connection_parameters(settings))
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(
                    sql.Identifier(settings.get('db_schema', 'wildmarket'))
                )
            )
    connection.close()
    from app import create_app
    from app.models import db
    app = create_app({'SKIP_SCHEMA_CHECK': True})
    with app.app_context():
        db.create_all()
    print('Схема и таблицы подготовлены. Существующие записи не удалялись.')


def create_admin(app):
    from app.models import db, User
    with app.app_context():
        username = input('Имя нового администратора: ').strip()
        email = input('Email администратора: ').strip().lower()
        if not username or len(username) > 80 or '@' not in email or len(email) > 120:
            raise ValueError('Некорректное имя или email.')
        if User.query.filter(db.or_(User.username == username, User.email == email)).first():
            raise ValueError('Такое имя или email уже заняты. Существующий аккаунт не изменён.')
        password = getpass.getpass('Новый пароль (не менее 12 символов): ')
        if len(password) < 12 or password != getpass.getpass('Повторите пароль: '):
            raise ValueError('Пароль слишком короткий или подтверждение не совпало.')
        user = User(username=username, email=email, role='admin', is_active=True)
        if user.is_demo_account:
            raise ValueError('Укажите свой email, а не адрес образцового аккаунта.')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
    print('Администратор создан. Пароль хранится в базе только в виде хэша.')


def main():
    parser = argparse.ArgumentParser(description='Локальный WildMarket с PostgreSQL')
    parser.add_argument('--configure', action='store_true', help='Настроить подключение')
    parser.add_argument('--init-db', action='store_true', help='Создать отдельную базу и таблицы')
    parser.add_argument('--create-admin', action='store_true', help='Создать администратора')
    parser.add_argument('--fill-catalog', action='store_true', help='Заполнить каталог 24 образцами')
    parser.add_argument('--check', action='store_true', help='Проверить базу без запуска сервера')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        raise ValueError('Некорректный HTTP-порт.')
    first_setup = not SETTINGS_FILE.exists()
    if args.configure or first_setup:
        configure()
        if args.configure:
            return
    settings = read_settings()
    if args.init_db or first_setup:
        initialize_database(settings)
        if args.init_db:
            return
    from app import create_app
    from app.models import User, Product
    app = create_app()
    if args.create_admin:
        create_admin(app)
        return
    if first_setup:
        with app.app_context():
            no_users = User.query.count() == 0
        if no_users:
            create_admin(app)
        if input('Заполнить каталог 24 образцами товаров? [д/н]: ').strip().lower() in ('д', 'да', 'y', 'yes'):
            from catalog_seed import fill_catalog
            fill_catalog(app)
    if args.fill_catalog:
        from catalog_seed import fill_catalog
        fill_catalog(app)
        return
    if args.check:
        with app.app_context():
            count = Product.query.filter_by(is_active=True, is_approved=True).count()
        print(f'Подключение к локальной PostgreSQL исправно. Активных товаров: {count}.')
        return
    print(f'Откройте http://127.0.0.1:{args.port} . Остановка: Ctrl+C.')
    app.run(host='127.0.0.1', port=args.port, debug=False, use_reloader=False)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except ImportError:
        print('Установите зависимости: python -m pip install -r requirements.txt', file=sys.stderr)
        sys.exit(1)
    except (ValueError, RuntimeError, OSError) as error:
        print(f'Ошибка: {error}', file=sys.stderr)
        sys.exit(1)
    except Exception:
        print(
            'Не удалось выполнить операцию. Проверьте запуск PostgreSQL, настройки '
            'settings.json и права пользователя базы. Подробности: README_RU.md.',
            file=sys.stderr,
        )
        sys.exit(1)
