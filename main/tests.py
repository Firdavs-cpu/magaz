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

	def test_catalog_search_matches_product_description(self):
		self.product.description = "Издание с картой горных маршрутов"
		self.product.save(update_fields=("description",))

		response = self.client.get(reverse("main:product_list"), {"q": "горных"})

		self.assertEqual(list(response.context["products"]), [self.product])

	def test_catalog_search_matches_category_name(self):
		response = self.client.get(reverse("main:product_list"), {"q": "Книги"})

		self.assertEqual(list(response.context["products"]), [self.product])

	def test_invalid_category_filter_does_not_show_all_products(self):
		response = self.client.get(
			reverse("main:product_list"),
			{"category": "unknown"},
		)

		self.assertEqual(list(response.context["products"]), [])

	def test_catalog_paginates_products(self):
		Product.objects.bulk_create([
			Product(
				category=self.category,
				name=f"Книга {index}",
				price="100.00",
				stock=1,
			)
			for index in range(12)
		])

		response = self.client.get(reverse("main:product_list"), {"page": "2"})

		self.assertEqual(response.context["page_obj"].number, 2)
		self.assertEqual(response.context["page_obj"].paginator.count, 13)
		self.assertEqual(len(response.context["products"]), 1)

	def test_catalog_can_sort_by_price(self):
		cheaper_product = Product.objects.create(
			category=self.category,
			name="Карманный атлас",
			price="500.00",
			stock=2,
		)

		response = self.client.get(
			reverse("main:product_list"),
			{"sort": "price_asc"},
		)

		self.assertEqual(response.context["products"][0], cheaper_product)

	def test_catalog_hides_inactive_products(self):
		self.product.is_active = False
		self.product.save(update_fields=("is_active",))

		response = self.client.get(reverse("main:product_list"))

		self.assertNotContains(response, "Атлас")
		self.assertEqual(list(response.context["products"]), [])

	def test_inactive_product_page_returns_not_found(self):
		self.product.is_active = False
		self.product.save(update_fields=("is_active",))

		response = self.client.get(
			reverse("main:product_detail", args=[self.product.pk]),
		)

		self.assertEqual(response.status_code, 404)

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

	def test_checkout_requires_confirmation_after_stock_changes(self):
		session = self.client.session
		session["cart"] = {str(self.product.pk): 4}
		session.save()
		self.product.stock = 2
		self.product.save(update_fields=("stock",))

		response = self.client.post(reverse("main:checkout"), {
			"customer_name": "Анна",
			"email": "anna@example.com",
			"shipping_address": "Москва",
		})

		self.assertRedirects(response, reverse("main:cart"))
		self.assertEqual(Order.objects.count(), 0)
		self.assertEqual(self.client.session["cart"], {str(self.product.pk): 2})

	def test_checkout_rejects_invalid_email_without_creating_order(self):
		self.client.post(reverse("main:cart_add", args=[self.product.pk]))

		response = self.client.post(reverse("main:checkout"), {
			"customer_name": "Анна",
			"email": "not-an-email",
			"phone": "",
			"shipping_address": "Москва",
		})

		self.assertEqual(response.status_code, 200)
		self.assertIn("email", response.context["form"].errors)
		self.assertEqual(Order.objects.count(), 0)

	def test_add_to_cart_does_not_redirect_to_external_url(self):
		response = self.client.post(
			reverse("main:cart_add", args=[self.product.pk]),
			{"next": "https://example.com"},
		)

		self.assertRedirects(response, reverse("main:cart"))

	def test_add_to_cart_does_not_exceed_stock(self):
		session = self.client.session
		session["cart"] = {str(self.product.pk): self.product.stock}
		session.save()

		response = self.client.post(reverse("main:cart_add", args=[self.product.pk]))

		self.assertRedirects(response, reverse("main:cart"))
		self.assertEqual(
			self.client.session["cart"][str(self.product.pk)],
			self.product.stock,
		)
		self.assertEqual(len(list(response.wsgi_request._messages)), 1)

	def test_cart_update_caps_quantity_at_stock(self):
		response = self.client.post(
			reverse("main:cart_update", args=[self.product.pk]),
			{"quantity": "100"},
		)

		self.assertRedirects(response, reverse("main:cart"))
		self.assertEqual(
			self.client.session["cart"][str(self.product.pk)],
			self.product.stock,
		)

	def test_cart_update_zero_removes_product(self):
		session = self.client.session
		session["cart"] = {str(self.product.pk): 2}
		session.save()

		response = self.client.post(
			reverse("main:cart_update", args=[self.product.pk]),
			{"quantity": "0"},
		)

		self.assertRedirects(response, reverse("main:cart"))
		self.assertEqual(self.client.session["cart"], {})

	def test_navigation_shows_cart_quantity(self):
		session = self.client.session
		session["cart"] = {str(self.product.pk): 3}
		session.save()

		response = self.client.get(reverse("main:product_list"))

		self.assertContains(response, '<span class="cart-count">3</span>', html=True)

	def test_cart_summary_counts_units(self):
		second_product = Product.objects.create(
			category=self.category,
			name="Глобус",
			price="700.00",
			stock=4,
		)
		session = self.client.session
		session["cart"] = {
			str(self.product.pk): 2,
			str(second_product.pk): 1,
		}
		session.save()

		response = self.client.get(reverse("main:cart"))

		self.assertContains(response, "3 шт.")

	def test_cart_recovers_from_invalid_session_structure(self):
		session = self.client.session
		session["cart"] = [str(self.product.pk)]
		session.save()

		response = self.client.get(reverse("main:cart"))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context["items"], [])
		self.assertEqual(self.client.session["cart"], {})

	def test_cart_discards_invalid_product_ids_and_quantities(self):
		session = self.client.session
		session["cart"] = {"not-an-id": 1, str(self.product.pk): "many"}
		session.save()

		response = self.client.get(reverse("main:cart"))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context["items"], [])
		self.assertEqual(self.client.session["cart"], {})

	def test_order_confirmation_requires_the_checkout_session(self):
		order = Order.objects.create(
			customer_name="Анна",
			email="anna@example.com",
			shipping_address="Москва",
		)

		response = self.client.get(reverse("main:order_success", args=[order.pk]))

		self.assertEqual(response.status_code, 404)
