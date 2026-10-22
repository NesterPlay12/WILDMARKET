from pathlib import Path
from local_settings import read_settings, database_url, session_secret

BASE_DIR = Path(__file__).resolve().parent
SETTINGS = read_settings()


class Config:
    ENVIRONMENT = 'local'
    SECRET_KEY = session_secret()
    SQLALCHEMY_DATABASE_URI = database_url(SETTINGS)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {
            'options': f"-csearch_path={SETTINGS.get('db_schema', 'wildmarket')}",
            'connect_timeout': 5,
        },
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_INIT_SCHEMA = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 14
    UPLOAD_FOLDER = str(BASE_DIR / 'static' / 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    PRODUCTS_PER_PAGE = 20
    WTF_CSRF_TIME_LIMIT = 60 * 60 * 8
    GOOGLE_CLIENT_ID = SETTINGS.get('google_client_id', '')
    GOOGLE_CLIENT_SECRET = SETTINGS.get('google_client_secret', '')
    GOOGLE_REDIRECT_URI = SETTINGS.get(
        'google_redirect_uri', 'http://127.0.0.1:8000/auth/google/callback'
    )
    GOOGLE_OAUTH_ENABLED = bool(
        SETTINGS.get('google_oauth_enabled', False)
        and GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
    )
    DELIVERY_DEMO_MODE = True
    YANDEX_MAPS_API_KEY = SETTINGS.get('yandex_maps_api_key', '')
