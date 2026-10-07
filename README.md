# Интернет-магазин «Лавка»

Небольшой магазин на Django: каталог с поиском и сортировкой, корзина на сессиях, гостевое оформление заказа и административная панель.

## Запуск локально

Нужен Python 3.14 или совместимая версия.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Откройте `http://127.0.0.1:8000/`. Для управления каталогом и заказами войдите под созданным администратором на `/admin/`, затем добавьте категории и товары. Фото товара задаётся URL в поле «Ссылка на изображение».

## Проверки

```bash
python manage.py check
python manage.py test main
python manage.py makemigrations --check --dry-run
```

## Примечания

- По умолчанию используется SQLite; база `db.sqlite3` подходит для локальной разработки.
- Письма выводятся в консоль, реальная отправка email не настроена.
- Онлайн-оплата не подключена.
- Перед публикацией замените `SECRET_KEY`, отключите `DEBUG` и настройте `ALLOWED_HOSTS` и production-базу данных.