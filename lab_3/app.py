
from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
from werkzeug.security import check_password_hash
import os

from database import (
    init_db,
    get_all_products,
    get_product,
    create_order,
    get_all_orders,
    get_order_items,
    update_order_status,
    ORDER_STATUSES,
    add_message,
    get_all_messages,
    get_admin,
    mark_message_read
)


# =====================================
# НАЛАШТУВАННЯ FLASK
# =====================================

app = Flask(__name__)

# Для локальної розробки.
# Перед публікацією сайту встанови SECRET_KEY у змінних середовища.
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "hookme-local-development-only"
)

# Створення таблиць, якщо їх ще немає
init_db()


# =====================================
# ПЕРЕВІРКА АВТОРИЗАЦІЇ АДМІНІСТРАТОРА
# =====================================

def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login"))

        return function(*args, **kwargs)

    return wrapper


# =====================================
# ДОПОМІЖНІ ФУНКЦІЇ
# =====================================

def find_product(product_id):
    """Знаходить товар у базі даних за ID."""
    return get_product(product_id)


@app.context_processor
def inject_cart_count():
    """Передає кількість товарів у всі HTML-шаблони."""
    cart_data = session.get("cart", {})

    return {
        "cart_count": sum(cart_data.values())
    }


# =====================================
# ГОЛОВНА СТОРІНКА
# =====================================

@app.route("/")
def home():
    return render_template("home.html")


# =====================================
# КАТАЛОГ ТОВАРІВ
# =====================================

@app.route("/catalog")
def catalog():

    category = request.args.get("category", "")
    search = request.args.get("search", "").strip()
    sort = request.args.get("sort", "")

    filtered = get_all_products()

    # Фільтрація за категорією
    if category:
        filtered = [
            product
            for product in filtered
            if product["category"] == category
        ]

    # Пошук за назвою
    if search:
        filtered = [
            product
            for product in filtered
            if search.casefold() in product["name"].casefold()
        ]

    # Сортування за ціною
    if sort == "price_asc":
        filtered.sort(
            key=lambda product: product["price"]
        )

    elif sort == "price_desc":
        filtered.sort(
            key=lambda product: product["price"],
            reverse=True
        )

    categories = [
        "Вудилища",
        "Котушки",
        "Приманки",
        "Гачки",
        "Аксесуари"
    ]

    return render_template(
        "catalog.html",
        products=filtered,
        categories=categories,
        selected_category=category,
        search=search,
        sort=sort
    )


# =====================================
# ДОДАВАННЯ ТОВАРУ В КОШИК
# =====================================

@app.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):

    product = find_product(product_id)

    if product is None:
        return redirect(url_for("catalog"))

    cart_data = session.get("cart", {})
    product_key = str(product_id)

    cart_data[product_key] = (
        cart_data.get(product_key, 0) + 1
    )

    session["cart"] = cart_data
    session.modified = True

    return redirect(url_for("catalog"))


# =====================================
# СТОРІНКА КОШИКА
# =====================================

@app.route("/cart")
def cart():

    cart_data = session.get("cart", {})

    cart_items = []
    total = 0

    for product_id, quantity in cart_data.items():

        product = find_product(int(product_id))

        if product is None:
            continue

        subtotal = product["price"] * quantity

        total += subtotal

        cart_items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal
        })

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total=total
    )


# =====================================
# ЗМІНА КІЛЬКОСТІ ТОВАРУ
# =====================================

@app.route("/cart/update/<int:product_id>", methods=["POST"])
def update_cart(product_id):

    cart_data = session.get("cart", {})
    product_key = str(product_id)

    if product_key in cart_data:

        action = request.form.get("action")

        if action == "increase":
            cart_data[product_key] += 1

        elif action == "decrease":
            cart_data[product_key] -= 1

            if cart_data[product_key] <= 0:
                del cart_data[product_key]

        session["cart"] = cart_data
        session.modified = True

    return redirect(url_for("cart"))


# =====================================
# ВИДАЛЕННЯ ТОВАРУ З КОШИКА
# =====================================

