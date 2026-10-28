
import json

from flask import Blueprint, Response, request, session

from database import (
    get_all_products,
    get_product,
    add_product,
    update_product,
    delete_product
)


# =====================================
# НАЛАШТУВАННЯ REST API
# =====================================

api = Blueprint("api", __name__)

CATEGORIES = (
    "Вудилища",
    "Котушки",
    "Приманки",
    "Гачки",
    "Аксесуари"
)


# =====================================
# JSON З ПІДТРИМКОЮ УКРАЇНСЬКОЇ МОВИ
# =====================================

def json_response(data, status=200):
    return Response(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        status=status,
        content_type="application/json; charset=utf-8"
    )


# =====================================
# ОБРОБКА ПОМИЛОК
# =====================================

def error_response(message, status=400):
    return json_response({
        "success": False,
        "error": message
    }, status)


# =====================================
# ПЕРЕВІРКА АДМІНІСТРАТОРА
# =====================================

def check_admin():
    return bool(session.get("admin_id"))


# =====================================
# ВАЛІДАЦІЯ ДАНИХ ТОВАРУ
# =====================================

def validate_product(data):

    if not isinstance(data, dict):
        return None, "Потрібно передати JSON-об'єкт."

    required_fields = (
        "name",
        "category",
        "price",
        "image",
        "description"
    )

    for field in required_fields:
        if field not in data:
            return None, f"Відсутнє поле: {field}"

    name = data["name"]
    category = data["category"]
    price = data["price"]
    image = data["image"]
    description = data["description"]

    if not all(
        isinstance(value, str)
        for value in (name, category, image, description)
    ):
        return None, "Текстові поля повинні містити рядки."

    name = name.strip()
    category = category.strip()
    image = image.strip()
    description = description.strip()

    if not name or len(name) > 200:
        return None, "Назва повинна містити від 1 до 200 символів."

    if category not in CATEGORIES:
        return None, "Некоректна категорія товару."

    if type(price) is not int or price < 0:
        return None, "Ціна повинна бути цілим невід'ємним числом."

    if not image or len(image) > 255:
        return None, "Некоректне зображення товару."

    if not description or len(description) > 3000:
        return None, "Опис повинен містити від 1 до 3000 символів."

    return (
        name,
        category,
        price,
        image,
        description
    ), None


# =====================================
# GET /api/v1/products
# ОТРИМАТИ ВСІ ТОВАРИ
# =====================================

@api.route("/api/v1/products", methods=["GET"])
def api_get_products():

    products = get_all_products()

    category = request.args.get("category", "").strip()
    search = request.args.get("search", "").strip()
    sort = request.args.get("sort", "").strip()

    if category:
        products = [
            product for product in products
            if product["category"] == category
        ]

    if search:
        products = [
            product for product in products
            if search.casefold() in product["name"].casefold()
        ]

    if sort == "price_asc":
        products.sort(key=lambda p: p["price"])

    elif sort == "price_desc":
        products.sort(
            key=lambda p: p["price"],
            reverse=True
        )

    return json_response(products, 200)


# =====================================
# GET /api/v1/products/<id>
# ОТРИМАТИ ОДИН ТОВАР
# =====================================

@api.route("/api/v1/products/<int:product_id>", methods=["GET"])
def api_get_product(product_id):

    product = get_product(product_id)

    if product is None:
        return error_response(
            "Товар не знайдено.",
            404
        )

    return json_response(product, 200)


# =====================================
# GET /api/v1/categories
# ОТРИМАТИ ВСІ КАТЕГОРІЇ
# =====================================

@api.route("/api/v1/categories", methods=["GET"])
def api_get_categories():

    return json_response(
        list(CATEGORIES),
        200
    )


# =====================================
# POST /api/v1/products
# СТВОРИТИ НОВИЙ ТОВАР
# =====================================

@api.route("/api/v1/products", methods=["POST"])
def api_create_product():

    if not check_admin():
        return error_response(
            "Потрібна авторизація адміністратора.",
            401
        )

    if not request.is_json:
        return error_response(
            "Очікується JSON.",
            415
        )

    data, error = validate_product(
        request.get_json(silent=True)
    )

    if error:
        return error_response(error, 400)

    add_product(*data)

    return json_response({
        "success": True,
        "message": "Товар успішно додано."
    }, 201)


# =====================================
# PUT /api/v1/products/<id>
# ОНОВИТИ ТОВАР
# =====================================

@api.route("/api/v1/products/<int:product_id>", methods=["PUT"])
def api_update_product(product_id):

    if not check_admin():
        return error_response(
            "Потрібна авторизація адміністратора.",
            401
        )

    product = get_product(product_id)

    if product is None:
        return error_response(
            "Товар не знайдено.",
            404
        )

    if not request.is_json:
        return error_response(
            "Очікується JSON.",
            415
        )

    data, error = validate_product(
        request.get_json(silent=True)
    )

    if error:
        return error_response(error, 400)

    if not update_product(product_id, *data):
        return error_response(
            "Не вдалося оновити товар.",
            500
        )

    return json_response({
        "success": True,
        "message": "Товар успішно оновлено."
    }, 200)


# =====================================
# DELETE /api/v1/products/<id>
# ВИДАЛИТИ ТОВАР
# =====================================

@api.route("/api/v1/products/<int:product_id>", methods=["DELETE"])
def api_delete_product(product_id):

    if not check_admin():
        return error_response(
            "Потрібна авторизація адміністратора.",
            401
        )

    product = get_product(product_id)

    if product is None:
        return error_response(
            "Товар не знайдено.",
            404
        )

    if not delete_product(product_id):
        return error_response(
            "Неможливо видалити товар, який входить до замовлення.",
            409
        )

    return json_response({
        "success": True,
        "message": "Товар успішно видалено."
    }, 200)


# =====================================
# GET /api/v2/products
# ДРУГА ВЕРСІЯ API
# =====================================

@api.route("/api/v2/products", methods=["GET"])
def api_v2_products():

    products = get_all_products()

    return json_response({
        "success": True,
        "version": "2.0",
        "count": len(products),
        "data": products
    }, 200)


# =====================================
# GET /api/v1/test
# ПЕРЕВІРКА РОБОТИ API
# =====================================

@api.route("/api/v1/test", methods=["GET"])
def api_test():

    return json_response({
        "success": True,
        "message": "HookMe REST API працює!",
        "version": "1.0"
    }, 200)
