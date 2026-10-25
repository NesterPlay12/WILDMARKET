from ..models import db

DEMO_EMAILS = (
    'admin@wildmarket.ru', 'moder@wildmarket.ru', 'seller1@wildmarket.ru',
    'seller2@wildmarket.ru', 'ivan@example.ru',
)


def assert_safe_production_accounts():
    from ..models import User

    known_demo = db.func.lower(db.func.trim(User.email)).in_(DEMO_EMAILS)
    if User.query.filter(known_demo, User.is_active.is_(True)).first():
        raise RuntimeError(
            'Active demo accounts exist. Secure or deactivate them before production.'
        )
    if not User.query.filter(
        ~known_demo, User.is_active.is_(True), User.role == 'admin',
        db.or_(User.has_local_password.is_(True), db.func.length(User.google_id) > 0),
    ).first():
        raise RuntimeError(
            'An active non-demo administrator is required before production. '
            'Create one with python run.py --create-admin.'
        )

