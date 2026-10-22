"""Optional example catalog without customer accounts or orders."""
from app.models import db, User, Category, Product
from app.services.starter_catalog import import_starter_catalog
from catalog_data import ROOT_CATEGORIES, CHILD_CATEGORIES, INITIAL_PRODUCTS


def fill_catalog(app):
    with app.app_context():
        if Product.query.count() == 0:
            owner = User.query.filter_by(role='admin', is_active=True).order_by(User.id).first()
            if owner is None:
                raise RuntimeError('Сначала создайте администратора: python run.py --create-admin')
            categories = {}
            for name, slug, icon, _ in ROOT_CATEGORIES:
                category = Category.query.filter_by(slug=slug).first()
                if category is None:
                    category = Category(name=name, slug=slug, icon=icon)
                    db.session.add(category)
                categories[slug] = category
            db.session.flush()
            for name, slug, icon, parent_slug in CHILD_CATEGORIES:
                category = Category.query.filter_by(slug=slug).first()
                if category is None:
                    category = Category(
                        name=name, slug=slug, icon=icon,
                        parent_id=categories[parent_slug].id,
                    )
                    db.session.add(category)
                categories[slug] = category
            db.session.flush()
            for index, row in enumerate(INITIAL_PRODUCTS, 1):
                name, description, price, old_price, brand, slug, _, stock, rating, reviews, image = row
                product = Product(
                    name=name, description=description, price=price, old_price=old_price,
                    brand=brand, category_id=categories[slug].id, seller_id=owner.id,
                    stock=stock, rating=rating, review_count=reviews, image_url=image,
                    sku=f'WM-LOCAL-{index:03}', is_active=True, is_approved=True,
                )
                if slug in ('womens-clothing', 'mens-clothing', 'shoes'):
                    product.color_options = 'Чёрный, Белый, Синий'
                    product.size_options = (
                        '36, 37, 38, 39, 40, 41, 42' if slug == 'shoes' else 'S, M, L, XL'
                    )
                elif slug in ('smartphones', 'laptops'):
                    product.color_options = 'Чёрный, Серебристый'
                db.session.add(product)
            db.session.commit()
        result = import_starter_catalog()
        print(f"Каталог готов. Активных товаров: {result['active_products']}.")
