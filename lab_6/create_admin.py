
from getpass import getpass
from werkzeug.security import generate_password_hash

from database import create_admin, get_admin

username = input("Логін адміністратора: ").strip()

if not username:
    print("Логін не може бути порожнім.")
    raise SystemExit

if get_admin(username):
    print("Адміністратор із таким логіном уже існує.")
    raise SystemExit

password = getpass("Пароль: ")
confirmation = getpass("Повторіть пароль: ")

if len(password) < 4:
    print("Пароль повинен містити щонайменше 4 символи.")
    raise SystemExit

if password != confirmation:
    print("Паролі не збігаються.")
    raise SystemExit

password_hash = generate_password_hash(password)

create_admin(username, password_hash)

print("Адміністратора успішно створено!")
