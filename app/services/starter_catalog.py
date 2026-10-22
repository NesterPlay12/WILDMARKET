"""Idempotent, admin-triggered import of the 12 additional storefront products."""
from sqlalchemy import func, text

from ..models import db, Category, Product, User


TARGET_ACTIVE_PRODUCTS = 24
CATALOG_CATEGORIES = (
    ('Аксессуары', 'accessories', '🎒'),
    ('Автотовары', 'auto-goods', '🚗'),
    ('Товары для животных', 'pets', '🐾'),
    ('Творчество', 'creative-goods', '🎨'),
)

CATALOG_PRODUCTS = (
    {
        'sku': 'WM-CAT26-NW-001',
        'name': 'Рюкзак городской 20 л',
        'description': 'Лёгкий городской рюкзак с мягким отделением для ноутбука до 15 дюймов, передним карманом и регулируемыми лямками.',
        'price': 3490,
        'brand': 'UrbanTrail',
        'category_slug': 'accessories',
        'stock': 32,
        'image': 'novinki-backpack.jpg',
        'color_options': 'Тёмно-синий, Чёрный',
        'size_options': '',
    },
    {
        'sku': 'WM-CAT26-NW-002',
        'name': 'Термокружка стальная 450 мл',
        'description': 'Двухслойная стальная кружка с крышкой-защёлкой, нескользящим основанием и удобной формой для ежедневных поездок.',
        'price': 1290,
        'brand': 'NordCup',
        'category_slug': 'accessories',
        'stock': 58,
        'image': 'novinki-thermocup.jpg',
        'color_options': 'Шалфейный, Графитовый',
        'size_options': '',
    },
    {
        'sku': 'WM-CAT26-NW-003',
        'name': 'Кошелёк компактный кожаный',
        'description': 'Компактный кошелёк из натуральной кожи с отделением для купюр, карманом для мелочи и шестью слотами для карт.',
        'price': 1990,
        'brand': 'Ledo',
        'category_slug': 'accessories',
        'stock': 24,
        'image': 'novinki-wallet.jpg',
        'color_options': 'Коричневый, Чёрный',
        'size_options': '',
    },
    {
        'sku': 'WM-CAT26-NW-004',
        'name': 'Видеорегистратор Full HD',
        'description': 'Компактный видеорегистратор с записью Full HD, широкоугольным объективом, экраном для настройки и креплением на стекло.',
        'price': 4990,
        'brand': 'Roadline',
        'category_slug': 'auto-goods',
        'stock': 19,
        'image': 'novinki-dashcam.jpg',
        'color_options': '',
        'size_options': '',
    },
    {
        'sku': 'WM-CAT26-NW-005',
        'name': 'Автомобильный компрессор 12 В',
        'description': 'Портативный компрессор для шин с питанием от разъёма 12 В, аналоговым манометром и набором переходников.',
        'price': 2990,
        'brand': 'Roadline',
        'category_slug': 'auto-goods',
        'stock': 22,
        'image': 'novinki-inflator.jpg',
        'color_options': '',
        'size_options': '',
    },
    {
        'sku': 'WM-CAT26-NW-006',
        'name': 'Магнитный держатель для смартфона в авто',
        'description': 'Поворотный держатель с магнитной площадкой и регулируемым шарниром для установки на приборную панель.',
        'price': 990,
        'brand': 'Roadline',
        'category_slug': 'auto-goods',
        'stock': 64,
        'image': 'novinki-car-mount.jpg',
        'color_options': '',
        'size_options': '',
    },
    {
        'sku': 'WM-CAT26-NW-007',
        'name': 'Когтеточка-столбик с площадкой',
        'description': 'Компактная когтеточка с прочным сизалевым столбиком, устойчивым основанием и верхней площадкой для отдыха.',
        'price': 2290,
        'brand': 'PetHome',
        'category_slug': 'pets',
        'stock': 28,
        'image': 'novinki-cat-scratcher.jpg',
        'color_options': 'Бежевый',
        'size_options': '',
    },
    {
        'sku': 'WM-CAT26-NW-008',
        'name': 'Переноска для кошек с сетчатыми вставками',
        'description': 'Мягкая переноска среднего размера с вентиляционными сетками, усиленными ручками и съёмным плечевым ремнём.',
        'price': 1990,
        'brand': 'PetHome',
        'category_slug': 'pets',
        'stock': 25,
        'image': 'novinki-cat-carrier.jpg',
        'color_options': 'Серый',
        'size_options': '',
    },
    {
        'sku': 'WM-CAT26-NW-009',
        'name': 'Лежанка для собак средняя',
        'description': 'Мягкая овальная лежанка с высокими бортиками и съёмной подушкой для собак среднего размера.',
        'price': 1590,
        'brand': 'PetHome',
        'category_slug': 'pets',
        'stock': 31,
        'image': 'novinki-dog-bed.jpg',
        'color_options': 'Песочный',
        'size_options': 'M',
    },
    {
        'sku': 'WM-CAT26-NW-010',
        'name': 'Акварельные краски, 24 цвета',
        'description': 'Набор акварельных красок в компактной палитре с кистью — для учебных заданий, скетчей и домашних проектов.',
        'price': 690,
        'brand': 'ArtLine',
        'category_slug': 'creative-goods',
        'stock': 70,
        'image': 'novinki-watercolor-set.jpg',
        'color_options': '',
        'size_options': '',
    },
    {
        'sku': 'WM-CAT26-NW-011',
        'name': 'Скетчбук А4 на спирали',
        'description': 'Скетчбук формата А4 с плотной бумагой для карандашей, ручек и лёгких маркерных набросков.',
        'price': 590,
        'brand': 'ArtLine',
        'category_slug': 'creative-goods',
        'stock': 85,
        'image': 'novinki-sketchbook.jpg',
        'color_options': '',
        'size_options': 'A4',
    },
    {
        'sku': 'WM-CAT26-NW-012',
        'name': 'Набор полимерной глины, 12 цветов',
        'description': 'Набор мягкой полимерной глины из 12 базовых цветов с простыми инструментами для лепки небольших поделок.',
        'price': 1290,
        'brand': 'ArtLine',
        'category_slug': 'creative-goods',
        'stock': 43,
        'image': 'novinki-clay-kit.jpg',
        'color_options': '',
        'size_options': '',
    },
)


