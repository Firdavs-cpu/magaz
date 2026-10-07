from django.test import TestCase
from django.urls import reverse

from .models import Category, Order, OrderItem, Product


class StorefrontTests(TestCase):
	def setUp(self):
		self.category = Category.objects.create(name="Книги")
		self.product = Product.objects.create(
			category=self.category,
			name="Атлас",
			price="1200.00",
			stock=5,
		)

	def test_catalog_shows_active_products(self):
		response = self.client.get(reverse("main:product_list"))

		self.assertContains(response, "Атлас")
		self.assertEqual(list(response.context["products"]), [self.product])

	def test_checkout_creates_order_and_decrements_stock(self):
		self.client.post(reverse("main:cart_add", args=[self.product.pk]))

		response = self.client.post(reverse("main:checkout"), {
			"customer_name": "Анна",
			"email": "anna@example.com",
			"phone": "+7 900 000-00-00",
			"shipping_address": "Москва, Тверская, 1",
		})

		order = Order.objects.get()
		item = OrderItem.objects.get(order=order)
		self.product.refresh_from_db()

		self.assertRedirects(
			response,
			reverse("main:order_success", args=[order.pk]),
		)
		self.assertEqual(item.quantity, 1)
		self.assertEqual(item.price, self.product.price)
		self.assertEqual(order.total, item.price)
		self.assertEqual(self.product.stock, 4)
		self.assertEqual(self.client.session["cart"], {})

	def test_add_to_cart_does_not_redirect_to_external_url(self):
		response = self.client.post(
			reverse("main:cart_add", args=[self.product.pk]),
			{"next": "https://example.com"},
		)

		self.assertRedirects(response, reverse("main:cart"))

	def test_order_confirmation_requires_the_checkout_session(self):
		order = Order.objects.create(
			customer_name="Анна",
			email="anna@example.com",
			shipping_address="Москва",
		)

		response = self.client.get(reverse("main:order_success", args=[order.pk]))

		self.assertEqual(response.status_code, 404)
