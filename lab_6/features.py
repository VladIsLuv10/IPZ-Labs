"""HookMe lab 4: customers, discounts and order history."""
import sqlite3
from database import get_connection
from werkzeug.security import generate_password_hash, check_password_hash


def init_features():
    with get_connection() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, phone TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            address TEXT NOT NULL DEFAULT '', password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
        db.execute('''CREATE TABLE IF NOT EXISTS promo_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE COLLATE NOCASE,
            discount INTEGER NOT NULL CHECK(discount BETWEEN 1 AND 90),
            active INTEGER NOT NULL DEFAULT 1)''')
        cols = {row['name'] for row in db.execute('PRAGMA table_info(orders)')}
        for name, definition in [('customer_id', 'INTEGER REFERENCES customers(id) ON DELETE SET NULL'),
                                 ('subtotal', 'INTEGER'), ('discount', 'INTEGER NOT NULL DEFAULT 0'),
                                 ('promo_code', 'TEXT')]:
            if name not in cols:
                db.execute(f'ALTER TABLE orders ADD COLUMN {name} {definition}')


def register_customer(name, email, password):
    with get_connection() as db:
        cursor = db.execute('INSERT INTO customers (name, email, password_hash) VALUES (?, ?, ?)',
                            (name, email, generate_password_hash(password)))
        return cursor.lastrowid


def authenticate_customer(email, password):
    with get_connection() as db:
        row = db.execute('SELECT * FROM customers WHERE email = ? COLLATE NOCASE', (email,)).fetchone()
        return dict(row) if row and check_password_hash(row['password_hash'], password) else None


def get_customer(customer_id):
    with get_connection() as db:
        row = db.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
        return dict(row) if row else None


def get_customers():
    with get_connection() as db:
        return [dict(r) for r in db.execute('SELECT * FROM customers ORDER BY id DESC')]


def edit_customer(customer_id, name, phone, address):
    with get_connection() as db:
        return db.execute('UPDATE customers SET name=?, phone=?, address=? WHERE id=?',
                          (name, phone, address, customer_id)).rowcount > 0


def remove_customer(customer_id):
    with get_connection() as db:
        return db.execute('DELETE FROM customers WHERE id=?', (customer_id,)).rowcount > 0


def get_promos():
    with get_connection() as db:
        return [dict(r) for r in db.execute('SELECT * FROM promo_codes ORDER BY id DESC')]


def add_promo(code, discount):
    with get_connection() as db:
        db.execute('INSERT INTO promo_codes (code, discount) VALUES (?, ?)', (code, discount))


def remove_promo(promo_id):
    with get_connection() as db:
        db.execute('DELETE FROM promo_codes WHERE id=?', (promo_id,))


def promo_discount(code):
    if not code:
        return 0
    with get_connection() as db:
        row = db.execute('SELECT discount FROM promo_codes WHERE code=? COLLATE NOCASE AND active=1',
                         (code,)).fetchone()
        if row is None:
            raise ValueError('Промокод недійсний або неактивний.')
        return row['discount']


def create_customer_order(customer_id, name, phone, email, address, comment, cart, promo_code):
    if not cart:
        raise ValueError('Кошик порожній.')
    with get_connection() as db:
        customer = db.execute('SELECT email FROM customers WHERE id=?', (customer_id,)).fetchone()
        if not customer:
            raise ValueError('Увійдіть до облікового запису.')
        email = customer['email']
        discount = 0
        if promo_code:
            row = db.execute('SELECT discount FROM promo_codes WHERE code=? COLLATE NOCASE AND active=1',
                             (promo_code,)).fetchone()
            if row is None:
                raise ValueError('Промокод недійсний або неактивний.')
            discount = row['discount']
        items, subtotal = [], 0
        for key, raw_quantity in cart.items():
            try:
                product_id, quantity = int(key), int(raw_quantity)
            except (TypeError, ValueError):
                raise ValueError('Некоректні дані кошика.')
            row = db.execute('SELECT * FROM products WHERE id=?', (product_id,)).fetchone()
            if row is None or quantity < 1:
                raise ValueError('У кошику є недоступний товар.')
            subtotal += row['price'] * quantity
            items.append((product_id, row['name'], quantity, row['price']))
        savings = subtotal * discount // 100
        total = subtotal - savings
        cursor = db.execute('''INSERT INTO orders
            (customer_name, phone, email, address, comment, total, customer_id, subtotal, discount, promo_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (name, phone, email, address, comment, total, customer_id, subtotal, savings,
             promo_code.upper() if promo_code else None))
        order_id = cursor.lastrowid
        db.executemany('''INSERT INTO order_items (order_id, product_id, product_name, quantity, price)
                          VALUES (?, ?, ?, ?, ?)''',
                       [(order_id, *item) for item in items])
        db.execute('UPDATE customers SET name=?, phone=?, address=? WHERE id=?',
                   (name, phone, address, customer_id))
        return order_id


def customer_orders(customer_id):
    with get_connection() as db:
        orders = [dict(r) for r in db.execute(
            'SELECT * FROM orders WHERE customer_id=? ORDER BY id DESC', (customer_id,))]
        for order in orders:
            order['items'] = [dict(r) for r in db.execute(
                'SELECT * FROM order_items WHERE order_id=? ORDER BY id', (order['id'],))]
        return orders
