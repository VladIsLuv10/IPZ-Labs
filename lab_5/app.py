
from flasgger import Swagger
from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
from functools import wraps
from werkzeug.security import check_password_hash
import os
import sqlite3

from api import api

from features import (
    init_features,
    register_customer,
    authenticate_customer,
    get_customer,
    get_customers,
    edit_customer,
    remove_customer,
    get_promos,
    add_promo,
    remove_promo,
    create_customer_order,
    customer_orders
)

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
    mark_message_read,
    add_product,
    update_product,
    delete_product,
    delete_message
)


# =====================================
# НАЛАШТУВАННЯ FLASK
# =====================================

app = Flask(__name__)

# Правильне відображення українських символів у JSON
app.json.ensure_ascii = False

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "hookme-local-development-only"
)

# Ініціалізація бази даних
init_db()
init_features()

# ПІДКЛЮЧЕННЯ REST API
app.register_blueprint(api)

# Документація REST API
app.config["SWAGGER"] = {
    "title": "HookMe REST API",
    "uiversion": 3,
    "specs_route": "/apidocs/"
}

Swagger(app, template_file="swagger.yml")

# =====================================
# АВТОРИЗАЦІЯ АДМІНІСТРАТОРА
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
    return get_product(product_id)


@app.context_processor
def inject_cart_count():
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
# КАТАЛОГ
# =====================================

@app.route("/catalog")
def catalog():

    category = request.args.get("category", "")
    search = request.args.get("search", "").strip()
    sort = request.args.get("sort", "")

    filtered = get_all_products()

    if category:
        filtered = [
            product for product in filtered
            if product["category"] == category
        ]

    if search:
        filtered = [
            product for product in filtered
            if search.casefold() in product["name"].casefold()
        ]

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
# ДОДАТИ ТОВАР У КОШИК
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
# КОШИК
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
# ЗМІНА КІЛЬКОСТІ
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
# ВИДАЛЕННЯ З КОШИКА
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

    if not session.get("customer_id"):
        flash(
            "Для оформлення замовлення увійдіть або зареєструйтеся.",
            "error"
        )
        return redirect(url_for("customer_login"))

    customer = get_customer(session["customer_id"])

    if not customer:
        session.pop("customer_id", None)
        return redirect(url_for("customer_login"))

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

        if not name or not phone or not address:
            error = "Заповніть ім'я, телефон та адресу."

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
                order_id = create_customer_order(
                    customer["id"],
                    name,
                    phone,
                    customer["email"],
                    address,
                    comment,
                    cart_data,
                    request.form.get(
                        "promo_code", ""
                    ).strip()
                )

            except (ValueError, TypeError) as exc:
                error = (
                    str(exc)
                    if isinstance(exc, ValueError)
                    else "Не вдалося оформити замовлення."
                )

            else:
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
        error=error,
        customer=customer
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
# ПРО НАС
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

    messages = get_all_messages()

    unread_count = sum(
        1 for message in messages
        if message["is_read"] == 0
    )

    orders = get_all_orders()

    for order in orders:
        order["items"] = get_order_items(order["id"])

    return render_template(
        "admin.html",
        messages=messages,
        unread_count=unread_count,
        orders=orders,
        order_statuses=ORDER_STATUSES,
        products=get_all_products(),
        customers=get_customers(),
        promos=get_promos()
    )


# =====================================
# ПОВІДОМЛЕННЯ АДМІНІСТРАТОРА
# =====================================

@app.route(
    "/admin/messages/<int:message_id>/read",
    methods=["POST"]
)
@admin_required
def admin_mark_read(message_id):

    mark_message_read(message_id)
    return redirect(url_for("admin"))


@app.route(
    "/admin/messages/<int:message_id>/delete",
    methods=["POST"]
)
@admin_required
def admin_delete_message(message_id):

    delete_message(message_id)
    flash("Повідомлення видалено.", "success")

    return redirect(url_for("admin") + "#messages")


# =====================================
# ЗАМОВЛЕННЯ АДМІНІСТРАТОРА
# =====================================

@app.route(
    "/admin/orders/<int:order_id>/status",
    methods=["POST"]
)
@admin_required
def admin_update_order_status(order_id):

    status = request.form.get("status", "")

    if status not in ORDER_STATUSES:
        return redirect(url_for("admin"))

    update_order_status(order_id, status)

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
# РЕЄСТРАЦІЯ КЛІЄНТА
# =====================================

@app.route("/register", methods=["GET", "POST"])
def customer_register():

    error = None

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if (
            not name
            or len(name) > 100
            or not email
            or len(email) > 254
            or "@" not in email
            or len(password) < 8
        ):
            error = (
                "Вкажіть ім'я, коректний email "
                "та пароль від 8 символів."
            )

        else:
            try:
                session["customer_id"] = register_customer(
                    name,
                    email,
                    password
                )

                return redirect(
                    url_for("customer_account")
                )

            except sqlite3.IntegrityError:
                error = "Такий email уже зареєстрований."

    return render_template(
        "customer_register.html",
        error=error
    )


