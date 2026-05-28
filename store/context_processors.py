from .models import WishlistItem

def wishlist_data(request):
    wishlist_count = 0
    wishlist_product_ids = []
    
    if request.user.is_authenticated:
        items = WishlistItem.objects.filter(user=request.user)
        wishlist_count = items.count()
        wishlist_product_ids = list(items.values_list('product_id', flat=True))
        
    return {
        'wishlist_count': wishlist_count,
        'wishlist_product_ids': wishlist_product_ids,
    }
