
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "hookme.db"



def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    # Увімкнення перевірки зовнішніх ключів
    connection.execute("PRAGMA foreign_keys = ON")

    return connection



def init_db():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price INTEGER NOT NULL CHECK (price >= 0),
                image TEXT NOT NULL,
                description TEXT NOT NULL
            )
        """)

        count = connection.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]

        if count == 0:
            initial_products = [
                (
                    "Спінінгове вудилище BlackFire",
                    "Вудилища",
                    1850,
                    "rods.jpg",
                    "Легке вудилище для спінінгової риболовлі."
                ),
                (
                    "Безінерційна котушка 2500",
                    "Котушки",
                    1290,
                    "reels.jpg",
                    "Універсальна котушка для спінінга."
                ),
                (
                    "Силіконові приманки Hitomi",
                    "Приманки",
                    145,
                    "lures.jpg",
                    "Силіконові приманки для окуня та щуки."
                ),
                (
                    "Набір офсетних гачків",
                    "Гачки",
                    95,
                    "hooks.jpg",
                    "Гачки для монтажу силіконових приманок."
                ),
                (
                    "Риболовна сумка",
                    "Аксесуари",
                    890,
                    "accessories.jpg",
                    "Зручна сумка для зберігання спорядження."
                ),
                (
                    "Набір воблерів для щуки",
                    "Приманки",
                    420,
                    "lures.jpg",
                    "Воблери для ловлі хижої риби."
                )
            ]

            connection.executemany("""
                INSERT INTO products
                    (name, category, price, image, description)
                VALUES (?, ?, ?, ?, ?)
            """, initial_products)


def get_all_products():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM products ORDER BY id"
        ).fetchall()

        return [dict(row) for row in rows]


def get_product(product_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        return dict(row) if row else None

def add_message(name, email, message):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO messages (name, email, message)
            VALUES (?, ?, ?)
        """, (name, email, message))


def get_all_messages():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT * FROM messages
            ORDER BY created_at DESC, id DESC
        """).fetchall()

        return [dict(row) for row in rows]

def get_admin(username):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM admins WHERE username = ?",
            (username,)
        ).fetchone()

        return dict(row) if row else None


def create_admin(username, password_hash):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO admins (username, password_hash)
            VALUES (?, ?)
            """,
            (username, password_hash)
        )


def mark_message_read(message_id):
    with get_connection() as connection:
        connection.execute(
            "UPDATE messages SET is_read = 1 WHERE id = ?",
            (message_id,)
        )

ORDER_STATUSES = (
    "Нове",
    "Підтверджено",
    "В обробці",
    "Відправлено",
    "Виконано",
    "Скасовано"
)


def create_order(customer_name, phone, email, address, comment, cart):
    if not cart:
        raise ValueError("Кошик порожній.")

    with get_connection() as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        items = []
        total = 0

        for product_id, quantity in cart.items():
            product = connection.execute(
                "SELECT * FROM products WHERE id = ?",
                (int(product_id),)
            ).fetchone()

            quantity = int(quantity)

            if product is None or quantity <= 0:
                raise ValueError("У кошику є недоступний товар.")

            price = product["price"]
            total += price * quantity

            items.append({
                "product_id": product["id"],
                "product_name": product["name"],
                "quantity": quantity,
                "price": price
            })

        cursor = connection.execute("""
            INSERT INTO orders
            (customer_name, phone, email, address, comment, total)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            customer_name,
            phone,
            email,
            address,
            comment,
            total
        ))

        order_id = cursor.lastrowid

        for item in items:
            connection.execute("""
                INSERT INTO order_items
                (order_id, product_id, product_name, quantity, price)
                VALUES (?, ?, ?, ?, ?)
            """, (
                order_id,
                item["product_id"],
                item["product_name"],
                item["quantity"],
                item["price"]
            ))

        return order_id


def get_all_orders():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT * FROM orders
            ORDER BY id DESC
        """).fetchall()

        return [dict(row) for row in rows]


def get_order_items(order_id):
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT * FROM order_items
            WHERE order_id = ?
            ORDER BY id
        """, (order_id,)).fetchall()

        return [dict(row) for row in rows]


def update_order_status(order_id, status):
    if status not in ORDER_STATUSES:
        return False

    with get_connection() as connection:
        cursor = connection.execute("""
            UPDATE orders
            SET status = ?
            WHERE id = ?
        """, (status, order_id))

        return cursor.rowcount > 0
