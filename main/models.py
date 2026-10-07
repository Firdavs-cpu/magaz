from decimal import Decimal

from django.conf import settings
from django.db import models


class Category(models.Model):
	name = models.CharField("Название", max_length=100, unique=True)
	description = models.TextField("Описание", blank=True)

	class Meta:
		verbose_name = "Категория"
		verbose_name_plural = "Категории"
		ordering = ["name"]

	def __str__(self):
		return self.name


class Product(models.Model):
	category = models.ForeignKey(
		Category,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="products",
		verbose_name="Категория",
	)
	name = models.CharField("Название", max_length=200)
	description = models.TextField("Описание", blank=True)
	price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
	stock = models.PositiveIntegerField("Остаток на складе", default=0)
	image_url = models.URLField("Ссылка на изображение", blank=True)
	is_active = models.BooleanField("Опубликован", default=True)
	created_at = models.DateTimeField("Создан", auto_now_add=True)
	updated_at = models.DateTimeField("Обновлён", auto_now=True)

	class Meta:
		verbose_name = "Товар"
		verbose_name_plural = "Товары"
		ordering = ["name"]
		constraints = [
			models.CheckConstraint(
				condition=models.Q(price__gte=0),
				name="product_price_nonnegative",
			),
		]

	def __str__(self):
		return self.name


class Order(models.Model):
	class Status(models.TextChoices):
		PENDING = "pending", "Ожидает оплаты"
		PAID = "paid", "Оплачен"
		SHIPPED = "shipped", "Отправлен"
		DELIVERED = "delivered", "Доставлен"
		CANCELLED = "cancelled", "Отменён"

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="orders",
		verbose_name="Покупатель",
	)
	customer_name = models.CharField("Имя покупателя", max_length=200)
	email = models.EmailField("Электронная почта")
	phone = models.CharField("Телефон", max_length=30, blank=True)
	shipping_address = models.TextField("Адрес доставки")
	status = models.CharField(
		"Статус",
		max_length=20,
		choices=Status.choices,
		default=Status.PENDING,
	)
	created_at = models.DateTimeField("Создан", auto_now_add=True)
	updated_at = models.DateTimeField("Обновлён", auto_now=True)

	class Meta:
		verbose_name = "Заказ"
		verbose_name_plural = "Заказы"
		ordering = ["-created_at"]

	def __str__(self):
		return f"Заказ №{self.pk}"

	@property
	def total(self):
		return sum((item.subtotal for item in self.items.all()), Decimal("0.00"))


class OrderItem(models.Model):
	order = models.ForeignKey(
		Order,
		on_delete=models.CASCADE,
		related_name="items",
		verbose_name="Заказ",
	)
	product = models.ForeignKey(
		Product,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="order_items",
		verbose_name="Товар",
	)
	product_name = models.CharField("Название товара", max_length=200)
	price = models.DecimalField("Цена на момент заказа", max_digits=10, decimal_places=2)
	quantity = models.PositiveIntegerField("Количество")

	class Meta:
		verbose_name = "Позиция заказа"
		verbose_name_plural = "Позиции заказа"
		constraints = [
			models.CheckConstraint(
				condition=models.Q(quantity__gt=0),
				name="order_item_quantity_positive",
			),
			models.CheckConstraint(
				condition=models.Q(price__gte=0),
				name="order_item_price_nonnegative",
			),
		]

	def __str__(self):
		return f"{self.product_name} × {self.quantity}"

	@property
	def subtotal(self):
		return self.price * self.quantity
