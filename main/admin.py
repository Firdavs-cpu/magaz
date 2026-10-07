from django.contrib import admin, messages
from django.db.models import Count
from django.utils.html import format_html
from django.utils import timezone

from .models import Category, Order, OrderItem, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	list_display = ("name", "product_count")
	search_fields = ("name",)

	@admin.display(description="Количество товаров")
	def product_count(self, category):
		return category.product_count

	def get_queryset(self, request):
		return super().get_queryset(request).annotate(product_count=Count("products"))


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ("image_preview", "name", "category", "price", "stock", "is_active")
	list_filter = ("is_active", "category")
	list_editable = ("price", "stock", "is_active")
	search_fields = ("name", "description")
	list_select_related = ("category",)
	readonly_fields = ("image_preview",)

	@admin.display(description="Фото")
	def image_preview(self, product):
		if not product.image_url:
			return "Нет фото"
		return format_html(
			'<img src="{}" alt="{}" style="width: 56px; height: 56px; object-fit: cover;">',
			product.image_url,
			product.name,
		)


class OrderItemInline(admin.TabularInline):
	model = OrderItem
	extra = 0
	can_delete = False
	readonly_fields = ("product", "product_name", "price", "quantity")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ("id", "customer_name", "email", "status", "created_at", "total")
	list_filter = ("status", "created_at")
	search_fields = ("customer_name", "email", "phone")
	readonly_fields = ("created_at", "updated_at", "total")
	inlines = (OrderItemInline,)
	actions = ("mark_paid", "mark_shipped")

	def get_queryset(self, request):
		return super().get_queryset(request).prefetch_related("items")

	@admin.action(description="Отметить выбранные заказы оплаченными")
	def mark_paid(self, request, queryset):
		updated_count = queryset.update(
			status=Order.Status.PAID,
			updated_at=timezone.now(),
		)
		self.message_user(
			request,
			f"Заказов отмечено оплаченными: {updated_count}.",
			messages.SUCCESS,
		)

	@admin.action(description="Отметить выбранные заказы отправленными")
	def mark_shipped(self, request, queryset):
		updated_count = queryset.update(
			status=Order.Status.SHIPPED,
			updated_at=timezone.now(),
		)
		self.message_user(
			request,
			f"Заказов отмечено отправленными: {updated_count}.",
			messages.SUCCESS,
		)