class StarterCatalogError(ValueError):
    """The existing catalog conflicts with the safe one-time import."""


def catalog_import_status():
    """Describe whether the explicit admin import can still add the starter catalog."""
    sku_list = [item['sku'] for item in CATALOG_PRODUCTS]
    imported_skus = {
        sku for (sku,) in db.session.query(Product.sku)
        .filter(Product.sku.in_(sku_list)).all()
    }
    existing_categories = {
        slug for (slug,) in db.session.query(Category.slug)
        .filter(Category.slug.in_([item[1] for item in CATALOG_CATEGORIES])).all()
    }
    active_count = Product.query.filter_by(is_active=True, is_approved=True).count()
    return {
        'active_products': active_count,
        'imported_products': len(imported_skus),
        'missing_categories': len(CATALOG_CATEGORIES) - len(existing_categories),
        'needs_import': active_count < TARGET_ACTIVE_PRODUCTS
        and (
            len(imported_skus) < len(CATALOG_PRODUCTS)
            or len(existing_categories) < len(CATALOG_CATEGORIES)
        ),
    }


def import_starter_catalog():
    """Add catalog rows in one transaction; safe to retry and never runs at startup."""
    if db.engine.dialect.name == 'postgresql':
        db.session.execute(text('SELECT pg_advisory_xact_lock(740345624)'))

    status = catalog_import_status()
    if not status['needs_import']:
        return {
            'added_products': 0,
            'added_categories': 0,
            'active_products': status['active_products'],
        }

    seller_id = db.session.query(Product.seller_id).filter(
        Product.is_active.is_(True),
        Product.is_approved.is_(True),
    ).order_by(Product.id).limit(1).scalar()
    if seller_id is None:
        seller = User.query.filter_by(role='seller').order_by(User.id).first()
        if seller is None:
            raise StarterCatalogError('Для товаров не найден профиль продавца.')
        seller_id = seller.id

    category_by_slug = {}
    added_categories = 0
    for name, slug, icon in CATALOG_CATEGORIES:
        category = Category.query.filter_by(slug=slug).first()
        if category is not None:
            if category.name != name or category.parent_id is not None:
                raise StarterCatalogError(
                    f'Категория «{slug}» уже существует с другим назначением.'
                )
        else:
            category = Category(name=name, slug=slug, icon=icon)
            db.session.add(category)
            added_categories += 1
        category_by_slug[slug] = category
    db.session.flush()

    sku_list = [item['sku'] for item in CATALOG_PRODUCTS]
    existing_by_sku = {
        product.sku: product for product in Product.query.filter(
            Product.sku.in_(sku_list)
        ).all()
    }
    for item in CATALOG_PRODUCTS:
        existing = existing_by_sku.get(item['sku'])
        if existing and existing.name != item['name']:
            raise StarterCatalogError(
                f'Артикул {item["sku"]} уже занят другим товаром.'
            )
        if not existing:
            same_name = Product.query.filter(
                func.lower(Product.name) == item['name'].lower()
            ).first()
            if same_name:
                raise StarterCatalogError(
                    f'Товар «{item["name"]}» уже есть в каталоге под другим артикулом.'
                )

    slots = max(TARGET_ACTIVE_PRODUCTS - status['active_products'], 0)
    missing_products = [
        item for item in CATALOG_PRODUCTS if item['sku'] not in existing_by_sku
    ][:slots]
    for item in missing_products:
        db.session.add(Product(
            name=item['name'],
            description=item['description'],
            price=item['price'],
            old_price=None,
            brand=item['brand'],
            sku=item['sku'],
            category_id=category_by_slug[item['category_slug']].id,
            seller_id=seller_id,
            stock=item['stock'],
            rating=0,
            review_count=0,
            image_url=f"/static/uploads/products/{item['image']}",
            color_options=item['color_options'],
            size_options=item['size_options'],
            is_active=True,
            is_approved=True,
        ))

    db.session.commit()
    return {
        'added_products': len(missing_products),
        'added_categories': added_categories,
        'active_products': status['active_products'] + len(missing_products),
    }