# =====================================
# ВХІД КЛІЄНТА
# =====================================

@app.route("/login", methods=["GET", "POST"])
def customer_login():

    error = None

    if request.method == "POST":

        customer = authenticate_customer(
            request.form.get("email", "").strip(),
            request.form.get("password", "")
        )

        if customer:

            session["customer_id"] = customer["id"]

            return redirect(
                url_for("checkout")
                if session.get("cart")
                else url_for("customer_account")
            )

        error = "Неправильний email або пароль."

    return render_template(
        "customer_login.html",
        error=error
    )


# =====================================
# ВИХІД КЛІЄНТА
# =====================================

@app.route("/logout", methods=["POST"])
def customer_logout():

    session.pop("customer_id", None)
    return redirect(url_for("home"))


# =====================================
# ОСОБИСТИЙ КАБІНЕТ
# =====================================

@app.route("/account")
def customer_account():

    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("customer_login"))

    customer = get_customer(customer_id)

    if not customer:
        session.pop("customer_id", None)
        return redirect(url_for("customer_login"))

    return render_template(
        "customer_account.html",
        customer=customer,
        orders=customer_orders(customer_id)
    )


# =====================================
# CRUD ТОВАРІВ
# =====================================

CATEGORIES = (
    "Вудилища",
    "Котушки",
    "Приманки",
    "Гачки",
    "Аксесуари"
)


def product_form():

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "")
    image = request.form.get("image", "").strip()
    description = request.form.get("description", "").strip()

    try:
        price = int(request.form.get("price", ""))
    except (ValueError, TypeError):
        return None

    if (
        not name
        or len(name) > 200
        or category not in CATEGORIES
        or price < 0
        or not image
        or len(image) > 255
        or not description
        or len(description) > 3000
    ):
        return None

    return name, category, price, image, description


@app.route("/admin/products/add", methods=["POST"])
@admin_required
def admin_add_product():

    data = product_form()

    if data:
        add_product(*data)
        flash("Товар додано.", "success")
    else:
        flash("Некоректні дані товару.", "error")

    return redirect(url_for("admin") + "#products")


@app.route(
    "/admin/products/<int:product_id>/edit",
    methods=["POST"]
)
@admin_required
def admin_edit_product(product_id):

    data = product_form()

    if data and update_product(product_id, *data):
        flash("Товар оновлено.", "success")
    else:
        flash("Не вдалося оновити товар.", "error")

    return redirect(url_for("admin") + "#products")


@app.route(
    "/admin/products/<int:product_id>/delete",
    methods=["POST"]
)
@admin_required
def admin_delete_product(product_id):

    if delete_product(product_id):
        flash("Товар видалено.", "success")
    else:
        flash(
            "Товар не можна видалити, "
            "якщо він входить до замовлення.",
            "error"
        )

    return redirect(url_for("admin") + "#products")


# =====================================
# КЕРУВАННЯ КЛІЄНТАМИ
# =====================================

@app.route(
    "/admin/customers/<int:customer_id>/edit",
    methods=["POST"]
)
@admin_required
def admin_edit_customer(customer_id):

    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()

    if (
        name
        and len(name) <= 100
        and len(phone) <= 30
        and len(address) <= 300
    ):
        edit_customer(
            customer_id,
            name,
            phone,
            address
        )

        flash("Дані клієнта оновлено.", "success")

    else:
        flash("Перевірте дані клієнта.", "error")

    return redirect(url_for("admin") + "#customers")


@app.route(
    "/admin/customers/<int:customer_id>/delete",
    methods=["POST"]
)
@admin_required
def admin_delete_customer(customer_id):

    remove_customer(customer_id)

    flash(
        "Клієнта видалено. "
        "Замовлення залишилися в базі "
        "без прив'язки до облікового запису.",
        "success"
    )

    return redirect(url_for("admin") + "#customers")


# =====================================
# ПРОМОКОДИ
# =====================================

@app.route("/admin/promos/add", methods=["POST"])
@admin_required
def admin_add_promo():

    code = request.form.get("code", "").strip().upper()

    try:
        discount = int(request.form.get("discount", ""))
    except (ValueError, TypeError):
        discount = 0

    if (
        not code
        or len(code) > 30
        or not code.isascii()
        or not code.replace("-", "").isalnum()
        or not 1 <= discount <= 90
    ):
        flash(
            "Код має містити латинські літери/цифри; "
            "знижка — 1–90%.",
            "error"
        )

    else:
        try:
            add_promo(code, discount)
            flash("Промокод створено.", "success")

        except sqlite3.IntegrityError:
            flash("Такий промокод уже існує.", "error")

    return redirect(url_for("admin") + "#promos")


@app.route(
    "/admin/promos/<int:promo_id>/delete",
    methods=["POST"]
)
@admin_required
def admin_delete_promo(promo_id):

    remove_promo(promo_id)
    flash("Промокод видалено.", "success")

    return redirect(url_for("admin") + "#promos")


# =====================================
# ЗАПУСК СЕРВЕРА
# =====================================

if __name__ == "__main__":
    app.run(
        debug=True,
        port=5001
    )
