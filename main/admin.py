from django.contrib import admin

from .models import Category, Order, OrderItem, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ("name", "category", "price", "stock", "is_active")
	list_filter = ("is_active", "category")
	list_editable = ("price", "stock", "is_active")
	search_fields = ("name", "description")
	list_select_related = ("category",)


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
