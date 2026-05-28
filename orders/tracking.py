from .models import OrderTrackingEvent


TRACKING_COPY = {
    'New': ('Order placed', 'We received your order.'),
    'Accepted': ('Accepted', 'Your order has been confirmed.'),
    'Shipped': ('Shipped', 'Your package is on the way.'),
    'Delivered': ('Delivered', "Enjoy. It's yours."),
    'Completed': ('Delivered', "Enjoy. It's yours."),
    'Cancelled': ('Order cancelled', 'This order was cancelled.'),
}


def tracking_copy(status):
    return TRACKING_COPY.get(status, (status, 'Order status updated.'))


def record_tracking_event(order, status=None, user=None):
    status = status or order.status
    title, description = tracking_copy(status)
    event, created = OrderTrackingEvent.objects.get_or_create(
        order=order,
        status=status,
        defaults={
            'title': title,
            'description': description,
            'created_by': user,
        },
    )
    return event
