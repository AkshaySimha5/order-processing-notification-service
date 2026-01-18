from django.contrib import admin
from django.utils.html import format_html

from payments.models import Payment, WebhookEvent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
	list_display = (
		"id",
		"order",
		"amount",
		"status",
		"uro_pay_order_id",
		"reference_number",
		"created_at",
	)
	list_filter = ("status", "created_at")
	search_fields = ("uro_pay_order_id", "reference_number", "order__id", "order__user__username")
	readonly_fields = ("created_at", "updated_at")

	def order(self, obj):
		return format_html("<a href='/admin/orders/order/{}/change/'>Order #{}</a>", obj.order_id, obj.order_id)


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
	list_display = ("webhook_id", "received_at")
	readonly_fields = ("webhook_id", "payload", "received_at")
	search_fields = ("webhook_id",)
	ordering = ("-received_at",)

