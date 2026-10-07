from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import CheckoutForm
from .models import Category, Order, OrderItem, Product


def product_list(request):
	products = Product.objects.filter(is_active=True).select_related("category")
	categories = Category.objects.all()
	selected_category = request.GET.get("category", "")
	search_query = request.GET.get("q", "").strip()

	if selected_category:
		if selected_category.isdigit():
			products = products.filter(category_id=int(selected_category))
		else:
			products = products.none()
	if search_query:
		products = products.filter(
			Q(name__icontains=search_query)
			| Q(description__icontains=search_query)
			| Q(category__name__icontains=search_query)
		)

	return render(request, "main/product_list.html", {
		"products": products,
		"categories": categories,
		"selected_category": selected_category,
		"search_query": search_query,
	})


def product_detail(request, product_id):
	product = get_object_or_404(
		Product.objects.select_related("category"),
		pk=product_id,
		is_active=True,
	)
	return render(request, "main/product_detail.html", {"product": product})


def _cart_items(request):
	cart = request.session.get("cart", {})
	products = Product.objects.filter(pk__in=cart.keys(), is_active=True)
	items = []
	cleaned_cart = {}

	for product in products:
		try:
			quantity = int(cart.get(str(product.pk), 0))
		except (TypeError, ValueError):
			continue
		quantity = min(max(quantity, 0), product.stock)
		if quantity:
			cleaned_cart[str(product.pk)] = quantity
			items.append({
				"product": product,
				"quantity": quantity,
				"subtotal": product.price * quantity,
			})

	if cleaned_cart != cart:
		request.session["cart"] = cleaned_cart

	total = sum((item["subtotal"] for item in items), start=0)
	return items, total


def cart_detail(request):
	items, total = _cart_items(request)
	return render(request, "main/cart.html", {"items": items, "total": total})


@require_POST
def cart_add(request, product_id):
	product = get_object_or_404(Product, pk=product_id, is_active=True)
	cart = request.session.get("cart", {})
	current_quantity = int(cart.get(str(product.pk), 0))

	if product.stock == 0:
		messages.error(request, "Этого товара сейчас нет в наличии.")
	else:
		cart[str(product.pk)] = min(current_quantity + 1, product.stock)
		request.session["cart"] = cart
		messages.success(request, "Товар добавлен в корзину.")

	next_url = request.POST.get("next", "")
	if url_has_allowed_host_and_scheme(
		next_url,
		allowed_hosts={request.get_host()},
		require_https=request.is_secure(),
	):
		return redirect(next_url)
	return redirect("main:cart")


@require_POST
def cart_update(request, product_id):
	cart = request.session.get("cart", {})
	product = Product.objects.filter(pk=product_id, is_active=True).first()

	try:
		quantity = int(request.POST.get("quantity", 0))
	except (TypeError, ValueError):
		quantity = 0

	if not product or quantity <= 0:
		cart.pop(str(product_id), None)
	else:
		cart[str(product_id)] = min(quantity, product.stock)
		if cart[str(product_id)] == 0:
			cart.pop(str(product_id))

	request.session["cart"] = cart
	return redirect("main:cart")


def checkout(request):
	items, total = _cart_items(request)
	if not items:
		messages.info(request, "Корзина пуста.")
		return redirect("main:cart")

	form = CheckoutForm(request.POST or None)
	if request.method == "POST" and form.is_valid():
		cart = request.session.get("cart", {})
		quantities = {int(product_id): int(quantity) for product_id, quantity in cart.items()}

		with transaction.atomic():
			products = Product.objects.select_for_update().filter(
				pk__in=quantities,
				is_active=True,
			)
			products_by_id = {product.pk: product for product in products}
			unavailable = [
				product_id
				for product_id, quantity in quantities.items()
				if product_id not in products_by_id
				or products_by_id[product_id].stock < quantity
			]

			if unavailable:
				form.add_error(None, "Некоторых товаров больше нет в нужном количестве. Обновите корзину.")
			else:
				order = form.save(commit=False)
				if request.user.is_authenticated:
					order.user = request.user
				order.save()

				order_items = []
				for product_id, quantity in quantities.items():
					product = products_by_id[product_id]
					order_items.append(OrderItem(
						order=order,
						product=product,
						product_name=product.name,
						price=product.price,
						quantity=quantity,
					))
					product.stock -= quantity
					product.save(update_fields=("stock", "updated_at"))

				OrderItem.objects.bulk_create(order_items)
				request.session["cart"] = {}
				request.session["confirmation_order_id"] = order.pk
				return redirect("main:order_success", order_id=order.pk)

	return render(request, "main/checkout.html", {
		"form": form,
		"items": items,
		"total": total,
	})


def order_success(request, order_id):
	if request.user.is_authenticated:
		order = get_object_or_404(
			Order.objects.prefetch_related("items"),
			pk=order_id,
			user=request.user,
		)
	else:
		if request.session.get("confirmation_order_id") != order_id:
			raise Http404
		order = get_object_or_404(
			Order.objects.prefetch_related("items"),
			pk=order_id,
			user__isnull=True,
		)
	return render(request, "main/order_success.html", {"order": order})
