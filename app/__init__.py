import os
from flask import Flask, jsonify, redirect, request
from flask_login import LoginManager
from flask_wtf.csrf import CSRFError, CSRFProtect
from sqlalchemy import event, inspect
from datetime import datetime, timezone
from .models import db, User, DemoPickupPoint
from .config import Config
from .oauth import init_oauth, oauth


login_manager = LoginManager()
# Proxy hops and mobile networks can change the observed address between requests.
# Basic protection marks such sessions non-fresh without silently signing users out.
login_manager.session_protection = 'basic'
csrf = CSRFProtect()


def _check_schema_readiness(app):
    """Required commerce tables fail closed; optional PVZ editing is isolated.

    No DDL or writes. A pending additive PVZ migration must not take the
    catalogue, authentication and checkout offline.
    """
    inspector = inspect(db.engine)
    for table in db.metadata.sorted_tables:
        exists = inspector.has_table(table.name)
        present = (
            {column['name'] for column in inspector.get_columns(table.name)}
            if exists else set()
        )
        ready = exists and set(table.c.keys()).issubset(present)
        if table is DemoPickupPoint.__table__:
            app.config['PICKUP_ADMIN_SCHEMA_READY'] = ready
            if not ready:
                app.logger.warning(
                    'Pickup point editing is unavailable pending schema publication; '
                    'the built-in demonstration catalogue remains active.'
                )
            continue
        if not exists:
            raise RuntimeError(
                f'Required database table is missing: {table.name}. '
                'Initialize the local database with python run.py --init-db.'
            )
        if not ready:
            raise RuntimeError(
                f'Required database table is outdated: {table.name}; '
                'Use a separate initialized local database.'
            )


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)
    if not app.config.get('SECRET_KEY'):
        raise RuntimeError('SESSION_SECRET must be configured outside development.')
    if (
        app.config.get('ENVIRONMENT') in ('production', 'staging')
        and app.config.get('SQLALCHEMY_DATABASE_URI', '').lower().startswith('sqlite')
    ):
        raise RuntimeError(
            'Production requires a persistent external database; SQLite is only for local development.'
        )


    db.init_app(app)
    with app.app_context():
        if db.engine.dialect.name == 'sqlite':
            @event.listens_for(db.engine, 'connect')
            def enable_sqlite_foreign_keys(connection, _record):
                cursor = connection.cursor()
                cursor.execute('PRAGMA foreign_keys=ON')
                cursor.close()
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите в аккаунт'
    login_manager.login_message_category = 'warning'

    init_oauth(app)

    from .routes.main import main_bp
    from .routes.auth import auth_bp
    from .routes.products import products_bp
    from .routes.cart import cart_bp
    from .routes.account import account_bp
    from .routes.seller import seller_bp
    from .routes.admin import admin_bp
    from .routes.admin_pickup import admin_pickup_bp
    from .routes.delivery import delivery_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(products_bp)
    app.register_blueprint(cart_bp, url_prefix='/cart')
    app.register_blueprint(account_bp, url_prefix='/account')
    app.register_blueprint(seller_bp, url_prefix='/seller')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(admin_pickup_bp, url_prefix='/admin/pickup-points')
    app.register_blueprint(delivery_bp)

    if not app.config.get('SKIP_SCHEMA_CHECK', False):
        with app.app_context():
            _check_schema_readiness(app)

    if app.config.get('ENVIRONMENT') == 'production':
        # Preserve imported demo records, but never publish usable demo logins.
        from .services.account_safety import assert_safe_production_accounts
        with app.app_context():
            assert_safe_production_accounts()

    # Передаём флаг Google OAuth во все шаблоны
    @app.context_processor
    def inject_google_oauth():
        from .services.demo_pickup import supported_cities
        from .services.pickup_delivery_price import pickup_delivery_settings
        return {
            'demo_pickup_cities': supported_cities,
            'google_oauth_enabled': bool(
                app.config.get('GOOGLE_OAUTH_ENABLED')
                and app.config.get('GOOGLE_CLIENT_ID') and app.config.get('GOOGLE_CLIENT_SECRET')
            ),
            'delivery_demo_mode': app.config.get('DELIVERY_DEMO_MODE', False),
            'pickup_delivery_pricing': pickup_delivery_settings(),
            'yandex_maps_api_key': app.config.get('YANDEX_MAPS_API_KEY', ''),
            'app_base_path': request.script_root.rstrip('/'),
            'current_year': datetime.now(timezone.utc).year,
        }

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'geolocation=(self)')
        if request.is_secure and app.config.get('ENVIRONMENT') == 'production':
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        return response

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': 'Форма устарела. Обновите страницу и повторите действие.'}), 400
        return 'Форма устарела или недействительна. Обновите страницу и повторите действие.', 400

    return app


@login_manager.user_loader
def load_user(user_id):
    try:
        user = db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
    return user if user and user.is_active else None