@app.route("/cart/remove/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):

    cart_data = session.get("cart", {})

    cart_data.pop(str(product_id), None)

    session["cart"] = cart_data
    session.modified = True

    return redirect(url_for("cart"))


# =====================================
# ОЧИЩЕННЯ КОШИКА
# =====================================

@app.route("/cart/clear", methods=["POST"])
def clear_cart():

    session.pop("cart", None)

    return redirect(url_for("cart"))


# =====================================
# ОФОРМЛЕННЯ ЗАМОВЛЕННЯ
# =====================================

@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    cart_data = session.get("cart", {})

    if not cart_data:
        return redirect(url_for("cart"))

    error = None

    if request.method == "POST":

        name = request.form.get(
            "customer_name", ""
        ).strip()

        phone = request.form.get(
            "phone", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip()

        address = request.form.get(
            "address", ""
        ).strip()

        comment = request.form.get(
            "comment", ""
        ).strip()

        # Перевірка обов'язкових полів
        if not name or not phone or not address:
            error = "Заповніть ім'я, телефон та адресу."

        # Перевірка довжини полів
        elif (
            len(name) > 100
            or len(phone) > 30
            or len(email) > 254
            or len(address) > 300
            or len(comment) > 1000
        ):
            error = "Одне з полів перевищує допустиму довжину."

        else:
            try:
                order_id = create_order(
                    name,
                    phone,
                    email,
                    address,
                    comment,
                    cart_data
                )

            except (ValueError, TypeError):
                error = (
                    "Не вдалося оформити замовлення. "
                    "Перевірте кошик."
                )

            else:
                # Очищення кошика після замовлення
                session.pop("cart", None)
                session.modified = True

                return redirect(
                    url_for(
                        "order_success",
                        order_id=order_id
                    )
                )

    return render_template(
        "checkout.html",
        error=error
    )


# =====================================
# УСПІШНЕ ЗАМОВЛЕННЯ
# =====================================

@app.route("/order/success/<int:order_id>")
def order_success(order_id):

    return render_template(
        "order_success.html",
        order_id=order_id
    )


# =====================================
# СТОРІНКА ПРО НАС
# =====================================

@app.route("/about")
def about():

    return render_template("about.html")


# =====================================
# КОНТАКТИ
# =====================================

@app.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        name = request.form.get(
            "name", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip()

        message = request.form.get(
            "message", ""
        ).strip()

        if not name or not email or not message:
            return render_template(
                "contact.html",
                error="Будь ласка, заповніть усі поля."
            )

        if (
            len(name) > 100
            or len(email) > 254
            or len(message) > 5000
        ):
            return render_template(
                "contact.html",
                error="Перевищено допустиму довжину повідомлення."
            )

        add_message(name, email, message)

        return redirect(
            url_for("contact", sent=1)
        )

    return render_template(
        "contact.html",
        success=request.args.get("sent") == "1"
    )


# =====================================
# ВХІД АДМІНІСТРАТОРА
# =====================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if session.get("admin_id"):
        return redirect(url_for("admin"))

    error = None

    if request.method == "POST":

        username = request.form.get(
            "username", ""
        ).strip()

        password = request.form.get(
            "password", ""
        )

        administrator = get_admin(username)

        if administrator and check_password_hash(
            administrator["password_hash"],
            password
        ):

            session.clear()

            session["admin_id"] = administrator["id"]
            session["admin_username"] = administrator["username"]

            return redirect(url_for("admin"))

        error = "Неправильний логін або пароль."

    return render_template(
        "admin_login.html",
        error=error
    )


# =====================================
# АДМІН-ПАНЕЛЬ
# =====================================

@app.route("/admin")
@admin_required
def admin():

    # Повідомлення клієнтів
    messages = get_all_messages()

    unread_count = sum(
        1 for message in messages
        if message["is_read"] == 0
    )

    # Замовлення клієнтів
    orders = get_all_orders()

    # Товари в кожному замовленні
    for order in orders:
        order["items"] = get_order_items(order["id"])

    return render_template(
        "admin.html",
        messages=messages,
        unread_count=unread_count,
        orders=orders,
        order_statuses=ORDER_STATUSES
    )


# =====================================
# ПОЗНАЧИТИ ПОВІДОМЛЕННЯ ПРОЧИТАНИМ
# =====================================

@app.route(
    "/admin/messages/<int:message_id>/read",
    methods=["POST"]
)
@admin_required
def admin_mark_read(message_id):

    mark_message_read(message_id)

    return redirect(url_for("admin"))


# =====================================
# ЗМІНА СТАТУСУ ЗАМОВЛЕННЯ
# =====================================

@app.route(
    "/admin/orders/<int:order_id>/status",
    methods=["POST"]
)
@admin_required
def admin_update_order_status(order_id):

    status = request.form.get(
        "status", ""
    )

    if status not in ORDER_STATUSES:
        return redirect(url_for("admin"))

    update_order_status(
        order_id,
        status
    )

    return redirect(url_for("admin"))


# =====================================
# ВИХІД АДМІНІСТРАТОРА
# =====================================

@app.route("/admin/logout", methods=["POST"])
@admin_required
def admin_logout():

    session.clear()

    return redirect(url_for("admin_login"))


# =====================================
# ЗАПУСК FLASK
# =====================================

if __name__ == "__main__":
    app.run(
        debug=True,
        port=5001
    )
