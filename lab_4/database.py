import sqlite3
from pathlib import Path
DB_PATH = Path(__file__).resolve().parent / 'hookme.db'


def get_connection():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db


def init_db():
    with get_connection() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            category TEXT NOT NULL, price INTEGER NOT NULL CHECK(price>=0),
            image TEXT NOT NULL, description TEXT NOT NULL)''')
        # Existing databases retain their records.
        if db.execute('SELECT COUNT(*) FROM products').fetchone()[0] == 0:
            db.executemany('INSERT INTO products (name, category, price, image, description) VALUES (?,?,?,?,?)', [
                ('Спінінгове вудилище BlackFire','Вудилища',1850,'rods.jpg','Легке вудилище для спінінгової риболовлі.'),
                ('Безінерційна котушка 2500','Котушки',1290,'reels.jpg','Універсальна котушка для спінінга.'),
                ('Силіконові приманки Hitomi','Приманки',145,'lures.jpg','Силіконові приманки для окуня та щуки.'),
                ('Набір офсетних гачків','Гачки',95,'hooks.jpg','Гачки для монтажу силіконових приманок.'),
                ('Риболовна сумка','Аксесуари',890,'accessories.jpg','Зручна сумка для зберігання спорядження.'),
                ('Набір воблерів для щуки','Приманки',420,'lures.jpg','Воблери для ловлі хижої риби.')])


def get_all_products():
    with get_connection() as db:
        return [dict(r) for r in db.execute('SELECT * FROM products ORDER BY id')]


def get_product(product_id):
    with get_connection() as db:
        row = db.execute('SELECT * FROM products WHERE id=?', (product_id,)).fetchone()
        return dict(row) if row else None


def add_product(name, category, price, image, description):
    with get_connection() as db:
        db.execute('INSERT INTO products (name,category,price,image,description) VALUES (?,?,?,?,?)',
                   (name,category,price,image,description))


def update_product(product_id, name, category, price, image, description):
    with get_connection() as db:
        return db.execute('''UPDATE products SET name=?,category=?,price=?,image=?,description=? WHERE id=?''',
                          (name,category,price,image,description,product_id)).rowcount > 0


def delete_product(product_id):
    with get_connection() as db:
        if db.execute('SELECT 1 FROM order_items WHERE product_id=? LIMIT 1', (product_id,)).fetchone():
            return False
        return db.execute('DELETE FROM products WHERE id=?', (product_id,)).rowcount > 0


def add_message(name, email, message):
    with get_connection() as db:
        db.execute('INSERT INTO messages (name,email,message) VALUES (?,?,?)', (name,email,message))


def get_all_messages():
    with get_connection() as db:
        return [dict(r) for r in db.execute('SELECT * FROM messages ORDER BY created_at DESC,id DESC')]


def mark_message_read(message_id):
    with get_connection() as db:
        db.execute('UPDATE messages SET is_read=1 WHERE id=?', (message_id,))


def delete_message(message_id):
    with get_connection() as db:
        db.execute('DELETE FROM messages WHERE id=?', (message_id,))


def get_admin(username):
    with get_connection() as db:
        row = db.execute('SELECT * FROM admins WHERE username=?', (username,)).fetchone()
        return dict(row) if row else None


def create_admin(username, password_hash):
    with get_connection() as db:
        db.execute('INSERT INTO admins (username,password_hash) VALUES (?,?)', (username,password_hash))

ORDER_STATUSES = ('Нове','Підтверджено','В обробці','Відправлено','Виконано','Скасовано')


def create_order(customer_name, phone, email, address, comment, cart):
    if not cart:
        raise ValueError('Кошик порожній.')
    with get_connection() as db:
        items, total = [], 0
        for key, value in cart.items():
            product = db.execute('SELECT * FROM products WHERE id=?', (int(key),)).fetchone()
            quantity = int(value)
            if product is None or quantity <= 0:
                raise ValueError('У кошику є недоступний товар.')
            total += product['price'] * quantity
            items.append((product['id'], product['name'], quantity, product['price']))
        cursor = db.execute('''INSERT INTO orders (customer_name,phone,email,address,comment,total)
                               VALUES (?,?,?,?,?,?)''', (customer_name,phone,email,address,comment,total))
        db.executemany('''INSERT INTO order_items (order_id,product_id,product_name,quantity,price)
                          VALUES (?,?,?,?,?)''', [(cursor.lastrowid,*item) for item in items])
        return cursor.lastrowid


def get_all_orders():
    with get_connection() as db:
        return [dict(r) for r in db.execute('SELECT * FROM orders ORDER BY id DESC')]


def get_order_items(order_id):
    with get_connection() as db:
        return [dict(r) for r in db.execute('SELECT * FROM order_items WHERE order_id=? ORDER BY id', (order_id,))]


def update_order_status(order_id, status):
    if status not in ORDER_STATUSES:
        return False
    with get_connection() as db:
        return db.execute('UPDATE orders SET status=? WHERE id=?', (status,order_id)).rowcount > 0
