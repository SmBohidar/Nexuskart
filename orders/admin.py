from django.contrib import admin
from .models import Payment, Order, OrderProduct, OrderTrackingEvent
from .tracking import record_tracking_event
# Register your models here.

class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    readonly_fields = ('payment', 'user', 'product', 'quantity', 'product_price', 'ordered')
    extra = 0

class OrderTrackingEventInline(admin.TabularInline):
    model = OrderTrackingEvent
    readonly_fields = ('created_at',)
    extra = 0

class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'full_name', 'phone', 'email', 'city', 'discount_code', 'discount_amount', 'order_total', 'tax', 'status', 'is_ordered', 'created_at']
    list_editable = ['status']
    list_filter = ['status', 'is_ordered']
    search_fields = ['order_number', 'first_name', 'last_name', 'phone', 'email']
    list_per_page = 20
    inlines = [OrderProductInline, OrderTrackingEventInline]

    def save_model(self, request, obj, form, change):
        previous_status = None
        if change and obj.pk:
            previous_status = Order.objects.filter(pk=obj.pk).values_list('status', flat=True).first()

        super().save_model(request, obj, form, change)

        if obj.is_ordered and (not change or previous_status != obj.status):
            record_tracking_event(obj, obj.status, request.user)
    


admin.site.register(Payment)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderProduct)
admin.site.register(OrderTrackingEvent)
