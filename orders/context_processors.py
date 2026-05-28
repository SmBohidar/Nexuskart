from .discounts import promotion_offer


def discount_offer(request):
    return {
        "promotion_offer": promotion_offer(request.user),
    }
